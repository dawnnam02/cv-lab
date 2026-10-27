"""T7a Tf 시험 (LX12 앞부분, C4 §6 규칙)."""
import numpy as np
import pytest

from cvlab.triangulation import Tf


def _rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def test_name_and_chain():
    A = Tf("G", "M", _rot(0.01, 0.02, 0.3), (100, 90, 0))
    B = Tf("M", "S", _rot(0.1, -0.2, 0.05), (0, 3, -1))
    C = A @ B
    assert A.name == "T_G_M" and C.name == "T_G_S" and C.inv().name == "T_S_G"
    p = np.random.default_rng(0).normal(0, 20, (50, 3))
    assert np.abs(C.apply(p) - A.apply(B.apply(p))).max() < 1e-12


def test_roundtrip_below_1e9():
    T = Tf("G", "M", _rot(0.4, -0.3, 1.2), (175.0, 155.0, 2.0))
    p = np.random.default_rng(1).normal(0, 100, (1000, 3))
    assert np.abs(T.inv().apply(T.apply(p)) - p).max() < 1e-9
    assert np.abs((T.inv() @ T).M - np.eye(4)).max() < 1e-12


def test_wrong_chain_rejected():
    A, B = Tf("G", "M"), Tf("M", "S")
    with pytest.raises(ValueError):
        B @ A


@pytest.mark.parametrize("R", [np.diag([1.0, 1.0, -1.0]), np.diag([-1.0, 1.0, 1.0]), 2 * np.eye(3),
                               np.array([[1, 0.1, 0], [0, 1, 0], [0, 0, 1.0]])])
def test_non_rotation_rejected(R):
    with pytest.raises(ValueError):
        Tf("G", "M", R)


def test_from_matrix_and_apply_shapes():
    M = np.eye(4)
    M[:3, 3] = (1, 2, 3)
    T = Tf.from_matrix("G", "M", M)
    assert T.apply(np.zeros(3)).shape == (3,)
    assert np.allclose(T.apply(np.zeros((2, 3))), [[1, 2, 3], [1, 2, 3]])
    M[3, 0] = 0.5
    with pytest.raises(ValueError):
        Tf.from_matrix("G", "M", M)


def test_bad_frame_names_rejected():
    with pytest.raises(ValueError):
        Tf("G_x", "M")
    with pytest.raises(ValueError):
        Tf("", "M")
