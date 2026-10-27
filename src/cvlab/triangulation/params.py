"""T7a 추출 설정 (`config/triangulation.yaml`의 `triangulation` 묶음).

기본값은 `config/triangulation.yaml`과 같습니다 (시험이 두 값을 비교함).
교정값은 이 설정에 넣지 않습니다.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path

METHODS = ("max", "cog", "parabola3", "gauss3", "gaussfit", "steger")


@dataclass(frozen=True)
class TriParams:
    method: str = "cog"
    threshold_k_sigma: float = 5.0
    half_win_px: int | None = None
    guide_win_cols: int = 51
    guide_band_px: int | None = 8
    low_peak_factor: float = 3.0
    wide_factor: float = 2.0
    multi_peak_ratio: float = 0.3
    steger_sigma_px: float = 1.5
    gaussfit_max_iter: int = 10

    def __post_init__(self):
        if self.method not in METHODS:
            raise ValueError(f"method={self.method!r}: {METHODS} 중 하나여야 함")
        if not self.threshold_k_sigma > 0:
            raise ValueError("threshold_k_sigma > 0 이어야 함")
        if self.half_win_px is not None and int(self.half_win_px) < 1:
            raise ValueError("half_win_px는 null 또는 1 이상")
        if int(self.guide_win_cols) < 1 or int(self.guide_win_cols) % 2 == 0:
            raise ValueError("guide_win_cols는 1 이상 홀수")
        if self.guide_band_px is not None and int(self.guide_band_px) < 1:
            raise ValueError("guide_band_px는 null 또는 1 이상")
        for k in ("low_peak_factor", "wide_factor", "multi_peak_ratio", "steger_sigma_px"):
            if not getattr(self, k) > 0:
                raise ValueError(f"{k} > 0 이어야 함")
        if int(self.gaussfit_max_iter) < 1:
            raise ValueError("gaussfit_max_iter ≥ 1")

    @classmethod
    def from_dict(cls, d: dict | None) -> "TriParams":
        """`triangulation` 묶음 안쪽 dict에서 만듦. 모르는 키는 ValueError."""
        d = dict(d or {})
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(d) - known)
        if unknown:
            raise ValueError(f"triangulation 설정에 모르는 키: {unknown}")
        return cls(**d)

    @classmethod
    def from_yaml(cls, path) -> "TriParams":
        """최상위 키 `triangulation` 하나인 YAML에서 만듦."""
        import yaml

        with open(Path(path), encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        if set(doc) != {"triangulation"}:
            raise ValueError(f"{path}: 최상위 키는 triangulation 하나여야 함 (있음: {sorted(doc)})")
        return cls.from_dict(doc["triangulation"])

    def replace(self, **kw) -> "TriParams":
        return dataclasses.replace(self, **kw)
