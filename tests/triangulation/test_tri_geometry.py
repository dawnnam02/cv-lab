"""T7a 왜곡 · 광선 · 평면 · image_to_G 시험 (LX12).

아래 기하와 왜곡 계수는 **시험용 가정**입니다 (교정값 아님, T8에서 실제 값).
"""
import warnings

import numpy as np
import pytest

from cvlab.triangulation import (CALIB_KEYS, Tf, distort_points, image_to_G, intersect_plane, pixel_to_ray,
                                 undistort_points)

DIST = np.array([-0.05, 0.01, 0.001, -0.0005, 0.002])   # 시험용 가정
K = np.array([[2666.7, 0, 640.0], [0, 2666.7, 400.0], [0, 0, 1.0]])   # 시험용 가정 (f 8 mm ÷ 3 µm)


def _ref_distort(xy, d):
    k1, k2, p1, p2, k3 = d
    x, y = xy[:, 0], xy[:, 1]
    r2 = x * x + y * y
    rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    return np.c_[x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x), y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y]


def _geom(rng):
    """카메라 광축이 레이저 평면과 30°, {S} 원점이 렌즈 앞 50 mm (시험용 가정)."""
    c, s = np.cos(np.radians(30)), np.sin(np.radians(30))
    R_C_S = np.array([[1, 0, 0], [0, -c, -s], [0, s, -c]])
    T_C_S = Tf("C", "S", R_C_S, (0, 0, 50.0))
    n = R_C_S[:, 1]
    plane = np.r_[n, -n @ np.array([0, 0, 50.0])]
    a = 0.003
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    T_G_M = Tf("G", "M", Rz, (175.0, 155.0, 2.0))
    calib = dict(K=K, dist=DIST, laser_plane_C=plane, T_S_C=T_C_S.inv(), scan_axis_C=n, T_G_M=T_G_M)
    P_S = np.c_[rng.uniform(-8, 8, 200), np.zeros(200), rng.uniform(-3, 3, 200)]
    P_C = T_C_S.apply(P_S)
    xd = _ref_distort(P_C[:, :2] / P_C[:, 2:3], DIST)
    uv = np.c_[K[0, 0] * xd[:, 0] + K[0, 2], K[1, 1] * xd[:, 1] + K[1, 2]]
    return calib, P_S, uv


def test_distort_matches_opencv_formula():
    xy = np.random.default_rng(0).uniform(-0.2, 0.2, (1000, 2))
    assert np.abs(distort_points(xy, DIST) - _ref_distort(xy, DIST)).max() < 1e-12
    assert np.abs(distort_points(xy, DIST[:4]) - _ref_distort(xy, np.r_[DIST[:4], 0])).max() < 1e-12


def test_undistort_roundtrip():
    xy = np.random.default_rng(1).uniform(-0.25, 0.25, (2000, 2))
    assert np.abs(undistort_points(distort_points(xy, DIST), DIST) - xy).max() < 1e-9


def test_undistort_nonconvergence_gives_nan_and_warning():
    bad = np.array([-5.0, 0, 0, 0, 0])                    # r가 크면 왜곡 함수가 뒤집힘
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        out = undistort_points(np.array([[3.0, 3.0], [0.01, 0.0]]), bad)
    assert np.isnan(out[0]).all() and np.isfinite(out[1]).all() and len(w) >= 1


def test_unsupported_distortion_terms_rejected():
    with pytest.raises(ValueError):
        distort_points(np.zeros((1, 2)), [0, 0, 0, 0, 0, 0.1, 0, 0])


def test_pixel_to_ray_principal_point():
    r = pixel_to_ray(np.array([[640.0, 400.0]]), K, DIST)
    assert np.allclose(r, [[0, 0, 1]], atol=1e-12)
    assert np.allclose(np.linalg.norm(pixel_to_ray(np.array([[0, 0], [1279, 799.0]]), K, DIST), axis=1), 1)


def test_intersect_plane_simple():
    rays = np.array([[0, 0, 1.0], [0.6, 0, 0.8], [1.0, 0, 0]])
    P = intersect_plane(rays, [0, 0, 1, -50.0])
    assert np.allclose(P[0], [0, 0, 50]) and np.allclose(P[1], [37.5, 0, 50]) and np.isnan(P[2]).all()
    with pytest.raises(ValueError):
        intersect_plane(rays, [0, 0, 2, -50.0])


def test_image_to_G_recovers_points():
    rng = np.random.default_rng(3)
    calib, P_S, uv = _geom(rng)
    assert (uv[:, 0] > 0).all() and (uv[:, 0] < 1279).all() and (uv[:, 1] > 0).all() and (uv[:, 1] < 799).all()
    for s in (0.0, 3.0, np.linspace(0, 10, len(uv))):
        P_G = calib["T_G_M"].apply(P_S + np.asarray(s).reshape(-1, 1) * np.array([0, 1.0, 0]))
        assert np.abs(image_to_G(uv, s, calib) - P_G).max() < 1e-6


@pytest.mark.parametrize("key", CALIB_KEYS)
def test_image_to_G_missing_calibration(key):
    calib, _, uv = _geom(np.random.default_rng(4))
    with pytest.raises((KeyError, ValueError)):
        image_to_G(uv, 0.0, {k: v for k, v in calib.items() if k != key})


def test_image_to_G_wrong_transform_name():
    calib, _, uv = _geom(np.random.default_rng(5))
    calib["T_S_C"] = calib["T_S_C"].inv()                 # 이름 T_C_S
    with pytest.raises(ValueError):
        image_to_G(uv, 0.0, calib)
