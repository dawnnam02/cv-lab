# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""시드 나무 (세부청사진 §6.8).

캠페인 시드 → 시편 → 층 → 스캔 → 성분. 갈래마다 이름 (문자열 · 정수)을 sha256으로 32비트 키로 바꿔
`numpy.random.SeedSequence(entropy=캠페인 시드, spawn_key=키들)`을 만든다. 그래서 갈래 값은 경로 이름에만
달려 있고 처리 순서 · 작업자 수 · 먼저 만든 갈래 수와 무관하다.

평가용 시드는 환경 변수 CVLAB_EVAL_SEED에서만 읽는다 (코드 · 설정 · 문서에 값 없음, §6.9).
"""
from __future__ import annotations

import hashlib
import os

import numpy as np

EVAL_ENV = "CVLAB_EVAL_SEED"
SEED_MAX = 2 ** 63  # 명세: 0 ≤ seed < 2^63


def _key(part) -> int:
    if isinstance(part, bool) or not isinstance(part, (str, int, np.integer)):
        raise TypeError(f"시드 갈래 이름은 문자열 또는 정수: {part!r}")
    tag = ("i:" if isinstance(part, (int, np.integer)) else "s:") + str(part)
    return int.from_bytes(hashlib.sha256(tag.encode("utf-8")).digest()[:4], "little")


def check_seed(seed) -> int:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError(f"시드는 정수: {seed!r}")
    seed = int(seed)
    if not 0 <= seed < SEED_MAX:
        raise ValueError("시드 범위 밖 (0 ≤ seed < 2^63)")
    return seed


class SeedTree:
    """갈래 하나. child()로 내려가고 rng() · int_seed()로 쓴다."""

    __slots__ = ("seed", "path")

    def __init__(self, seed: int, path: tuple = ()):
        self.seed = check_seed(seed)
        self.path = tuple(path)
        for p in self.path:
            _key(p)

    def child(self, *parts) -> "SeedTree":
        return SeedTree(self.seed, self.path + tuple(parts))

    def seed_sequence(self) -> np.random.SeedSequence:
        return np.random.SeedSequence(entropy=self.seed, spawn_key=tuple(_key(p) for p in self.path))

    def rng(self) -> np.random.Generator:
        return np.random.Generator(np.random.PCG64(self.seed_sequence()))

    def int_seed(self) -> int:
        """이 갈래를 대표하는 정수 시드 (meta.sim_seed · rep.noise_seed 용, 0 ≤ x < 2^63)."""
        w = self.seed_sequence().generate_state(2, np.uint32)
        return ((int(w[1]) << 32) | int(w[0])) & (SEED_MAX - 1)

    def __repr__(self) -> str:  # 시드 값은 찍지 않음 (평가 세트 보호)
        return f"SeedTree(tag={seed_tag(self.seed)}, path={self.path})"


def seed_tag(seed: int) -> str:
    """요약 줄에 쓰는 시드 꼬리표 (시드 값 대신 sha256 앞 8자리)."""
    return hashlib.sha256(f"cvlab-sim:{check_seed(seed)}".encode()).hexdigest()[:8]


def eval_seed_from_env(environ=None) -> int:
    """평가용 시드. 환경 변수가 없거나 정수가 아니면 오류 (기본값 없음)."""
    env = os.environ if environ is None else environ
    raw = env.get(EVAL_ENV)
    if raw is None or not str(raw).strip():
        raise RuntimeError(f"평가용 실행은 환경 변수 {EVAL_ENV}가 필요함 (기본값 없음)")
    try:
        return check_seed(int(str(raw).strip()))
    except ValueError as e:
        raise RuntimeError(f"{EVAL_ENV}가 0 ≤ x < 2^63 정수가 아님") from e
