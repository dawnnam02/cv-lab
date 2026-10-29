# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""T3 시험 도우미: 작은 손 G코드 평판, 설정."""
from __future__ import annotations

from cvlab.gcode import GCodeParams, parse_text
from cvlab.sim.shape import specimen_from_result
from cvlab.sim.simconfig import load_default


def plate_gcode(n_layers: int = 2, size: float = 4.0, x0: float = 100.0, y0: float = 100.0,
                pitch: float = 0.4, lh: float = 0.2) -> str:
    lines = ["; 시험용 손 평판 (T3)", "G21", "G90", "M83", "G92 E0"]
    for k in range(n_layers):
        z = round((k + 1) * lh, 4)
        lines += [";LAYER_CHANGE", f";Z:{z}", f";HEIGHT:{lh}", f"G1 Z{z} F600",
                  f"G0 X{x0 + pitch / 2:.3f} Y{y0 + pitch / 2:.3f} F6000", ";TYPE:Solid infill"]
        n = int(round(size / pitch))
        for i in range(n):
            y = y0 + pitch / 2 + i * pitch
            xa, xb = (x0 + pitch / 2, x0 + size - pitch / 2) if i % 2 == 0 else (x0 + size - pitch / 2, x0 + pitch / 2)
            if i:
                lines.append(f"G1 X{xa:.3f} Y{y:.3f} E0.01 F1800")
            lines.append(f"G1 X{xb:.3f} Y{y:.3f} E0.12 F1800")
    return "\n".join(lines) + "\n"


def plate_specimen(n_layers: int = 2, **kw):
    cfg = load_default()
    r = parse_text(plate_gcode(n_layers, **kw), GCodeParams(line_width_mm=0.4))
    return cfg, specimen_from_result("hand_plate", r, cfg)
