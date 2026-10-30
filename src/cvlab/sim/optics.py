# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""레이저 · 광학 순방향 모델 (세부청사진 §6.3, SM4). 식과 근거는 docs/시뮬레이터_모델.md §3.

좌표 ({S}: 레이저 평면 위 기준점, x 선 방향, y 평면 법선, z 위. {C}: OpenCV 카메라):
- 카메라 중심 C_S = (0, −D sin θ, D cos θ) + 장착 오차, 축 x_c = +x_S, z_c = (0, sin θ, −cos θ) (원점을 봄).
  높은 면일수록 영상 v가 작아짐 (위로 감). 표면 아래 산란 꼬리는 v가 커지는 쪽 (낮아 보이는 쪽).
- 내부: fx = fy = f (1 + M) ÷ 화소 [계산, 얇은 렌즈 상거리], 왜곡은 OpenCV 유리 모델 8계수 (고차항 포함).
- {S} → {G}: 작은 회전 R_GS (레이저 평면 기울기, MF-OPT-13) + 원점 O_S = 노즐 끝 + 오프셋 (참값).

한 프레임 렌더 (render_line):
선 방향 x_S 표본 (화소당 samples_per_px) × 시트 두께 방향 3점 (가우스-에르미트) → 각 표본에서 시트와 표면이
만나는 점 → 법선 · 람베르트 · 정반사 로브 (뜨거운 윗면 배율) · 가림 (카메라 쪽 · 레이저 부채꼴 쪽) → 투영 (u, v)
→ v 방향 화소 적분 단면 = (1 − β) 가우스 + β 지수 꼬리 가우스 (EMG, 꼬리 길이 = δ × dv/dz) → u 두 열에 나눠 쌓음
→ u 방향 PSF → 스펙클 (곱, 부분 발달, 프레임 사이 AR(1)) → 주변광.
처리 쪽 단순 모델과 다르게 만든 점은 모델 문서 §4 차이 목록.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage, special

SQRT2 = math.sqrt(2.0)


# ---------------------------------------------------------------- 기하
def rot_xyz(ax: float, ay: float, az: float) -> np.ndarray:
    """작은 회전 (라디안) Rz · Ry · Rx."""
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def distort(xn, yn, k):
    k1, k2, p1, p2, k3, k4, k5, k6 = k
    r2 = xn * xn + yn * yn
    radial = (1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3) / (1 + k4 * r2 + k5 * r2 ** 2 + k6 * r2 ** 3)
    xd = xn * radial + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
    yd = yn * radial + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
    return xd, yd


def undistort(xd, yd, k, iters: int = 8):
    xn, yn = np.array(xd, float), np.array(yd, float)
    for _ in range(iters):
        x2, y2 = distort(xn, yn, k)
        xn = xn - (x2 - xd)
        yn = yn - (y2 - yd)
    return xn, yn


@dataclass
class Geometry:
    """참 센서 기하 (참값 truth.cam_k · cam_dist · laser_plane · scan_axis · t_g_m · nozzle_sensor_offset_mm)."""
    K: np.ndarray
    dist: np.ndarray
    R_cs: np.ndarray          # {S} → {C} 회전
    C_s: np.ndarray           # 카메라 중심, {S}
    R_gs: np.ndarray          # {S} → {G} 회전
    offset_g: np.ndarray      # {S} 원점 − 노즐 끝, {G}
    width: int
    height: int
    roi_y0: int
    roi_h: int
    focus_depth: float        # 초점이 맞는 카메라 깊이 (mm)
    aperture_mm: float
    pixel_mm: float
    wavelength_mm: float
    f_number: float
    magnification: float
    laser_src_s: np.ndarray   # 레이저 광원 위치, {S}

    def project_s(self, P):
        """{S} 점 (N, 3) → (u, v, 카메라 깊이)."""
        Pc = (np.asarray(P, float) - self.C_s) @ self.R_cs.T
        z = Pc[:, 2]
        xd, yd = distort(Pc[:, 0] / z, Pc[:, 1] / z, self.dist)
        return self.K[0, 0] * xd + self.K[0, 2], self.K[1, 1] * yd + self.K[1, 2], z

    def ray_s(self, u, v):
        """화소 → {S} 광선 (원점 C_s, 방향 단위 벡터 (N, 3))."""
        xd = (np.asarray(u, float) - self.K[0, 2]) / self.K[0, 0]
        yd = (np.asarray(v, float) - self.K[1, 2]) / self.K[1, 1]
        xn, yn = undistort(xd, yd, self.dist)
        d = np.stack([xn, yn, np.ones_like(xn)], axis=-1) @ self.R_cs  # C → S (R_cs.T의 전치)
        return d / np.linalg.norm(d, axis=-1, keepdims=True)

    def laser_plane_c(self) -> list:
        """레이저 평면 (y_S = 0) [nx, ny, nz, d], {C}, n · p + d = 0."""
        n = self.R_cs @ np.array([0.0, 1.0, 0.0])
        p0 = self.R_cs @ (np.zeros(3) - self.C_s)
        return [float(n[0]), float(n[1]), float(n[2]), float(-n @ p0)]

    def scan_axis_c(self) -> list:
        """스캔 방향 ({G} +Y)을 {C} 단위 벡터로."""
        a_s = self.R_gs.T @ np.array([0.0, 1.0, 0.0])
        a = self.R_cs @ a_s
        return [float(v) for v in a / np.linalg.norm(a)]

    def t_g_m(self) -> list:
        """{M} → {G} (축 = {S}, 원점 = 노즐 끝이 {G} 원점일 때의 {S} 원점). 스캔마다의 원점은 위치 로그로 옮김."""
        T = np.eye(4)
        T[:3, :3] = self.R_gs
        T[:3, 3] = self.offset_g
        return T.tolist()

    def dv_dz(self, x_s: float = 0.0, z_s: float = 0.0, h: float = 0.01) -> float:
        _, v0, _ = self.project_s(np.array([[x_s, 0.0, z_s]]))
        _, v1, _ = self.project_s(np.array([[x_s, 0.0, z_s + h]]))
        return float((v1[0] - v0[0]) / h)


