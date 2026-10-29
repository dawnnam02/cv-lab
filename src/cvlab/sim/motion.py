# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""움직임 · 위치 로그 (세부청사진 §6.5, SM6). SV08 + Klipper, 층 스캔 매크로 LM-T14-3 (T14 9.4절).

층마다: layer_change → 리트랙트 · Z hop → 줄마다 (_SCAN_LINE: 도움닫기 시작점 → M400 → GET_POSITION (report)
→ 등속 → 펄스 시작 (scan_start, cmd) → 펄스마다 plan → 펄스 끝 (scan_end, cmd) → M400 · GET_POSITION) → 레인
→ 낮은 단 h2 → 높은 단 h1 → 레인 → resume. Z는 줄 · 단 내내 같은 명령 Z.
post (COOL_RESCAN): Z +10 상대 → cool_start → 대기 → cool_end → 층 윗면 + hop → 모든 줄 + 두 단 (리트랙트 없음,
resume 없음, pass 0, 모터 유지).

위치 출처 (T14 §12): cmd = 명령 (실제보다 cmd_lead_s 앞선 시각에 기록), plan = 펄스 번호 × 주기 보간 (지연 없는 이상
위치), report = 정지 뒤. 실제 노즐 위치는 펄스 시작 지연을 넣은 값이고 렌더에만 씀 (위치 로그에 안 적음).
실제 Z = 명령 Z (1 + g) + 워블 + Z 이동마다 무작위 + 프레임 드리프트 (시각) + 메시 (노즐 XY). 출력과 같은 Z축 모델.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .clock import VirtualClock

POS_FIELDS = ["t_ns", "clock", "source", "x_mm", "y_mm", "z_mm", "e_mm", "feed_mm_s", "layer_idx", "pass_idx",
              "mesh_dz_mm", "event"]


def choose_steps(z_top: float, steps: dict) -> tuple[int, int]:
    """T14 9.2: h1 = 층 윗면 이하 가장 높은 단, h2 = h1보다 낮고 h1 − gap 이상인 단 중 가장 낮은 단. 없으면 −1."""
    h, use, gap = steps["height_mm"], steps["use"], steps["gap_mm"]
    i1 = -1
    for i, hv in enumerate(h):
        if use[i] and hv <= z_top + 1e-4:
            i1 = i
    i2 = -1
    if i1 >= 0:
        for i, hv in enumerate(h):
            if use[i] and hv < h[i1] and hv >= h[i1] - gap - 1e-4:
                i2 = i
                break
    return i1, i2


class ZModel:
    """노즐 실제 Z (출력과 같은 Z축 오차 모델, shape.ZAxis 참값을 이어받음)."""

    def __init__(self, zparams: dict, rng, bed, t0_s: float = 0.0):
        self.p = zparams
        self.rng = rng
        self.bed = bed
        self.t0 = t0_s
        self.err_um = 0.0
        self.moves = []

    def new_move(self):
        s = self.p.get("nonrep_sigma_um", 0.0)
        self.err_um = float(self.rng.normal(0.0, s)) if (self.rng is not None and s > 0) else 0.0
        self.moves.append(round(self.err_um, 4))

    def actual(self, z_cmd, t_s, x, y):
        p = self.p
        g = p.get("gain_ppm", 0.0) * 1e-6
        z = z_cmd * (1 + g)
        if p.get("wobble_amp_um", 0.0):
            z = z + p["wobble_amp_um"] / 1000.0 * np.sin(2 * np.pi * z_cmd / p["wobble_period_mm"] +
                                                         p.get("wobble_phase_rad", 0.0))
        z = z + self.err_um / 1000.0 + p.get("frame_drift_um_per_h", 0.0) / 1000.0 * (np.asarray(t_s) - self.t0) / 3600.0
        if p.get("step_um", 0.0):
            q = p["step_um"] / 1000.0
            z = np.round(z / q) * q
        return z + (self.bed.mesh(x, y) if self.bed is not None else 0.0)


