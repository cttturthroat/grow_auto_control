from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
import json
import threading
import time

import serial  # type: ignore[import-untyped]
import serial.tools.list_ports  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.hardware.base import SensorReading, raw_to_soil_pct

_logger = get_logger(__name__)

_ARDUINO_KEYWORDS = ('arduino', 'ch340', 'ch341', 'cp210', 'ftdi', 'usb serial')
_HANDSHAKE = 'GROW_CTRL_READY'
_HANDSHAKE_TIMEOUT = 10.0
_RESET_DELAY = 2.0


def _find_arduino_port() -> str | None:
    for port_info in serial.tools.list_ports.comports():
        desc: str = port_info.description.lower()
        if any(kw in desc for kw in _ARDUINO_KEYWORDS):
            return str(port_info.device)
    return None


class SerialBoard:
    def __init__(
        self,
        port: str,
        baud: int,
        soil_adc_wet: int,
        soil_adc_dry: int,
    ) -> None:
        self._port = port
        self._baud = baud
        self._soil_adc_wet = soil_adc_wet
        self._soil_adc_dry = soil_adc_dry
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._latest: SensorReading | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and bool(self._serial.is_open)

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._connect_sync)
        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name='serial-read'
        )
        self._thread.start()

    def _connect_sync(self) -> None:
        port = self._port
        if port == 'AUTODETECT':
            port = _find_arduino_port() or ''
        if not port:
            raise ConnectionError(
                'No Arduino-compatible port found. Check USB cable and driver.'
            )

        _logger.info(f'Connecting to {port} at {self._baud} baud')
        self._serial = serial.Serial(port, self._baud, timeout=5.0)

        time.sleep(_RESET_DELAY)
        self._serial.reset_input_buffer()

        deadline = time.monotonic() + _HANDSHAKE_TIMEOUT
        while time.monotonic() < deadline:
            raw = self._serial.readline()
            if not raw:
                continue
            line: str = raw.decode('utf-8', errors='replace').strip()
            if line == _HANDSHAKE:
                _logger.info(f'Arduino ready on {port}')
                return

        raise TimeoutError(
            'Sketch did not send GROW_CTRL_READY. Re-flash grow_control.ino.'
        )

    async def disconnect(self) -> None:
        self._running = False
        if self._serial is not None:
            with contextlib.suppress(Exception):
                self._serial.close()
        self._serial = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        _logger.info('Serial board disconnected')

    def get_latest_reading(self) -> SensorReading | None:
        with self._lock:
            return self._latest

    def set_digital(self, pin: int, value: bool) -> None:
        self._send(f'DOUT {pin} {1 if value else 0}')

    def set_servo(self, pin: int, angle: int) -> None:
        self._send(f'SERVO {pin} {angle}')

    def set_pwm(self, pin: int, duty: float) -> None:
        value = int(max(0.0, min(1.0, duty)) * 255)
        self._send(f'PWM {pin} {value}')

    def _send(self, command: str) -> None:
        if self._serial is None or not self._serial.is_open:
            return
        with self._write_lock:
            try:
                self._serial.write(f'{command}\n'.encode())
            except serial.SerialException as exc:
                _logger.error(f'Serial write error: {exc}')

    def _read_loop(self) -> None:
        while self._running:
            if self._serial is None or not self._serial.is_open:
                break
            try:
                raw = self._serial.readline()
                if not raw:
                    continue
                line: str = raw.decode('utf-8', errors='replace').strip()
                if line.startswith('{'):
                    self._parse_reading(line)
            except serial.SerialException as exc:
                _logger.error(f'Serial read error: {exc}')
                self._close_port()
                break
            except Exception as exc:
                _logger.error(f'Unexpected read error: {exc}')
                self._close_port()
                break

    def _close_port(self) -> None:
        if self._serial is not None:
            with contextlib.suppress(Exception):
                self._serial.close()
            self._serial = None
        with self._lock:
            self._latest = None

    def _parse_reading(self, text: str) -> None:
        try:
            payload: dict[str, float] = json.loads(text)
            temp = payload.get('t')
            humidity_air = payload.get('h')
            s_val = payload.get('s')

            soil_raw = int(s_val) if s_val is not None else None
            soil_pct = (
                raw_to_soil_pct(soil_raw, self._soil_adc_wet, self._soil_adc_dry)
                if soil_raw is not None
                else None
            )

            reading = SensorReading(
                temperature=temp,
                humidity_air=humidity_air,
                humidity_soil_raw=soil_raw,
                humidity_soil_pct=round(soil_pct, 1) if soil_pct is not None else None,
                timestamp=datetime.now(),
            )
            with self._lock:
                self._latest = reading
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            _logger.warning(f'Failed to parse reading {text!r}: {exc}')
