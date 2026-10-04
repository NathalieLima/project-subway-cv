"""Classificacao do modo MAOS a partir dos gestos e landmarks do MediaPipe."""
from __future__ import annotations

import math
from typing import Any

from config import (
    HAND_GESTURE_MIN_SCORE,
    HAND_HEART_CONTACT_RATIO,
    HAND_HEART_MIN_OPENING_RATIO,
    HAND_HEART_MIN_VERTICAL_GAP_RATIO,
)
from states import Estado


class HandClassifier:
    """Converte combinacoes de gestos em estados do jogo.

    Regras:
    - esquerda aberta somente -> ESQUERDA
    - direita aberta somente -> DIREITA
    - duas abertas -> PULO
    - duas fechadas -> AGACHADO
    - coracao com duas maos -> REINICIAR (F5)
    """

    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    PINKY_MCP = 17

    def __init__(self) -> None:
        self.debug: dict[str, Any] = {}

    def reset(self) -> None:
        self.debug = {}

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        _ = baseline

    @staticmethod
    def _distance(a: Any, b: Any) -> float:
        return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))

    def _hand_scale(self, hand: dict[str, Any]) -> float:
        landmarks = hand.get("landmarks") or []
        if len(landmarks) <= self.PINKY_MCP:
            return 0.0
        wrist_to_middle = self._distance(landmarks[self.WRIST], landmarks[self.MIDDLE_MCP])
        palm_width = self._distance(landmarks[self.INDEX_MCP], landmarks[self.PINKY_MCP])
        return max(wrist_to_middle, palm_width, 1e-5)

    def _detect_heart(
        self,
        left: dict[str, Any] | None,
        right: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, float]]:
        """Detecta um coracao feito com as duas maos.

        O gesto esperado e o coracao classico de duas maos: indicadores se
        encontram na parte superior e polegares na parte inferior.
        """
        empty = {
            "heart_index_contact": 99.0,
            "heart_thumb_contact": 99.0,
            "heart_left_opening": 0.0,
            "heart_right_opening": 0.0,
            "heart_vertical_gap": 0.0,
        }
        if not left or not right:
            return False, empty

        ll = left.get("landmarks") or []
        rl = right.get("landmarks") or []
        if len(ll) <= self.PINKY_MCP or len(rl) <= self.PINKY_MCP:
            return False, empty

        scale = (self._hand_scale(left) + self._hand_scale(right)) / 2.0
        if scale <= 1e-5:
            return False, empty

        index_contact = self._distance(ll[self.INDEX_TIP], rl[self.INDEX_TIP]) / scale
        thumb_contact = self._distance(ll[self.THUMB_TIP], rl[self.THUMB_TIP]) / scale
        left_opening = self._distance(ll[self.INDEX_TIP], ll[self.THUMB_TIP]) / scale
        right_opening = self._distance(rl[self.INDEX_TIP], rl[self.THUMB_TIP]) / scale

        index_center_y = (float(ll[self.INDEX_TIP].y) + float(rl[self.INDEX_TIP].y)) / 2.0
        thumb_center_y = (float(ll[self.THUMB_TIP].y) + float(rl[self.THUMB_TIP].y)) / 2.0
        vertical_gap = (thumb_center_y - index_center_y) / scale

        metrics = {
            "heart_index_contact": index_contact,
            "heart_thumb_contact": thumb_contact,
            "heart_left_opening": left_opening,
            "heart_right_opening": right_opening,
            "heart_vertical_gap": vertical_gap,
        }

        detected = (
            index_contact <= HAND_HEART_CONTACT_RATIO
            and thumb_contact <= HAND_HEART_CONTACT_RATIO
            and left_opening >= HAND_HEART_MIN_OPENING_RATIO
            and right_opening >= HAND_HEART_MIN_OPENING_RATIO
            and vertical_gap >= HAND_HEART_MIN_VERTICAL_GAP_RATIO
        )
        return detected, metrics

    @staticmethod
    def _valid_gesture(hand: dict[str, Any] | None) -> tuple[str, float]:
        if not hand:
            return "AUSENTE", 0.0
        gesture = str(hand.get("gesture", "None"))
        score = float(hand.get("gesture_score", 0.0))
        if score < HAND_GESTURE_MIN_SCORE:
            return "INCERTO", score
        if gesture == "Open_Palm":
            return "ABERTA", score
        if gesture == "Closed_Fist":
            return "FECHADA", score
        return "OUTRO", score

    def classificar(self, hand_data: dict[str, Any] | None, now: float | None = None) -> Estado:
        _ = now
        hands = (hand_data or {}).get("hands", [])

        left: dict[str, Any] | None = None
        right: dict[str, Any] | None = None
        for hand in hands:
            side = str(hand.get("side", "UNKNOWN")).upper()
            if side == "LEFT":
                left = hand
            elif side == "RIGHT":
                right = hand

        left_gesture, left_score = self._valid_gesture(left)
        right_gesture, right_score = self._valid_gesture(right)
        heart_detected, heart_metrics = self._detect_heart(left, right)

        self.debug = {
            "left_gesture": left_gesture,
            "left_score": left_score,
            "right_gesture": right_gesture,
            "right_score": right_score,
            "hands_detected": len(hands),
            "heart_detected": 1.0 if heart_detected else 0.0,
            **heart_metrics,
        }

        if not hands:
            return Estado.SEM_POSE

        # Reinicio tem prioridade sobre os outros gestos.
        if heart_detected:
            return Estado.REINICIAR

        if left_gesture == "ABERTA" and right_gesture == "ABERTA":
            return Estado.PULO
        if left_gesture == "FECHADA" and right_gesture == "FECHADA":
            return Estado.AGACHADO

        if left_gesture == "ABERTA" and right_gesture != "ABERTA":
            return Estado.ESQUERDA
        if right_gesture == "ABERTA" and left_gesture != "ABERTA":
            return Estado.DIREITA

        return Estado.CENTRO
