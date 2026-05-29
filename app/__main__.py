from __future__ import annotations

import asyncio
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.gui.main_window import MainWindow
from app.hardware.mock_board import MockBoard
from app.hardware.serial_board import SerialBoard
from app.services.controller import Controller
from app.services.settings_store import SettingsStore

_logger = get_logger(__name__)


def _build_board() -> MockBoard | SerialBoard:
    if settings.MOCK_HARDWARE:
        return MockBoard(
            soil_adc_wet=settings.SOIL_ADC_WET,
            soil_adc_dry=settings.SOIL_ADC_DRY,
        )
    return SerialBoard(
        port=settings.SERIAL_PORT,
        baud=settings.SERIAL_BAUD,
        soil_adc_wet=settings.SOIL_ADC_WET,
        soil_adc_dry=settings.SOIL_ADC_DRY,
    )


def main() -> None:
    setup_logging()
    _logger.info(
        f'Grow Auto Control starting — '
        f'mock={settings.MOCK_HARDWARE} '
        f'port={settings.SERIAL_PORT} '
        f'log_level={settings.LOG_LEVEL}'
    )

    app = QApplication(sys.argv)
    app.setApplicationName('Grow Auto Control')
    app.setApplicationVersion('0.1.0')
    app.setOrganizationName('GrowCtrl')

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    board = _build_board()
    store = SettingsStore()
    ctrl = Controller(board, store, settings)

    window = MainWindow(ctrl, settings, store)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == '__main__':
    main()
