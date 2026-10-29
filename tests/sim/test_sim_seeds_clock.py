# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""시드 나무 · 가상 시계 · 설정 (S1)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from cvlab.sim import SeedTree, VirtualClock, eval_seed_from_env, seed_tag
from cvlab.sim.simconfig import ROOT, data_roots, load_default


def test_same_path_same_values():
    a = SeedTree(123).child("S01", 1, "L004", 0).rng().normal(size=5)
    b = SeedTree(123).child("S01", 1, "L004", 0).rng().normal(size=5)
    assert np.array_equal(a, b)


def test_order_independent():
    t = SeedTree(7)
    first = [t.child("S01", i).int_seed() for i in range(5)]
    later = [t.child("S01", i).int_seed() for i in reversed(range(5))][::-1]
    assert first == later


def test_paths_and_seeds_differ():
    t = SeedTree(7)
    assert t.child("S01", 1).int_seed() != t.child("S01", 2).int_seed()
    assert t.child("1").int_seed() != t.child(1).int_seed()  # 문자열과 정수 갈래는 다름
    assert SeedTree(7).child("a").int_seed() != SeedTree(8).child("a").int_seed()


def test_int_seed_range_and_bad_seed():
    for i in range(50):
        assert 0 <= SeedTree(i).child("x").int_seed() < 2 ** 63
    with pytest.raises(ValueError):
        SeedTree(-1)
    with pytest.raises(TypeError):
        SeedTree(1.5)


def test_eval_seed_env_only():
    with pytest.raises(RuntimeError):
        eval_seed_from_env({})
    with pytest.raises(RuntimeError):
        eval_seed_from_env({"CVLAB_EVAL_SEED": "abc"})
    assert eval_seed_from_env({"CVLAB_EVAL_SEED": " 99 "}) == 99


def test_seed_not_printed():
    t = SeedTree(987654321)
    assert "987654321" not in repr(t)
    tag = seed_tag(987654321)
    assert len(tag) == 8 and tag == seed_tag(987654321) and tag != seed_tag(987654322)


def test_clock_start_and_advance():
    c = VirtualClock("2026-11-20T09:00:00+09:00")
    assert c.start_ns == int(datetime.fromisoformat("2026-11-20T09:00:00+09:00").timestamp()) * 10 ** 9
    c.advance(1.5)
    assert c.t_ns - c.start_ns == 1_500_000_000
    assert c.iso() == "2026-11-20T09:00:01+09:00"
    assert c.iso("milliseconds").endswith("01.500+09:00")


def test_clock_rules():
    with pytest.raises(ValueError):
        VirtualClock("2026-11-20T09:00:00")
    c = VirtualClock("2026-11-20T09:00:00+09:00")
    with pytest.raises(ValueError):
        c.advance(-1)
    f = c.fork()
    f.advance(10)
    assert c.elapsed_s == 0 and f.elapsed_s == 10


def test_data_roots(tmp_path):
    cfg = load_default()
    raw, truth = data_roots(cfg, tmp_path)
    assert raw == tmp_path / "raw" and truth == tmp_path / "truth"
    with pytest.raises(ValueError):
        data_roots(cfg, ROOT / "data")
    raw, truth = data_roots(cfg)  # 승인된 설정 값 (저장소 밖)
    assert Path(cfg["paths"]["raw_root"]) == raw and not str(raw.resolve()).startswith(str(ROOT.resolve()))


def test_default_config_unknown_key(tmp_path):
    p = tmp_path / "d.yaml"
    p.write_text("paths: {}\nfoo: 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_default(p)
