from __future__ import annotations

from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTimeEdit,
    QWidget,
)

from app.services.settings_store import RuntimeSettings


class SettingsPanel(QGroupBox):
    settings_applied = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__('Settings', parent)
        self._led_manual_override: bool | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(8)

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 60.0)
        self._temp_spin.setSingleStep(0.5)
        self._temp_spin.setDecimals(1)
        self._temp_spin.setSuffix(' °C')
        layout.addRow('Temp threshold:', self._temp_spin)

        self._temp_hyst_spin = QDoubleSpinBox()
        self._temp_hyst_spin.setRange(0.0, 10.0)
        self._temp_hyst_spin.setSingleStep(0.1)
        self._temp_hyst_spin.setDecimals(1)
        self._temp_hyst_spin.setSuffix(' °C')
        layout.addRow('Temp hysteresis:', self._temp_hyst_spin)

        self._soil_spin = QDoubleSpinBox()
        self._soil_spin.setRange(0.0, 100.0)
        self._soil_spin.setSingleStep(1.0)
        self._soil_spin.setDecimals(1)
        self._soil_spin.setSuffix(' %')
        layout.addRow('Soil threshold:', self._soil_spin)

        self._soil_hyst_spin = QDoubleSpinBox()
        self._soil_hyst_spin.setRange(0.0, 20.0)
        self._soil_hyst_spin.setSingleStep(0.5)
        self._soil_hyst_spin.setDecimals(1)
        self._soil_hyst_spin.setSuffix(' %')
        layout.addRow('Soil hysteresis:', self._soil_hyst_spin)

        self._led_on_edit = QTimeEdit()
        self._led_on_edit.setDisplayFormat('HH:mm')
        layout.addRow('LED ON time:', self._led_on_edit)

        self._led_off_edit = QTimeEdit()
        self._led_off_edit.setDisplayFormat('HH:mm')
        layout.addRow('LED OFF time:', self._led_off_edit)

        self._error_label = QLabel('')
        self._error_label.setStyleSheet('color: #e74c3c; font-size: 11px;')
        layout.addRow(self._error_label)

        self._apply_btn = QPushButton('Apply')
        self._apply_btn.clicked.connect(self._on_apply)  # type: ignore[attr-defined]
        layout.addRow(self._apply_btn)

    def populate(self, s: RuntimeSettings) -> None:
        self._led_manual_override = s.led_manual_override
        self._temp_spin.setValue(s.temp_threshold)
        self._temp_hyst_spin.setValue(s.temp_hysteresis)
        self._soil_spin.setValue(s.soil_threshold_pct)
        self._soil_hyst_spin.setValue(s.soil_hysteresis_pct)
        try:
            h_on, m_on = (int(p) for p in s.led_on_time.split(':'))
            h_off, m_off = (int(p) for p in s.led_off_time.split(':'))
            self._led_on_edit.setTime(QTime(h_on, m_on))
            self._led_off_edit.setTime(QTime(h_off, m_off))
        except ValueError:
            pass

    def _on_apply(self, _checked: bool = False) -> None:
        on_t = self._led_on_edit.time()
        off_t = self._led_off_edit.time()
        if on_t == off_t:
            self._error_label.setText('LED ON and OFF times must differ.')
            return
        self._error_label.setText('')
        new_settings = RuntimeSettings(
            temp_threshold=self._temp_spin.value(),
            temp_hysteresis=self._temp_hyst_spin.value(),
            soil_threshold_pct=self._soil_spin.value(),
            soil_hysteresis_pct=self._soil_hyst_spin.value(),
            led_on_time=f'{on_t.hour():02d}:{on_t.minute():02d}',
            led_off_time=f'{off_t.hour():02d}:{off_t.minute():02d}',
            led_manual_override=self._led_manual_override,
        )
        self.settings_applied.emit(new_settings)  # type: ignore[attr-defined]

    def set_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self._temp_spin,
            self._temp_hyst_spin,
            self._soil_spin,
            self._soil_hyst_spin,
            self._led_on_edit,
            self._led_off_edit,
            self._apply_btn,
        ):
            widget.setEnabled(enabled)
