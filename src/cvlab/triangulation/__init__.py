"""cvlab.triangulation: 레이저 선 중심 추출 (F1)과 좌표 변환 뼈대 (C4), T7a 1차.

정확도 숫자는 단순 합성 영상에서 잰 것입니다. 하드웨어 성능의 증거가 아닙니다.
교정값은 모두 인자로 받습니다 (기본값 없음, T8).
"""
from .extract import METHODS, extract_centers, roi_to_full
from .frames import Tf
from .geometry import CALIB_KEYS, distort_points, image_to_G, intersect_plane, pixel_to_ray, undistort_points
from .params import TriParams
from .quality import FLAG, line_quality
from .reader import SPEC_FRAME_COLUMNS, load_frame, read_frames_index

__all__ = [
    "METHODS", "extract_centers", "roi_to_full", "TriParams", "FLAG", "line_quality",
    "Tf", "CALIB_KEYS", "distort_points", "undistort_points", "pixel_to_ray", "intersect_plane", "image_to_G",
    "SPEC_FRAME_COLUMNS", "read_frames_index", "load_frame",
]
