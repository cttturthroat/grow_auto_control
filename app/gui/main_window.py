from __future__ import annotations

import asyncio
import contextlib

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.config import Settings
from app.core.logging import add_gui_sink, get_logger, remove_gui_sink
from app.gui.widgets.actuator_panel import ActuatorPanel
from app.gui.widgets.led_panel import LedPanel
from app.gui.widgets.log_panel import LogPanel
from app.gui.widgets.sensor_panel import SensorPanel
from app.gui.widgets.settings_panel import SettingsPanel
from app.hardware.base import SensorReading
from app.services.controller import Controller
from app.services.settings_store import RuntimeSettings, SettingsStore

_logger = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, ctrl: Controller, cfg: Settings, store: SettingsStore) -> None:
        super().__init__()
        self._ctrl = ctrl
        self._cfg = cfg
        self._store = store
        self._ctrl_task: asyncio.Task[None] | None = None
        self._shutting_down = False
        self._gui_sink_id: int | None = None
        self._runtime_settings = store.load()
        self._setup_ui()
        self._connect_signals()
        self._apply_initial_settings()

    # ------------------------------------------------------------------ UI --

    def _setup_ui(self) -> None:
        self.setWindowTitle('Grow Auto Control')
        self.setMinimumSize(960, 640)
        self.resize(1200, 780)

        # --- central splitter (top panels / bottom log) ---
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(self._splitter)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(12, 12, 12, 8)
        top_layout.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)

        self._sensor_panel = SensorPanel()
        grid.addWidget(self._sensor_panel, 0, 0)

        self._led_panel = LedPanel(self._ctrl, self._cfg)
        grid.addWidget(self._led_panel, 0, 1)

        self._settings_panel = SettingsPanel()
        grid.addWidget(self._settings_panel, 1, 0)

        self._actuator_panel = ActuatorPanel()
        grid.addWidget(self._actuator_panel, 1, 1)

        top_layout.addLayout(grid)
        self._splitter.addWidget(top)

        # --- log panel (hidden until toggled) ---
        self._log_panel = LogPanel()
        self._splitter.addWidget(self._log_panel)
        self._splitter.setCollapsible(1, True)
        self._log_panel.hide()

        # --- status bar ---
        self.statusBar().showMessage('Disconnected')
        self._log_toggle_btn = QPushButton('Show Logs')
        self._log_toggle_btn.setCheckable(True)
        self._log_toggle_btn.setFlat(True)
        self._log_toggle_btn.toggled.connect(  # type: ignore[attr-defined]
            self._toggle_log_panel
        )
        self.statusBar().addPermanentWidget(self._log_toggle_btn)

    def _connect_signals(self) -> None:
        self._ctrl.connection_changed.connect(  # type: ignore[attr-defined]
            self._on_connection_changed
        )
        self._ctrl.sensor_updated.connect(  # type: ignore[attr-defined]
            self._on_sensor_updated
        )
        self._ctrl.fan_state_changed.connect(  # type: ignore[attr-defined]
            self._on_fan_state_changed
        )
        self._ctrl.servo_state_changed.connect(  # type: ignore[attr-defined]
            self._on_servo_state_changed
        )
        self._ctrl.led_state_changed.connect(  # type: ignore[attr-defined]
            self._on_led_state_changed
        )
        self._settings_panel.settings_applied.connect(  # type: ignore[attr-defined]
            self._on_settings_applied
        )

    def _apply_initial_settings(self) -> None:
        s = self._runtime_settings
        self._sensor_panel.set_thresholds(s.temp_threshold, s.soil_threshold_pct)
        self._led_panel.update_schedule(s.led_on_time, s.led_off_time)
        self._settings_panel.populate(s)

    # ------------------------------------------------------- Qt overrides --

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self._ctrl_task is None:
            self._ctrl_task = asyncio.ensure_future(self._ctrl.run())
        if self._cfg.LOG_TO_GUI and not self._log_toggle_btn.isChecked():
            self._log_toggle_btn.setChecked(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._shutting_down:
            event.accept()
            return
        event.ignore()
        asyncio.ensure_future(self._shutdown())  # noqa: RUF006

    # -------------------------------------------------- async lifecycle  --

    async def _shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        _logger.info('Shutting down…')
        if self._ctrl_task is not None:
            self._ctrl_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ctrl_task
        if self._gui_sink_id is not None:
            remove_gui_sink(self._gui_sink_id)
            self._gui_sink_id = None
        await self._ctrl.stop()
        app = QCoreApplication.instance()
        if app is not None:
            app.quit()

    # ----------------------------------------------------------- slots  --

    def _toggle_log_panel(self, checked: bool) -> None:
        if checked:
            if self._gui_sink_id is None:
                self._gui_sink_id = add_gui_sink(self._log_panel.append_message)
            self._log_panel.show()
            total = self._splitter.height()
            self._splitter.setSizes([total * 3 // 4, total // 4])
            self._log_toggle_btn.setText('Hide Logs')
        else:
            self._log_panel.hide()
            self._log_toggle_btn.setText('Show Logs')

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self.statusBar().showMessage('Connected')
        else:
            self.statusBar().showMessage('Disconnected')
            self._sensor_panel.on_disconnected()

    def _on_sensor_updated(self, reading: object) -> None:
        if isinstance(reading, SensorReading):
            self._sensor_panel.on_sensor_updated(reading)

    def _on_fan_state_changed(self, is_on: bool) -> None:
        self._actuator_panel.on_fan_state_changed(is_on)

    def _on_servo_state_changed(self, is_open: bool) -> None:
        self._actuator_panel.on_servo_state_changed(is_open)

    def _on_led_state_changed(self, is_on: bool) -> None:
        self._led_panel.on_led_state_changed(is_on)

    def _on_settings_applied(self, new_settings: object) -> None:
        if not isinstance(new_settings, RuntimeSettings):
            return
        self._store.save(new_settings)
        self._runtime_settings = new_settings
        self._ctrl.reload_settings()
        self._sensor_panel.set_thresholds(
            new_settings.temp_threshold, new_settings.soil_threshold_pct
        )
        self._led_panel.update_schedule(
            new_settings.led_on_time, new_settings.led_off_time
        )
        self.statusBar().showMessage('Settings saved.', 3000)
        _logger.info('Runtime settings updated from GUI')
