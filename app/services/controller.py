from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, Signal

from app.core.config import Settings
from app.core.logging import get_logger
from app.hardware.base import BoardGateway, SensorReading
from app.services.led_scheduler import LedScheduler
from app.services.settings_store import SettingsStore

_logger = get_logger(__name__)

_RECONNECT_DELAY = 5.0
_LED_RGB_ON: tuple[float, float, float] = (1.0, 0.0, 1.0)
_LED_RGB_OFF: tuple[float, float, float] = (0.0, 0.0, 0.0)


class Controller(QObject):
    sensor_updated = Signal(object)
    connection_changed = Signal(bool)
    fan_state_changed = Signal(bool)
    servo_state_changed = Signal(bool)
    led_state_changed = Signal(bool)

    def __init__(
        self,
        board: BoardGateway,
        store: SettingsStore,
        cfg: Settings,
    ) -> None:
        super().__init__()
        self._board = board
        self._store = store
        self._cfg = cfg
        self._settings = store.load()
        self._scheduler = LedScheduler(cfg.TIMEZONE)
        self._fan_on = False
        self._servo_open = False
        self._led_on = False
        self._link_up = False

    def reload_settings(self) -> None:
        self._settings = self._store.load()
        _logger.debug('Runtime settings reloaded')

    def set_led_override(self, override: bool | None) -> None:
        self._settings.led_manual_override = override
        self._store.save(self._settings)
        label = {True: 'Force ON', False: 'Force OFF', None: 'Auto'}[override]
        _logger.info(f'LED override set to: {label}')

    async def run(self) -> None:
        _logger.info('Controller started')
        while True:
            try:
                if not self._board.is_connected:
                    if self._link_up:
                        self._on_link_lost()
                    await self._board.connect()
                    self._on_link_restored()

                reading = self._board.get_latest_reading()
                if reading is not None:
                    self.sensor_updated.emit(reading)  # type: ignore[attr-defined]
                    self._check_temperature(reading)
                    self._check_soil(reading)
                elif not self._board.is_connected and self._link_up:
                    self._on_link_lost()

                self._check_led()

            except asyncio.CancelledError:
                raise
            except (ConnectionError, TimeoutError, OSError) as exc:
                _logger.warning(f'Hardware connection failed: {exc}')
                if self._link_up:
                    self._on_link_lost()
                await asyncio.sleep(_RECONNECT_DELAY)
                continue
            except Exception as exc:
                _logger.error(f'Unexpected controller error: {exc}')

            await asyncio.sleep(self._cfg.SENSOR_POLL_MS / 1000.0)

    async def stop(self) -> None:
        if self._link_up:
            self._on_link_lost()
        await self._board.disconnect()
        _logger.info('Controller stopped')

    def _on_link_lost(self) -> None:
        if self._fan_on:
            self._fan_on = False
            self.fan_state_changed.emit(False)  # type: ignore[attr-defined]
        if self._servo_open:
            self._servo_open = False
            self.servo_state_changed.emit(False)  # type: ignore[attr-defined]
        self._link_up = False
        self.connection_changed.emit(False)  # type: ignore[attr-defined]

    def _on_link_restored(self) -> None:
        # Arduino resets on reconnect; re-apply actuator logic from fresh readings.
        self._fan_on = False
        self._servo_open = False
        self._link_up = True
        self.connection_changed.emit(True)  # type: ignore[attr-defined]
        _logger.info('Board connected')

    def _set_fan(self, on: bool) -> None:
        level = on
        if self._cfg.RELAY_ACTIVE_LOW:
            level = not on
        self._board.set_digital(self._cfg.PIN_FAN_RELAY, level)

    def _set_servo_open(self, open_val: bool) -> None:
        angle = self._cfg.SERVO_OPEN_ANGLE if open_val else self._cfg.SERVO_STOP_ANGLE
        self._board.set_servo(self._cfg.PIN_SERVO, angle)

    def _check_temperature(self, reading: SensorReading) -> None:
        if reading.temperature is None:
            return
        temp = reading.temperature
        threshold = self._settings.temp_threshold
        hysteresis = self._settings.temp_hysteresis

        if not self._fan_on and temp > threshold:
            self._fan_on = True
            self._set_fan(True)
            self.fan_state_changed.emit(True)  # type: ignore[attr-defined]
            _logger.info(f'Fan ON  (T={temp:.1f}°C > {threshold:.1f}°C)')
        elif self._fan_on and temp < (threshold - hysteresis):
            self._fan_on = False
            self._set_fan(False)
            self.fan_state_changed.emit(False)  # type: ignore[attr-defined]
            _logger.info(f'Fan OFF (T={temp:.1f}°C < {threshold - hysteresis:.1f}°C)')

    def _check_soil(self, reading: SensorReading) -> None:
        if reading.humidity_soil_pct is None:
            return
        pct = reading.humidity_soil_pct
        threshold = self._settings.soil_threshold_pct
        hysteresis = self._settings.soil_hysteresis_pct

        if not self._servo_open and pct < threshold:
            self._servo_open = True
            self._set_servo_open(True)
            self.servo_state_changed.emit(True)  # type: ignore[attr-defined]
            _logger.info(f'Servo OPEN  (soil={pct:.1f}% < {threshold:.1f}%)')
        elif self._servo_open and pct > (threshold + hysteresis):
            self._servo_open = False
            self._set_servo_open(False)
            self.servo_state_changed.emit(False)  # type: ignore[attr-defined]
            _logger.info(
                f'Servo CLOSE (soil={pct:.1f}% > {threshold + hysteresis:.1f}%)'
            )

    def _check_led(self) -> None:
        try:
            on_time = self._scheduler.parse_time(self._settings.led_on_time)
            off_time = self._scheduler.parse_time(self._settings.led_off_time)
        except ValueError as exc:
            _logger.warning(f'Invalid LED schedule time: {exc}')
            return

        should_on = self._scheduler.should_be_on(
            on_time, off_time, self._settings.led_manual_override
        )
        if should_on == self._led_on:
            return

        self._led_on = should_on
        if self._cfg.LED_HARDWARE_ENABLED:
            rgb = _LED_RGB_ON if should_on else _LED_RGB_OFF
            self._set_rgb(rgb[0], rgb[1], rgb[2])
            _logger.info(f'LED {"ON" if should_on else "OFF"} (hardware)')
        else:
            _logger.info(f'LED {"ON" if should_on else "OFF"} (simulated)')
        self.led_state_changed.emit(should_on)  # type: ignore[attr-defined]

    def _set_rgb(self, r: float, g: float, b: float) -> None:
        inv = self._cfg.LED_COMMON_ANODE
        self._board.set_pwm(self._cfg.PIN_LED_R, 1.0 - r if inv else r)
        self._board.set_pwm(self._cfg.PIN_LED_G, 1.0 - g if inv else g)
        self._board.set_pwm(self._cfg.PIN_LED_B, 1.0 - b if inv else b)
