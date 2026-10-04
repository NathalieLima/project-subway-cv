"""Envio de teclas globais para o jogo via pynput."""
from __future__ import annotations

import ctypes
import platform
import time
from threading import Lock

from pynput.keyboard import Controller, Key

from config import (
    COMMAND_COOLDOWN,
    DOUBLE_LANE_COMMAND_INTERVAL,
    GAME_WINDOW_KEYWORDS,
    REQUIRE_GAME_FOCUS,
)
from states import Estado


class GameController:
    """Converte comandos discretos em eventos reais de teclado."""

    KEY_HOLD_SECONDS = 0.055
    JUMP_KEY_HOLD_SECONDS = 0.120
    RESTART_KEY_HOLD_SECONDS = 0.100

    def __init__(self) -> None:
        self.keyboard = Controller()
        self._last_command_at: dict[Estado, float] = {}
        self._lock = Lock()
        self.last_sent_command: Estado | None = None

    @staticmethod
    def _foreground_window_title() -> str:
        if platform.system() != "Windows":
            return ""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def game_has_focus(self) -> bool:
        if not REQUIRE_GAME_FOCUS:
            return True
        if platform.system() != "Windows":
            return True
        title = self._foreground_window_title().lower()
        return any(keyword.lower() in title for keyword in GAME_WINDOW_KEYWORDS)

    def _press(self, state: Estado) -> None:
        key_map = {
            Estado.ESQUERDA: Key.left,
            Estado.DIREITA: Key.right,
            Estado.PULO: Key.up,
            Estado.AGACHADO: Key.down,
            Estado.REINICIAR: Key.f5,
        }

        key = key_map[state]
        if state == Estado.PULO:
            hold_seconds = self.JUMP_KEY_HOLD_SECONDS
        elif state == Estado.REINICIAR:
            hold_seconds = self.RESTART_KEY_HOLD_SECONDS
        else:
            hold_seconds = self.KEY_HOLD_SECONDS

        self.keyboard.press(key)
        time.sleep(hold_seconds)
        self.keyboard.release(key)

        self.last_sent_command = state
        key_name = "F5" if state == Estado.REINICIAR else state.value
        print(
            f"[TECLADO] {key_name} enviado "
            f"({hold_seconds * 1000:.0f} ms de pressionamento)",
            flush=True,
        )

    def send(self, commands: list[Estado]) -> bool:
        if not commands:
            return False

        if not self.game_has_focus():
            print("[TECLADO] comando ignorado: jogo sem foco.", flush=True)
            return False

        first = commands[0]
        now = time.perf_counter()
        last = self._last_command_at.get(first, -1e9)
        if now - last < COMMAND_COOLDOWN:
            print(
                f"[TECLADO] {first.value} ignorado pelo cooldown "
                f"({now - last:.3f}s < {COMMAND_COOLDOWN:.3f}s).",
                flush=True,
            )
            return False

        with self._lock:
            for i, command in enumerate(commands):
                self._press(command)
                if i < len(commands) - 1:
                    time.sleep(DOUBLE_LANE_COMMAND_INTERVAL)

            finished = time.perf_counter()
            for command in set(commands):
                self._last_command_at[command] = finished

        return True

    def reset_cooldowns(self) -> None:
        self._last_command_at.clear()
        self.last_sent_command = None
