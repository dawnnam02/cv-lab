# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5). import · grep · 열기 모두 금지.
"""가상 센서 시뮬레이터 (T3). 순방향: G코드 → 참 형상 → (S3 이후) 레이저 · 카메라 · 위치 로그.

모델 분리: 처리 패키지 (triangulation · region · 이후 calibration · heightmap)를 import하지 않는다.
쓸 수 있는 것: cvlab.gcode (정답 지도), cvlab.judge (참 판정), cvlab.io · cvlab.repro (S5 쓰기 · 검사).
"""
from .clock import VirtualClock
from .seeds import SeedTree, eval_seed_from_env, seed_tag

__all__ = ["SeedTree", "VirtualClock", "eval_seed_from_env", "seed_tag"]
