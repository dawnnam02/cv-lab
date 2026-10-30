# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""장면 (세부청사진 §6.1 ②): 베드 (기울기 · 휨 · 메시) + 시편 참 높이맵 + 계단 기준물 · 필러게이지.

높이는 {G} 기계 Z (메시 포함). 출력물은 메시를 따라 쌓이므로 (fade 꺼짐) 시편 윗면 = 메시 m(x, y) + 참 높이맵 H.
베드 실제 면 b(x, y) = 메시 + 프로브 잔차. 명세 0.4절 h(p) = Z_n + d_s + m(x_n) − m(x_p)로 되돌리면 시편은 H,
베드는 b − m (잔차)이 된다. 기준물은 베드 면 위에 서므로 윗면 = b + 참 높이 (온도 반영).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from .optics import Surface


class Bed:
    def __init__(self, bcfg: dict, rng=None, zero_error: bool = True, mesh: bool | None = None):
        """zero_error=False면 베드 기울기 · 휨 0 (스위치 bed_zero_error), mesh로 메시 켬/끔 덮어씀 (bed_mesh_z)."""
        self.c = bcfg
        self.sx, self.sy = bcfg["size_mm"]
        self.tx = math.tan(math.radians(bcfg["tilt_x_deg"])) if zero_error else 0.0
        self.ty = math.tan(math.radians(bcfg["tilt_y_deg"])) if zero_error else 0.0
        self.bowl = bcfg["bowl_um"] / 1000.0 if zero_error else 0.0
        n = int(bcfg["mesh_n"])
        self.gx = np.linspace(10.0, self.sx - 10.0, n)
        self.gy = np.linspace(10.0, self.sy - 10.0, n)
        GX, GY = np.meshgrid(self.gx, self.gy)
        noise = rng.normal(0.0, bcfg["probe_sigma_um"] / 1000.0, GX.shape) if rng is not None else 0.0
        self.mesh_z = self.surface(GX, GY) + noise
        self.mesh_on = bool(bcfg["mesh_enabled"]) if mesh is None else bool(mesh)

    def surface(self, x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        cx, cy = self.sx / 2, self.sy / 2
        r2 = ((x - cx) ** 2 + (y - cy) ** 2) / (cx ** 2 + cy ** 2)
        return self.tx * (x - cx) + self.ty * (y - cy) + self.bowl * r2

    def mesh(self, x, y):
        """Klipper 메시 보정량 m (기계 Z − {G} Z). 꺼져 있으면 0. 격자 밖은 가장자리 값."""
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        if not self.mesh_on:
            return np.zeros(x.shape)
        fx = np.interp(x.ravel(), self.gx, np.arange(len(self.gx)))
        fy = np.interp(y.ravel(), self.gy, np.arange(len(self.gy)))
        return ndimage.map_coordinates(self.mesh_z, [fy, fx], order=1, mode="nearest").reshape(x.shape)

    def mesh_json(self) -> dict:
        """Klipper printer.bed_mesh 꼴 [추정, T1 형식이 정해지기 전]."""
        m = [[round(float(v), 6) for v in row] for row in self.mesh_z]
        return {"profile_name": "default", "mesh_min": [float(self.gx[0]), float(self.gy[0])],
                "mesh_max": [float(self.gx[-1]), float(self.gy[-1])], "probed_matrix": m, "mesh_matrix": m,
                "x_count": len(self.gx), "y_count": len(self.gy), "algo": "bilinear"}

    def truth(self) -> dict:
        return {"tilt_x_deg": self.c["tilt_x_deg"], "tilt_y_deg": self.c["tilt_y_deg"], "bowl_um": self.c["bowl_um"],
                "mesh_z_mm": [[round(float(v), 6) for v in r] for r in self.mesh_z]}


@dataclass
class Block:
    """기준물 윗면 사각형 (베드 면 위 높이)."""
    gid: str
    x0: float
    x1: float
    y0: float
    y1: float
    height: float     # 그 순간 참 높이 (온도 반영), 베드 면 = 0
    material: str = "steel"


@dataclass
class Scene(Surface):
    bed: Bed
    hmap: np.ndarray | None = None          # 시편 참 높이맵 H (mm), 칸 중심 격자
    origin: tuple = (0.0, 0.0)
    step: float = 0.02
    blocks: list = field(default_factory=list)
    hot_above_mm: float | None = None       # 이 높이 이상 시편 칸은 뜨거운 윗면 (정반사 배율)
    _hmax: float = 0.0

    def __post_init__(self):
        if self.hmap is not None:
            self._hmax = float(np.nanmax(self.hmap))

    def heights(self, x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        b = self.bed.surface(x, y)
        z = b.copy()
        mat = np.zeros(x.shape, np.int64)
        hot = np.zeros(x.shape, bool)
        if x.size == 0:
            return z, mat, hot
        qx0, qx1, qy0, qy1 = float(x.min()), float(x.max()), float(y.min()), float(y.max())  # 겹치지 않는 것은 건너뜀 (속도)
        if self.hmap is not None:
            ny, nx = self.hmap.shape
            hx0, hy0 = self.origin
            hx1, hy1 = hx0 + (nx - 1) * self.step, hy0 + (ny - 1) * self.step
            if qx1 >= hx0 - self.step and qx0 <= hx1 + self.step and qy1 >= hy0 - self.step and qy0 <= hy1 + self.step:
                fx = (x - hx0) / self.step
                fy = (y - hy0) / self.step
                H = ndimage.map_coordinates(self.hmap, [fy.ravel(), fx.ravel()], order=1, mode="constant",
                                            cval=0.0).reshape(x.shape)
                on = H > 1e-6
                if on.any():
                    if self.bed.mesh_on:
                        zo = z.copy()
                        zo[on] = self.bed.mesh(x[on], y[on]) + H[on]
                        z = zo
                    else:
                        z = np.where(on, H, z)
                    mat = np.where(on, 1, mat)
                    if self.hot_above_mm is not None:
                        hot = on & (H >= self.hot_above_mm)
        for bk in self.blocks:
            if bk.x1 < qx0 or bk.x0 > qx1 or bk.y1 < qy0 or bk.y0 > qy1:
                continue
            inb = (x >= bk.x0) & (x <= bk.x1) & (y >= bk.y0) & (y <= bk.y1)
            if inb.any():
                z = np.where(inb, b + bk.height, z)
                mat = np.where(inb, Surface.MATERIALS.index(bk.material), mat)
        return z, mat, hot

    def band_max(self, x0, x1, y0, y1) -> float:
        top = float(np.max(self.bed.surface(np.array([x0, x1, x0, x1]), np.array([y0, y0, y1, y1]))))
        if self.hmap is not None:
            ny, nx = self.hmap.shape
            ix0 = int(max(0, math.floor((x0 - self.origin[0]) / self.step)))
            ix1 = int(min(nx, math.ceil((x1 - self.origin[0]) / self.step) + 1))
            iy0 = int(max(0, math.floor((y0 - self.origin[1]) / self.step)))
            iy1 = int(min(ny, math.ceil((y1 - self.origin[1]) / self.step) + 1))
            if ix1 > ix0 and iy1 > iy0:
                sub = self.hmap[iy0:iy1, ix0:ix1]
                if sub.size:
                    top = max(top, float(np.max(sub)) + float(np.max(self.bed.mesh(np.array([x0, x1]),
                                                                               np.array([y0, y1])))) + 1e-3)
        for bk in self.blocks:
            if bk.x1 >= x0 and bk.x0 <= x1 and bk.y1 >= y0 and bk.y0 <= y1:
                top = max(top, float(np.max(self.bed.surface(np.array([bk.x0, bk.x1]), np.array([bk.y0, bk.y1]))))
                          + bk.height + 1e-3)
        return top


def mesh_json_bytes(bed: Bed) -> bytes:
    return (json.dumps(bed.mesh_json(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
