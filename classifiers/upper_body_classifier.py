"""Classificador do modo PEITORAL.

Os ombros continuam sendo os unicos pontos obrigatorios para o controle normal.
Pulsos sao opcionais e usados apenas para o gesto de reinicio com bracos abertos.
"""
from __future__ import annotations

import math
from typing import Any

from config import (
    POSE_MIN_VISIBILITY,
    UPPER_CROUCH_CONFIRM_SECONDS,
    UPPER_CROUCH_DROP_THRESHOLD,
    UPPER_CROUCH_MAX_UPWARD_VELOCITY,
    UPPER_JUMP_LIFT_THRESHOLD,
    UPPER_JUMP_MIN_LIFT_WITH_VELOCITY,
    UPPER_JUMP_UPWARD_VELOCITY,
    UPPER_LATERAL_THRESHOLD,
    UPPER_RESTART_ARM_SPAN_THRESHOLD,
    UPPER_RESTART_MAX_VERTICAL_OFFSET,
    UPPER_RESTART_MIN_SIDE_EXTENSION,
)
from states import Estado


class UpperBodyClassifier:
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16

    def __init__(self) -> None:
        self.baseline: dict[str, float] | None = None
        self.debug: dict[str, float] = {}
        self._prev_y: float | None = None
        self._prev_t: float | None = None
        self._crouch_since: float | None = None

    def reset(self) -> None:
        self.baseline = None
        self.debug = {}
        self._prev_y = None
        self._prev_t = None
        self._crouch_since = None

    def reset_temporal(self) -> None:
        self._prev_y = None
        self._prev_t = None
        self._crouch_since = None
        self.debug = {}

    @staticmethod
    def _ok(lm: Any) -> bool:
        visibility = getattr(lm, "visibility", 1.0)
        presence = getattr(lm, "presence", 1.0)
        return visibility >= POSE_MIN_VISIBILITY and presence >= 0.3

    def extrair_features(self, landmarks: list[Any] | None) -> dict[str, float] | None:
        if not landmarks or len(landmarks) <= self.RIGHT_SHOULDER:
            return None
        ls = landmarks[self.LEFT_SHOULDER]
        rs = landmarks[self.RIGHT_SHOULDER]
        if not self._ok(ls) or not self._ok(rs):
            return None

        shoulder_x = (ls.x + rs.x) / 2.0
        shoulder_y = (ls.y + rs.y) / 2.0
        shoulder_width = math.hypot(ls.x - rs.x, ls.y - rs.y)
        if shoulder_width <= 1e-5:
            return None

        features: dict[str, float] = {
            "shoulder_x": shoulder_x,
            "shoulder_y": shoulder_y,
            "shoulder_width": shoulder_width,
        }

        # Pulsos sao opcionais. A ausencia deles nao invalida PEITORAL.
        if len(landmarks) > self.RIGHT_WRIST:
            lw = landmarks[self.LEFT_WRIST]
            rw = landmarks[self.RIGHT_WRIST]
            if self._ok(lw) and self._ok(rw):
                wrist_span = abs(float(lw.x) - float(rw.x)) / shoulder_width
                shoulder_min_x = min(float(ls.x), float(rs.x))
                shoulder_max_x = max(float(ls.x), float(rs.x))
                wrist_min_x = min(float(lw.x), float(rw.x))
                wrist_max_x = max(float(lw.x), float(rw.x))
                left_extension = (shoulder_min_x - wrist_min_x) / shoulder_width
                right_extension = (wrist_max_x - shoulder_max_x) / shoulder_width
                min_side_extension = min(left_extension, right_extension)
                vertical_offset = (
                    abs(float(lw.y) - shoulder_y) + abs(float(rw.y) - shoulder_y)
                ) / (2.0 * shoulder_width)

                features.update({
                    "arm_span": wrist_span,
                    "arm_min_side_extension": min_side_extension,
                    "arm_vertical_offset": vertical_offset,
                })

        return features

    def definir_baseline(self, baseline: dict[str, float]) -> None:
        # A baseline pode conter metricas opcionais de bracos coletadas durante
        # a calibracao; elas nao sao necessarias para o classificador.
        self.baseline = {
            "shoulder_x": baseline["shoulder_x"],
            "shoulder_y": baseline["shoulder_y"],
            "shoulder_width": baseline["shoulder_width"],
        }
        self.reset_temporal()

    def classificar(self, features: dict[str, float] | None, timestamp_s: float) -> Estado:
        if features is None or self.baseline is None:
            return Estado.SEM_POSE

        b = self.baseline
        width = max(b["shoulder_width"], 1e-5)
        y = features["shoulder_y"]

        lateral = (features["shoulder_x"] - b["shoulder_x"]) / width
        lift = (b["shoulder_y"] - y) / width
        drop = (y - b["shoulder_y"]) / width

        velocity = 0.0
        if self._prev_y is not None and self._prev_t is not None:
            dt = max(timestamp_s - self._prev_t, 1e-4)
            velocity = (self._prev_y - y) / width / dt
        self._prev_y = y
        self._prev_t = timestamp_s

        arm_span = float(features.get("arm_span", 0.0))
        arm_min_side_extension = float(features.get("arm_min_side_extension", -99.0))
        arm_vertical_offset = float(features.get("arm_vertical_offset", 99.0))
        arms_open = (
            arm_span >= UPPER_RESTART_ARM_SPAN_THRESHOLD
            and arm_min_side_extension >= UPPER_RESTART_MIN_SIDE_EXTENSION
            and arm_vertical_offset <= UPPER_RESTART_MAX_VERTICAL_OFFSET
        )

        # Abrir os dois bracos e o gesto de reinicio e tem prioridade.
        if arms_open:
            self._crouch_since = None
            crouch_time = 0.0
            state = Estado.REINICIAR
            jump_by_height = False
            jump_by_speed = False
        else:
            jump_by_height = lift >= UPPER_JUMP_LIFT_THRESHOLD
            jump_by_speed = (
                lift >= UPPER_JUMP_MIN_LIFT_WITH_VELOCITY
                and velocity >= UPPER_JUMP_UPWARD_VELOCITY
            )
            if jump_by_height or jump_by_speed:
                self._crouch_since = None
                crouch_time = 0.0
                state = Estado.PULO
            else:
                crouch_condition = (
                    drop >= UPPER_CROUCH_DROP_THRESHOLD
                    and velocity < UPPER_CROUCH_MAX_UPWARD_VELOCITY
                )
                if crouch_condition:
                    if self._crouch_since is None:
                        self._crouch_since = timestamp_s
                    crouch_time = timestamp_s - self._crouch_since
                else:
                    self._crouch_since = None
                    crouch_time = 0.0

                if crouch_time >= UPPER_CROUCH_CONFIRM_SECONDS:
                    state = Estado.AGACHADO
                elif lateral <= -UPPER_LATERAL_THRESHOLD:
                    state = Estado.ESQUERDA
                elif lateral >= UPPER_LATERAL_THRESHOLD:
                    state = Estado.DIREITA
                else:
                    state = Estado.CENTRO

        self.debug = {
            "lateral": lateral,
            "lift": lift,
            "drop": drop,
            "velocity": velocity,
            "crouch_time": crouch_time,
            "crouch_candidate": 1.0 if (
                not arms_open
                and not jump_by_height
                and not jump_by_speed
                and drop >= UPPER_CROUCH_DROP_THRESHOLD
                and velocity < UPPER_CROUCH_MAX_UPWARD_VELOCITY
            ) else 0.0,
            "arms_visible": 1.0 if "arm_span" in features else 0.0,
            "arms_open": 1.0 if arms_open else 0.0,
            "arm_span": arm_span,
            "arm_min_side_extension": arm_min_side_extension,
            "arm_vertical_offset": arm_vertical_offset,
        }
        return state

    def limites_guias(self) -> dict[str, float] | None:
        if self.baseline is None:
            return None
        b = self.baseline
        return {
            "left_x": b["shoulder_x"] - b["shoulder_width"] * UPPER_LATERAL_THRESHOLD,
            "right_x": b["shoulder_x"] + b["shoulder_width"] * UPPER_LATERAL_THRESHOLD,
            "jump_y": b["shoulder_y"] - b["shoulder_width"] * UPPER_JUMP_LIFT_THRESHOLD,
            "neutral_y": b["shoulder_y"],
            "crouch_y": b["shoulder_y"] + b["shoulder_width"] * UPPER_CROUCH_DROP_THRESHOLD,
        }
