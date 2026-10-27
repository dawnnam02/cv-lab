"""합격 판정 (T15). 규칙 문서: docs/판정-규칙.md

U는 코드에 고정하지 않는다. JudgeParams(U_mm=..., U_source=...)로 출처와 함께 넣는다.
"""
from .aggregate import aggregate_to_cells, cell_factor
from .classify import FAIL, HOLD, NODATA, PASS, classify_cells, thresholds_nm
from .cooled import cooled_difference, cooling_criterion
from .params import JudgeParams, load_params
from .reject import META_FIELDS, REJECT_CODES, check_meta
from .scoring import score_c12
from .verdict import (VERDICTS, JudgeResult, LayerInput, decide, fine_to_cell_layer, judge_print,
                      judge_print_fine)

__all__ = [
    "classify_cells", "aggregate_to_cells", "cell_factor", "thresholds_nm",
    "PASS", "HOLD", "FAIL", "NODATA",
    "LayerInput", "JudgeParams", "JudgeResult", "judge_print", "judge_print_fine", "fine_to_cell_layer",
    "decide", "VERDICTS", "load_params",
    "cooled_difference", "cooling_criterion", "score_c12",
    "META_FIELDS", "REJECT_CODES", "check_meta",
]
