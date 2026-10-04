"""Baixa os modelos oficiais do MediaPipe usados pelo projeto."""
from pathlib import Path
from urllib.request import urlretrieve

MODELS = {
    "pose_landmarker_lite.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
    "gesture_recognizer.task": (
        "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
        "gesture_recognizer/float16/1/gesture_recognizer.task"
    ),
}


def main() -> None:
    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(exist_ok=True)

    for filename, url in MODELS.items():
        destination = models_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            print(f"[OK] Ja existe: {destination}")
            continue
        print(f"Baixando {filename}...")
        urlretrieve(url, destination)
        print(f"[OK] Salvo em {destination}")


if __name__ == "__main__":
    main()
