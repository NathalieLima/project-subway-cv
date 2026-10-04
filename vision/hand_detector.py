"""Deteccao de duas maos e reconhecimento de gestos com MediaPipe Tasks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from config import (
    HAND_HANDEDNESS_MIN_SCORE,
    HAND_SWAP_SIDES,
    MIN_DETECTION_CONFIDENCE,
    MIN_PRESENCE_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)


class HandDetector:
    """Reconhece gestos e landmarks de ate duas maos em modo VIDEO."""

    def __init__(self, model_path: Path) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo de gestos nao encontrado: {model_path}. "
                "Execute: python download_models.py"
            )

        model_bytes = model_path.read_bytes()
        if not model_bytes:
            raise ValueError(f"Modelo de gestos vazio ou invalido: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_buffer=model_bytes)
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
        )
        self._recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

    @staticmethod
    def _swap_side(side: str) -> str:
        if not HAND_SWAP_SIDES:
            return side
        if side == "LEFT":
            return "RIGHT"
        if side == "RIGHT":
            return "LEFT"
        return side

    def detect(self, frame_bgr: Any, timestamp_ms: int) -> dict[str, Any]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._recognizer.recognize_for_video(image, timestamp_ms)

        hands: list[dict[str, Any]] = []
        hand_landmarks = result.hand_landmarks or []
        handedness_list = result.handedness or []
        gestures_list = result.gestures or []
        # Para o coracao precisamos dos landmarks mesmo quando o classificador
        # de gestos nao devolve uma categoria util para aquela mao.
        count = min(len(hand_landmarks), len(handedness_list))

        for index in range(count):
            side = "UNKNOWN"
            side_score = 0.0
            if handedness_list[index]:
                handedness = handedness_list[index][0]
                side = str(handedness.category_name or "UNKNOWN").upper()
                side_score = float(handedness.score or 0.0)
                if side_score < HAND_HANDEDNESS_MIN_SCORE:
                    side = "UNKNOWN"
                side = self._swap_side(side)

            gesture = "None"
            gesture_score = 0.0
            if index < len(gestures_list) and gestures_list[index]:
                category = gestures_list[index][0]
                gesture = str(category.category_name or "None")
                gesture_score = float(category.score or 0.0)

            hands.append(
                {
                    "side": side,
                    "side_score": side_score,
                    "gesture": gesture,
                    "gesture_score": gesture_score,
                    "landmarks": hand_landmarks[index],
                }
            )

        return {"hands": hands}

    def close(self) -> None:
        self._recognizer.close()
