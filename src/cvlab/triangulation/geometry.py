"""영상 점 → {G} 점 변환 사슬 뼈대 (C4 · B1, docs/좌표계.md §3).

교정값은 모두 인자로 받습니다. 기본값은 없습니다 (실제 교정은 T8, D1 – D4).
왜곡 식은 OpenCV 순서 (k1, k2, p1, p2[, k3])를 numpy로 다시 씀 (cv2를 쓰지 않음).
"""
from __future__ import annotations

import warnings

import numpy as np

from .frames import Tf

CALIB_KEYS = ("K", "dist", "laser_plane_C", "T_S_C", "scan_axis_C", "T_G_M")

_UNDIST_MAX_ITER = 50
_UNDIST_TOL = 1e-12


def _dist5(dist):
    d = np.asarray(dist, dtype=np.float64).reshape(-1)
    if d.size < 4:
        raise ValueError(f"dist 길이 {d.size}: (k1, k2, p1, p2[, k3]) 이상이어야 함")
    if d.size > 5 and np.any(d[5:] != 0):
        raise ValueError("k4 이후 (유리식 · 얇은 프리즘 · 기울임) 왜곡 항은 아직 지원하지 않음 (0이어야 함)")
    out = np.zeros(5)
    out[:min(5, d.size)] = d[:5]
    if not np.isfinite(out).all():
        raise ValueError("dist에 유한하지 않은 값")
    return out


def _xy(a, name):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"{name}는 [N, 2]여야 함 (받음 {a.shape})")
    return a


def distort_points(xy, dist):
    """정규 좌표 (x, y) → 왜곡된 정규 좌표 (x_d, y_d). OpenCV 식."""
    xy = _xy(xy, "xy")
    k1, k2, p1, p2, k3 = _dist5(dist)
    x, y = xy[:, 0], xy[:, 1]
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    return np.stack([xd, yd], axis=1)


def undistort_points(xy_d, dist):
    """왜곡된 정규 좌표 → 정규 좌표 (뉴턴 반복, 최대 50회, 허용 1e-12). 수렴 못 하면 경고 + NaN."""
    xy_d = _xy(xy_d, "xy_d")
    k1, k2, p1, p2, k3 = _dist5(dist)
    xd, yd = xy_d[:, 0], xy_d[:, 1]
    x, y = xd.copy(), yd.copy()
    done = np.zeros(x.shape, bool)
    for _ in range(_UNDIST_MAX_ITER):
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        drad = k1 + 2 * k2 * r2 + 3 * k3 * r2 ** 2
        fx = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x) - xd
        fy = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y - yd
        done = np.maximum(np.abs(fx), np.abs(fy)) < _UNDIST_TOL
        if done.all():
            break
        a = rad + 2 * x * x * drad + 2 * p1 * y + 6 * p2 * x
        b = 2 * x * y * drad + 2 * p1 * x + 2 * p2 * y
        c = 2 * x * y * drad + 2 * p1 * x + 2 * p2 * y
        e = rad + 2 * y * y * drad + 6 * p1 * y + 2 * p2 * x
        det = a * e - b * c
        with np.errstate(invalid="ignore", divide="ignore"):
            dx = (e * fx - b * fy) / det
            dy = (-c * fx + a * fy) / det
        x = np.where(done, x, x - dx)
        y = np.where(done, y, y - dy)
    else:
        r2 = x * x + y * y
        rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        fx = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x) - xd
        fy = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y - yd
        done = np.maximum(np.abs(fx), np.abs(fy)) < _UNDIST_TOL
    # 왜곡 함수가 접히는 곳 (rad ≤ 0 또는 야코비안 det ≤ 0) 의 해는 렌즈의 실제 가지가 아님 → 수렴 실패로 봄
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    drad = k1 + 2 * k2 * r2 + 3 * k3 * r2 ** 2
    a = rad + 2 * x * x * drad + 2 * p1 * y + 6 * p2 * x
    b = 2 * x * y * drad + 2 * p1 * x + 2 * p2 * y
    e = rad + 2 * y * y * drad + 6 * p1 * y + 2 * p2 * x
    out = np.stack([x, y], axis=1)
    bad = ~done | ~np.isfinite(out).all(axis=1) | ~(rad > 0) | ~(a * e - b * b > 0)
    if bad.any():
        warnings.warn(f"undistort_points: {int(bad.sum())}개 점이 수렴하지 않아 NaN", RuntimeWarning, stacklevel=2)
        out[bad] = np.nan
    return out


