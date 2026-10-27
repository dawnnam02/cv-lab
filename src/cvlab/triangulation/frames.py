"""이름 붙은 4 × 4 강체 변환 (C4 §6, docs/좌표계.md §2).

`T_<to>_<from>`: from 좌표계의 점을 to 좌표계로 바꿈. p_to = R · p_from + t (mm).
"""
from __future__ import annotations

import numpy as np

_TOL = 1e-6


def _check_frame_name(n):
    if not isinstance(n, str) or not n or "_" in n:
        raise ValueError(f"좌표계 이름 {n!r}: 밑줄 없는 빈칸 아닌 문자열이어야 함")


def _check_R(R, label):
    R = np.asarray(R, dtype=np.float64)
    if R.shape != (3, 3) or not np.isfinite(R).all():
        raise ValueError(f"{label}: R은 유한한 3 × 3이어야 함")
    det = float(np.linalg.det(R))
    if abs(det - 1.0) > _TOL:
        raise ValueError(f"{label}: det(R) = {det:.6f} ≠ +1 (거울 · 배율 거부)")
    if np.abs(R.T @ R - np.eye(3)).max() > _TOL:
        raise ValueError(f"{label}: RᵀR ≠ I (직교 아님)")
    return R


class Tf:
    """T_to_from 강체 변환."""

    def __init__(self, to, frm, R=np.eye(3), t=(0, 0, 0)):
        _check_frame_name(to)
        _check_frame_name(frm)
        self.to, self.frm = to, frm
        R = _check_R(R, f"T_{to}_{frm}")
        t = np.asarray(t, dtype=np.float64).reshape(-1)
        if t.shape != (3,) or not np.isfinite(t).all():
            raise ValueError(f"T_{to}_{frm}: t는 유한한 길이 3이어야 함")
        self._M = np.eye(4)
        self._M[:3, :3] = R
        self._M[:3, 3] = t

    @classmethod
    def from_matrix(cls, to, frm, M4):
        M4 = np.asarray(M4, dtype=np.float64)
        if M4.shape != (4, 4):
            raise ValueError("M4는 4 × 4여야 함")
        if np.abs(M4[3] - np.array([0, 0, 0, 1.0])).max() > _TOL:
            raise ValueError("M4 마지막 행은 [0, 0, 0, 1]이어야 함")
        return cls(to, frm, M4[:3, :3], M4[:3, 3])

    @property
    def name(self) -> str:
        return f"T_{self.to}_{self.frm}"

    @property
    def M(self) -> np.ndarray:
        return self._M.copy()

    @property
    def R(self) -> np.ndarray:
        return self._M[:3, :3].copy()

    @property
    def t(self) -> np.ndarray:
        return self._M[:3, 3].copy()

    def __matmul__(self, other):
        """T_a_b @ T_b_c = T_a_c. 가운데 이름이 다르면 ValueError."""
        if not isinstance(other, Tf):
            raise TypeError("Tf끼리만 곱함 (점은 .apply)")
        if self.frm != other.to:
            raise ValueError(f"{self.name} @ {other.name}: 연결 불가 ({self.frm} ≠ {other.to})")
        M = self._M @ other._M
        return Tf(self.to, other.frm, M[:3, :3], M[:3, 3])

    def inv(self):
        R, t = self._M[:3, :3], self._M[:3, 3]
        return Tf(self.frm, self.to, R.T, -R.T @ t)

    def apply(self, P):
        """점 P ([N, 3] 또는 [3])를 바꿈. 입력과 같은 모양으로 돌려줌."""
        P = np.asarray(P, dtype=np.float64)
        one = P.ndim == 1
        Q = np.atleast_2d(P)
        if Q.shape[-1] != 3 or Q.ndim != 2:
            raise ValueError(f"점 배열은 [N, 3] 또는 [3]이어야 함 (받음 {P.shape})")
        out = Q @ self._M[:3, :3].T + self._M[:3, 3]
        return out[0] if one else out

    def __repr__(self):
        return f"Tf({self.name}, t={np.round(self._M[:3, 3], 6).tolist()})"
