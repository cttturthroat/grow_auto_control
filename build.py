"""
One-command build helper.

Usage:
    poetry run python build.py

Steps:
  1. Runs PyInstaller with grow_control.spec.
  2. Copies .env.example to dist/grow_control/ (next to the exe) so users
     can find it easily and rename/edit it to .env before first launch.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

DIST = Path('dist') / 'grow_control'
SPEC = Path('grow_control.spec')


def main() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', str(SPEC), '--noconfirm'],
        check=False,
    )
    if result.returncode != 0:
        print(f'PyInstaller failed with exit code {result.returncode}')
        sys.exit(result.returncode)

    src = DIST / '_internal' / '.env.example'
    dst = DIST / '.env.example'
    if src.exists():
        shutil.copy2(src, dst)
        print(f'Copied .env.example -> {dst}')
    else:
        print(f'WARNING: {src} not found — .env.example not copied to dist root.')

    print()
    print('Build finished.')
    print(f'Executable: {(DIST / "grow_control.exe").resolve()}')
    print()
    print('Next steps for end-user deployment:')
    print(f'  1. Copy {DIST.resolve()} to any location.')
    print('  2. Copy .env.example -> .env and edit settings.')
    print('  3. Double-click grow_control.exe.')


if __name__ == '__main__':
    main()