def make_geometry(ocfg: dict, rng=None, lens_residual: bool = True) -> Geometry:
    """명목 기하 + 장착 공차 (rng가 있으면 참 기하를 뽑음). lens_residual=False면 왜곡 고차항 (k4–k6) 0."""
    th = math.radians(ocfg["triang_angle_deg"])
    D = float(ocfg["working_distance_mm"])
    p = ocfg["pixel_um"] / 1000.0
    f = float(ocfg["focal_mm"])
    M = f / (D - f)
    fx = f * (1.0 + M) / p
    W, H = int(ocfg["sensor_w_px"]), int(ocfg["sensor_h_px"])
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    R0 = np.array([[1.0, 0, 0], [0, -math.cos(th), -math.sin(th)], [0, math.sin(th), -math.cos(th)]])
    C = np.array([0.0, -D * math.sin(th), D * math.cos(th)])
    Rm = np.eye(3)
    Rgs = np.eye(3)
    off = np.array(ocfg["nozzle_sensor_offset_mm"], float)
    if rng is not None:
        sa = math.radians(ocfg["mount_angle_sigma_deg"])
        Rm = rot_xyz(*rng.normal(0, sa, 3))
        C = C + rng.normal(0, ocfg["mount_pos_sigma_mm"], 3)
        tl = math.radians(ocfg["laser_plane_tilt_sigma_deg"])
        Rgs = rot_xyz(rng.normal(0, tl), 0.0, rng.normal(0, tl))
        cx += rng.normal(0, ocfg["principal_jitter_px"])
        cy += rng.normal(0, ocfg["principal_jitter_px"])
        off = off + rng.normal(0, ocfg["mount_pos_sigma_mm"], 3)
    K = np.array([[fx, 0, cx], [0, fx, cy], [0, 0, 1.0]])
    R = Rm @ R0
    focus = float((R @ (np.zeros(3) - C))[2])
    dist = np.array(ocfg["dist_k"], float)
    if not lens_residual:
        dist[5:] = 0.0
    return Geometry(K=K, dist=dist, R_cs=R, C_s=C, R_gs=Rgs, offset_g=off,
                    width=W, height=H, roi_y0=int(ocfg["roi_y0_px"]), roi_h=int(ocfg["roi_h_px"]),
                    focus_depth=focus, aperture_mm=f / ocfg["f_number"], pixel_mm=p,
                    wavelength_mm=ocfg["wavelength_um"] / 1000.0, f_number=float(ocfg["f_number"]),
                    magnification=M, laser_src_s=np.array([0.0, 0.0, float(ocfg["laser_height_mm"])]))


def geometry_truth(g: Geometry) -> dict:
    return {"cam_k": [[round(float(v), 6) for v in row] for row in g.K],
            "cam_dist": [float(v) for v in g.dist],
            "laser_plane": [round(v, 9) for v in g.laser_plane_c()],
            "scan_axis": [round(v, 9) for v in g.scan_axis_c()],
            "t_g_m": [[round(float(v), 9) for v in row] for row in g.t_g_m()],
            "nozzle_sensor_offset_mm": [round(float(v), 6) for v in g.offset_g]}


# ---------------------------------------------------------------- 단면 (화소 적분)
def _phi(x):
    return 0.5 * special.erfc(-x / SQRT2)


def emg_cdf(x, sigma, tau):
    """지수 꼬리 (+쪽, 길이 τ) 가우스 (σ)의 누적분포. τ → 0이면 가우스."""
    x = np.asarray(x, float)
    sigma = np.broadcast_to(np.asarray(sigma, float), x.shape)
    tau = np.broadcast_to(np.asarray(tau, float), x.shape)
    g = _phi(x / sigma)
    small = tau < 1e-6
    ts = np.where(small, 1.0, tau)
    z = x / sigma - sigma / ts
    w = -z / SQRT2
    A = -x / ts + sigma ** 2 / (2 * ts ** 2)
    pos = w >= 0
    term = np.where(pos, 0.5 * special.erfcx(np.where(pos, w, 0.0)) * np.exp(np.where(pos, A - w * w, 0.0)),
                    0.5 * special.erfc(np.where(pos, 0.0, w)) * np.exp(np.where(pos, 0.0, np.minimum(A, 700.0))))
    return np.where(small, g, g - term)


