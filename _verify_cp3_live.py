"""
CP-3 live actuator check — uses the same DOUT levels as Controller._set_fan.

Usage:
    poetry run python _verify_cp3_live.py

Watch relay LED and fan while this runs (9V toggle ON).
"""

from __future__ import annotations

import io
import sys
import time

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import serial  # type: ignore[import-untyped]
import serial.tools.list_ports  # type: ignore[import-untyped]

from app.core.config import settings

_HANDSHAKE = 'GROW_CTRL_READY'
_RESET_DELAY = 2.5


def _find_port() -> str:
    if settings.SERIAL_PORT != 'AUTODETECT':
        return settings.SERIAL_PORT
    keywords = ('arduino', 'ch340', 'ch341', 'cp210', 'ftdi', 'usb serial')
    for info in serial.tools.list_ports.comports():
        if any(kw in info.description.lower() for kw in keywords):
            return str(info.device)
    raise ConnectionError('No Arduino COM port found')


def _fan_dout_level(on: bool) -> int:
    level = on
    if settings.RELAY_ACTIVE_LOW:
        level = not on
    return 1 if level else 0


def _connect(port: str) -> serial.Serial:
    ser = serial.Serial(port, settings.SERIAL_BAUD, timeout=2)
    time.sleep(_RESET_DELAY)
    ser.reset_input_buffer()
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        if raw.decode('utf-8', errors='replace').strip() == _HANDSHAKE:
            return ser
    ser.close()
    raise TimeoutError('No GROW_CTRL_READY')


def _send_fan(ser: serial.Serial, on: bool) -> str:
    val = _fan_dout_level(on)
    cmd = f'DOUT {settings.PIN_FAN_RELAY} {val}'
    ser.write(f'{cmd}\n'.encode())
    ser.flush()
    return cmd


def main() -> None:
    port = _find_port()
    print(f'CP-3 live verify on {port}')
    print(
        f'PIN_FAN_RELAY={settings.PIN_FAN_RELAY} '
        f'RELAY_ACTIVE_LOW={settings.RELAY_ACTIVE_LOW}'
    )
    print('=' * 50)

    steps = [
        ('fan OFF (controller idle)', False),
        ('fan ON  (over-temp action)', True),
        ('fan OFF (back to normal)', False),
    ]
    for label, on in steps:
        ser = _connect(port)
        cmd = _send_fan(ser, on)
        time.sleep(0.8)
        ser.close()
        print(f'{label}: sent {cmd!r} -> watch relay LED / fan')
        time.sleep(2.0)

    ser = _connect(port)
    for cmd, label in [
        (f'SERVO {settings.PIN_SERVO} {settings.SERVO_STOP_ANGLE}', 'servo STOP'),
        (f'SERVO {settings.PIN_SERVO} {settings.SERVO_OPEN_ANGLE}', 'servo SPIN'),
        (f'SERVO {settings.PIN_SERVO} {settings.SERVO_STOP_ANGLE}', 'servo STOP'),
    ]:
        ser.write(f'{cmd}\n'.encode())
        ser.flush()
        time.sleep(0.8)
        print(f'{label}: sent {cmd!r}')
        time.sleep(2.0)
    ser.close()

    print('=' * 50)
    print('Done. Reply: fan ON/OFF steps and servo spin/stop matched expectation?')


if __name__ == '__main__':
    main()
