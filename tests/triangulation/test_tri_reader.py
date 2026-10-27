"""T7a 얇은 읽기 시험 (LX13). 가짜 스캔 폴더는 tmp_path에만 만듦 (원시 데이터 폴더에 쓰지 않음)."""
import csv

import numpy as np
import pytest
from PIL import Image

from cvlab.triangulation import SPEC_FRAME_COLUMNS, load_frame, read_frames_index

REQ = [k for k, (_, req) in SPEC_FRAME_COLUMNS.items() if req]


def _row(i, file, **kw):
    r = dict(scan_id="S01_r01_L004", layer_idx=4, frame_idx=i, file=file, t_host_ns=4990008333 + i,
             exposure_us=800.0, gain_db=0.0, bit_depth=10, pixel_format="GRAY10", lossy="false",
             roi_x0_px=0, roi_y0_px=272, roi_w_px=8, roi_h_px=5, laser_on="true", trigger_mode="hw",
             trig_pulse_idx=i, dropped_before=0, future_col="x")
    r.update(kw)
    return r


def _write(d, rows, drop=()):
    keys = [k for k in rows[0] if k not in drop]
    with open(d / "frames_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows([{k: r[k] for k in keys} for r in rows])


def _imgs():
    rng = np.random.default_rng(0)
    return [rng.integers(0, 1024, (5, 8)).astype(np.uint16), rng.integers(0, 256, (5, 8)).astype(np.uint8)]


def test_required_columns_constant():
    assert REQ == ["frame_idx", "file", "laser_on", "bit_depth", "roi_x0_px", "roi_y0_px", "roi_w_px",
                   "roi_h_px", "t_host_ns"]


def test_png_16_and_8_bit(tmp_path):
    (tmp_path / "frames").mkdir()
    a16, a8 = _imgs()
    Image.fromarray(a16).save(tmp_path / "frames" / "000000.png")
    Image.fromarray(a8).save(tmp_path / "frames" / "000001.png")
    _write(tmp_path, [_row(0, "frames/000000.png"), _row(1, "frames/000001.png", bit_depth=8, laser_on="false",
                                                          trig_pulse_idx="")])
    df = read_frames_index(tmp_path)
    assert len(df) == 2 and df["laser_on"].dtype == bool and list(df["laser_on"]) == [True, False]
    assert df["bit_depth"].dtype == np.int64 and df["t_host_ns"].iloc[0] == 4990008333
    assert df["future_col"].iloc[0] == "x"                    # 모르는 열은 그대로
    assert df["trig_pulse_idx"].isna().iloc[1]               # 조건부 열 빈 칸 = 결측
    f0, f1 = load_frame(tmp_path, df.iloc[0]), load_frame(tmp_path, df.iloc[1])
    assert f0.dtype == np.uint16 and np.array_equal(f0, a16)
    assert f1.dtype == np.uint16 and np.array_equal(f1, a8)


def test_npz_frames(tmp_path):
    a16, _ = _imgs()
    np.savez(tmp_path / "frames.npz", f000000=a16, f000001=a16[::-1])
    _write(tmp_path, [_row(0, "frames.npz#f000000"), _row(1, "frames.npz#f000001")])
    df = read_frames_index(tmp_path)
    assert np.array_equal(load_frame(tmp_path, df.iloc[1]), a16[::-1])


@pytest.mark.parametrize("col", REQ)
def test_missing_required_column_named(tmp_path, col):
    _write(tmp_path, [_row(0, "frames/000000.png")], drop=(col,))
    with pytest.raises(ValueError, match=col):
        read_frames_index(tmp_path)


def test_conditional_columns_optional(tmp_path):
    _write(tmp_path, [_row(0, "frames/000000.png")], drop=("trig_pulse_idx",))
    df = read_frames_index(tmp_path)
    assert "trig_pulse_idx" not in df.columns and len(df) == 1


def test_gate_on_bool(tmp_path):
    _write(tmp_path, [_row(0, "f", trigger_mode="gate", gate_on="true"), _row(1, "f", trigger_mode="gate", gate_on="false")])
    df = read_frames_index(tmp_path)
    assert list(df["gate_on"]) == [True, False]


def test_size_mismatch_rejected(tmp_path):
    (tmp_path / "frames").mkdir()
    a16, _ = _imgs()
    Image.fromarray(a16).save(tmp_path / "frames" / "000000.png")
    _write(tmp_path, [_row(0, "frames/000000.png", roi_h_px=6)])
    df = read_frames_index(tmp_path)
    with pytest.raises(ValueError):
        load_frame(tmp_path, df.iloc[0])


def test_bad_bool_value_rejected(tmp_path):
    _write(tmp_path, [_row(0, "f", laser_on="yes")])
    with pytest.raises(ValueError):
        read_frames_index(tmp_path)