def pixel_profile(rows, v0, sigma, beta, tau):
    """rows: 화소 중심 (K,), v0 · σ · β · τ: 표본마다 (N,). 화소 [r − ½, r + ½] 적분값 (N, K)."""
    a = rows[None, :] - 0.5 - np.asarray(v0, float)[:, None]
    return _profile_rows(a, np.asarray(sigma, float), np.asarray(beta, float), np.asarray(tau, float))


# ---------------------------------------------------------------- 장면 인터페이스
class Surface:
    """렌더러가 쓰는 장면: heights(x, y) → (Z 절대, 재료 번호, 뜨거움). {G} 기계 Z (메시 포함)."""

    MATERIALS = ("bed", "pla", "steel")

    def heights(self, x, y):  # pragma: no cover - 하위 클래스가 채움
        raise NotImplementedError

    def band_max(self, x0, x1, y0, y1) -> float:  # 가림 계산을 건너뛸지 정하는 위 한계
        raise NotImplementedError


class PlaneSurface(Surface):
    """해석해 시험용: 평면 몇 개 (x 구간마다 높이)."""

    def __init__(self, edges_x=(), heights=(0.0,), material="pla", hot=False):
        self.edges = np.asarray(edges_x, float)
        self.hs = np.asarray(heights, float)
        self.mat = self.MATERIALS.index(material)
        self.hot = hot

    def heights(self, x, y):
        x = np.asarray(x, float)
        i = np.searchsorted(self.edges, x, side="right")
        return self.hs[i], np.full(x.shape, self.mat), np.full(x.shape, self.hot)

    def band_max(self, *a):
        return float(self.hs.max())


# ---------------------------------------------------------------- 스펙클
@dataclass
class Speckle:
    contrast: float
    corr_u: float
    corr_v: float
    rho: float
    rng: np.random.Generator
    shape: tuple
    z: np.ndarray | None = field(default=None, repr=False)

    def _new(self):
        w = self.rng.standard_normal(self.shape, dtype=np.float32)
        f = ndimage.gaussian_filter(w, (self.corr_v, self.corr_u), mode="wrap", truncate=3.0)
        return f / (f.std() + 1e-12)

    def next(self) -> np.ndarray:
        if self.contrast <= 0:
            return np.ones(self.shape)
        n = self._new()
        self.z = n if self.z is None else self.rho * self.z + math.sqrt(1.0 - self.rho ** 2) * n
        return np.clip(1.0 + self.contrast * self.z, 0.0, None)


# ---------------------------------------------------------------- 렌더러
GH3 = (np.array([-math.sqrt(3.0), 0.0, math.sqrt(3.0)]), np.array([1 / 6, 2 / 3, 1 / 6]))


