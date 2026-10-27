"""판정 영역 (T4b · G4). 문서: docs/판정-영역.md

G코드와 센서 기하만으로 층마다 판정에 넣는 칸과 빼는 칸을 정한다. 측정값은 보지 않는다 (MF-JDG-03).
"""
from .coverage import coverage_mask, plan_passes
from .grid import aligned_grid, is_aligned, object_bbox
from .masks import depth_out, edge_band, predict_occlusion
from .params import RegionParams
from .stack import REASON_BITS, REASON_CODE, RegionStack, build_region, codes_from_bits

__all__ = [
    "RegionParams", "object_bbox", "aligned_grid", "is_aligned", "plan_passes", "coverage_mask",
    "edge_band", "predict_occlusion", "depth_out", "build_region", "RegionStack",
    "REASON_BITS", "REASON_CODE", "codes_from_bits",
]
