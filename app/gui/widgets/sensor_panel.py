from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QWidget

from app.hardware.base import SensorReading

_V = 'font-size: 26px; font-weight: bold; padding: 6px;'
_S_NORMAL: str = f'{_V} color: #27ae60;'
_S_ALERT_HIGH: str = f'{_V} color: #e74c3c;'
_S_ALERT_LOW: str = f'{_V} color: #e67e22;'
_S_NA: str = f'{_V} color: #95a5a6;'
_S_HDR = 'font-weight: bold; font-size: 12px;'


class SensorPanel(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__('Sensor Readings', parent)
        self._temp_threshold = 28.0
        self._soil_threshold = 40.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        grid = QGridLayout(self)
        grid.setSpacing(10)

        for col, title in enumerate(
            ('Temperature', 'Soil Moisture', 'Air Humidity (audit)')
        ):
            hdr = QLabel(title)
            hdr.setStyleSheet(_S_HDR)
            grid.addWidget(hdr, 0, col)

        self._temp_value = QLabel('--')
        self._temp_value.setStyleSheet(_S_NA)
        self._temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._temp_value, 1, 0)

        self._soil_value = QLabel('--')
        self._soil_value.setStyleSheet(_S_NA)
        self._soil_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._soil_value, 1, 1)

        self._hum_value = QLabel('--')
        self._hum_value.setStyleSheet(_S_NA)
        self._hum_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._hum_value, 1, 2)

        self._temp_thresh_lbl = QLabel('Threshold: -- °C')
        grid.addWidget(self._temp_thresh_lbl, 2, 0)

        self._soil_thresh_lbl = QLabel('Threshold: -- %')
        grid.addWidget(self._soil_thresh_lbl, 2, 1)

        self._soil_raw_lbl = QLabel('Raw ADC: --')
        self._soil_raw_lbl.setStyleSheet('font-size: 11px; color: #7f8c8d;')
        self._soil_raw_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._soil_raw_lbl, 3, 1)

    def set_thresholds(self, temp: float, soil: float) -> None:
        self._temp_threshold = temp
        self._soil_threshold = soil
        self._temp_thresh_lbl.setText(f'Threshold: {temp:.1f} °C')
        self._soil_thresh_lbl.setText(f'Threshold: {soil:.1f} %')

    def on_sensor_updated(self, reading: SensorReading) -> None:
        if reading.temperature is not None:
            t = reading.temperature
            self._temp_value.setText(f'{t:.1f} °C')
            self._temp_value.setStyleSheet(
                _S_ALERT_HIGH if t > self._temp_threshold else _S_NORMAL
            )
        if reading.humidity_soil_pct is not None:
            s = reading.humidity_soil_pct
            self._soil_value.setText(f'{s:.1f} %')
            self._soil_value.setStyleSheet(
                _S_ALERT_LOW if s < self._soil_threshold else _S_NORMAL
            )
        if reading.humidity_soil_raw is not None:
            self._soil_raw_lbl.setText(f'Raw ADC: {reading.humidity_soil_raw}')
        if reading.humidity_air is not None:
            self._hum_value.setText(f'{reading.humidity_air:.1f} %')
            self._hum_value.setStyleSheet(_S_NORMAL)

    def on_disconnected(self) -> None:
        for lbl in (self._temp_value, self._soil_value, self._hum_value):
            lbl.setText('--')
            lbl.setStyleSheet(_S_NA)
        self._soil_raw_lbl.setText('Raw ADC: --')
