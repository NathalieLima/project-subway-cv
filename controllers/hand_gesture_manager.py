"""Gerencia gestos discretos do modo MAOS."""
from __future__ import annotations

from states import Estado


class HandGestureManager:
    """Gera um unico comando por entrada em cada gesto.

    Diferente de CORPO/PEITORAL/ROSTO, ESQUERDA e DIREITA aqui sao comandos
    relativos (um passo), nao a posicao fisica absoluta da pessoa.
    """

    ACTIONS = {
        Estado.ESQUERDA,
        Estado.DIREITA,
        Estado.PULO,
        Estado.AGACHADO,
        Estado.REINICIAR,
    }

    def __init__(self) -> None:
        self._last_action: Estado | None = None

    def reset(self) -> None:
        self._last_action = None

    def process(self, state: Estado) -> list[Estado]:
        if state in (Estado.CENTRO, Estado.SEM_POSE):
            self._last_action = None
            return []

        if state not in self.ACTIONS:
            return []

        if state == self._last_action:
            return []

        self._last_action = state
        return [state]
