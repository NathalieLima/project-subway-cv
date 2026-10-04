"""Maquina de estados simples para calibracao por mediana."""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field

from config import CALIBRATION_COUNTDOWN_SECONDS, CALIBRATION_SAMPLES


@dataclass
class Calibrator:
    countdown_seconds: float = CALIBRATION_COUNTDOWN_SECONDS
    sample_count: int = CALIBRATION_SAMPLES
    active: bool = False
    complete: bool = False
    started_at: float = 0.0
    samples: list[dict[str, float]] = field(default_factory=list)
    baseline: dict[str, float] | None = None

    def start(self) -> None:
        self.active = True
        self.complete = False
        self.started_at = time.perf_counter()
        self.samples.clear()
        self.baseline = None

    def reset(self) -> None:
        self.active = False
        self.complete = False
        self.samples.clear()
        self.baseline = None

    def update(self, features: dict[str, float] | None) -> dict[str, float] | None:
        if not self.active:
            return None

        elapsed = time.perf_counter() - self.started_at
        if elapsed < self.countdown_seconds:
            return None

        if features is not None:
            self.samples.append(dict(features))

        if len(self.samples) < self.sample_count:
            return None

        common_keys = set.intersection(*(set(s.keys()) for s in self.samples))
        baseline = {
            key: float(statistics.median(sample[key] for sample in self.samples))
            for key in sorted(common_keys)
        }
        self.baseline = baseline
        self.active = False
        self.complete = True
        return baseline

    def message(self) -> str:
        if self.complete:
            return "CALIBRACAO CONCLUIDA"
        if not self.active:
            return "PRESSIONE F8 PARA CALIBRAR"

        elapsed = time.perf_counter() - self.started_at
        remaining = self.countdown_seconds - elapsed
        if remaining > 0:
            return f"FIQUE PARADO... {max(1, int(remaining + 0.999))}"
        return f"CALIBRANDO - NAO SE MOVA ({len(self.samples)}/{self.sample_count})"
