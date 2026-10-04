"""Classificador do modo CORPO."""
from __future__ import annotations

import math
from typing import Any

from config import (
    CROUCH_DEEP_HIP_THRESHOLD,
    CROUCH_HIP_THRESHOLD,
    CROUCH_KNEE_ANGLE,
    JUMP_THRESHOLD,
    LATERAL_THRESHOLD,
    POSE_MIN_VISIBILITY,
)
from states import Estado


class BodyClassifier:
    # Indices do MediaPipe Pose.
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}

    @staticmethod
    def _ok(lm: Any) -> bool:
        visibility = getattr(lm, "visibility", 1.0)
        presence = getattr(lm, "presence", 1.0)
        return visibility >= POSE_MIN_VISIBILITY and presence >= 0.3

    @staticmethod
    def _mid(a: Any, b: Any) -> tuple[float, float]:
        return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _angle(a: Any, b: Any, c: Any) -> float:
        ba = (a.x - b.x, a.y - b.y)
        bc = (c.x - b.x, c.y - b.y)
        denom = math.hypot(*ba) * math.hypot(*bc)
        if denom <= 1e-8:
            return 180.0
        cos_angle = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1]) / denom))
        return math.degrees(math.acos(cos_angle))

    def extrair_features(self, landmarks: list[Any] | None) -> dict[str, float] | None:
        if not landmarks or len(landmarks) <= self.RIGHT_ANKLE:
            return None

        idxs = [
            self.LEFT_SHOULDER,
            self.RIGHT_SHOULDER,
            self.LEFT_HIP,
            self.RIGHT_HIP,
            self.LEFT_KNEE,
            self.RIGHT_KNEE,
            self.LEFT_ANKLE,
            self.RIGHT_ANKLE,
        ]
        if not all(self._ok(landmarks[i]) for i in idxs):
            return None

        ls, rs = landmarks[self.LEFT_SHOULDER], landmarks[self.RIGHT_SHOULDER]
        lh, rh = landmarks[self.LEFT_HIP], landmarks[self.RIGHT_HIP]
        lk, rk = landmarks[self.LEFT_KNEE], landmarks[self.RIGHT_KNEE]
        la, ra = landmarks[self.LEFT_ANKLE], landmarks[self.RIGHT_ANKLE]

        shoulder = self._mid(ls, rs)
        hip = self._mid(lh, rh)
        ankle = self._mid(la, ra)
        torso = ((shoulder[0] + hip[0]) / 2.0, (shoulder[1] + hip[1]) / 2.0)

        shoulder_width = self._distance((ls.x, ls.y), (rs.x, rs.y))
        torso_height = self._distance(shoulder, hip)
        if shoulder_width <= 1e-5 or torso_height <= 1e-5:
            return None

        return {
            "torso_x": torso[0],
            "hip_x": hip[0],
            "hip_y": hip[1],
            "ankle_y": ankle[1],
            "shoulder_width": shoulder_width,
            "torso_height": torso_height,
            "left_knee_angle": self._angle(lh, lk, la),
            "right_knee_angle": self._angle(rh, rk, ra),
        }

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        self.baseline = dict(baseline)
        self.debug = {}

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        del timestamp_s
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        b = self.baseline
        width = max(b["shoulder_width"], 1e-5)
        torso_h = max(b["torso_height"], 1e-5)

        lateral = (features["torso_x"] - b["torso_x"]) / width
        hip_lift = (b["hip_y"] - features["hip_y"]) / torso_h
        ankle_lift = (b["ankle_y"] - features["ankle_y"]) / torso_h
        jump_score = hip_lift * 0.70 + ankle_lift * 0.30
        hip_drop = (features["hip_y"] - b["hip_y"]) / torso_h
        knee_angle = (features["left_knee_angle"] + features["right_knee_angle"]) / 2.0

        crouch_by_posture = (
            hip_drop >= CROUCH_HIP_THRESHOLD
            and knee_angle <= CROUCH_KNEE_ANGLE
        )
        # Se o quadril desceu muito, aceitamos o agachamento mesmo que o angulo
        # estimado dos joelhos esteja ruidoso ou parcialmente ocluido.
        crouch_by_depth = hip_drop >= CROUCH_DEEP_HIP_THRESHOLD

        self.debug = {
            "lateral": lateral,
            "jump_score": jump_score,
            "hip_drop": hip_drop,
            "knee_angle": knee_angle,
            "crouch_by_posture": 1.0 if crouch_by_posture else 0.0,
            "crouch_by_depth": 1.0 if crouch_by_depth else 0.0,
        }

        # Movimento vertical tem prioridade, mas nao altera a faixa interna do jogo.
        if jump_score >= JUMP_THRESHOLD:
            return Estado.PULO
        if crouch_by_posture or crouch_by_depth:
            return Estado.AGACHADO

        if lateral <= -LATERAL_THRESHOLD:
            return Estado.ESQUERDA
        if lateral >= LATERAL_THRESHOLD:
            return Estado.DIREITA
        return Estado.CENTRO

    def limites_guias(self) -> dict[str, float] | None:
        if self.baseline is None:
            return None
        return {
            "left_x": self.baseline["torso_x"] - self.baseline["shoulder_width"] * LATERAL_THRESHOLD,
            "right_x": self.baseline["torso_x"] + self.baseline["shoulder_width"] * LATERAL_THRESHOLD,
        }
