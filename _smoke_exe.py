"""
CP-8 exe smoke test.

Launches dist/grow_control/grow_control.exe with MOCK_HARDWARE=true,
waits a few seconds, checks the process is alive (no immediate crash),
then terminates it cleanly.

Usage:
    poetry run python _smoke_exe.py
"""

from __future__ import annotations

import io
from pathlib import Path
import subprocess
import sys
import time

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

DIST = Path('dist') / 'grow_control'
EXE = DIST / 'grow_control.exe'
ENV_FILE = DIST / '.env'
LOG_FILE = DIST / 'grow_control.log'

STARTUP_WAIT = 6.0  # seconds to wait after launch before checking liveness


def _ok(msg: str) -> None:
    print(f'  [PASS] {msg}')


def _fail(msg: str) -> None:
    print(f'  [FAIL] {msg}')
    sys.exit(1)


def _info(msg: str) -> None:
    print(f'         {msg}')


def main() -> None:
    print('CP-8 exe smoke test')
    print('=' * 45)

    if not EXE.exists():
        _fail(f'{EXE} not found.\n         Run: poetry run python build.py')

    _ok(f'Executable found: {EXE}')

    # ── write a .env with MOCK_HARDWARE=true into the dist folder ────────────
    # This avoids needing the Arduino for the packaging smoke test.
    mock_env_content = (
        'LOG_LEVEL=DEBUG\n'
        'LOG_TO_GUI=false\n'
        'MOCK_HARDWARE=true\n'
        'SERIAL_PORT=AUTODETECT\n'
        'SERIAL_BAUD=115200\n'
        'TIMEZONE=Europe/Minsk\n'
    )
    ENV_FILE.write_text(mock_env_content, encoding='utf-8')
    _ok(f'.env written to dist (MOCK_HARDWARE=true): {ENV_FILE}')

    # ── launch exe ────────────────────────────────────────────────────────────
    _info(f'Launching {EXE.name} (cwd={DIST})...')
    proc = subprocess.Popen(
        [str(EXE)],
        cwd=str(DIST),  # .env and log file resolve relative to exe dir
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _info(f'Process started: PID {proc.pid}')
    _info(f'Waiting {STARTUP_WAIT}s for startup...')

    time.sleep(STARTUP_WAIT)

    # ── liveness check ────────────────────────────────────────────────────────
    exit_code = proc.poll()
    if exit_code is not None:
        _fail(
            f'Process exited immediately with code {exit_code}.\n'
            f'         Check {LOG_FILE} for details.'
        )

    _ok(f'Process still running after {STARTUP_WAIT}s (PID {proc.pid})')

    # ── log file check ────────────────────────────────────────────────────────
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        _ok(f'Log file created: {LOG_FILE} ({LOG_FILE.stat().st_size} bytes)')
        _info('Last 5 log lines:')
        lines = LOG_FILE.read_text(encoding='utf-8', errors='replace').splitlines()
        for line in lines[-5:]:
            _info(f'  {line}')
    else:
        _info(f'Log file not yet written (normal if app just started): {LOG_FILE}')

    # ── terminate ─────────────────────────────────────────────────────────────
    proc.terminate()
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    _ok(f'Process terminated cleanly (exit code {proc.returncode})')

    print()
    print('=' * 45)
    print('EXE smoke test PASSED - CP-8 complete.')
    print()
    print('For a real-hardware run, edit dist/grow_control/.env:')
    print('  MOCK_HARDWARE=false')
    print('Then double-click dist/grow_control/grow_control.exe')


if __name__ == '__main__':
    main()