def _K(K):
    K = np.asarray(K, dtype=np.float64)
    if K.shape != (3, 3) or not np.isfinite(K).all():
        raise ValueError("K는 유한한 3 × 3이어야 함")
    if not (K[0, 0] > 0 and K[1, 1] > 0) or np.abs(K[2] - [0, 0, 1]).max() > 1e-12:
        raise ValueError("K: fx · fy > 0, 마지막 행 [0, 0, 1]이어야 함")
    return K


def pixel_to_ray(uv, K, dist):
    """{I} 화소 (u, v) (전체 영상 좌표) → {C} 단위 광선 방향 [N, 3]."""
    uv = _xy(uv, "uv")
    K = _K(K)
    h = np.c_[uv, np.ones(len(uv))]
    xn_d = np.linalg.solve(K, h.T).T[:, :2]
    xn = undistort_points(xn_d, dist)
    r = np.c_[xn, np.ones(len(xn))]
    return r / np.linalg.norm(r, axis=1, keepdims=True)


def intersect_plane(rays, plane):
    """광선 (원점 = {C} 원점) 과 평면 n·p + d = 0 ({C}, |n| = 1, d mm) 의 교점 [N, 3].

    평면과 나란하거나 교점이 카메라 뒤 (t ≤ 0) 면 NaN.
    """
    rays = np.asarray(rays, dtype=np.float64)
    if rays.ndim != 2 or rays.shape[1] != 3:
        raise ValueError("rays는 [N, 3]이어야 함")
    pl = np.asarray(plane, dtype=np.float64).reshape(-1)
    if pl.shape != (4,) or not np.isfinite(pl).all():
        raise ValueError("plane은 [nx, ny, nz, d]")
    n, d = pl[:3], pl[3]
    if abs(np.linalg.norm(n) - 1) > 1e-6:
        raise ValueError(f"평면 법선 크기 {np.linalg.norm(n):.8f} ≠ 1")
    den = rays @ n
    with np.errstate(invalid="ignore", divide="ignore"):
        t = -d / den
    t[~(np.abs(den) > 1e-12) | ~(t > 0)] = np.nan
    return rays * t[:, None]


def _check_calib(calib):
    if not isinstance(calib, dict):
        raise ValueError("calib는 dict여야 함")
    miss = [k for k in CALIB_KEYS if k not in calib or calib[k] is None]
    if miss:
        raise ValueError(f"교정값이 빠짐: {miss} (기본값 없음, T8 교정 결과에서 넣음)")
    for k in ("T_S_C", "T_G_M"):
        T = calib[k]
        if not isinstance(T, Tf) or T.name != k:
            got = T.name if isinstance(T, Tf) else type(T).__name__
            raise ValueError(f"calib[{k!r}]는 이름이 {k}인 Tf여야 함 (받음 {got})")
    a = np.asarray(calib["scan_axis_C"], dtype=np.float64).reshape(-1)
    if a.shape != (3,) or abs(np.linalg.norm(a) - 1) > 1e-6:
        raise ValueError("scan_axis_C는 {C}의 단위 벡터 [3]이어야 함")
    return a


def image_to_G(uv_full, scan_s_mm, calib):
    """{I} 전체 영상 화소 → {G} 점 [N, 3] (mm).

    p_G = T_G_M · (T_S_C · (광선 ∩ 레이저 평면) + s · a_S),  a_S = R_S_C · scan_axis_C.
    scan_s_mm: 스캔 시작에서 잰 스캔 위치 s (mm), 스칼라 또는 [N].
    calib: CALIB_KEYS 모두 필요 (K, dist, laser_plane_C, T_S_C (Tf), scan_axis_C, T_G_M (Tf)).
    """
    a_C = _check_calib(calib)
    uv = _xy(uv_full, "uv_full")
    s = np.broadcast_to(np.asarray(scan_s_mm, dtype=np.float64), (len(uv),))
    P_C = intersect_plane(pixel_to_ray(uv, calib["K"], calib["dist"]), calib["laser_plane_C"])
    T_S_C = calib["T_S_C"]
    P_S = T_S_C.apply(P_C)
    a_S = T_S_C.R @ a_C
    P_M = P_S + s[:, None] * a_S[None, :]
    return calib["T_G_M"].apply(P_M)