@dataclass
class ScanLine:
    """등속 한 번 (스캔 폴더 또는 움직이는 기준 폴더 하나)."""
    kind: str                  # specimen | step_gauge | feeler | bed_bare
    layer_idx: int
    spass: int
    thermal: str
    x_laser: float
    y0_laser: float
    length: float
    z_cmd: float
    x_nozzle: float
    y0_nozzle: float
    gauge_idx: int | None = None
    rows: list = field(default_factory=list)
    t_pulse_ns: np.ndarray | None = None
    y_nozzle_act: np.ndarray | None = None
    z_nozzle_act: np.ndarray | None = None
    t_m400_ns: int = 0
    scan_start_ns: int = 0
    scan_end_ns: int = 0
    t_layer_end_ns: int | None = None
    gauge_temp_c: float | None = None

    @property
    def n_pulses(self) -> int:
        return 0 if self.t_pulse_ns is None else len(self.t_pulse_ns)


class MacroSim:
    """LM-T14-3 매크로를 가상 시계 위에서 펼침."""

    def __init__(self, mcfg: dict, steps: dict, clock: VirtualClock, zmodel: ZModel, offset_nominal,
                 switches: dict | None = None, gauge_temp_fn=None):
        self.m = mcfg
        self.steps = steps
        self.clock = clock
        self.z = zmodel
        self.off = np.asarray(offset_nominal, float)   # 매크로 변수 sensor_dx · dy (명목, 참 오프셋 아님)
        sw = dict(pulse_delay=False)
        sw.update(switches or {})
        self.sw = sw
        self.pos = np.array([175.0, 175.0, 0.0])
        self.e = 0.0
        self.boot_ns = int(round(mcfg["host_boot_s"] * 1e9))
        self.gauge_temp_fn = gauge_temp_fn or (lambda t_s: None)
        self.t_print0_s = 0.0

    # 시각 ---------------------------------------------------------------
    def host_ns(self) -> int:
        return self.boot_ns + int(round(self.clock.elapsed_s * 1e9))

    def _adv(self, s: float):
        self.clock.advance(max(0.0, s))

    def _travel(self, x=None, y=None, z=None, speed=None):
        tgt = self.pos.copy()
        if x is not None:
            tgt[0] = x
        if y is not None:
            tgt[1] = y
        if z is not None:
            tgt[2] = z
        d = float(np.linalg.norm(tgt[:2] - self.pos[:2]))
        dz = abs(tgt[2] - self.pos[2])
        v = speed or self.m["travel_speed_mm_s"]
        a = self.m["accel_mm_s2"]
        t = (d / v + v / a if d > 0 else 0.0) + (dz / self.m["z_speed_mm_s"] if dz > 0 else 0.0)
        self._adv(t)
        self.pos = tgt

    def _row(self, rows, source, event, layer, x=None, y=None, z=None, feed=0.0, t_ns=None, pass_idx=0, mesh=None):
        x = self.pos[0] if x is None else x
        y = self.pos[1] if y is None else y
        z = self.pos[2] if z is None else z
        on = self.z.bed is not None and self.z.bed.mesh_on
        if on and mesh is None:
            mesh = float(self.z.bed.mesh(x, y))
        rows.append(dict(t_ns=int(self.host_ns() if t_ns is None else t_ns), clock="host", source=source,
                         x_mm=round(float(x), 4), y_mm=round(float(y), 4), z_mm=round(float(z), 4),
                         e_mm=round(self.e, 4), feed_mm_s=round(float(feed), 3), layer_idx=int(layer),
                         pass_idx=int(pass_idx), mesh_dz_mm=round(float(mesh), 4) if on else None, event=event))

    # 한 줄 ----------------------------------------------------------------
    def scan_line(self, kind, x_laser, y0_laser, length, layer, spass, thermal, gauge_idx=None,
                  pass_idx: int = 0) -> ScanLine:
        m = self.m
        row = self._row

        def _r(rows, source, event, lay, **kw):  # 이 줄의 모든 행에 같은 pos.pass_idx
            row(rows, source, event, lay, pass_idx=pass_idx, **kw)
        v, T = m["scan_speed_mm_s"], m["trigger_period_s"]
        xn, y0n = x_laser - self.off[0], y0_laser - self.off[1]
        L = ScanLine(kind, layer, spass, thermal, x_laser, y0_laser, length, float(self.pos[2]), xn, y0n, gauge_idx)
        self._travel(x=xn)
        self._travel(y=y0n - m["lead_in_mm"])
        self._adv(m["m400_settle_s"])
        L.t_m400_ns = self.host_ns()
        _r(L.rows, "report", "m400_done", layer)
        self._adv(m["gcode_roundtrip_s"])
        if kind in ("step_gauge", "feeler"):
            L.gauge_temp_c = self.gauge_temp_fn(self.clock.elapsed_s - self.t_print0_s)
        acc = v * v / (2 * m["accel_mm_s2"])
        self._adv(v / m["accel_mm_s2"] + max(0.0, m["lead_in_mm"] - acc) / v)
        ts = self.host_ns()
        lead = int(round(m["cmd_lead_s"] * 1e9))
        delay = (m["pulse_start_delay_on_ms"] * 1e-3) if self.sw["pulse_delay"] else 0.0
        n = int(round(length / (v * T)))
        k = np.arange(n)
        L.t_pulse_ns = ts + np.rint((delay + k * T) * 1e9).astype(np.int64)
        L.y_nozzle_act = y0n + v * (delay + k * T)
        t_s = (L.t_pulse_ns - self.boot_ns) / 1e9
        L.z_nozzle_act = self.z.actual(L.z_cmd, t_s, xn, L.y_nozzle_act)
        L.scan_start_ns = ts - lead
        _r(L.rows, "cmd", "scan_start", layer, y=y0n, feed=v, t_ns=L.scan_start_ns)
        yp = y0n + v * k * T
        mz = self.z.bed.mesh(xn, yp) if (self.z.bed is not None and self.z.bed.mesh_on) else np.zeros(n)
        for kk in range(n):  # plan: 펄스 번호 × 주기
            _r(L.rows, "plan", "none", layer, y=yp[kk], feed=v, t_ns=ts + int(round(kk * T * 1e9)), mesh=mz[kk])
        L.scan_end_ns = ts + int(round(length / v * 1e9)) - lead
        _r(L.rows, "cmd", "scan_end", layer, y=y0n + length, feed=v, t_ns=L.scan_end_ns)
        self._adv(length / v)
        self.pos[1] = y0n + length
        self._adv(v / m["accel_mm_s2"] + m["m400_settle_s"])
        _r(L.rows, "report", "none", layer)
        self._adv(m["gcode_roundtrip_s"])
        L.rows.sort(key=lambda r: r["t_ns"])
        return L

    def lane(self):
        self._travel(y=self.m["lane_y_mm"])

    # 출력 전 -------------------------------------------------------------
    def preprint(self, line_xs, scan_y0, scan_len) -> tuple[list, list]:
        """SCAN_PREPRINT: 줄마다 bed_bare (같은 X) → 레인 → 필러게이지 4장 → 레인. 층 번호 −1."""
        st = self.steps
        self._travel(z=self.m["z_hop_mm"])
        self.z.new_move()
        beds = [self.scan_line("bed_bare", x, scan_y0, scan_len, -1, i, "in_process") for i, x in enumerate(line_xs)]
        self.lane()
        feelers = []
        for i, gid in enumerate(st["ids"]):
            if gid.startswith("FG-"):
                feelers.append(self.scan_line("feeler", st["laser_x_mm"][i], st["y0_mm"], st["len_mm"], -1, 0,
                                              "in_process", gauge_idx=i))
        self.lane()
        return beds, feelers

    # 층 ---------------------------------------------------------------------
    def layer(self, layer, z_top, line_xs, scan_y0, scan_len, print_s, print_xy=(175.0, 175.0),
              repeats: int = 0) -> dict:
        """층 하나 출력 + LM-T14-3. 돌려줌: {"lines": [...], "steps": [h2, h1], "repeats": [...], …}.
        repeats > 0이면 첫 줄 바로 뒤 같은 줄을 pass_idx 1..repeats로 다시 지남 (같은 층 반복, MSA)."""
        m = self.m
        self.pos = np.array([print_xy[0], print_xy[1], z_top])
        self._adv(print_s)
        t_end = self.host_ns()
        first_rows = []
        self._row(first_rows, "cmd", "layer_change", layer, t_ns=t_end)
        self.e -= m["retract_mm"]
        self._travel(z=z_top + m["z_hop_mm"])
        self.z.new_move()
        lines, reps = [], []
        for i, x in enumerate(line_xs):
            lines.append(self.scan_line("specimen", x, scan_y0, scan_len, layer, i, "in_process"))
            if i == 0:
                reps = [self.scan_line("specimen", x, scan_y0, scan_len, layer, 0, "in_process", pass_idx=k)
                        for k in range(1, repeats + 1)]
        steps = self._two_steps(layer, z_top, "in_process")
        self._travel(x=print_xy[0], y=print_xy[1], z=z_top)
        self.e += m["retract_mm"]
        t_res = self.host_ns()
        self._row(first_rows, "cmd", "resume", layer, t_ns=t_res)
        for L in lines:
            L.t_layer_end_ns = t_end
        for L in reps:
            L.t_layer_end_ns = t_end
        lines[0].rows = sorted(first_rows[:1] + lines[0].rows + first_rows[1:], key=lambda r: r["t_ns"])
        return {"lines": lines, "steps": steps, "repeats": reps, "t_layer_end_ns": t_end, "t_resume_ns": t_res}

    def _two_steps(self, layer, z_top, thermal) -> list:
        st = self.steps
        i1, i2 = choose_steps(z_top, st)
        if i2 < 0:
            return []
        self.lane()
        out = [self.scan_line("step_gauge", st["laser_x_mm"][i], st["y0_mm"], st["len_mm"], layer, 0, thermal,
                              gauge_idx=i) for i in (i2, i1)]
        self.lane()
        return out

    # post ---------------------------------------------------------------
    def cool_rescan(self, layer, z_top, line_xs, scan_y0, scan_len, wait_s) -> dict:
        m = self.m
        rows0 = []
        self._travel(z=self.pos[2] + 10.0)
        self._row(rows0, "cmd", "cool_start", layer)
        self._adv(wait_s)
        self._row(rows0, "cmd", "cool_end", layer)
        self._travel(z=z_top + m["z_hop_mm"])
        self.z.new_move()
        lines = [self.scan_line("specimen", x, scan_y0, scan_len, layer, i, "cooled") for i, x in enumerate(line_xs)]
        steps = self._two_steps(layer, z_top, "cooled")
        lines[0].rows = sorted(rows0 + lines[0].rows, key=lambda r: r["t_ns"])
        return {"lines": lines, "steps": steps}


