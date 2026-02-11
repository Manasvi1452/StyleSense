import cv2
import numpy as np

def detect_skin_tone(image_path):
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return "Could not read image"

    # Convert to grayscale for face detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Load face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return "No face detected"

    # Take first detected face
    (x, y, w, h) = faces[0]

    # Extract central cheek region
    face = image[y:y+h, x:x+w]
    h_face, w_face, _ = face.shape

    cheek_region = face[
        int(h_face*0.4):int(h_face*0.6),
        int(w_face*0.3):int(w_face*0.7)
    ]

    # Calculate average color
    avg_color = np.mean(cheek_region, axis=(0,1))
    b, g, r = avg_color

    brightness = (r + g + b) / 3

    # Simple classification
    if brightness > 200:
        tone = "Fair"
    elif brightness > 170:
        tone = "Light"
    elif brightness > 140:
        tone = "Medium"
    elif brightness > 110:
        tone = "Tan"
    else:
        tone = "Deep"

    return {
        "tone": tone,
        "rgb": (int(r), int(g), int(b))
    }
