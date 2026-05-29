from __future__ import annotations

import asyncio
from datetime import datetime
import math
import time

from app.core.logging import get_logger
from app.hardware.base import SensorReading, raw_to_soil_pct

_logger = get_logger(__name__)

_TEMP_CENTER = 27.0
_TEMP_AMPLITUDE = 3.0
_TEMP_PERIOD = 60.0

_HUMIDITY_AIR_CENTER = 60.0
_HUMIDITY_AIR_AMPLITUDE = 5.0
_HUMIDITY_AIR_PERIOD = 45.0

_SOIL_CENTER = 500
_SOIL_AMPLITUDE = 200
_SOIL_PERIOD = 90.0


class MockBoard:
    def __init__(self, soil_adc_wet: int = 300, soil_adc_dry: int = 900) -> None:
        self._connected = False
        self._start_time: float = 0.0
        self._soil_adc_wet = soil_adc_wet
        self._soil_adc_dry = soil_adc_dry

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        await asyncio.sleep(0.05)
        self._connected = True
        self._start_time = time.monotonic()
        _logger.info('Mock board connected (simulated sensors active)')

    async def disconnect(self) -> None:
        self._connected = False
        _logger.info('Mock board disconnected')

    def get_latest_reading(self) -> SensorReading | None:
        if not self._connected:
            return None
        elapsed = time.monotonic() - self._start_time

        temp = round(
            _TEMP_CENTER
            + _TEMP_AMPLITUDE * (-math.cos(2 * math.pi * elapsed / _TEMP_PERIOD)),
            1,
        )

        humidity_air = round(
            _HUMIDITY_AIR_CENTER
            + _HUMIDITY_AIR_AMPLITUDE
            * math.sin(2 * math.pi * elapsed / _HUMIDITY_AIR_PERIOD),
            1,
        )

        soil_raw = int(
            _SOIL_CENTER
            - _SOIL_AMPLITUDE * math.cos(2 * math.pi * elapsed / _SOIL_PERIOD)
        )

        soil_pct = round(
            raw_to_soil_pct(soil_raw, self._soil_adc_wet, self._soil_adc_dry), 1
        )

        return SensorReading(
            temperature=temp,
            humidity_air=humidity_air,
            humidity_soil_raw=soil_raw,
            humidity_soil_pct=soil_pct,
            timestamp=datetime.now(),
        )

    def set_digital(self, pin: int, value: bool) -> None:
        _logger.debug(f'[MOCK] set_digital(pin={pin}, value={value})')

    def set_servo(self, pin: int, angle: int) -> None:
        _logger.debug(f'[MOCK] set_servo(pin={pin}, angle={angle})')

    def set_pwm(self, pin: int, duty: float) -> None:
        _logger.debug(f'[MOCK] set_pwm(pin={pin}, duty={duty:.3f})')
