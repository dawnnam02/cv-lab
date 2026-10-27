"""판정 영역 설정 (config/region.yaml 의 `region` 절).

기본값 = config/region.yaml (시험 test_region_params_yaml_equals_defaults). 모르는 키는 오류.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields
from fractions import Fraction
from typing import Any

CAMERA_SIDES = ("+y", "-y", "both")
DEFAULT_EXCLUDE = ("SKIRT", "BRIM", "SUPPORT", "PRIME-TOWER")


def _num(name: str, v, *, pos: bool = False, nonneg: bool = False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{name}: 숫자가 아님 ({v!r})")
    v = float(v)
    if not math.isfinite(v):
        raise ValueError(f"{name}: 유한한 값이 아님")
    if pos and v <= 0:
        raise ValueError(f"{name}: 0보다 커야 함 ({v})")
    if nonneg and v < 0:
        raise ValueError(f"{name}: 0 이상이어야 함 ({v})")
    return v


@dataclass
class RegionParams:
    res_mm: float = 0.02             # G3 결정
    cell_mm: float = 0.4             # judge cell_mm_alt (D-20 R1)
    margin_mm: float = 1.0           # T4a grid_margin_mm
    exclude_types: tuple = DEFAULT_EXCLUDE  # G4 §4
    edge_band_mm: float | None = None  # None = 외벽 선폭/2 + 2·res (E2)
    step_mm: float | None = None       # None = 최소 층 높이/2 (E2)
    theta_deg: float = 30.0          # meta.triang_angle_deg
    camera_side: str = "both"        # 장착 방향 [미상]
    occlusion_grow_cells: int = 2    # E2 §4
    dof_mm: float = 8.0              # 청사진 §1
    dof_top_mm: float = 0.0          # [추정]
    fov_mm: float = 20.0             # 청사진 §1
    scan_len_mm: float = 40.0        # meta.scan_length_mm
    pass_overlap_mm: float = 2.0     # MF-GCD-08
    extend_scan_len: bool = False
    lead_in_mm: float = 5.0          # LM-T14-2
    scan_speed_mm_s: float = 2.4     # meta.scan_speed_mm_s
    post_edge_band_mm: float | None = None  # None = max(2·res, α·반폭·ΔT) [추정] (팀장검증 5차 R-2, P-B)
    post_delta_t_c: float = 30.0     # 식힘 온도차 ΔT [추정] (팀장검증 5차 §3.4). post 띠 자동값에만 씀

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.res_mm = _num("res_mm", self.res_mm, pos=True)
        self.cell_mm = _num("cell_mm", self.cell_mm, pos=True)
        ratio = Fraction(str(self.cell_mm)) / Fraction(str(self.res_mm))
        if ratio.denominator != 1:
            raise ValueError(f"cell_mm {self.cell_mm} ÷ res_mm {self.res_mm}가 정수가 아님")
        self.margin_mm = _num("margin_mm", self.margin_mm, nonneg=True)
        if isinstance(self.exclude_types, str) or not all(isinstance(t, str) for t in self.exclude_types):
            raise ValueError("exclude_types는 문자열 목록")
        self.exclude_types = tuple(str(t).strip().upper() for t in self.exclude_types)
        for name in ("edge_band_mm", "step_mm", "post_edge_band_mm"):
            v = getattr(self, name)
            if v is not None:
                setattr(self, name, _num(name, v, pos=True))
        self.theta_deg = _num("theta_deg", self.theta_deg)
        if not (0 < self.theta_deg < 90):
            raise ValueError("theta_deg는 0–90° 사이")
        if self.camera_side not in CAMERA_SIDES:
            raise ValueError(f"camera_side는 {CAMERA_SIDES} 중 하나 ({self.camera_side!r})")
        if isinstance(self.occlusion_grow_cells, bool) or not isinstance(self.occlusion_grow_cells, int) \
                or self.occlusion_grow_cells < 0:
            raise ValueError("occlusion_grow_cells는 0 이상의 정수")
        self.dof_mm = _num("dof_mm", self.dof_mm, pos=True)
        self.dof_top_mm = _num("dof_top_mm", self.dof_top_mm)
        self.fov_mm = _num("fov_mm", self.fov_mm, pos=True)
        self.scan_len_mm = _num("scan_len_mm", self.scan_len_mm, pos=True)
        self.pass_overlap_mm = _num("pass_overlap_mm", self.pass_overlap_mm, nonneg=True)
        if self.pass_overlap_mm >= min(self.fov_mm, self.scan_len_mm):
            raise ValueError("pass_overlap_mm는 fov_mm · scan_len_mm보다 작아야 함")
        if not isinstance(self.extend_scan_len, bool):
            raise ValueError("extend_scan_len은 true/false")
        self.lead_in_mm = _num("lead_in_mm", self.lead_in_mm, nonneg=True)
        self.scan_speed_mm_s = _num("scan_speed_mm_s", self.scan_speed_mm_s, pos=True)
        self.post_delta_t_c = _num("post_delta_t_c", self.post_delta_t_c, nonneg=True)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["exclude_types"] = list(self.exclude_types)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "RegionParams":
        if d is None:
            return cls()
        if set(d) == {"region"}:
            d = d["region"] or {}
        known = {f.name for f in fields(cls)}
        bad = sorted(set(d) - known)
        if bad:
            raise ValueError(f"config region 절에 모르는 키: {bad}")
        d = dict(d)
        if "exclude_types" in d and d["exclude_types"] is not None:
            if isinstance(d["exclude_types"], str):
                raise ValueError("exclude_types는 문자열 목록")
            d["exclude_types"] = tuple(d["exclude_types"])
        return cls(**d)

    @classmethod
    def from_yaml(cls, path) -> "RegionParams":
        import yaml

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if set(data) != {"region"}:
            raise ValueError("config/region.yaml 최상위 키는 region 하나")
        return cls.from_dict(data)
