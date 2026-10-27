"""G코드 해석 설정 (config/gcode.yaml 의 `gcode` 절).

값마다 근거를 주석으로 둔다. 모르는 키는 오류.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


class GCodeError(Exception):
    """엄격 모드에서 G코드를 믿을 수 없을 때 내는 오류."""


_LAYER_SOURCES = ("both", "comment", "z")
_WIDTH_MODELS = ("nominal", "extrusion")
_HEIGHT_MODELS = ("flat",)


@dataclass
class GCodeParams:
    arc_seg_mm: float = 0.1            # G1 결정: 원호 현 길이 상한
    g9x_sets_e: bool = True            # G1 결정 (Marlin 동작). Klipper 동작은 문서 §2 [확인 필요]
    strict_unknown: bool = True        # MF-GCD-04: 모르는 명령이면 멈춤
    allow_commands: list = field(default_factory=list)  # [{name, reason}]
    layer_source: str = "both"         # MF-GCD-05: both | comment | z
    layer_z_tol_mm: float = 0.0001     # 명세 meta.layer_z_mm 규칙
    line_width_mm: float | None = None         # 머리말 값 우선
    filament_diameter_mm: float | None = None  # 머리말 값 우선
    w_eff_min_len_mm: float = 0.5      # G2 결정
    width_model: str = "nominal"       # G2 결정
    height_model: str = "flat"         # G3 결정, MF-GCD-01 기본 정의
    grid_res_mm: float = 0.02          # G3 결정
    grid_margin_mm: float = 1.0        # 팀장 안

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not (0 < self.arc_seg_mm <= 1.0):
            raise ValueError("arc_seg_mm는 0보다 크고 1 이하")
        if self.layer_source not in _LAYER_SOURCES:
            raise ValueError(f"layer_source는 {_LAYER_SOURCES} 중 하나")
        if self.width_model not in _WIDTH_MODELS:
            raise ValueError(f"width_model은 {_WIDTH_MODELS} 중 하나")
        if self.height_model not in _HEIGHT_MODELS:
            raise ValueError(f"height_model은 {_HEIGHT_MODELS} 중 하나 (대안은 민감도 함수로만)")
        if not (0 < self.layer_z_tol_mm < 0.01):
            raise ValueError("layer_z_tol_mm 범위 밖")
        if not (0 < self.grid_res_mm <= 1.0) or self.grid_margin_mm < 0:
            raise ValueError("grid_res_mm·grid_margin_mm 범위 밖")
        for v, name in ((self.line_width_mm, "line_width_mm"), (self.filament_diameter_mm, "filament_diameter_mm")):
            if v is not None and not (0 < float(v) < 10):
                raise ValueError(f"{name} 범위 밖")
        if self.w_eff_min_len_mm < 0:
            raise ValueError("w_eff_min_len_mm는 0 이상")
        if not isinstance(self.allow_commands, list):
            raise ValueError("allow_commands는 목록")
        for item in self.allow_commands:
            if not isinstance(item, dict) or set(item) != {"name", "reason"}:
                raise ValueError("allow_commands 항목은 {name, reason}")
            if not str(item["name"]).strip() or not str(item["reason"]).strip():
                raise ValueError("allow_commands 항목에 이름과 이유가 모두 있어야 함")

    @property
    def allowed_names(self) -> set:
        return {str(i["name"]).strip().upper() for i in self.allow_commands}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "GCodeParams":
        if d is None:
            return cls()
        if set(d) == {"gcode"}:
            d = d["gcode"] or {}
        known = {f.name for f in fields(cls)}
        bad = sorted(set(d) - known)
        if bad:
            raise ValueError(f"config gcode 절에 모르는 키: {bad}")
        return cls(**d)

    @classmethod
    def from_yaml(cls, path) -> "GCodeParams":
        import yaml

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if set(data) != {"gcode"}:
            raise ValueError("config/gcode.yaml 최상위 키는 gcode 하나")
        return cls.from_dict(data)
