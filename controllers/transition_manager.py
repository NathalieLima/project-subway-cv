"""Transforma estados fisicos em comandos discretos de jogo."""
from __future__ import annotations

from states import Estado, ESTADOS_LATERAIS, ESTADOS_MOMENTANEOS


class TransitionManager:
    def __init__(self) -> None:
        self.faixa_lateral = Estado.CENTRO
        self._ultimo_estado_momentaneo: Estado | None = None

    def reset(self) -> None:
        self.faixa_lateral = Estado.CENTRO
        self._ultimo_estado_momentaneo = None

    @staticmethod
    def _lane_index(state: Estado) -> int:
        return {
            Estado.ESQUERDA: -1,
            Estado.CENTRO: 0,
            Estado.DIREITA: 1,
        }[state]

    def process(self, state: Estado) -> list[Estado]:
        if state == Estado.SEM_POSE:
            return []

        # PULO, AGACHADO e REINICIAR sao eventos momentaneos. Nenhum deles muda
        # a faixa lateral interna.
        if state in ESTADOS_MOMENTANEOS:
            if self._ultimo_estado_momentaneo == state:
                return []
            self._ultimo_estado_momentaneo = state
            return [state]

        self._ultimo_estado_momentaneo = None

        if state not in ESTADOS_LATERAIS:
            return []

        old_idx = self._lane_index(self.faixa_lateral)
        new_idx = self._lane_index(state)
        delta = new_idx - old_idx
        self.faixa_lateral = state

        if delta == 0:
            return []
        command = Estado.DIREITA if delta > 0 else Estado.ESQUERDA
        return [command] * abs(delta)
