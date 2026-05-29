from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SensorReading:
    temperature: float | None
    humidity_air: float | None
    humidity_soil_raw: int | None
    humidity_soil_pct: float | None
    timestamp: datetime


def raw_to_soil_pct(raw: int, adc_wet: int, adc_dry: int) -> float:
    if adc_dry == adc_wet:
        return 50.0
    clamped = max(float(adc_wet), min(float(adc_dry), float(raw)))
    return 100.0 * (adc_dry - clamped) / (adc_dry - adc_wet)


class BoardGateway(Protocol):
    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    def get_latest_reading(self) -> SensorReading | None: ...

    def set_digital(self, pin: int, value: bool) -> None: ...

    def set_servo(self, pin: int, angle: int) -> None: ...

    def set_pwm(self, pin: int, duty: float) -> None: ...
