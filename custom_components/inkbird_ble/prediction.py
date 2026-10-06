"""Temperature trend and ETA helpers for the ISC-027BW."""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class TemperatureTrend:
    """Keep a rolling sample window and calculate a linear trend."""

    window_seconds: float
    minimum_span_seconds: float = 30.0
    minimum_samples: int = 5
    _samples: deque[tuple[float, float]] = field(default_factory=deque)

    def add(self, value: float | None, timestamp: float | None = None) -> None:
        """Add one reading and discard samples outside the configured window."""
        now = time.monotonic() if timestamp is None else timestamp
        if value is None or not math.isfinite(value) or value == 0:
            self._samples.clear()
            return

        self._samples.append((now, value))
        cutoff = now - self.window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    @property
    def rate_per_minute(self) -> float | None:
        """Return the least-squares slope in degrees per minute."""
        if len(self._samples) < self.minimum_samples:
            return None
        if self._samples[-1][0] - self._samples[0][0] < self.minimum_span_seconds:
            return None

        origin = self._samples[0][0]
        xs = [(timestamp - origin) / 60 for timestamp, _ in self._samples]
        ys = [value for _, value in self._samples]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        denominator = sum((x - mean_x) ** 2 for x in xs)
        if denominator == 0:
            return None
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
        return round(slope, 3)


def meat_eta_minutes(
    temperature: float | None,
    chamber_temperature: float | None,
    target: float | None,
    rate_per_minute: float | None,
) -> float | None:
    """Estimate meat target time with a Newton's-law heating curve."""
    values = (temperature, chamber_temperature, target, rate_per_minute)
    if any(value is None or not math.isfinite(value) for value in values):
        return None
    assert temperature is not None
    assert chamber_temperature is not None
    assert target is not None
    assert rate_per_minute is not None
    if temperature >= target or rate_per_minute <= 0.02 or chamber_temperature <= target:
        return None

    gap = chamber_temperature - temperature
    target_gap = chamber_temperature - target
    if gap <= 0 or target_gap <= 0:
        return None
    coefficient = rate_per_minute / gap
    minutes = math.log(gap / target_gap) / coefficient
    return minutes if 0 < minutes <= 2880 else None


def eta_state(
    temperature: float | None,
    target: float | None,
    rate_per_minute: float | None,
    chamber_temperature: float | None,
) -> tuple[str, float | None]:
    """Return a human-readable meat ETA state and its numeric estimate."""
    if temperature is None:
        return "Sensor not connected", None
    if target is None:
        return "No target temperature", None
    if temperature >= target:
        return "Target reached", 0
    if rate_per_minute is None:
        return "Collecting heating data", None
    if rate_per_minute <= 0.02:
        return "Stalled or cooling — no reliable estimate", None
    if chamber_temperature is None or chamber_temperature <= target:
        return "Chamber temperature is too low for this target", None

    minutes = meat_eta_minutes(
        temperature, chamber_temperature, target, rate_per_minute
    )
    if minutes is None:
        return "No reliable estimate", None
    rounded = max(1, math.ceil(minutes / 5) * 5)
    return f"About {rounded} min", float(rounded)
