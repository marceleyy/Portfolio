"""API de détection de comportements suspects (YOLOv8 + Flask).

Les secrets ne sont jamais écrits dans le code : ils sont lus dans les variables
d'environnement suivantes.

    MODEL_PATH           chemin vers le modèle entraîné (défaut : best.pt)
    API_SECRET_CODE      code attendu dans l'en-tête Secret-Code
    TWILIO_ACCOUNT_SID   identifiant du compte Twilio      (optionnel)
    TWILIO_AUTH_TOKEN    jeton du compte Twilio            (optionnel)
    TWILIO_FROM_NUMBER   numéro d'envoi Twilio             (optionnel)
    ALERT_TO_NUMBER      numéro qui reçoit les alertes     (optionnel)
"""
import os

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from ultralytics import YOLO

app = Flask(__name__)
model = YOLO(os.environ.get("MODEL_PATH", "best.pt"))

SECRET_CODE = os.environ.get("API_SECRET_CODE")
ALERT_CLASS = "shoplifting"
ALERT_THRESHOLD = 0.5

# Client Twilio créé uniquement si toutes les variables sont présentes
twilio_client = None
if all(os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                                    "TWILIO_FROM_NUMBER", "ALERT_TO_NUMBER")):
    from twilio.rest import Client
    twilio_client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.route("/analyze_frame", methods=["POST"])
def analyze_frame():
    # Contrôle d'accès
    if not SECRET_CODE or request.headers.get("Secret-Code") != SECRET_CODE:
        return jsonify({"error": "Unauthorized"}), 401

    # Lecture et décodage de l'image
    if "frame" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    buffer = np.frombuffer(request.files["frame"].read(), np.uint8)
    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "Invalid image format"}), 400

    # Inférence YOLOv8
    results = model(frame)
    boxes = results[0].boxes.data.cpu().numpy() if len(results[0].boxes) > 0 else []

    detections = []
    alert_triggered = False
    for x1, y1, x2, y2, confidence, class_id in boxes:
        class_name = model.names[int(class_id)]
        detections.append({
            "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
            "confidence": float(confidence),
            "class": class_name,
        })
        if class_name == ALERT_CLASS and confidence > ALERT_THRESHOLD:
            alert_triggered = True

    if alert_triggered and twilio_client:
        try:
            twilio_client.messages.create(
                body="Alerte : comportement suspect détecté (shoplifting). Vérifiez immédiatement.",
                from_=os.environ["TWILIO_FROM_NUMBER"],
                to=os.environ["ALERT_TO_NUMBER"],
            )
        except Exception as exc:  # l'échec d'envoi ne doit pas bloquer la détection
            app.logger.error("Envoi de l'alerte impossible : %s", exc)

    return jsonify({"detections": detections, "alert_triggered": alert_triggered}), 200


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
