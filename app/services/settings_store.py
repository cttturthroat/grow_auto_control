from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.core.logging import get_logger
from app.utils.paths import resource_path

_logger = get_logger(__name__)


@dataclass
class RuntimeSettings:
    temp_threshold: float = 28.0
    temp_hysteresis: float = 1.0
    soil_threshold_pct: float = 40.0
    soil_hysteresis_pct: float = 5.0
    led_on_time: str = '20:15'
    led_off_time: str = '06:30'
    led_manual_override: bool | None = None


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else resource_path('settings.json')

    def load(self) -> RuntimeSettings:
        if not self._path.exists():
            default = RuntimeSettings()
            self.save(default)
            _logger.info(f'Created default settings at {self._path}')
            return default
        try:
            with self._path.open(encoding='utf-8') as f:
                raw: object = json.load(f)
            if not isinstance(raw, dict):
                return RuntimeSettings()
            return self._from_dict(raw)
        except (json.JSONDecodeError, OSError) as exc:
            _logger.warning(f'Could not load {self._path}: {exc} — using defaults')
            return RuntimeSettings()

    def save(self, s: RuntimeSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, object] = {
            'temp_threshold': s.temp_threshold,
            'temp_hysteresis': s.temp_hysteresis,
            'soil_threshold_pct': s.soil_threshold_pct,
            'soil_hysteresis_pct': s.soil_hysteresis_pct,
            'led_on_time': s.led_on_time,
            'led_off_time': s.led_off_time,
            'led_manual_override': s.led_manual_override,
        }
        with self._path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _from_dict(data: dict[str, object]) -> RuntimeSettings:
        def get_float(key: str, default: float) -> float:
            v = data.get(key, default)
            return float(v) if isinstance(v, (int, float)) else default

        def get_str(key: str, default: str) -> str:
            v = data.get(key, default)
            return v if isinstance(v, str) else default

        def get_bool_or_none(key: str) -> bool | None:
            v = data.get(key)
            return v if isinstance(v, bool) else None

        return RuntimeSettings(
            temp_threshold=get_float('temp_threshold', 28.0),
            temp_hysteresis=get_float('temp_hysteresis', 1.0),
            soil_threshold_pct=get_float('soil_threshold_pct', 40.0),
            soil_hysteresis_pct=get_float('soil_hysteresis_pct', 5.0),
            led_on_time=get_str('led_on_time', '20:15'),
            led_off_time=get_str('led_off_time', '06:30'),
            led_manual_override=get_bool_or_none('led_manual_override'),
        )
