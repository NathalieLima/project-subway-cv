"""Atalhos globais F8/F10 usando pynput."""
from __future__ import annotations

from threading import Event

from pynput import keyboard


class GlobalHotkeys:
    def __init__(self) -> None:
        self.calibrate = Event()
        self.exit = Event()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key == keyboard.Key.f8:
            self.calibrate.set()
        elif key == keyboard.Key.f10:
            self.exit.set()

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()

    @staticmethod
    def consume(event: Event) -> bool:
        if event.is_set():
            event.clear()
            return True
        return False
