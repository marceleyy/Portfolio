// Capture la webcam, envoie une image toutes les 3 secondes à l'API Flask
// et dessine les détections YOLOv8 sur un canvas superposé à la vidéo.

const API_URL = '/analyze_frame';
const SECRET_CODE = 'a-remplacer';   // même valeur que API_SECRET_CODE côté serveur
const INTERVAL_MS = 3000;

const video = document.getElementById('cameraFeed');
const canvas = document.getElementById('overlay');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const ctx = canvas.getContext('2d');

function drawDetections(detections) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2;
    ctx.font = '16px Arial';
    detections.forEach(det => {
        const color = det.class === 'shoplifting' ? 'red' : 'lime';
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.strokeRect(det.x1, det.y1, det.x2 - det.x1, det.y2 - det.y1);
        ctx.fillText(`${det.class} (${(det.confidence * 100).toFixed(1)} %)`, det.x1, det.y1 - 5);
    });
}

function analyzeFrame() {
    // Image capturée sur un canvas hors écran pour ne pas effacer l'overlay
    const capture = document.createElement('canvas');
    capture.width = video.videoWidth;
    capture.height = video.videoHeight;
    capture.getContext('2d').drawImage(video, 0, 0);

    loadingDiv.style.display = 'block';
    capture.toBlob(blob => {
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');

        fetch(API_URL, { method: 'POST', headers: { 'Secret-Code': SECRET_CODE }, body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                drawDetections(data.detections);
                resultsDiv.textContent = data.alert_triggered
                    ? 'Alerte : comportement suspect détecté'
                    : `${data.detections.length} détection(s)`;
            })
            .catch(err => console.error(err))
            .finally(() => { loadingDiv.style.display = 'none'; });
    }, 'image/jpeg', 0.5);
}

navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
        video.addEventListener('loadedmetadata', () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            setInterval(analyzeFrame, INTERVAL_MS);
        });
    })
    .catch(err => console.error("Erreur d'accès à la caméra :", err));
