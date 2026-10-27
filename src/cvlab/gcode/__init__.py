"""G코드 해석과 층별 정답 높이 지도 (T4a · G1 · G2 · G3)."""
from .bead import bead_area, bead_profile_height, effective_width, width_from_area
from .grid import make_grid
from .params import GCodeError, GCodeParams
from .parser import ParseResult, parse_file, parse_text
from .reference import RefStack, build_reference

__all__ = [
    "GCodeError", "GCodeParams", "ParseResult", "RefStack",
    "bead_area", "bead_profile_height", "build_reference", "effective_width",
    "make_grid", "parse_file", "parse_text", "width_from_area",
]