class LineRenderer:
    """레이저 선 한 프레임 렌더 (ROI 행만)."""

    def __init__(self, geom: Geometry, ocfg: dict, switches: dict | None = None):
        self.g = geom
        self.o = ocfg
        sw = dict(subsurface_scatter=True, subsurface_stress=False, hot_gloss=True, speckle=True, room_light=False,
                  occlusion=True)
        sw.update(switches or {})
        self.sw = sw
        self.mats = [ocfg["materials"][m] for m in Surface.MATERIALS]
        self.dvdz = geom.dv_dz()
        self._scale = None

    # 표본 ------------------------------------------------------------
    def _x_range(self):
        g = self.g
        D = g.focus_depth
        xa = (-3 - g.K[0, 2]) / g.K[0, 0] * D * 1.06
        xb = (g.width + 2 - g.K[0, 2]) / g.K[0, 0] * D * 1.06
        return min(xa, xb), max(xa, xb)

    def _samples(self):
        xa, xb = self._x_range()
        n = int(math.ceil((self.g.width + 6) * self.o["samples_per_px"]))
        xs = np.linspace(xa, xb, n)
        sig = self.o["sheet_w_um"] / 1000.0 / 2.0
        ys = GH3[0] * sig
        X = np.repeat(xs, 3)
        Y = np.tile(ys, n)
        Wt = np.tile(GH3[1], n)
        return X, Y, Wt, (xb - xa) / (n - 1)

    def _hit(self, surf, O, X, Y):
        """{S} 연직선 (x, y, t)과 표면이 만나는 점: {G} 좌표 · 재료 · 뜨거움 · {S} z."""
        R = self.g.R_gs
        t = np.zeros_like(X)
        for _ in range(3):
            P = O[None, :] + np.stack([X, Y, t], 1) @ R.T
            h, mat, hot = surf.heights(P[:, 0], P[:, 1])
            t = t + (h - P[:, 2]) / R[2, 2]
        P = O[None, :] + np.stack([X, Y, t], 1) @ R.T
        return P, mat, hot, t

    def _normals(self, surf, P, e=0.02):
        hx1, _, _ = surf.heights(P[:, 0] + e, P[:, 1])
        hx0, _, _ = surf.heights(P[:, 0] - e, P[:, 1])
        hy1, _, _ = surf.heights(P[:, 0], P[:, 1] + e)
        hy0, _, _ = surf.heights(P[:, 0], P[:, 1] - e)
        n = np.stack([-(hx1 - hx0) / (2 * e), -(hy1 - hy0) / (2 * e), np.ones(len(P))], 1)
        return n / np.linalg.norm(n, axis=1, keepdims=True)

    def _occluded_camera(self, surf, P, Cg):
        V = Cg[None, :] - P
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        y_lo = float(P[:, 1].min()) - 10.0
        y_hi = float(P[:, 1].max()) + 10.0
        top = surf.band_max(float(P[:, 0].min()) - 10, float(P[:, 0].max()) + 10, y_lo, y_hi)
        occ = np.zeros(len(P), bool)
        cand = np.flatnonzero((P[:, 2] < top - 1e-6) & (V[:, 2] > 0))
        if cand.size == 0:
            return occ
        cand = self._prune_occlusion(surf, P, V, cand, top)
        if cand.size == 0:
            return occ
        Pc, Vc = P[cand], V[cand]
        hxy = np.hypot(Vc[:, 0], Vc[:, 1])
        ds = 0.02 / np.maximum(hxy, 1e-6)
        kmax = min(int(np.ceil(np.max((top - Pc[:, 2]) / (ds * Vc[:, 2])))) + 1, 2000)
        # 광선마다 k = 1 … n_i (n_i = 광선 높이가 top에 처음 닿는 걸음, 그 걸음까지 봄)를 한 번에 펼쳐 높이를 한 번에 구함.
        # 걸음마다 반복하던 것과 같은 점 · 같은 비교라 결과가 같음 (T3-2, 파이썬 반복 비용만 없앰)
        n_i = np.minimum(np.floor((top - Pc[:, 2]) / (ds * Vc[:, 2]) - 1e-12).astype(int) + 1, kmax)
        n_i = np.maximum(n_i, 1)
        hit = np.zeros(len(cand), bool)
        alive = np.arange(len(cand))
        G = 16                                         # 걸음 16개씩 묶어 한 번에 (가린 광선은 일찍 빠짐)
        for k0 in range(1, kmax + 1, G):
            if alive.size == 0:
                break
            ks = np.arange(k0, k0 + G)
            ok = ks[None, :] <= n_i[alive][:, None]   # 광선마다 볼 걸음만
            a_idx, k_idx = np.nonzero(ok)
            own = alive[a_idx]
            q = Pc[own] + (ks[k_idx] * ds[own])[:, None] * Vc[own]
            h, _, _ = surf.heights(q[:, 0], q[:, 1])
            hk = h > q[:, 2] + 1e-9
            hit[np.unique(own[hk])] = True
            alive = alive[(~hit[alive]) & (n_i[alive] >= k0 + G)]
        occ[cand] = hit
        return occ

    def _prune_occlusion(self, surf, P, V, cand, top, step=0.02, margin=1e-3):
        """보수적 가지치기 (속도): 후보 광선이 지나는 띠를 한 번에 높이 격자로 찍고 (5 × 5 최댓값 + 여유 1 µm)
        광선 높이가 그 상한을 한 번도 넘지 않으면 가림 없음으로 뺌. 남은 후보만 정밀 광선 따라가기."""
        Pc, Vc = P[cand], V[cand]
        t_end = (top - Pc[:, 2]) / Vc[:, 2]
        ends = Pc[:, :2] + t_end[:, None] * Vc[:, :2]
        x0 = min(Pc[:, 0].min(), ends[:, 0].min()) - 3 * step
        x1 = max(Pc[:, 0].max(), ends[:, 0].max()) + 3 * step
        y0 = min(Pc[:, 1].min(), ends[:, 1].min()) - 3 * step
        y1 = max(Pc[:, 1].max(), ends[:, 1].max()) + 3 * step
        nx, ny = int(math.ceil((x1 - x0) / step)) + 1, int(math.ceil((y1 - y0) / step)) + 1
        if nx * ny > 3_000_000:
            return cand
        gx = x0 + np.arange(nx) * step
        gy = y0 + np.arange(ny) * step
        GX, GY = np.meshgrid(gx, gy)
        Hr, _, _ = surf.heights(GX, GY)
        Hf = ndimage.maximum_filter(Hr, size=5, mode="nearest") + margin
        hxy = np.maximum(np.hypot(Vc[:, 0], Vc[:, 1]), 1e-6)
        need = np.zeros(len(cand), bool)
        # ① 가까운 0.24 mm: 고운 칸 (0.02 mm) 간격으로 (자기 면을 굵은 칸에 넣지 않게)
        dsf = step / hxy
        n_near = 12
        tk = np.arange(1, n_near + 1)[:, None] * dsf[None, :]          # (걸음, 광선) 한 번에
        qx, qy, qz = (Pc[None, :, i] + tk * Vc[None, :, i] for i in range(3))
        ix = np.clip(np.rint((qx - x0) / step).astype(int), 0, nx - 1)
        iy = np.clip(np.rint((qy - y0) / step).astype(int), 0, ny - 1)
        need |= ((Hf[iy, ix] > qz) & (qz < top)).any(axis=0)
        # ② 그 너머: 5 × 5 고운 칸을 묶은 굵은 칸 (0.1 mm) 최댓값 = 칸 안 어디든 상한. 반 칸 간격으로 걸으며,
        #    표본 사이에서 광선이 가장 낮은 높이 (앞 표본 높이)와 비교해 보수적으로
        B = 5
        Hp = np.pad(Hf, ((0, (-ny) % B), (0, (-nx) % B)), mode="edge")
        Hb = Hp.reshape(Hp.shape[0] // B, B, Hp.shape[1] // B, B).max(axis=(1, 3))
        Hb = ndimage.maximum_filter(Hb, size=3, mode="nearest")   # 반 칸 사이에 모서리로 스치는 이웃 칸까지
        cs = step * B
        dsc = 0.5 * cs / hxy
        t0 = n_near * dsf
        kmax = min(int(np.ceil(np.max((t_end - t0) / dsc))) + 1, 4000)
        per = max(1, 1_500_000 // max(len(cand), 1))                 # 걸음 묶음 (메모리 한도)
        for k0 in range(1, kmax + 1, per):
            ks = np.arange(k0, min(k0 + per, kmax + 1))[:, None]
            t = t0[None, :] + ks * dsc[None, :]
            qx, qy, qz = (Pc[None, :, i] + t * Vc[None, :, i] for i in range(3))
            ix = np.clip(((qx - x0) / step + 0.5).astype(int) // B, 0, Hb.shape[1] - 1)
            iy = np.clip(((qy - y0) / step + 0.5).astype(int) // B, 0, Hb.shape[0] - 1)
            zlow = qz - (dsc * Vc[:, 2])[None, :]
            need |= ((Hb[iy, ix] > zlow) & (zlow < top)).any(axis=0)
        return cand[need]

    def _shadowed_laser(self, z_s, x_s, line_mask):
        """레이저 부채꼴 (광원 {S} (0, 0, Lh))이 선 위 더 높은 점에 막히는지. 시트 가운데 표본으로 봄."""
        # 광원 (0, Lh)에서 점 j까지의 내림 기울기 s_j = (Lh − z_j) ÷ |x_j|. 점 i는 같은 쪽에서 광원에 더 가까운 점 j
        # (|x_j| < |x_i|) 중 s_j < s_i인 것이 있으면 그림자 (광선 z(x) = Lh − s_i |x|보다 z_j가 높음과 같은 식).
        # 정렬 + 누적 최솟값으로 O(N log N) (팀장검증 7차 §5.4 결정 3이 허용한 방법, 물리는 그대로).
        Lh = float(self.g.laser_src_s[2])
        idx_line = np.flatnonzero(line_mask)
        xs, zs = x_s[idx_line], z_s[idx_line]
        sh = np.zeros(len(xs), bool)
        cand = zs < zs.max() - 1e-6
        for side in (xs > 0, xs < 0):
            ii = np.flatnonzero(side)
            if ii.size < 2:
                continue
            ax = np.abs(xs[ii])
            order = np.argsort(ax, kind="stable")
            ii, ax = ii[order], ax[order]
            s = (Lh - zs[ii]) / ax
            prev_min = np.concatenate([[np.inf], np.minimum.accumulate(s)[:-1]])
            sh[ii] = (prev_min < s - 1e-12) & cand[ii]
        full = np.zeros(len(x_s), bool)
        full[idx_line] = sh
        return full

    # 한 프레임 ----------------------------------------------------------
    def render_line(self, surf: Surface, O_g, speckle: Speckle | None = None, laser_on: bool = True,
                    with_info: bool = False):
        """O_g: 이 프레임의 {S} 원점 ({G} 기계 좌표, 실제 위치). 돌려줌: ROI 빛 세기 (roi_h, W), 명목 선 꼭대기 ≈ 1."""
        g, o = self.g, self.o
        amb = o["ambient"] + (o["room_light"] if self.sw["room_light"] else 0.0)
        if not laser_on:
            return np.full((g.roi_h, g.width), amb), ({"valid_cols": 0} if with_info else None)
        img, info = self._render_raw(surf, np.asarray(O_g, float))
        img = img * self.scale()
        if speckle is not None and self.sw["speckle"]:
            img = img * speckle.next()
        img = img + amb
        return img, (info if with_info else None)

    def scale(self) -> float:
        """명목 평평한 PLA 선 꼭대기를 1로 맞추는 배율 (기하마다 한 번)."""
        if self._scale is None:
            sw = dict(self.sw)
            self.sw.update(hot_gloss=False)
            raw, _ = self._render_raw(PlaneSurface(heights=(0.0,)), np.zeros(3))
            self.sw = sw
            self._scale = 1.0 / float(raw.max())
        return self._scale

    def _render_raw(self, surf, O):
        g, o = self.g, self.o
        X, Y, Wt, dx = self._samples()
        P, mat, hot, t = self._hit(surf, O, X, Y)
        Ps = np.stack([X, Y, t], 1)                       # {S} 점
        u, v, depth = g.project_s(Ps)
        Cg = O + g.R_gs @ g.C_s
        n = self._normals(surf, P)
        Lg = O + g.R_gs @ g.laser_src_s
        Ldir = Lg[None, :] - P
        Ldir /= np.linalg.norm(Ldir, axis=1, keepdims=True)
        Vdir = Cg[None, :] - P
        Vdir /= np.linalg.norm(Vdir, axis=1, keepdims=True)
        md = np.array([m["diffuse"] for m in self.mats])[mat]
        ms = np.array([m["spec"] for m in self.mats])[mat]
        ml = np.radians(np.array([m["lobe_deg"] for m in self.mats]))[mat]
        ndl = np.clip((n * Ldir).sum(1), 0.0, None)
        ndv = (n * Vdir).sum(1)
        Hb = Ldir + Vdir
        Hb /= np.linalg.norm(Hb, axis=1, keepdims=True)
        ang = np.arccos(np.clip((n * Hb).sum(1), -1.0, 1.0))
        gloss = np.where(hot & self.sw["hot_gloss"], o["hot_gloss_gain"], 1.0)
        refl = md * ndl + ms * gloss * np.exp(-ang ** 2 / (2 * ml ** 2))
        fan = np.exp(-2.0 * X ** 2 / o["fan_w_mm"] ** 2)
        w = Wt * fan * refl * (ndv > 0) * dx
        valid = (ndv > 0) & (ndl > 0)
        if self.sw["occlusion"]:
            # 영상에 들어갈 표본만 가림을 봄 (ROI · 열 범위 밖이거나 빛이 0인 표본은 어차피 안 그림 → 결과 같음, T3-2)
            vr0 = v - g.roi_y0
            inroi = (w > 0) & (u > -1.5) & (u < g.width + 0.5) & (vr0 > -30) & (vr0 < g.roi_h + 30)
            occ = np.zeros(len(P), bool)
            if inroi.any():
                occ[inroi] = self._occluded_camera(surf, P[inroi], Cg)
            sh = self._shadowed_laser(t, X, Y == 0.0)           # 시트 가운데 표본으로 보고
            sh = np.repeat(sh.reshape(-1, 3).any(1), 3)          # 같은 x의 세 표본에 같이 적용
            w = w * ~occ * ~sh
            valid &= ~occ & ~sh
        # 단면 폭: 회절 + 초점 밖 흐림
        sig_diff = 0.42 * g.wavelength_mm * g.f_number * (1 + g.magnification) / g.pixel_mm
        blur_mm = g.aperture_mm * g.K[0, 0] * g.pixel_mm * np.abs(depth - g.focus_depth) / (depth * g.focus_depth)
        sig = np.sqrt(sig_diff ** 2 + (blur_mm / g.pixel_mm / 4.0) ** 2 + 0.25 ** 2)
        mb = np.array([m["beta"] for m in self.mats])[mat]
        mdlt = np.array([m["delta_um"] for m in self.mats])[mat] / 1000.0
        if not self.sw["subsurface_scatter"]:
            mb = np.zeros_like(mb)
        tau = mdlt * abs(self.dvdz)
        if self.sw["subsurface_stress"]:
            pla = mat == Surface.MATERIALS.index("pla")
            mb = np.where(pla, o["stress_beta"], mb)
            tau = np.where(pla, o["stress_tail_px"], tau)
        vr = v - g.roi_y0
        keep = (w > 0) & (u > -1.5) & (u < g.width + 0.5) & (vr > -30) & (vr < g.roi_h + 30)
        img = np.zeros((g.roi_h, g.width))
        info = {"valid_cols": 0}
        if keep.any():
            uk, vk, wk = u[keep], vr[keep], w[keep]
            sk, bk, tk = sig[keep], mb[keep], tau[keep]
            rows, prof = self._lut_profile(vk, sk, bk, tk)
            u0 = np.floor(uk).astype(int)
            fu = uk - u0
            okr = (rows >= 0) & (rows < g.roi_h)
            flats, wts = [], []
            for du, wu in ((0, 1.0 - fu), (1, fu)):   # u 두 열에 선형으로 나눔 (한 번의 bincount로 모음)
                cols = u0 + du
                ok = okr & ((cols >= 0) & (cols < g.width))[:, None]
                flats.append((rows * g.width + cols[:, None])[ok])
                wts.append((prof * (wk * wu)[:, None])[ok])
            img += np.bincount(np.concatenate(flats), weights=np.concatenate(wts),
                               minlength=g.roi_h * g.width).reshape(g.roi_h, g.width)
            su = float(np.median(np.sqrt(sig_diff ** 2 + (blur_mm[keep] / g.pixel_mm / 4.0) ** 2)))
            nz = np.flatnonzero(img.any(axis=1))      # u 방향 흐림은 행마다 따로라 빛이 있는 행만 (결과 같음)
            if nz.size:
                r0, r1 = int(nz[0]), int(nz[-1]) + 1
                img[r0:r1] = ndimage.gaussian_filter1d(img[r0:r1], su, axis=1, mode="constant")
            vv = valid & keep
            info["valid_cols"] = int(len(np.unique(np.clip(np.round(u[vv]), 0, g.width - 1)))) if vv.any() else 0
        return img, info

    # 단면 표 (속도) --------------------------------------------------------
    S_GRID = np.linspace(0.25, 3.0, 45)      # σ 0.0625 px 간격. 3 px 넘는 흐림은 3 px로 자름 (심도 끝 밖)
    F_GRID = np.linspace(0.0, 1.0, 33)       # v의 소수 부분 1/32 px 간격
    HALF = 16

    def _table(self, b: float, t: float):
        key = (round(b, 6), round(t, 5))
        cache = self.__dict__.setdefault("_tables", {})
        if key not in cache:
            tail = int(math.ceil(10 * t)) if b > 0 else 0
            offs = np.arange(-self.HALF, self.HALF + tail + 1)
            S, F = np.meshgrid(self.S_GRID, self.F_GRID, indexing="ij")
            a = offs[None, :] - 0.5 - F.ravel()[:, None]
            n = a.shape[0]
            tab = _profile_rows(a, S.ravel(), np.full(n, b), np.full(n, t))
            cache[key] = (offs, tab.reshape(len(self.S_GRID), len(self.F_GRID), len(offs)))
        return cache[key]

    def _lut_profile(self, v0, s, b, t):
        """화소 적분 단면을 표에서 (σ · 소수 부분 이중선형) 꺼냄. 소수 부분 보간이 선형이라 무게중심은 정확히 보존."""
        keys = np.round(b, 6) * 1e6 + np.round(t, 5)
        groups = np.unique(keys)
        tabs = [self._table(float(b[keys == k][0]), float(t[keys == k][0])) for k in groups]
        # 앞쪽 (높은 쪽) 행은 이 프레임 최대 σ의 5배 + 1행까지만 (그 밖 가우스 몫 < 3e-7, T3-2 속도). 꼬리 쪽은 그대로
        h = min(self.HALF, int(math.ceil(5.0 * float(np.max(s)))) + 1)
        cut = self.HALF - h
        tabs = [(o[cut:], tb[:, :, cut:]) for o, tb in tabs]
        K = max(len(o) for o, _ in tabs)
        base = np.floor(v0).astype(int)
        rows = base[:, None] + np.arange(-h, -h + K)[None, :]
        prof = np.zeros((len(v0), K))
        si = np.clip((s - self.S_GRID[0]) / (self.S_GRID[1] - self.S_GRID[0]), 0, len(self.S_GRID) - 1 - 1e-9)
        fi = np.clip((v0 - base) * (len(self.F_GRID) - 1), 0, len(self.F_GRID) - 1 - 1e-9)
        i0, j0 = si.astype(int), fi.astype(int)
        ws, wf = (si - i0)[:, None], (fi - j0)[:, None]
        for k, (offs, tab) in zip(groups, tabs):
            m = keys == k
            a, c = i0[m], j0[m]
            p = ((1 - ws[m]) * (1 - wf[m]) * tab[a, c] + (1 - ws[m]) * wf[m] * tab[a, c + 1]
                 + ws[m] * (1 - wf[m]) * tab[a + 1, c] + ws[m] * wf[m] * tab[a + 1, c + 1])
            prof[m, :len(offs)] = p
        return rows, prof

    # 해석해 ---------------------------------------------------------------
    def true_v(self, x_s, z_s):
        """{S} 레이저 평면 위 점 (x, 0, z)의 참 영상 위치 (u, v) — 시험 · 채점용."""
        x_s = np.atleast_1d(np.asarray(x_s, float))
        z_s = np.broadcast_to(np.asarray(z_s, float), x_s.shape)
        u, v, _ = self.g.project_s(np.stack([x_s, np.zeros_like(x_s), z_s], 1))
        return u, v


def _profile_rows(a, s, b, t):
    """a = (행 − ½ − v0) (N, K). 화소 적분 단면."""
    s2, t2, b2 = s[:, None], t[:, None], b[:, None]
    gauss = _phi((a + 1) / s2) - _phi(a / s2)
    if not (b > 0).any():
        return gauss
    tail = emg_cdf(a + 1, s2, t2) - emg_cdf(a, s2, t2)
    return (1.0 - b2) * gauss + b2 * tail


# ---------------------------------------------------------------- 평면 표적 (D1 · D2 · D3)
def checker_texture(square_mm: float, rows: int, cols: int, marker_mm: float | None = None):
    """체커보드 (ChArUco 판의 칸 무늬). 마커 칸은 marker_mm 크기 정사각형을 비워 둠 (ArUco 무늬는 미반영)."""
    W, H = cols * square_mm, rows * square_mm

    def tex(x, y):
        inside = (np.abs(x) <= W / 2) & (np.abs(y) <= H / 2)
        i = np.floor((x + W / 2) / square_mm)
        j = np.floor((y + H / 2) / square_mm)
        black = ((i + j) % 2 == 0)
        out = np.where(black, 0.08, 0.85)
        if marker_mm:
            cxm = (i + 0.5) * square_mm - W / 2
            cym = (j + 0.5) * square_mm - H / 2
            inm = (np.abs(x - cxm) < marker_mm / 2) & (np.abs(y - cym) < marker_mm / 2) & ~black
            out = np.where(inm, 0.5, out)
        return np.where(inside, out, 0.6)
    return tex


def load_aruco_bits(path=None) -> dict:
    """config/sim/aruco_dict_4x4_50.csv → {id: (4, 4) 비트 배열, 1 = 흰색} (출처 머리 · 팀장검증 7차 §5.3)."""
    import csv as _csv
    from pathlib import Path as _P
    p = _P(path) if path else _P(__file__).resolve().parents[3] / "config" / "sim" / "aruco_dict_4x4_50.csv"
    with open(p, encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.startswith("#")]
    return {int(r["id"]): np.array([int(c) for c in r["bits"]]).reshape(4, 4) for r in _csv.DictReader(lines)}


def charuco_texture(square_mm: float, rows: int, cols: int, marker_mm: float, bits: dict):
    """OpenCV CharucoBoard 규약 (legacy 무늬 아님, 명세 v1.2 V12-3): 판 좌표 원점 왼쪽 위 · x 오른쪽 · y 아래 (영상 행).
    9 × 6 판은 왼쪽 위 칸이 검정, 마커는 흰 칸에 행 우선으로 ID 0부터 (스크래치 OpenCV 4.13.0 그림과 대조, 모델 문서 §5.1).
    평면 좌표 (x, y)는 판 가운데 원점 · y 위쪽이라 판 y = −평면 y (위에서 볼 때 거울상이 아니게)."""
    W, H = cols * square_mm, rows * square_mm
    cell = marker_mm / 6.0          # 4 × 4 비트 + 테 1칸
    pad = (square_mm - marker_mm) / 2.0
    lut = np.zeros((max(bits) + 1, 4, 4))
    for k, b in bits.items():
        lut[k] = b

    def tex(x, y):
        xt = np.asarray(x, float) + W / 2
        yt = -np.asarray(y, float) + H / 2
        inside = (xt >= 0) & (xt < W) & (yt >= 0) & (yt < H)
        j = np.clip(np.floor(xt / square_mm).astype(int), 0, cols - 1)
        i = np.clip(np.floor(yt / square_mm).astype(int), 0, rows - 1)
        black = (i + j) % 2 == 0
        val = np.where(black, 0.0, 1.0)
        mid = (i * cols + j) // 2
        mx = xt - j * square_mm - pad
        my = yt - i * square_mm - pad
        inm = ~black & (mx >= 0) & (mx < marker_mm) & (my >= 0) & (my < marker_mm) & (mid < len(lut))
        cx = np.clip(np.floor(mx / cell).astype(int), 0, 5)
        cy = np.clip(np.floor(my / cell).astype(int), 0, 5)
        border = (cx == 0) | (cx == 5) | (cy == 0) | (cy == 5)
        bit = lut[np.clip(mid, 0, len(lut) - 1), np.clip(cy - 1, 0, 3), np.clip(cx - 1, 0, 3)]
        val = np.where(inm, np.where(border, 0.0, bit), val)
        return np.where(inside, 0.08 + 0.77 * val, 0.6)
    return tex


def dots_texture(pitch_mm: float, d_mm: float):
    def tex(x, y):
        fx = (x / pitch_mm) - np.round(x / pitch_mm)
        fy = (y / pitch_mm) - np.round(y / pitch_mm)
        r = np.hypot(fx, fy) * pitch_mm
        return np.where(r < d_mm / 2, 0.08, 0.85)
    return tex


def render_plane(geom: Geometry, R_ps: np.ndarray, t_ps: np.ndarray, texture, light: float = 0.6,
                 supersample: int = 2) -> np.ndarray:
    """평면 표적 (판 좌표 (x, y, 0) → {S}: R_ps · p + t_ps)을 전체 프레임으로 렌더 (빛 세기, 흰 칸 ≈ light)."""
    H, W = geom.height, geom.width
    acc = np.zeros((H, W))
    offs = (np.arange(supersample) + 0.5) / supersample - 0.5
    nrm = R_ps[:, 2]
    depths = []
    cache = geom.__dict__.setdefault("_ray_cache", {})   # 화소 광선은 기하마다 같음 → 한 번만 (왜곡 역계산 비용)
    if supersample not in cache:
        vv, uu = np.mgrid[0:H, 0:W].astype(float)
        cache[supersample] = [geom.ray_s((uu + dx).ravel(), (vv + dy).ravel()).astype(np.float32)
                              for dy in offs for dx in offs]
    for d32 in cache[supersample]:
        d = d32.astype(float)
        denom = d @ nrm
        tt = ((t_ps - geom.C_s) @ nrm) / np.where(np.abs(denom) < 1e-9, 1e-9, denom)
        P = geom.C_s[None, :] + tt[:, None] * d
        q = (P - t_ps[None, :]) @ R_ps
        acc += texture(q[:, 0], q[:, 1]).reshape(H, W)
        depths.append(np.median(tt))
    img = acc / supersample ** 2 * light
    dep = float(np.median(depths))
    blur = geom.aperture_mm * geom.K[0, 0] * geom.pixel_mm * abs(dep - geom.focus_depth) / (dep * geom.focus_depth)
    s = math.hypot(0.4, blur / geom.pixel_mm / 4.0)
    return ndimage.gaussian_filter(img, s, mode="nearest")
