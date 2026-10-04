"""Classificador do modo ROSTO usando yaw e pitch da matriz facial 3D."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from config import (
    FACE_ANGLE_SMOOTHING_ALPHA,
    FACE_PITCH_DIRECTION,
    FACE_PITCH_THRESHOLD_DEG,
    FACE_YAW_DIRECTION,
    FACE_YAW_THRESHOLD_DEG,
)
from states import Estado


class FaceClassifier:
    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}
        self._smooth_yaw: float | None = None
        self._smooth_pitch: float | None = None

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}
        self._smooth_yaw = None
        self._smooth_pitch = None

    def reset_temporal(self) -> None:
        self._smooth_yaw = None
        self._smooth_pitch = None
        self.debug = {}

    @staticmethod
    def _rotation_to_angles(matrix: np.ndarray) -> tuple[float, float]:
        """Converte a rotacao da matriz facial em yaw(Y) e pitch(X), em graus.

        A convencao de sinal pode variar com camera/espelhamento, por isso o
        resultado ainda passa por FACE_YAW_DIRECTION/FACE_PITCH_DIRECTION.
        """
        r = np.asarray(matrix, dtype=float)
        if r.shape[0] < 3 or r.shape[1] < 3:
            raise ValueError("Matriz facial invalida")
        r = r[:3, :3]

        pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
        yaw = math.degrees(math.atan2(-r[2, 0], math.hypot(r[2, 1], r[2, 2])))
        return yaw, pitch

    def extrair_features(self, face_data: dict[str, Any] | None) -> dict[str, float] | None:
        if not face_data:
            return None
        matrix = face_data.get("matrix")
        if matrix is None:
            return None
        try:
            yaw, pitch = self._rotation_to_angles(np.asarray(matrix))
        except (ValueError, TypeError, IndexError):
            return None
        return {"yaw": yaw, "pitch": pitch}

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        self.baseline = dict(baseline)
        self.reset_temporal()

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        del timestamp_s
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        raw_yaw = (features["yaw"] - self.baseline["yaw"]) * FACE_YAW_DIRECTION
        raw_pitch = (features["pitch"] - self.baseline["pitch"]) * FACE_PITCH_DIRECTION

        alpha = FACE_ANGLE_SMOOTHING_ALPHA
        if self._smooth_yaw is None:
            self._smooth_yaw = raw_yaw
            self._smooth_pitch = raw_pitch
        else:
            self._smooth_yaw = alpha * raw_yaw + (1.0 - alpha) * self._smooth_yaw
            self._smooth_pitch = alpha * raw_pitch + (1.0 - alpha) * self._smooth_pitch

        yaw = float(self._smooth_yaw)
        pitch = float(self._smooth_pitch)
        self.debug = {
            "raw_yaw": raw_yaw,
            "raw_pitch": raw_pitch,
            "yaw": yaw,
            "pitch": pitch,
        }

        # Vertical primeiro para que olhar para cima/baixo seja inequívoco.
        if pitch >= FACE_PITCH_THRESHOLD_DEG:
            return Estado.PULO
        if pitch <= -FACE_PITCH_THRESHOLD_DEG:
            return Estado.AGACHADO
        if yaw <= -FACE_YAW_THRESHOLD_DEG:
            return Estado.ESQUERDA
        if yaw >= FACE_YAW_THRESHOLD_DEG:
            return Estado.DIREITA
        return Estado.CENTRO
