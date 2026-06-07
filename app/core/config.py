from pathlib import Path
import sys
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable).parent / '.env')
    return '.env'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore',
        env_file=_env_file(),
        env_file_encoding='utf-8',
    )

    LOG_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    LOG_TO_GUI: bool = False

    MOCK_HARDWARE: bool = False

    SERIAL_PORT: str = 'AUTODETECT'
    SERIAL_BAUD: int = 115200

    PIN_DHT: int = 4
    PIN_SOIL_ANALOG: int = 1
    PIN_FAN_RELAY: int = 8
    PIN_SERVO: int = 9

    # Reserved for a future single-colour LED (not wired yet).
    PIN_LED_FUTURE: int = 7

    # Used only when LED_HARDWARE_ENABLED=true (GUI simulation ignores these pins).
    PIN_LED_R: int = 2
    PIN_LED_G: int = 3
    PIN_LED_B: int = 5
    LED_COMMON_ANODE: bool = False

    # false = LED schedule runs in GUI only; no PWM/DOUT sent to Arduino.
    LED_HARDWARE_ENABLED: bool = False

    # JQC3F module on the bench: IN low energises the relay coil.
    RELAY_ACTIVE_LOW: bool = True

    # Continuous-rotation servo (S2): 90 = stop, 0 = spin CW (irrigation open).
    SERVO_STOP_ANGLE: int = Field(default=90, ge=0, le=180)
    SERVO_OPEN_ANGLE: int = Field(default=0, ge=0, le=180)

    SOIL_ADC_WET: int = 300
    SOIL_ADC_DRY: int = 900

    SENSOR_POLL_MS: int = 1000

    TIMEZONE: str = 'Europe/Minsk'


settings = Settings()  # type: ignore[call-arg]
