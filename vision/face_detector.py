"""Wrapper do MediaPipe Face Landmarker."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from config import (
    MIN_DETECTION_CONFIDENCE,
    MIN_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)


class FaceDetector:
    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo Face Landmarker nao encontrado: {model_path}. "
                "Baixe face_landmarker.task e coloque em models/."
            )

        model_bytes = model_path.read_bytes()
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_face_presence_confidence=MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame_bgr: Any, timestamp_ms: int) -> dict[str, Any] | None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return None

        matrix = None
        if result.facial_transformation_matrixes:
            matrix = result.facial_transformation_matrixes[0]

        return {
            "landmarks": result.face_landmarks[0],
            "matrix": matrix,
        }

    def close(self) -> None:
        self._landmarker.close()
