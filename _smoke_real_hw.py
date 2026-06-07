"""
Hardware smoke test (bench configuration).

Prerequisites
─────────────
1. grow_control.ino flashed to Arduino Mega 2560.
2. DHT11 DATA → D4, VCC → 3.3V, GND → GND.
3. Relay IN → D8 (active LOW), fan via COM/NO + 9V.
4. .env with MOCK_HARDWARE=false.

Usage:
    poetry run python _smoke_real_hw.py
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time

# Force UTF-8 output so replacement characters (\ufffd) from garbled serial
# bytes don't crash on Windows consoles that default to CP1251 / CP1252.
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import serial  # type: ignore[import-untyped]
import serial.tools.list_ports  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.logging import setup_logging
from app.hardware.base import SensorReading
from app.hardware.serial_board import SerialBoard

# ── constants ────────────────────────────────────────────────────────────────

_HANDSHAKE = 'GROW_CTRL_READY'
_RESET_DELAY = 2.5  # seconds to wait for Arduino reset after serial open
_HANDSHAKE_TIMEOUT = 15.0  # seconds to wait for GROW_CTRL_READY
_READ_COUNT = 3  # JSON frames to collect in Phase 1
_READ_TIMEOUT = 12.0  # seconds to collect _READ_COUNT frames
_BOARD_WARMUP = 7.0  # seconds to let SerialBoard collect readings in Phase 2

_DHT11_TEMP_RANGE = (-10.0, 85.0)  # °C — DHT11 absolute range
_DHT11_HUM_RANGE = (0.0, 100.0)  # %
_ADC_RANGE = (0, 1023)  # raw Arduino ADC range


# ── helpers ───────────────────────────────────────────────────────────────────


def _find_port() -> str | None:
    keywords = ('arduino', 'ch340', 'ch341', 'cp210', 'ftdi', 'usb serial')
    for info in serial.tools.list_ports.comports():
        if any(kw in info.description.lower() for kw in keywords):
            return str(info.device)
    return None


def _ok(msg: str) -> None:
    print(f'  [PASS] {msg}')


def _fail(msg: str) -> None:
    print(f'  [FAIL] {msg}')


def _info(msg: str) -> None:
    print(f'         {msg}')


# ── Phase 1: raw serial ───────────────────────────────────────────────────────


def phase1_raw_serial(port: str) -> list[dict[str, object]]:
    print()
    print('Phase 1 - raw pyserial')
    print('-' * 30)

    readings: list[dict[str, object]] = []

    with serial.Serial(port, settings.SERIAL_BAUD, timeout=5.0) as ser:
        _info(f'Port open: {port} @ {settings.SERIAL_BAUD} baud')
        _info(f'Waiting {_RESET_DELAY}s for Arduino boot...')
        time.sleep(_RESET_DELAY)
        ser.reset_input_buffer()

        # ── handshake ────────────────────────────────────────────────────────
        deadline = time.monotonic() + _HANDSHAKE_TIMEOUT
        handshake_ok = False
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace').strip()
            if line == _HANDSHAKE:
                _ok(f'Handshake received: {line!r}')
                handshake_ok = True
                break
            _info(f'(skipping pre-handshake line): {line!r}')

        if not handshake_ok:
            _fail(
                f'No {_HANDSHAKE!r} within {_HANDSHAKE_TIMEOUT}s.\n'
                '         → Is grow_control.ino flashed? Is baud rate 115200?'
            )
            sys.exit(1)

        # ── JSON readings ─────────────────────────────────────────────────────
        _info(f'Collecting {_READ_COUNT} JSON readings (up to {_READ_TIMEOUT}s)...')
        deadline = time.monotonic() + _READ_TIMEOUT
        while len(readings) < _READ_COUNT and time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace').strip()
            if not line.startswith('{'):
                _info(f'(non-JSON line): {line!r}')
                continue
            try:
                data: dict[str, object] = json.loads(line)
                readings.append(data)
                _info(f'Reading {len(readings)}: {line}')
            except json.JSONDecodeError as exc:
                _info(f'(JSON parse error — {exc}): {line!r}')

        if len(readings) < _READ_COUNT:
            _fail(
                f'Only {len(readings)}/{_READ_COUNT} readings received.\n'
                '         → Check SENSOR_POLL_MS and loop() in grow_control.ino.'
            )
            sys.exit(1)
        else:
            _ok(f'Received {len(readings)} readings')

        # ── validate field ranges ─────────────────────────────────────────────
        dht_seen = False
        errors: list[str] = []
        for idx, r in enumerate(readings, 1):
            if 's' not in r:
                errors.append(f'Reading {idx}: missing "s" (soil ADC) field')
            elif not (_ADC_RANGE[0] <= int(r['s']) <= _ADC_RANGE[1]):  # type: ignore[call-overload]
                errors.append(f'Reading {idx}: soil ADC {r["s"]} outside [0, 1023]')

            if 't' in r:
                dht_seen = True
                t = float(r['t'])  # type: ignore[arg-type]
                if not (_DHT11_TEMP_RANGE[0] <= t <= _DHT11_TEMP_RANGE[1]):
                    errors.append(
                        f'Reading {idx}: temperature {t}°C outside DHT11 range'
                    )

            if 'h' in r:
                h = float(r['h'])  # type: ignore[arg-type]
                if not (_DHT11_HUM_RANGE[0] <= h <= _DHT11_HUM_RANGE[1]):
                    errors.append(f'Reading {idx}: humidity {h}% outside [0, 100]')

        if errors:
            for e in errors:
                _fail(e)
            sys.exit(1)

        if dht_seen:
            sample = readings[-1]
            _ok(f'DHT11 values in range — t={sample.get("t")}°C  h={sample.get("h")}%')
        else:
            print(
                '  [WARN] "t"/"h" absent in all readings — '
                'DHT11 may be unwired or returning NaN. '
                'Soil field "s" is still validated.'
            )

        # ── fan relay safe-idle command (matches Controller._set_fan(False)) ──
        off_val = 1 if settings.RELAY_ACTIVE_LOW else 0
        cmd = f'DOUT {settings.PIN_FAN_RELAY} {off_val}'
        _info(f'Sending {cmd} (fan relay idle)...')
        ser.write(f'{cmd}\n'.encode())
        ser.flush()
        time.sleep(0.1)
        _ok('Command sent without serial error')

    return readings


# ── Phase 2: SerialBoard abstraction layer ────────────────────────────────────


async def phase2_serial_board() -> SensorReading | None:
    print()
    print('Phase 2 - SerialBoard abstraction layer')
    print('-' * 40)

    board = SerialBoard(
        port=settings.SERIAL_PORT,
        baud=settings.SERIAL_BAUD,
        soil_adc_wet=settings.SOIL_ADC_WET,
        soil_adc_dry=settings.SOIL_ADC_DRY,
    )

    _info('Calling board.connect()...')
    try:
        await board.connect()
    except (ConnectionError, TimeoutError) as exc:
        _fail(f'board.connect() raised: {exc}')
        sys.exit(1)

    _ok(f'board.is_connected = {board.is_connected}')

    _info(f'Waiting {_BOARD_WARMUP}s for readings to accumulate...')
    await asyncio.sleep(_BOARD_WARMUP)

    reading = board.get_latest_reading()

    await board.disconnect()
    _ok('board.disconnect() completed')

    if reading is None:
        _fail(
            'get_latest_reading() returned None — '
            'no JSON frames were parsed by the background thread.'
        )
        sys.exit(1)

    _ok(f'SensorReading received at {reading.timestamp.strftime("%H:%M:%S")}')
    _info(f'  temperature      = {reading.temperature}°C')
    _info(f'  humidity_air     = {reading.humidity_air}%')
    _info(f'  humidity_soil_raw= {reading.humidity_soil_raw}')
    _info(f'  humidity_soil_pct= {reading.humidity_soil_pct:.1f}%')

    return reading


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    setup_logging()

    print('Hardware smoke test')
    print('=' * 45)
    print(f'MOCK_HARDWARE  = {settings.MOCK_HARDWARE}')
    print(f'SERIAL_PORT    = {settings.SERIAL_PORT}')
    print(f'SERIAL_BAUD    = {settings.SERIAL_BAUD}')

    if settings.MOCK_HARDWARE:
        print()
        print('[ERROR] MOCK_HARDWARE=true — this test requires real hardware.')
        print('        Set MOCK_HARDWARE=false in .env and re-run.')
        sys.exit(1)

    # Detect port once; both phases use the same device.
    if settings.SERIAL_PORT == 'AUTODETECT':
        port = _find_port()
        if port is None:
            print()
            print('[ERROR] No Arduino-compatible USB serial port detected.')
            print('        Troubleshooting:')
            print('          1. Check USB cable and connection.')
            print(
                '          2. Install CH340 driver (Windows: zadig or vendor installer).'
            )
            print(
                '          3. Open Device Manager → Ports to confirm the COM port appears.'
            )
            sys.exit(1)
        print(f'Auto-detected port: {port}')
    else:
        port = settings.SERIAL_PORT
        print(f'Using explicit port: {port}')

    phase1_raw_serial(port)

    asyncio.run(phase2_serial_board())

    print()
    print('=' * 45)
    print('ALL PHASES PASSED.')
    print()
    print('Next step: launch the full GUI app:')
    print('  poetry run python -m app')


if __name__ == '__main__':
    main()
