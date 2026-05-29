from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import Settings
from app.services.controller import Controller
from app.services.led_scheduler import LedScheduler

_S_ON = 'font-size: 20px; font-weight: bold; color: #27ae60;'
_S_OFF = 'font-size: 20px; font-weight: bold; color: #95a5a6;'
_S_OVERRIDE = 'font-size: 11px; color: #e67e22;'


def _fmt_countdown(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h > 0:
        return f'{h}h {m:02d}m {s:02d}s'
    if m > 0:
        return f'{m}m {s:02d}s'
    return f'{s}s'


class LedPanel(QGroupBox):
    def __init__(
        self, ctrl: Controller, cfg: Settings, parent: QWidget | None = None
    ) -> None:
        super().__init__('LED Schedule', parent)
        self._ctrl = ctrl
        self._scheduler = LedScheduler(cfg.TIMEZONE)
        self._on_time_str = '20:15'
        self._off_time_str = '06:30'
        self._setup_ui()
        self._start_timer()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._status_label = QLabel('● OFF')
        self._status_label.setStyleSheet(_S_OFF)
        layout.addWidget(self._status_label)

        self._schedule_label = QLabel(
            f'Schedule:  {self._on_time_str}  →  {self._off_time_str}'
        )
        layout.addWidget(self._schedule_label)

        self._countdown_label = QLabel('Next change in: ...')
        layout.addWidget(self._countdown_label)

        self._override_label = QLabel('')
        self._override_label.setStyleSheet(_S_OVERRIDE)
        layout.addWidget(self._override_label)

        btn_row = QHBoxLayout()
        self._force_on_btn = QPushButton('Force ON')
        self._force_off_btn = QPushButton('Force OFF')
        self._auto_btn = QPushButton('Auto')
        self._auto_btn.setEnabled(False)
        btn_row.addWidget(self._force_on_btn)
        btn_row.addWidget(self._force_off_btn)
        btn_row.addWidget(self._auto_btn)
        layout.addLayout(btn_row)

        self._force_on_btn.clicked.connect(self._on_force_on)  # type: ignore[attr-defined]
        self._force_off_btn.clicked.connect(self._on_force_off)  # type: ignore[attr-defined]
        self._auto_btn.clicked.connect(self._on_auto)  # type: ignore[attr-defined]

    def _start_timer(self) -> None:
        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._update_countdown)  # type: ignore[attr-defined]
        timer.start()

    # ---------------------------------------------------------------- slots --

    def _on_force_on(self, _checked: bool = False) -> None:
        self._ctrl.set_led_override(True)
        self._set_override_ui(True)

    def _on_force_off(self, _checked: bool = False) -> None:
        self._ctrl.set_led_override(False)
        self._set_override_ui(False)

    def _on_auto(self, _checked: bool = False) -> None:
        self._ctrl.set_led_override(None)
        self._set_override_ui(None)

    # ----------------------------------------------------------- public API --

    def update_schedule(self, on_time: str, off_time: str) -> None:
        self._on_time_str = on_time
        self._off_time_str = off_time
        self._schedule_label.setText(f'Schedule:  {on_time}  →  {off_time}')

    def on_led_state_changed(self, is_on: bool) -> None:
        if is_on:
            self._status_label.setText('● ON')
            self._status_label.setStyleSheet(_S_ON)
        else:
            self._status_label.setText('● OFF')
            self._status_label.setStyleSheet(_S_OFF)

    # ------------------------------------------------------------ internals --

    def _set_override_ui(self, override: bool | None) -> None:
        if override is True:
            self._override_label.setText('Override: Force ON')
            self._auto_btn.setEnabled(True)
        elif override is False:
            self._override_label.setText('Override: Force OFF')
            self._auto_btn.setEnabled(True)
        else:
            self._override_label.setText('')
            self._auto_btn.setEnabled(False)

    def _update_countdown(self) -> None:
        try:
            on_t = LedScheduler.parse_time(self._on_time_str)
            off_t = LedScheduler.parse_time(self._off_time_str)
            secs = self._scheduler.seconds_to_next_change(on_t, off_t)
            self._countdown_label.setText(f'Next change in: {_fmt_countdown(secs)}')
        except ValueError:
            self._countdown_label.setText('Next change in: invalid schedule')
