"""
CP-2 live matrix — sends DOUT/SERVO commands over serial.

Brother must flash arduino/grow_control/grow_control.ino before running.

Usage:
    poetry run python _probe_cp2.py

Watch the bench and compare with EXPECTED below.
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


def _connect(port: str) -> serial.Serial:
    ser = serial.Serial(port, settings.SERIAL_BAUD, timeout=2)
    time.sleep(_RESET_DELAY)
    ser.reset_input_buffer()
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode('utf-8', errors='replace').strip()
        if line == _HANDSHAKE:
            return ser
    ser.close()
    raise TimeoutError('No GROW_CTRL_READY — re-flash grow_control.ino?')


def _send(ser: serial.Serial, cmd: str) -> None:
    ser.write(f'{cmd}\n'.encode())
    ser.flush()


STEPS: list[tuple[str, str | None, str]] = [
    (
        '1_after_reset',
        None,
        'Relay red LED OFF, servo STOP, fan STOP',
    ),
    (
        '2_relay_off',
        'DOUT 8 1',
        'Relay red LED OFF, fan STOP',
    ),
    (
        '3_relay_on',
        'DOUT 8 0',
        'Relay red LED ON, fan SPINS (9V on)',
    ),
    (
        '4_relay_off_again',
        'DOUT 8 1',
        'Relay red LED OFF, fan STOP',
    ),
    (
        '5_servo_stop',
        'SERVO 9 90',
        'Servo STOP',
    ),
    (
        '6_servo_spin',
        'SERVO 9 0',
        'Servo spins CW',
    ),
    (
        '7_servo_stop_again',
        'SERVO 9 90',
        'Servo STOP',
    ),
]


def main() -> None:
    port = _find_port()
    print(f'CP-2 matrix on {port} @ {settings.SERIAL_BAUD}')
    print('=' * 60)

    for step_id, cmd, expected in STEPS:
        ser = _connect(port)
        if cmd is not None:
            _send(ser, cmd)
            time.sleep(0.6)
        ser.close()
        print(f'\n[{step_id}]')
        if cmd:
            print(f'  SENT:     {cmd!r}')
        print(f'  EXPECTED: {expected}')
        print('  YOUR EYES: relay LED / fan / servo ?')
        time.sleep(2.0)

    print('\n' + '=' * 60)
    print('Matrix finished. Reply with observations for each step 1-7.')


if __name__ == '__main__':
    main()