def line_plan(bbox: dict, mcfg: dict, passes: int | None = None) -> tuple[list, float, float]:
    """(레이저 X 목록, 스캔 Y0, 스캔 길이). 줄 수가 설정 목록과 같으면 T14 9절 X (166 · 184), 다르면 물체 가운데에
    18 mm 간격 [T14 9절 P1 식]. Y는 물체 경계 상자 (+ 여유)."""
    margin = mcfg["scan_margin_mm"]
    y0 = bbox["ymin"] - margin / 2
    xs = list(mcfg["line_x_mm"])
    if passes is not None and passes != len(xs):
        cx = (bbox["xmin"] + bbox["xmax"]) / 2
        xs = [round(cx + 18.0 * (i - (passes - 1) / 2), 4) for i in range(passes)]
    return xs, round(y0, 4), round(bbox["ymax"] - bbox["ymin"] + margin, 4)


def check_same_z(lines: list, tol: float = 0.001) -> float:
    """그 층 모든 줄 · 두 단 스캔 구간 cmd 행 Z가 첫 줄 기준 Z와 tol 안인지. 최대 차를 돌려줌."""
    def seg_cmd(L):
        return [r["z_mm"] for r in L.rows if r["source"] == "cmd" and L.scan_start_ns <= r["t_ns"] <= L.scan_end_ns]
    ref = float(np.mean(seg_cmd(lines[0])))
    return max(abs(z - ref) for L in lines for z in seg_cmd(L))
