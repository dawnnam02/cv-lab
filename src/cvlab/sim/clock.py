# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""가상 시계 (세부청사진 §6.8). 벽시계를 쓰지 않는다.

캠페인 시작 시각 (설정값, 시간대 포함 ISO 8601)에서 정수 나노초로 센다. meta.datetime · cal.created ·
t_ns는 모두 이 시계에서 나온다. 같은 설정이면 같은 시각 열이 나온다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

NS = 1_000_000_000


class VirtualClock:
    def __init__(self, start_iso: str):
        start = datetime.fromisoformat(start_iso)
        if start.tzinfo is None:
            raise ValueError("시작 시각에 시간대가 없음 (예: 2026-11-20T09:00:00+09:00)")
        self._start = start
        delta = start - datetime(1970, 1, 1, tzinfo=timezone.utc)
        self._start_ns = (delta.days * 86400 + delta.seconds) * NS + delta.microseconds * 1000
        self._elapsed_ns = 0

    @property
    def start_ns(self) -> int:
        return self._start_ns

    @property
    def t_ns(self) -> int:
        """지금 가상 시각 (유닉스 기준 ns, 정수)."""
        return self._start_ns + self._elapsed_ns

    @property
    def elapsed_s(self) -> float:
        return self._elapsed_ns / NS

    def advance(self, seconds: float) -> int:
        """seconds만큼 앞으로 (ns 반올림). 음수는 오류. 새 시각 (ns)을 돌려줌."""
        ns = int(round(float(seconds) * NS))
        if ns < 0:
            raise ValueError("가상 시계는 뒤로 가지 않음")
        self._elapsed_ns += ns
        return self.t_ns

    def iso(self, timespec: str = "seconds") -> str:
        us = self._elapsed_ns // 1000
        return (self._start + timedelta(microseconds=us)).isoformat(timespec=timespec)

    def fork(self) -> "VirtualClock":
        """같은 시각에서 따로 가는 시계 (병렬 작업용: 계획에서 정한 시각으로 시작)."""
        c = VirtualClock(self._start.isoformat())
        c._elapsed_ns = self._elapsed_ns
        return c
