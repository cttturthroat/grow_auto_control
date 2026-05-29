from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QWidget

_S_ON = 'font-weight: bold; color: #27ae60;'
_S_OFF = 'font-weight: bold; color: #95a5a6;'


class ActuatorPanel(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__('Actuators', parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self._fan_label = QLabel('OFF')
        self._fan_label.setStyleSheet(_S_OFF)
        layout.addRow('Fan (relay):', self._fan_label)

        self._servo_label = QLabel('CLOSED')
        self._servo_label.setStyleSheet(_S_OFF)
        layout.addRow('Servo (irrigation):', self._servo_label)

    def on_fan_state_changed(self, is_on: bool) -> None:
        self._fan_label.setText('ON' if is_on else 'OFF')
        self._fan_label.setStyleSheet(_S_ON if is_on else _S_OFF)

    def on_servo_state_changed(self, is_open: bool) -> None:
        self._servo_label.setText('OPEN' if is_open else 'CLOSED')
        self._servo_label.setStyleSheet(_S_ON if is_open else _S_OFF)
