# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""기준 · 반복 (세부청사진 §6.7, SM8). 명세 4절 (ref) · 7절 (rep) 필드 이름 그대로의 행을 만든다.

- 세션 기준: 줄마다 bed_bare (같은 X, ref.scan_pass_idx = 줄 번호), 필러게이지 4장 (feeler), 배경 · 암흑 · 정지 반복
  (각 100장). 층 번호 −1 (출력 전).
- 층마다 두 단 (step_gauge 2행, 같은 Z): ref.scan_id = 그 층 첫 줄 스캔, ref_id 숫자는 세션 안 약어별 순번.
- 같은 층 반복 (MSA-01): 가운데 층 첫 줄, 반복마다 잡음 시드 다름 · 참값 같음.
"""
from __future__ import annotations

ABBR = {"bed_bare": "BED", "background": "BKG", "dark": "DRK", "bed_marker": "MRK", "ref_tower": "TWR",
        "step_gauge": "STG", "feeler": "FLR", "daily_ref": "DAY", "static_repeat": "STA"}
REF_FIELDS = ["ref_id", "kind", "scan_id", "layer_idx", "scan_pass_idx", "n_frames", "frames_dir", "marker_id",
              "marker_x_mm", "marker_y_mm", "t_start_ns", "calibration_id", "gauge_block_id", "gauge_height_mm",
              "gauge_temp_c", "line_peak_pct", "note"]
REP_FIELDS = ["study_id", "specimen_id", "part_idx", "repeat_idx", "session_id", "operator", "remount", "rehome",
              "run_order", "interval_s", "scan_id", "noise_seed", "truth_id"]
NEEDS_CAL = {"bed_bare", "bed_marker", "ref_tower", "step_gauge", "feeler"}


class RefIds:
    """세션 안 약어별 순번 (001부터 빈 번호 없이, 999 넘으면 4자리)."""

    def __init__(self):
        self.n = {}

    def next(self, kind: str) -> str:
        a = ABBR[kind]
        self.n[a] = self.n.get(a, 0) + 1
        k = self.n[a]
        return f"REF-{a}-{k:03d}" if k < 1000 else f"REF-{a}-{k:04d}"


def ref_row(ref_id, kind, t_start_ns, n_frames, cal_id=None, scan_id=None, layer_idx=None, scan_pass_idx=None,
            gauge_id=None, gauge_h=None, gauge_temp=None, line_peak_pct=None, note="-") -> dict:
    if kind in NEEDS_CAL and not cal_id:
        raise ValueError(f"{kind} 기준은 교정 ID가 필요함")
    row = {k: None for k in REF_FIELDS}
    row.update(ref_id=ref_id, kind=kind, scan_id=scan_id, layer_idx=layer_idx, scan_pass_idx=scan_pass_idx,
               n_frames=int(n_frames), frames_dir="frames/", t_start_ns=int(t_start_ns), calibration_id=cal_id,
               gauge_block_id=gauge_id, gauge_height_mm=None if gauge_h is None else round(float(gauge_h), 4),
               gauge_temp_c=None if gauge_temp is None else round(float(gauge_temp), 2),
               line_peak_pct=line_peak_pct, note=note or "-")
    return row


def msa_design(study_id: str, specimen_id: str, session_id: str, scan_id: str, n_repeats: int, tree,
               truth_id: str, operator: str = "sim_A", interval_s: float = 0.0, blind: bool = False) -> tuple:
    """(design 행, design_executed 행). 실행 순서는 시드로 섞음 (반복 번호와 다르게 권장, 명세 7절)."""
    rng = tree.child("msa", study_id, "order").rng()
    order = list(rng.permutation(n_repeats) + 1)
    design, executed = [], []
    for i in range(n_repeats):
        seed = tree.child("msa", study_id, i + 1).int_seed()
        row = dict(study_id=study_id, specimen_id=specimen_id, part_idx=0, repeat_idx=i + 1, session_id=session_id,
                   operator=operator, remount=False, rehome=False, run_order=int(order[i]),
                   interval_s=float(interval_s), scan_id=None, noise_seed=None if blind else seed, truth_id=truth_id)
        design.append(row)
        executed.append(dict(row, scan_id=scan_id))
    return design, executed


def two_step_rule(h1: float, h2: float, layer_z: float, u1_um: float, u2_um: float, sigma_um: float = 1.5) -> dict:
    """명세 4절 두 단 규칙 + v1.1 두 단 비 경고 (검증기와 같은 식을 시뮬레이터 쪽에서 미리 봄)."""
    gap = h1 - h2
    ok = (0 < gap <= 3.04 + 1e-9) and (h1 <= layer_z + 1e-9) and (layer_z - h2 <= 8.0 + 1e-9)
    u = max(u1_um, u2_um)
    thr = 4.0 / (2 * sigma_um ** 2 + 2 * u ** 2) ** 0.5
    ratio = (layer_z - h1) / gap if gap > 0 else float("inf")
    return {"rule_ok": ok, "ratio": ratio, "ratio_limit": thr, "ratio_ok": ratio <= thr + 1e-9}
