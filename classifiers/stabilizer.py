from collections import Counter, deque
from typing import Deque

from config import MIN_STATE_VOTES, SMOOTHING_WINDOW
from states import Estado


class StateStabilizer:
    """Suaviza os estados por votacao em uma janela curta.

    SEM_POSE e propositalmente ignorado no historico para que a perda de
    deteccao nao apague o ultimo estado fisico confiavel.

    PULO recebe um tratamento especial: como e um movimento muito rapido,
    esperar MIN_STATE_VOTES (3 por padrao) em toda a janela pode fazer o evento
    desaparecer antes de chegar ao controlador. Para continuar evitando falsos
    positivos de um unico frame, o pulo e confirmado quando aparece em dois dos
    tres frames mais recentes.
    """

    def __init__(self, window_size: int = SMOOTHING_WINDOW, min_votes: int = MIN_STATE_VOTES):
        self.window_size = window_size
        self.min_votes = min_votes
        self._history: Deque[Estado] = deque(maxlen=window_size)
        self._stable_state = Estado.CENTRO

    @property
    def stable_state(self) -> Estado:
        return self._stable_state

    def reset(self, initial_state: Estado = Estado.CENTRO) -> None:
        self._history.clear()
        self._stable_state = initial_state

    def update(self, state: Estado) -> Estado:
        if state == Estado.SEM_POSE:
            return Estado.SEM_POSE

        self._history.append(state)

        # PULO e um evento curto. Exigir 3 votos em 5 frames pode engolir o
        # movimento antes de ele chegar ao TransitionManager. Dois votos nos
        # tres frames mais recentes continuam filtrando um falso positivo de
        # apenas um frame, mas deixam o comando UP responder a tempo.
        recent = list(self._history)[-3:]
        jump_votes = sum(1 for item in recent if item == Estado.PULO)
        if jump_votes >= 2:
            self._stable_state = Estado.PULO
            return self._stable_state

        counts = Counter(self._history)
        candidate, votes = counts.most_common(1)[0]

        if votes >= self.min_votes:
            self._stable_state = candidate

        return self._stable_state
