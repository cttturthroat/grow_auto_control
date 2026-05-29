from __future__ import annotations

from datetime import datetime, time, timedelta
import zoneinfo


class LedScheduler:
    def __init__(self, timezone: str) -> None:
        self._tz = zoneinfo.ZoneInfo(timezone)

    def now(self) -> datetime:
        return datetime.now(self._tz)

    def should_be_on(
        self,
        on_time: time,
        off_time: time,
        manual_override: bool | None,
    ) -> bool:
        if manual_override is not None:
            return manual_override
        current = self.now().time().replace(second=0, microsecond=0)
        return self._in_window(current, on_time, off_time)

    def seconds_to_next_change(self, on_time: time, off_time: time) -> int:
        now = self.now()
        currently_on = self._in_window(now.time(), on_time, off_time)
        target = off_time if currently_on else on_time

        next_change = now.replace(
            hour=target.hour,
            minute=target.minute,
            second=0,
            microsecond=0,
        )
        if next_change <= now:
            next_change += timedelta(days=1)

        return max(0, int((next_change - now).total_seconds()))

    @staticmethod
    def parse_time(time_str: str) -> time:
        hour_s, minute_s = time_str.split(':')
        return time(int(hour_s), int(minute_s))

    @staticmethod
    def _in_window(current: time, on_time: time, off_time: time) -> bool:
        if on_time <= off_time:
            return on_time <= current < off_time
        return current >= on_time or current < off_time
