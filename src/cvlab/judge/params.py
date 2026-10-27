"""판정 설정값 (JudgeParams).

- 결정 근거는 docs/판정-규칙.md 와 config/judge.yaml 주석에 있다.
- U는 코드에 고정하지 않는다. 기본값 None이고, 판정할 때 출처 문자열(U_source)과 함께 반드시 넣어야 한다.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

import numpy as np

OUTLIER_PRIMARY = ("worse", "before", "after")
CELL_STATS = ("mean", "median")


def _pct_fraction(name: str, value: Any) -> Fraction:
    """문턱 백분율을 정확한 분수로 바꾼다 (정수 곱셈 비교용)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Fraction)):
        raise ValueError(f"{name}: 숫자가 아님 ({value!r})")
    f = Fraction(str(value)) if not isinstance(value, Fraction) else value
    if f < 0 or f > 100:
        raise ValueError(f"{name}: 0–100 범위 밖 ({value!r})")
    return f


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: 숫자가 아님 ({value!r})")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name}: 유한한 값이 아님 ({value!r})")
    return v


@dataclass(frozen=True)
class JudgeParams:
    T_mm: float = 0.20                 # D-05 확정
    U_mm: float | None = None          # 판정 때 반드시 지정. 기본값 두지 않음 (D-15 참고값은 문서에만)
    U_source: str | None = None        # U의 출처 문자열, 필수
    pass_min_pct: float = 95           # D-08
    fail_max_pct: float = 5            # 청사진 §2.3
    valid_min_pct: float = 90          # D-20 R2 확정
    cell_mm: float = 0.2               # D-20 R1 확정
    cell_mm_alt: float = 0.4           # D-20 R1 확정 (함께 보고)
    cell_fill_min: float = 0.5         # D-20 R6 확정
    region_fill_min: float = 1.0       # D-20 R6 확정
    cell_stat: str = "mean"            # D-20 R6 확정
    layer_fail_warn_pct: float = 50    # D-20 R7 확정
    outlier_primary: str = "worse"     # D-20 R3 확정
    cooled_delta_max_um: float = 5.0   # D-20 R4 확정
    cooled_alpha_um_per_m_c: float = 68.0  # PLA 열팽창 계수, 청사진 §1.2 (사용자 제시)

    def __post_init__(self) -> None:
        T = _finite_number("T_mm", self.T_mm)
        if T <= 0:
            raise ValueError(f"T_mm: 0보다 커야 함 ({self.T_mm!r})")
        for name in ("pass_min_pct", "fail_max_pct", "valid_min_pct", "layer_fail_warn_pct"):
            _pct_fraction(name, getattr(self, name))
        # J-1: 합이 100 미만이면 합격과 불합격이 함께 참일 수 있다 (decide는 합격을 먼저 봄)
        if _pct_fraction("pass_min_pct", self.pass_min_pct) + _pct_fraction("fail_max_pct", self.fail_max_pct) < 100:
            raise ValueError(
                f"pass_min_pct + fail_max_pct < 100 ({self.pass_min_pct!r} + {self.fail_max_pct!r}). "
                "합격과 불합격이 함께 참이 될 수 있음")
        for name in ("cell_mm", "cell_mm_alt"):
            if _finite_number(name, getattr(self, name)) <= 0:
                raise ValueError(f"{name}: 0보다 커야 함")
        for name in ("cell_fill_min", "region_fill_min"):
            v = _finite_number(name, getattr(self, name))
            if not (0 < v <= 1):
                raise ValueError(f"{name}: (0, 1] 범위 밖 ({v!r})")
        if self.cell_stat not in CELL_STATS:
            raise ValueError(f"cell_stat: {CELL_STATS} 중 하나여야 함 ({self.cell_stat!r})")
        if self.outlier_primary not in OUTLIER_PRIMARY:
            raise ValueError(f"outlier_primary: {OUTLIER_PRIMARY} 중 하나여야 함 ({self.outlier_primary!r})")
        if _finite_number("cooled_delta_max_um", self.cooled_delta_max_um) <= 0:
            raise ValueError("cooled_delta_max_um: 0보다 커야 함")
        if _finite_number("cooled_alpha_um_per_m_c", self.cooled_alpha_um_per_m_c) <= 0:
            raise ValueError("cooled_alpha_um_per_m_c: 0보다 커야 함")
        if self.U_source is not None and not isinstance(self.U_source, str):
            raise ValueError("U_source: 문자열이어야 함")

    # --- 판정 직전 검사 -------------------------------------------------
    def require_ready(self) -> None:
        """판정에 쓸 수 있는지 검사한다. U 없음 · NaN · 음수 · T 이상 · 출처 없음이면 ValueError."""
        check_U(self.T_mm, self.U_mm)
        if self.U_source is None or not str(self.U_source).strip():
            raise ValueError("U_source: U의 출처 문자열이 없음 (MF-JDG-01, 출처를 보고서에 적어야 함)")

    # --- 정수 비교용 분수 ------------------------------------------------
    def pct(self, name: str) -> Fraction:
        return _pct_fraction(name, getattr(self, name))

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "JudgeParams":
        """{'judge': {...}} 또는 평평한 dict를 받는다. 모르는 키는 오류."""
        if not isinstance(d, Mapping):
            raise ValueError("설정은 dict여야 함")
        if set(d.keys()) == {"judge"}:
            d = d["judge"]
            if not isinstance(d, Mapping):
                raise ValueError("judge: dict여야 함")
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(d.keys()) - known)
        if unknown:
            raise ValueError(f"모르는 설정 키: {unknown}")
        return cls(**dict(d))

    def to_dict(self) -> dict:
        return asdict(self)


def check_U(T_mm: float, U_mm: Any) -> float:
    """U 검사. 통과하면 float로 돌려준다."""
    if U_mm is None:
        raise ValueError("U_mm: 없음. U는 출처와 함께 반드시 지정해야 함")
    if isinstance(U_mm, (bool, np.bool_)) or not isinstance(U_mm, (int, float, np.integer, np.floating)):
        raise ValueError(f"U_mm: 숫자가 아님 ({U_mm!r})")
    U = float(U_mm)
    if math.isnan(U):
        raise ValueError("U_mm: NaN")
    if U < 0:
        raise ValueError(f"U_mm: 음수 ({U})")
    if U >= float(T_mm):
        raise ValueError(f"U_mm: T 이상 ({U} ≥ {T_mm}). 합격점이 생길 수 없음")
    return U


def load_params(path: str | Path, **override: Any) -> JudgeParams:
    """config/judge.yaml 을 yaml.safe_load로 직접 읽는다 (공통 설정 모듈은 쓰지 않음). override로 U 등을 넣는다."""
    import yaml  # 지역 import: 판정 계산 자체는 PyYAML 없이 돈다

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, Mapping) or set(raw.keys()) != {"judge"}:
        raise ValueError("judge.yaml: 최상위 키는 'judge' 하나여야 함")
    d = dict(raw["judge"] or {})
    known = {f.name for f in fields(JudgeParams)}
    bad = sorted(set(override) - known)
    if bad:
        raise ValueError(f"모르는 설정 키: {bad}")
    d.update(override)
    return JudgeParams.from_dict(d)
