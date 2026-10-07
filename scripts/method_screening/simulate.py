"""simulate.py — 실험 3: 측정 시뮬레이션 (청사진 0_방법탐색 4.3절).

단위는 모두 µm (높이 포함). 부호: 오차 = 측정 − 설계, + = 재료 과다(A1).

합성 시편은 20 × 40 mm 전체를 2 µm 격자로 만들면 메모리가 너무 커서, 지표마다 필요한
작은 패치로 나눈다. 패치는 같은 시편의 일부이므로 '전체 위치 오차'(+200, −100) µm 가
모든 패치에 똑같이 들어가고, 샘플링 격자의 위상도 한 번의 측정(MC 1회) 안에서 공유한다.

  패치          정답(넣은 오차)                         지표 추출 (측정 데이터 + 설계값만 사용)
  단차 패치     윗면 400 → 아랫면 220 (설계 단차 200, −20) 경계 띠를 뺀 두 면 중앙값 차
  선 패치       단일 선 FWHM 400 → 440 (+40), 높이 200     행 평균 단면의 반높이 폭(FWHM)
  구멍 패치     판 두께 1000 위 Ø4000 → Ø3900 (−100)        경계점 Kåsa 원 맞춤
  핀 패치 ×9    Ø2000·높이 1000 핀 3×3 (간격 6 mm)          경계점 Kåsa 원 중심의 평균 이동

모델 가정 (보고서 '모델 가정 목록'과 같은 내용)
  A1. 가로 흐림: 광학 = 가우시안 σ = xy_blur/2.355 (xy_blur 를 PSF FWHM 으로 해석).
      접촉식 = 반경 r = xy_blur 구 프로브의 형태학적 '닫힘(closing)'.
      ※ 지시서는 '열림(opening)'이라 했지만, 위에서 내려오는 구가 기록하는 면은
        (f ⊕ b) ⊖ b = 닫힘이다(좁은 골·오목 모서리가 메워짐). 열림은 아래에서 올라오는
        구에 해당한다. CONTACT_MORPH 상수로 바꿀 수 있다.
  A2. 샘플링: 간격 xy_step, 위상 오프셋 U[0, step) 를 x·y 각각 MC 1회마다 새로 뽑는다.
      정답 격자(2 µm)보다 촘촘한 간격은 2 µm 로 처리한다(약간 보수적).
  A3. Z 잡음: 샘플마다 독립 가우시안 N(0, z_sigma). 공간 상관 잡음·드리프트·보정 오차는 없음
      → 면 전체를 평균하는 단차·선폭은 실제보다 낙관적일 수 있다(한계로 기록).
  A4. 결측: 흐린 면의 경사 > max_slope 인 곳 + 실제(흐리기 전) 벽에서 양쪽 edge_loss/2
      (합계 edge_loss 폭) 띠를 NaN 으로 둔다. 벽 = 정답 면 경사 > WALL_DEG.
      가림은 실제로는 한쪽에만 생기지만 여기서는 대칭으로 둔다.
  A5. measures_z = 0 (2D): 높이 없이 재료 실루엣의 이진 마스크만 준다. 실루엣에 가우시안
      흐림 후 0.5 문턱 → 샘플 점에서 판정(서브픽셀 없음). 그래서 경계 위치 잡음은 z_sigma 가
      아니라 '양자화' 오차, 즉 한 샘플 간격 안의 균등분포 → 표준편차 xy_step/√12 수준이다.
      위상이 한 영상 안에서 공유되므로 곧은 경계에서는 이 오차가 서로 상관(평균해도 안 줄어듦),
      곡선 경계(구멍·핀)에서는 점마다 달라져 원 맞춤에서 줄어든다. 2D 접촉식은 광학처럼 다룬다.
  A6. 선 단면: 반타원 z = h·√(1 − (x/a)²), a = w/√3 → 반높이 폭 = w (선폭 정의 = FWHM).
      2D 방식은 바닥 폭 2a 만 보므로 설계 비드 모델의 비율 FWHM/바닥폭 = √3/2 로 환산한다.
  A7. 선 패치는 단면이 y 방향으로 일정하고 결측도 열 단위이므로, 행 평균 단면 =
      단면 + N(0, z_sigma/√행수) 로 바로 만든다 (독립 잡음에서 nanmean 과 분포가 같음).
  A8. 이어 붙이기(시야 < 시편) 오차, 정합 오차, 표면 산란·다중 반사는 모델에 없다.
  A9. 측정 깊이: 패치의 높이 범위(단차 400, 선 200, 구멍 판 1000, 핀 1000 µm)가 depth_mm 를
      넘으면 그 패치의 지표는 '측정 불가'. 점이 모자라 지표를 못 뽑으면(점 측정 후보 등)
      오류 대신 NaN → 유효 회차가 80 % 미만이면 '측정 불가'.
  A10. 지표 추출은 측정 데이터와 설계값(G코드 위치·치수)만 쓴다. 넣은 오차(정답)는 쓰지 않는다.
       판정량 Q = |bias| + 2σ (위치는 |평균 오차 벡터| + 2·max(σx, σy)).

국소 지표 (판정의 주 지표)
  L1. 국소높이: 평평한 윗면 2 × 2 mm 를 0.2 mm 셀로 나눠 (셀 평균 − 설계 높이). 모든 회차의 셀을 모아
      |평균| + 2σ. 기준 4:1 = 5 µm, 10:1 = 2 µm. '높이' 그룹의 주 판정 (단차는 참고).
  L2. 국소선폭: 선 9 mm 를 0.5 mm 구간마다 따로 FWHM. 구간 오차를 모아 |bias| + 2σ.
      기준 10 / 4 µm. '윤곽' 그룹의 주 판정 (전체 선폭·경계는 참고).
  L3. 길이40: 시편 양 끝 경계 사이 40 mm 를 해석적으로 계산. 경계 잡음 2개(각 xy_step/√12)
      + [보수] 배율·이어 붙이기. 치우침 0, Q = 2σ. '치수' = 구멍지름·길이40 중 나쁜 쪽.
      ※ 측정 깊이(depth)는 길이에 적용하지 않았다 (윗면 경계만 찾으면 된다고 봄).

시나리오 ('낙관'은 위 A3 그대로, '보수'가 판정 기준)
  B1. 공간 상관 Z 잡음: 전체 분산 z_sigma² 유지, 백색 σ = z_sigma/√2 + 상관 σ = z_sigma/√2
      (상관 성분 = 백색 잡음에 σ 0.5 mm 가우시안 필터, 50 µm 격자에서 만들어 보간).
  B2. XY 배율 오차: 회차마다 s ~ N(0, u_s), XY 좌표 전체에 (1+s). u_s 는 CAL_CLASS (근거는 상수 주석).
  B3. 이어 붙이기: fov < 40 mm 이면 seam = ceil(40/fov) − 1. seam 마다 XY σ = max(0.5·xy_step, 1 µm),
      Z σ = z_sigma/√10 를 랜덤워크로 누적. 길이40 (XY) 와 국소높이 (Z, 패치를 가운데 seam 에 걸침,
      전체 평균을 기준면으로 뺌) 에만 넣었다.
      단, 프린터 축 래스터 점 센서(RASTER_POINT = M03·M07·M08)는 seam 0 이고, 대신 샘플마다
      XY 위치 잡음 σ = 5 µm (실제로 읽는 위치만 흔들림, 보고 좌표는 명목 격자) + u_s printer_axis 500 ppm.
      M18 은 카메라 타일이라 seam 규칙을 쓰되 u_s 는 printer_axis.
  B2'. 배율 민감도: diy 등급 u_s 500 ppm (보수-500, 판정 기준) / 100 ppm (보수-100, 격자판 교정).
      printer_axis 등급은 두 경우 모두 500 ppm.
  B4. 점 측정 (POINT_IDS = M01, M04): 높이맵 모델 대신 해석 판정. 구멍 σ = z·√(2/8),
      길이 √(2z² + (40 mm·u_s)²), 단차 z·√2, 선폭은 볼 지름 > 0.4 mm 면 측정 불가,
      국소높이는 xy_step ≥ 200 µm 면 측정 불가, 위치 축별 σ = z·√(2/8).
  B5. 2차 후보(청사진 8.1절): 사양 CSV 의 mode 열이 위 id 목록을 대신한다 (raster_point → B3 래스터 규칙,
      point_probe → B4 해석 판정, line_profiler → 면 래스터, 2d → measures_z 0, indirect → 시뮬레이션 생략·
      모든 지표 측정 불가). cal_class 열은 CAL_CLASS 의 id 목록을 대신한다. 열이 비면 id 목록을 쓴다.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# ---------------------------------------------------------------- 상수 (µm)
TRUTH_GRID = 2.0                 # 정답 격자 2 µm
POS_ERR = (200.0, -100.0)        # 전체 위치 오차
STEP_UPPER, STEP_NOM, STEP_ERR = 400.0, 200.0, -20.0
FACE_W, FACE_L = 2500.0, 3000.0  # 단차 면 하나의 폭(x)·길이(y)
LINE_W_NOM, LINE_ERR, LINE_H = 400.0, 40.0, 200.0
LINE_LEN = 9000.0                # 선 3줄 × 3 mm
FWHM_PER_BASE = np.sqrt(3) / 2   # 반타원 단면: FWHM / 바닥폭
HOLE_D_NOM, HOLE_ERR, PLATE_T = 4000.0, -100.0, 1000.0
PIN_D, PIN_H, PIN_PITCH = 2000.0, 1000.0, 6000.0
EDGE_BAND = 250.0                # 단차 면 경계 띠 (H5 edge_band 0.25 mm)
WALL_DEG = 60.0                  # edge_loss 를 적용할 '벽' 경사 문턱
ROI_PAD = 150.0                  # 원 ROI 의 여유 (위치 오차 224 µm 에 더함)
VALID_FRAC_MIN = 0.8             # 유효 MC 비율이 이보다 낮으면 '측정 불가'
MIN_BOUNDARY_PTS = 12
DEFAULT_SLOPE_OPTICAL, DEFAULT_SLOPE_CONTACT = 60.0, 90.0
CONTACT_MORPH = "closing"        # 'closing'(물리적으로 맞음) 또는 'opening'(지시서 원문)

# 국소 지표 (청사진 2.1절 취지: A2 요구 = 격자점별 높이맵 정확도)
FLAT_W, FLAT_H = 2000.0, PLATE_T  # 국소 높이용 평평한 윗면 패치 (한 변 2 mm, 높이 1 mm)
CELL = 200.0                     # 국소 높이 셀 0.2 × 0.2 mm (비드 1개 폭)
CELL_VALID_MIN = 0.5             # 점이 있는 셀이 이 비율 미만이면 그 회차는 측정 불가
SEG_LEN = 500.0                  # 국소 선폭 구간 길이 0.5 mm
SPEC_LEN = 40000.0               # 시편 길이 40 mm (양 끝 경계 사이)

# ---------------------------------------------------------------- 보수 시나리오 상수
# 시나리오: '낙관' = 샘플마다 독립 잡음만, '보수' = 아래 항을 모두 더함. 판정·점수는 '보수' 기준.
CORR_LEN = 500.0                 # 공간 상관 Z 잡음의 가우시안 필터 σ [µm]
CORR_FRAC = 0.5                  # 전체 분산 z_sigma² 중 상관 성분 비율 (백색 σ = 상관 σ = z_sigma/√2)
CORR_GRID = 50.0                 # 상관 잡음장을 만드는 거친 격자 [µm] (상관 길이의 1/10, 샘플 점에 쌍선형 보간)
# XY 배율 교정 오차 u_s [ppm]. 회차마다 s ~ N(0, u_s), XY 좌표 전체에 (1 + s).
#  20 ppm : 교정 성적서가 있는 계측기 (학내·외부 CMM, 형상측정기, 현미경, CT, 상용 공초점 라인).
#           일반 CMM MPE_E ≈ (1.5 + L/333) µm → 40 mm 에서 약 1.6 µm ≈ 40 ppm (최대허용오차, 표준불확도는 그 1/2 수준)
#  100 ppm: 상용 산업 센서 (자체 구입). 데이터시트 직선성 ±0.01–0.05 % F.S. 수준 → 100 ppm
#  500 ppm: 자작·비계측 장비 (평판 스캐너, 자작 광학계, 프린터 축). 스캐너 배율 0.1–0.3 %,
#           프린터 스텝 축 0.05–0.2 % 수준이 보고됨 → 교정 후 잔차로 500 ppm
#  printer_axis 500 ppm: 위치를 프린터 축(벨트·스텝모터)으로 정하는 방식. steps/mm 미교정 기준 0.05 % 수준.
#  등급 이름 → (ppm, id 목록). 'diy' 는 배율 민감도(--diy-ppm, 기본 500 / 대안 100)의 대상이다.
#  diy 100 ppm = 기준 격자판으로 배율을 교정한 경우 (D5·C3 계획).
CAL_CLASS = {
    "calibrated": (20, ["M01", "M02", "M04", "M14", "M15", "M16", "M23", "M09"]),   # M04: 교정 계측기(팀장 결정)
    "industrial": (100, ["M06", "M10", "M21"]),
    "diy": (500, ["M05", "M11", "M13", "M17", "M19", "M20", "M22", "M12"]),
    "printer_axis": (500, ["M03", "M07", "M08", "M18"]),
}
CAL_DEFAULT_BY_ACCESS = {"lab": 20, "outsource": 20, "own": 500}   # 목록에 없는 id (예: 시험용 S*)
# 프린터 축 래스터 점 센서: 한 점(또는 짧은 선)을 프린터 축으로 끌고 다니며 면을 만든다.
#  → 카메라 타일을 잇는 것이 아니므로 이어 붙이기 seam 은 0. 대신 샘플마다 축 위치 잡음
#    σ = 5 µm (GT2 벨트·1.8° 스텝모터 반복성 수 µm 수준)를 XY 좌표에 넣는다.
#  M18 (카메라 타일을 프린터 축으로 옮김)은 seam 규칙을 그대로 쓰고 u_s 만 printer_axis.
RASTER_POINT = {"M03", "M07", "M08"}
RASTER_XY_SIGMA = 5.0
STITCH_LEN_MM = 40.0             # 시야가 이보다 작으면 이어 붙이기: seam 수 = ceil(40/fov) − 1
# seam 마다 XY 오차 σ = max(0.5·xy_step, 1 µm), Z 오프셋 σ = z_sigma/√10, 둘 다 랜덤워크로 누적
POINT_IDS = {"M01", "M04"}       # 점 측정 방식 → 높이맵 모델 대신 사양값 해석 판정
POINT_N_HOLE = 8                 # 구멍 원 맞춤 점 수
# 선 단면 장비 (촉침·윤곽): 면 측정은 래스터 가정, 시간은 scoring.raster_time_min 으로 다시 계산
LINE_PROFILER_IDS = {"M02"}

# ---------------------------------------------------------------- mode · cal_class (청사진 8.1절)
# 사양 CSV 에 mode / cal_class 열이 있으면 그 값을 쓰고, 없거나 비면(1차 A–D) 위 id 목록 상수로 판정한다.
#  area          면 높이맵 (기본)
#  line_profiler 선 단면 장비 → 면 래스터 모델 + 면 래스터 시간 재계산 (LINE_PROFILER_IDS 와 같음)
#  raster_point  프린터 축으로 끄는 점 센서 → RASTER_POINT 규칙 (seam 0, 축 잡음 5 µm)
#  point_probe   점 측정 CMM·게이지 → POINT_IDS 해석 판정
#  2d            높이 없음 → measures_z = 0
#  indirect      형상을 재지 않음(질량·유량 등) → 모든 지표 '측정 불가', 시뮬레이션 생략
MODES = ("area", "line_profiler", "raster_point", "point_probe", "2d", "indirect")
CAL_PPM = {c: p for c, (p, _) in CAL_CLASS.items()}


def _choice(v):
    s = str(v if v is not None else "").strip().lower()
    return "" if s in ("", "nan", "none", "na", "-") else s


def resolve_mode(row) -> tuple[str, str]:
    """→ (mode, 출처 'csv' | 'id목록'). CSV 값이 허용값이면 그대로, 아니면 id 목록 상수와 measures_z 로."""
    v = _choice(row.get("mode", ""))
    if v in MODES:
        return v, "csv"
    rid = str(row.get("id", "")).upper()
    if rid in POINT_IDS:
        return "point_probe", "id목록"
    if rid in RASTER_POINT:
        return "raster_point", "id목록"
    if rid in LINE_PROFILER_IDS:
        return "line_profiler", "id목록"
    mz = row.get("measures_z", np.nan)
    try:
        mz = float(mz)
    except (TypeError, ValueError):
        mz = np.nan
    if np.isfinite(mz) and mz < 0.5:
        return "2d", "id목록"
    return "area", "id목록"


def resolve_cal(row, diy_ppm=None) -> tuple[str, float, str]:
    """→ (등급 이름 또는 '', ppm, 메모). CSV cal_class → id 목록(CAL_CLASS) → access 기본값 순."""
    v = _choice(row.get("cal_class", ""))
    rid = str(row.get("id", "")).upper()
    note = ""
    if v in CAL_PPM:
        cls = v
    else:
        cls = next((c for c, (p, ids) in CAL_CLASS.items() if rid in ids), "")
    if cls:
        ppm = CAL_PPM[cls]
        if cls == "diy" and diy_ppm is not None:
            ppm = diy_ppm
    else:
        ppm = CAL_DEFAULT_BY_ACCESS.get(str(row.get("access", "")).lower(), 500)
        note = f"배율 등급 목록에 없음 → access 기준 {ppm} ppm"
    return cls, float(ppm), note

# 오차 종류: (이름, 그룹, 정답, 4:1 한계, 10:1 한계)   — 청사진 2.1절
#  그룹 판정: 높이 = 국소높이, 윤곽 = 국소선폭, 치수 = 구멍지름·길이40 중 나쁜 쪽 (scoring.GROUP_RULES)
ERROR_TYPES = [
    ("국소높이", "높이", 0.0, 5.0, 2.0),
    ("단차", "높이(참고)", STEP_ERR, 5.0, 2.0),
    ("국소선폭", "윤곽", LINE_ERR, 10.0, 4.0),
    ("선폭", "윤곽(참고)", LINE_ERR, 10.0, 4.0),
    ("구멍지름", "치수", HOLE_ERR, 25.0, 10.0),
    ("길이40", "치수", 0.0, 25.0, 10.0),
    ("경계", "윤곽(참고)", -HOLE_ERR / 2, 25.0, 10.0),   # 구멍 경계의 반경 방향 이동, + = 재료 과다
    ("위치", "위치", float(np.hypot(*POS_ERR)), 50.0, 20.0),
]
SCENARIOS = ["낙관", "보수"]
TYPE_NAMES = [t[0] for t in ERROR_TYPES]
GRADES = ["10:1 통과", "4:1 통과", "불합격", "측정 불가"]
GRADE_RANK = {"10:1 통과": 3, "4:1 통과": 2, "불합격": 1, "측정 불가": 0}


@dataclass
class Model:
    z_sigma: float = 0.0
    xy_step: float = TRUTH_GRID
    xy_blur: float = 0.0
    edge_loss: float = 0.0
    max_slope: float = 90.0
    measures_z: bool = True
    contact: bool = False
    depth: float = np.inf               # 측정 깊이 [µm] (depth_mm × 1000)
    u_s: float = 0.0                    # XY 배율 교정 표준불확도 (무차원, 20 ppm = 20e-6)
    cal_class: str = ""
    xy_jitter: float = 0.0              # 샘플마다 XY 위치 잡음 σ [µm] (프린터 축 래스터, 보수 시나리오)
    raster: bool = False                # 프린터 축 래스터 점 센서 → seam 0
    fov: float = np.inf                 # 시야 [µm]
    point: bool = False                 # 점 측정 방식 (해석 판정)

    @property
    def n_seams(self):
        f = self.fov / 1000.0
        if self.raster:
            return 0
        if not np.isfinite(f) or f <= 0 or f >= STITCH_LEN_MM:
            return 0
        return int(np.ceil(STITCH_LEN_MM / f)) - 1

    @property
    def seam_xy(self):
        return max(0.5 * self.xy_step, 1.0)

    @property
    def seam_z(self):
        return self.z_sigma / np.sqrt(10)

    @property
    def step(self):
        return max(float(self.xy_step), TRUTH_GRID)

    @property
    def sigma(self):                       # 광학 가우시안 σ
        return 0.0 if self.contact else self.xy_blur / 2.355

    @property
    def probe_r(self):
        return self.xy_blur if (self.contact and self.measures_z) else 0.0

    @property
    def sigma_2d(self):                    # 2D 실루엣 흐림 (접촉식이어도 가우시안)
        return self.xy_blur / 2.355

    @property
    def margin(self):                      # 흐림·결측이 퍼지는 거리
        s = self.sigma if self.measures_z else self.sigma_2d
        return 4 * s + 1.2 * self.probe_r + self.edge_loss


def model_from_row(row, diy_ppm=None) -> tuple[Model | None, list[str]]:
    """사양 행 → Model. 시뮬레이션 불가면 (None, 사유). 결측값 대체는 notes 에 적는다."""
    notes = []
    mode, _ = resolve_mode(row)
    if mode == "indirect":
        return None, ["간접 지표 (형상을 재지 않음) → 모든 지표 측정 불가, 시뮬레이션 생략"]
    step = row.get("xy_step_um", np.nan)
    if not np.isfinite(step) or step <= 0:
        return None, ["xy_step 없음 → 측정 불가"]
    mz = row.get("measures_z", np.nan)
    zs = row.get("z_sigma_um", np.nan)
    if mode == "2d":
        if np.isfinite(mz) and mz >= 0.5:
            notes.append("mode 2d → measures_z 0 으로 처리")
        mz = 0.0
    if not np.isfinite(mz):
        mz = 1.0 if np.isfinite(zs) else 0.0
        notes.append(f"measures_z 없음 → {int(mz)} 가정")
    mz = bool(mz >= 0.5)
    if mz and not np.isfinite(zs):
        return None, ["measures_z=1 인데 z_sigma 없음 → 측정 불가"]
    contact = bool(row.get("contact", False))
    blur = row.get("xy_blur_um", np.nan)
    if not np.isfinite(blur):
        blur = step
        notes.append("xy_blur 없음 → xy_step 가정")
    el = row.get("edge_loss_um", np.nan)
    if not np.isfinite(el):
        el = 0.0
        notes.append("edge_loss 없음 → 0 가정")
    ms = row.get("max_slope_deg", np.nan)
    if not np.isfinite(ms):
        ms = DEFAULT_SLOPE_CONTACT if contact else DEFAULT_SLOPE_OPTICAL
        if mz:
            notes.append(f"max_slope 없음 → {ms:.0f}° 가정")
    if step < TRUTH_GRID:
        notes.append(f"xy_step {step:g} < 2 µm → 2 µm 로 처리")
    dep = row.get("depth_mm", np.nan)
    dep = float(dep) * 1000 if np.isfinite(dep) and dep > 0 else np.inf
    cls, ppm, cnote = resolve_cal(row, diy_ppm)
    if cnote:
        notes.append(cnote)
    raster = mode == "raster_point"
    if raster:
        notes.append(f"프린터 축 래스터: seam 0, 샘플 XY 잡음 {RASTER_XY_SIGMA:g} µm(보수)")
    fov = row.get("fov_mm", np.nan)
    fov = float(fov) * 1000 if np.isfinite(fov) and fov > 0 else np.inf
    point = mode == "point_probe"
    if point:
        notes.append("해석 판정")
    return Model(z_sigma=float(zs) if mz else 0.0, xy_step=float(step), xy_blur=max(float(blur), 0.0),
                 edge_loss=max(float(el), 0.0), max_slope=float(ms), measures_z=mz,
                 contact=contact, depth=dep, u_s=ppm * 1e-6, fov=fov, point=point, cal_class=cls,
                 raster=raster, xy_jitter=RASTER_XY_SIGMA if raster else 0.0), notes


# ---------------------------------------------------------------- 흐림 연산
def _ball(res, r, ndim):
    k = int(np.ceil(r / res))
    ax = np.arange(-k, k + 1) * res
    if ndim == 1:
        d2 = ax ** 2
    else:
        d2 = ax[:, None] ** 2 + ax[None, :] ** 2
    fp = d2 <= r * r
    s = np.where(fp, np.sqrt(np.clip(r * r - d2, 0, None)) - r, 0.0)
    return s, fp


def _morph(z, res, r):
    if r < res:
        return z
    s, fp = _ball(res, r, z.ndim)
    f = ndimage.grey_closing if CONTACT_MORPH == "closing" else ndimage.grey_opening
    return f(z, footprint=fp, structure=s, mode="nearest")


def _gauss2d_fft(z, sig_px):
    if sig_px < 0.3:
        return z
    F = np.fft.rfft2(z)
    F = ndimage.fourier_gaussian(F, sigma=sig_px, n=z.shape[1])
    return np.fft.irfft2(F, s=z.shape).astype(z.dtype)


def _nan_mask(zb, ztrue, res, m: Model):
    """경사 결측 + 벽 주변 edge_loss 띠 (가정 A4)."""
    grads = np.gradient(zb, res)
    if zb.ndim == 1:
        grads = [grads]
    slope = np.degrees(np.arctan(np.sqrt(sum(g * g for g in grads))))
    nanm = slope > m.max_slope
    if m.edge_loss > 0:
        gt = np.gradient(ztrue, res)
        if ztrue.ndim == 1:
            gt = [gt]
        wall = np.degrees(np.arctan(np.sqrt(sum(g * g for g in gt)))) > WALL_DEG
        if wall.any():
            dist = ndimage.distance_transform_edt(~wall) * res
            nanm |= dist <= m.edge_loss / 2
    return nanm


# ---------------------------------------------------------------- 시나리오별 회차 상태
def _gauss_w2(sig_px, truncate=4.0):
    """scipy gaussian_filter1d 커널 가중치의 제곱합 (백색 잡음을 거르면 분산이 이만큼 줄어듦)."""
    r = int(truncate * sig_px + 0.5)
    k = np.arange(-r, r + 1)
    w = np.exp(-0.5 * (k / sig_px) ** 2)
    w /= w.sum()
    return float((w * w).sum())


class CorrField:
    """공간 상관 Z 잡음장: 거친 격자(CORR_GRID)의 백색 잡음에 σ = CORR_LEN 가우시안 필터 →
    표준편차 sigma 로 맞춤 → 샘플 점에 쌍선형 보간."""

    def __init__(self, rng, x0, x1, y0, y1, sigma):
        self.sigma = sigma
        if sigma <= 0:
            return
        g, pad = CORR_GRID, 4 * CORR_LEN
        self.ox, self.oy, self.g = x0 - pad, y0 - pad, g
        nx = int(np.ceil((x1 - x0 + 2 * pad) / g)) + 2
        ny = int(np.ceil((y1 - y0 + 2 * pad) / g)) + 2
        sp = CORR_LEN / g
        f = ndimage.gaussian_filter(rng.standard_normal((ny, nx)), sp, mode="wrap")
        self.f = (f * (sigma / _gauss_w2(sp))).astype(np.float32)   # 2D 분리형: std = Σw²

    def __call__(self, x, y):
        if self.sigma <= 0:
            return np.zeros(np.broadcast(x, y).shape, np.float32)
        x, y = np.broadcast_arrays(np.asarray(x, np.float32), np.asarray(y, np.float32))
        return ndimage.map_coordinates(self.f, [(y - self.oy) / self.g, (x - self.ox) / self.g],
                                       order=1, mode="nearest")


@dataclass
class Ctx:
    """MC 1회의 시나리오 상태."""
    cons: bool
    ws: float          # 백색 Z 잡음 σ
    cs: float          # 상관 Z 잡음 σ
    s: float           # XY 배율 오차
    dL: float          # 국소 높이 패치 왼쪽 타일 Z 오프셋 (seam 랜덤워크)
    dR: float          # 오른쪽 타일
    jit: float = 0.0   # 샘플마다 XY 위치 잡음 σ (프린터 축 래스터)

    def field(self, rng, x0, x1, y0, y1):
        return CorrField(rng, x0, x1, y0, y1, self.cs)


def make_ctx(m: Model, rng, cons: bool) -> Ctx:
    z = m.z_sigma if m.measures_z else 0.0
    if not cons:
        return Ctx(False, z, 0.0, 0.0, 0.0, 0.0)
    ws, cs = z * np.sqrt(1 - CORR_FRAC), z * np.sqrt(CORR_FRAC)
    s = float(rng.normal(0, m.u_s)) if m.u_s > 0 else 0.0
    dL = dR = 0.0
    n = m.n_seams
    if n > 0 and m.seam_z > 0:
        W = np.concatenate([[0.0], np.cumsum(rng.normal(0, m.seam_z, n))])   # 타일 0..n 의 Z 오프셋
        W -= W.mean()                                                        # 전체 기준면(바닥 평면)으로 상수 제거
        k = n // 2                                                           # 패치를 가운데 seam 에 걸침
        dL, dR = float(W[k]), float(W[k + 1])
    return Ctx(True, ws, cs, s, dL, dR, m.xy_jitter)


# ---------------------------------------------------------------- 1D 패치 (단차·선)
class Profile1D:
    """y 방향으로 일정한 형상의 단면. x0 = 격자 첫 점, res = 격자 간격."""

    def __init__(self, z, ztrue, x0, res, m: Model, silhouette=None):
        self.x0, self.res = x0, res
        if m.measures_z:
            if m.contact:
                zb = _morph(z, res, m.probe_r)
            else:
                sp = m.sigma / res
                zb = ndimage.gaussian_filter1d(z, sp, mode="nearest") if sp >= 0.3 else z
            self.z = zb
            self.nan = _nan_mask(zb, ztrue, res, m)
        else:
            sp = m.sigma_2d / res
            sb = ndimage.gaussian_filter1d(silhouette, sp, mode="nearest") if sp >= 0.3 else silhouette
            # 회색값을 그대로 두고 샘플 점에서 보간한 뒤 0.5 문턱 (격자 양자화가 끼지 않게)
            self.z = sb.astype(float)
            self.nan = np.zeros(z.shape, bool)

    def sample(self, xs):
        g = (xs - self.x0) / self.res
        z = np.interp(g, np.arange(self.z.size), self.z)
        nan = self.nan[np.clip(np.rint(g).astype(int), 0, self.nan.size - 1)]
        return z, nan


def _res1d(m: Model):
    s = m.sigma if m.measures_z else m.sigma_2d
    res = min(m.step, max(s, 1.0)) / 4
    if m.probe_r > 0:
        res = max(res, m.probe_r / 300)
    return float(np.clip(res, 0.5, 25.0))


def build_step(m: Model):
    res = _res1d(m)
    L = FACE_W + m.margin + 4 * res
    x = np.arange(-L, L + res / 2, res)
    xe = POS_ERR[0]                                   # 실제 경계 (설계 0 + 위치 오차)
    lower = STEP_UPPER - (STEP_NOM + STEP_ERR)
    frac = np.clip(0.5 - (x - xe) / res, 0, 1)        # 경계를 1칸 폭으로 부드럽게(정답 양자화 방지)
    z = lower + (STEP_UPPER - lower) * frac
    return Profile1D(z, z, x[0], res, m, silhouette=np.ones_like(z))


def _line_halfwidth_max():
    return (LINE_W_NOM + LINE_ERR) / np.sqrt(3)


def build_line(m: Model):
    res = _res1d(m)
    L = _line_halfwidth_max() + abs(POS_ERR[0]) + 400 + 2 * m.xy_blur + m.margin + 4 * res
    x = np.arange(-L, L + res / 2, res)
    a = (LINE_W_NOM + LINE_ERR) / np.sqrt(3)
    t = (x - POS_ERR[0]) / a
    z = LINE_H * np.sqrt(np.clip(1 - t * t, 0, None))
    sil = np.clip(0.5 - (np.abs(x - POS_ERR[0]) - a) / res, 0, 1)
    return Profile1D(z, z, x[0], res, m, silhouette=sil)


def _phase_axis(lo, hi, phase, step):
    k0 = int(np.ceil((lo - phase) / step))
    k1 = int(np.floor((hi - phase) / step))
    return phase + np.arange(k0, k1 + 1) * step


def measure_step(p: Profile1D, m: Model, rng, phase, ctx: Ctx):
    if not m.measures_z:
        return np.nan
    xs = _phase_axis(-FACE_W, FACE_W, phase[0], m.step)
    ys = _phase_axis(0, FACE_L, phase[1], m.step)
    if ys.size == 0:
        ys = np.array([phase[1]])
    ny = ys.size
    if ctx.jit > 0:      # 샘플마다 실제 위치가 흔들림 (보고 좌표는 명목 격자)
        z, nan = p.sample(xs[None, :] + ctx.jit * rng.standard_normal((ny, xs.size)))
    else:
        z, nan = p.sample(xs)
    Z = np.broadcast_to(z.astype(np.float32), (ny, xs.size))
    if ctx.ws > 0:
        Z = Z + np.float32(ctx.ws) * rng.standard_normal((ny, xs.size), dtype=np.float32)
    if ctx.cs > 0:
        F = ctx.field(rng, xs[0], xs[-1], ys[0], ys[-1])
        Z = Z + F(xs[None, :], ys[:, None])
    Z = np.array(Z, dtype=np.float32)
    Z[np.broadcast_to(nan, Z.shape)] = np.nan
    if not (~nan).any():
        return np.nan
    col = np.nanmedian(Z[:min(ny, 200)], axis=0)       # 경계 찾기용 열 중앙값 (앞 200행)
    # 1차 면 추정: 설계 경계(0)에서 충분히 먼 바깥쪽 절반 (위치 오차 0.2 mm ≪ 1.25 mm)
    up0 = np.nanmedian(Z[:, xs < -FACE_W / 2]) if (xs < -FACE_W / 2).any() else np.nan
    lo0 = np.nanmedian(Z[:, xs > FACE_W / 2]) if (xs > FACE_W / 2).any() else np.nan
    if not (np.isfinite(up0) and np.isfinite(lo0)):
        return np.nan
    thr = (up0 + lo0) / 2
    ok = np.isfinite(col)
    xv, cv = xs[ok], col[ok]
    above = cv > thr
    idx = np.nonzero(above[:-1] != above[1:])[0]
    if idx.size == 0:
        return np.nan
    i = idx[np.argmin(np.abs(xv[idx]))]               # 설계 경계에 가장 가까운 교차
    x_e = xv[i] + (thr - cv[i]) * (xv[i + 1] - xv[i]) / (cv[i + 1] - cv[i])
    band = max(EDGE_BAND, 2 * m.xy_blur, m.edge_loss)
    up = Z[:, xs < x_e - band]
    lo = Z[:, xs > x_e + band]
    if np.isfinite(up).sum() < 3 or np.isfinite(lo).sum() < 3:
        return np.nan
    return float(np.nanmedian(up) - np.nanmedian(lo)) - STEP_NOM


def fwhm(xs, prof):
    """단면의 반높이 폭. 바닥 = 양 끝 15 % 중앙값, 꼭대기 = 최고점 근처 포물선 꼭짓점."""
    ok = np.isfinite(prof)
    x, v = xs[ok], prof[ok]
    if x.size < 7:
        return np.nan
    n15 = max(int(0.15 * xs.size), 1)
    edge = np.concatenate([prof[:n15], prof[-n15:]])
    base = np.nanmedian(edge)
    if not np.isfinite(base):
        return np.nan
    ip = int(np.argmax(v))
    vmax = v[ip]
    if vmax - base <= 0:
        return np.nan
    sel = np.nonzero(v >= base + 0.95 * (vmax - base))[0]
    sel = sel[np.abs(sel - ip) <= max(np.abs(sel - ip).min() + sel.size, 1)]
    if sel.size < 3:
        sel = np.arange(max(ip - 1, 0), min(ip + 2, v.size))
    top = vmax
    if sel.size >= 3:
        c = np.polyfit(x[sel] - x[ip], v[sel], 2)
        if c[0] < 0:
            xv = -c[1] / (2 * c[0])
            if abs(xv) <= (x[sel].max() - x[sel].min()):
                top = c[2] - c[1] ** 2 / (4 * c[0])
    half = base + (top - base) / 2
    # 왼쪽
    j = ip
    while j > 0 and v[j] >= half:
        j -= 1
    if v[j] >= half:
        return np.nan
    xl = x[j] + (half - v[j]) * (x[j + 1] - x[j]) / (v[j + 1] - v[j])
    k = ip
    while k < v.size - 1 and v[k] >= half:
        k += 1
    if v[k] >= half:
        return np.nan
    xr = x[k - 1] + (half - v[k - 1]) * (x[k] - x[k - 1]) / (v[k] - v[k - 1])
    return float(xr - xl)


def measure_line(p: Profile1D, m: Model, rng, phase, ctx: Ctx):
    """→ (전체 선폭 오차, 0.5 mm 구간별 선폭 오차 배열). 배율 오차 (1+s) 포함."""
    L = _line_halfwidth_max() + abs(POS_ERR[0]) + 400 + 2 * m.xy_blur + m.edge_loss
    xs = _phase_axis(-L, L, phase[0], m.step)
    ys = _phase_axis(0, LINE_LEN - 1e-6, phase[1], m.step)
    nan_out = (np.nan, np.array([np.nan]))
    if ys.size == 0 or xs.size < 3:
        return nan_out
    seg = np.floor(ys / SEG_LEN).astype(int)
    z, nan = p.sample(xs)
    k = 1.0 + ctx.s
    if not m.measures_z:
        # 2D: 열마다 같은 판정 → 마스크 폭 = 재료 칸 수 × 간격 (가정 A5·A6). 모든 행·구간이 같다.
        base_w = float((z > 0.5).sum()) * m.step
        if base_w <= 0:
            return nan_out
        e = base_w * FWHM_PER_BASE * k - LINE_W_NOM
        return e, np.full(np.unique(seg).size, e)
    profs, nrow = [], []
    F = ctx.field(rng, xs[0], xs[-1], 0, LINE_LEN) if ctx.cs > 0 else None
    sub = max(1, int(round(25.0 / m.step)))           # 상관 잡음은 매끈하므로 25 µm 간격 행으로 평균
    for sid in np.unique(seg):
        yr = ys[seg == sid]
        n = yr.size
        # 구간 평균 단면 = 단면 + 백색 N(0, ws/√행수) (독립 잡음의 행 평균과 같은 분포, 가정 A7) + 상관 성분 행 평균
        if ctx.jit > 0:   # 프린터 축 위치 잡음: 행마다 실제 위치에서 단면을 읽어 평균
            zj, _ = p.sample(xs[None, :] + ctx.jit * rng.standard_normal((n, xs.size)))
            zz = zj.mean(axis=0)
        else:
            zz = z
        pr = zz + (rng.normal(0, ctx.ws / np.sqrt(n), xs.size) if ctx.ws > 0 else 0)
        if F is not None:
            pr = pr + F(xs[None, :], yr[::sub][:, None]).mean(axis=0)
        profs.append(np.where(nan, np.nan, pr))
        nrow.append(n)
    profs = np.array(profs)
    segw = np.array([fwhm(xs, pr) for pr in profs]) * k - LINE_W_NOM
    whole = fwhm(xs, np.average(profs, axis=0, weights=nrow))
    return (whole * k - LINE_W_NOM if np.isfinite(whole) else np.nan), segw


def measure_flat(m: Model, rng, phase, ctx: Ctx):
    """국소 높이: 평평한 윗면 2 × 2 mm 를 0.2 mm 셀로 나눠 셀 평균 − 설계 높이.
    seam 이 있으면 패치 가운데(x = 0)에 걸쳐 놓는다 → 왼쪽·오른쪽 타일의 Z 오프셋이 다르다."""
    if not m.measures_z:
        return np.array([np.nan])
    h = FLAT_W / 2
    xs = _phase_axis(-h, h - 1e-6, phase[0], m.step)
    ys = _phase_axis(0, FLAT_W - 1e-6, phase[1], m.step)
    if xs.size == 0 or ys.size == 0:
        return np.array([np.nan])
    Z = np.zeros((ys.size, xs.size), np.float32)
    if ctx.ws > 0:
        Z += np.float32(ctx.ws) * rng.standard_normal(Z.shape, dtype=np.float32)
    if ctx.cs > 0:
        Z += ctx.field(rng, -h, h, 0, FLAT_W)(xs[None, :], ys[:, None])
    Z += np.where(xs < 0, ctx.dL, ctx.dR).astype(np.float32)[None, :]
    nc = int(FLAT_W // CELL)
    cx = np.clip(((xs + h) // CELL).astype(int), 0, nc - 1)
    cy = np.clip((ys // CELL).astype(int), 0, nc - 1)
    cid = (cy[:, None] * nc + cx[None, :]).ravel()
    cnt = np.bincount(cid, minlength=nc * nc)
    sm = np.bincount(cid, weights=Z.ravel().astype(float), minlength=nc * nc)
    ok = cnt > 0
    if ok.mean() < CELL_VALID_MIN:
        return np.array([np.nan])
    return sm[ok] / cnt[ok]          # 측정 − 설계 (평평한 면이라 설계 높이를 빼면 잡음·오프셋만 남음)


# ---------------------------------------------------------------- 2D 패치 (구멍·핀)
def _res2d(m: Model):
    if m.measures_z and m.contact:
        r = m.probe_r
        res = max(min(m.step / 2, max(TRUTH_GRID, r / 12)), r / 30)
    else:
        s = m.sigma if m.measures_z else m.sigma_2d
        res = min(m.step, max(s, 1.0)) / 2
    # 큰 프로브(예: 볼 반경 1–3 mm)에서도 구조요소가 61×61 칸을 넘지 않게 상한을 r/30 까지 올린다
    return float(np.clip(res, TRUTH_GRID, max(100.0, m.probe_r / 30)))


class Patch2D:
    """원형 형상(구멍·핀) 패치. 격자 원점 = 실제 형상 중심. kind='hole' 또는 'pin'."""

    def __init__(self, kind, m: Model):
        self.kind = kind
        R = (HOLE_D_NOM + HOLE_ERR) / 2 if kind == "hole" else PIN_D / 2
        Rd = HOLE_D_NOM / 2 if kind == "hole" else PIN_D / 2
        self.R_design = Rd
        self.w = roi_halfwidth(m)
        res = _res2d(m)
        half = Rd + self.w + float(np.hypot(*POS_ERR)) + m.margin + 4 * res
        n = int(np.ceil(2 * half / res)) + 1
        ax = (np.arange(n) - (n - 1) / 2) * res
        r = np.hypot(ax[:, None], ax[None, :]).astype(np.float32)
        if kind == "hole":
            ind = np.clip((r - R) / res + 0.5, 0, 1)
            h = PLATE_T
        else:
            ind = np.clip((R - r) / res + 0.5, 0, 1)
            h = PIN_H
        del r
        self.res, self.n = res, n
        if m.measures_z:
            z = (h * ind).astype(np.float32)
            if m.contact:
                zb = _morph(z.astype(float), res, m.probe_r).astype(np.float32)
            else:
                zb = _gauss2d_fft(z, m.sigma / res)
            self.z = zb
            self.nan = _nan_mask(zb, z, res, m)
        else:
            sb = _gauss2d_fft(ind.astype(np.float32), m.sigma_2d / res)
            self.z = sb.astype(np.float32)        # 샘플 점에서 보간 후 0.5 문턱
            self.nan = np.zeros(self.z.shape, bool)

    def sample(self, X, Y):
        """실제 중심 기준 좌표 (X, Y) 에서 표본 (쌍선형) + 결측 (최근접)."""
        c = (self.n - 1) / 2
        gi = Y / self.res + c
        gj = X / self.res + c
        z = ndimage.map_coordinates(self.z, [gi, gj], order=1, mode="nearest")
        if not self.has_nan:
            return z, np.zeros(z.shape, bool)
        ii = np.clip(np.rint(gi).astype(np.int64), 0, self.n - 1)
        jj = np.clip(np.rint(gj).astype(np.int64), 0, self.n - 1)
        return z, self.nan[ii, jj]

    @property
    def has_nan(self):
        if not hasattr(self, "_has_nan"):
            self._has_nan = bool(self.nan.any())
        return self._has_nan


def roi_halfwidth(m: Model):
    return float(np.hypot(*POS_ERR)) + ROI_PAD + 3 * (m.sigma if m.measures_z else m.sigma_2d) \
        + m.edge_loss + 1.2 * m.probe_r + 2 * m.step


def kasa(x, y):
    """대수적(Kåsa) 원 맞춤 → (cx, cy, r)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x * x + y * y)
    (D, E, F), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -D / 2, -E / 2
    r2 = cx * cx + cy * cy - F
    return cx, cy, (np.sqrt(r2) if r2 > 0 else np.nan)


def measure_circle(patch: Patch2D, m: Model, rng, phase, design_c, true_c, ctx: Ctx = None):
    """설계 중심 design_c 둘레 고리 ROI 에서 경계점을 찾아 원 맞춤.
    반환 (cx, cy, r): 설계 좌표계. 재료 쪽 경계와 빈 쪽 경계를 따로 맞춰 평균한다
    (결측 띠나 반 칸 치우침이 양쪽에 대칭으로 상쇄됨)."""
    # 1차(거친) 단계: 간격을 k 배로 솎아 설계 고리 ROI 전체에서 문턱과 대략의 원을 구한다.
    # 2차(세밀) 단계: 1차 원 둘레의 얇은 고리만 원래 간격으로 다시 봐서 맞춘다 (계산량 절감).
    # 두 단계 모두 측정 데이터와 설계값만 쓴다.
    Rd, w, st = patch.R_design, patch.w, m.step
    if ctx is None:
        ctx = make_ctx(m, rng, False)
    F = ctx.field(rng, design_c[0] - Rd - w, design_c[0] + Rd + w, design_c[1] - Rd - w,
                  design_c[1] + Rd + w) if ctx.cs > 0 else None

    def noise(x, y):
        out = np.zeros(x.shape, np.float32)
        if m.measures_z and ctx.ws > 0:
            out += rng.normal(0, ctx.ws, x.size).astype(np.float32)
        if m.measures_z and F is not None:
            out += F(x, y)
        return out

    c, r = _measure_circle_core(patch, m, rng, phase, design_c, true_c, noise, Rd, w, st, ctx.jit)
    k = 1.0 + ctx.s                                   # XY 배율 오차: 시편 원점 기준 좌표 전체에 (1+s)
    return c[0] * k, c[1] * k, r * k


def _measure_circle_core(patch, m, rng, phase, design_c, true_c, noise, Rd, w, st, jit=0.0):
    nanc = ((np.nan, np.nan), np.nan)
    k = max(1, int(np.ceil(COARSE_STEP / st)))
    if k > 1:
        fit0, thr = _circle_pass(patch, m, rng, phase, st * k, design_c, max(Rd - w, 0), Rd + w, true_c,
                                 noise=noise, jitter=jit)
        if fit0 is None or not np.isfinite(fit0[2]):
            return nanc
        c0 = (design_c[0] + fit0[0], design_c[1] + fit0[1])
        wf = 3 * (m.sigma if m.measures_z else m.sigma_2d) + m.edge_loss / 2 + 1.2 * m.probe_r \
            + 1.5 * st * k + 24
        fit, _ = _circle_pass(patch, m, rng, phase, st, c0, max(fit0[2] - wf, 0), fit0[2] + wf,
                              true_c, thr=thr, noise=noise, jitter=jit)
        if fit is None:
            return nanc
        return (c0[0] + fit[0], c0[1] + fit[1]), fit[2]
    fit, _ = _circle_pass(patch, m, rng, phase, st, design_c, max(Rd - w, 0), Rd + w, true_c, noise=noise, jitter=jit)
    if fit is None:
        return nanc
    return (design_c[0] + fit[0], design_c[1] + fit[1]), fit[2]


COARSE_STEP = 16.0   # 1차 단계 간격 하한 [µm]


def _circle_pass(patch, m, rng, phase, st, ctr, r_in, r_out, true_c, thr=None, noise=None, jitter=0.0):
    """중심 ctr, 반경 [r_in, r_out] 고리 안 샘플 → (ctr 기준 원 맞춤, 문턱).
    재료 쪽 경계와 빈 쪽 경계를 따로 맞춰 평균한다 (결측 띠·반 칸 치우침이 대칭으로 상쇄)."""
    xs = _phase_axis(ctr[0] - r_out, ctr[0] + r_out, phase[0], st).astype(np.float32)
    ys = _phase_axis(ctr[1] - r_out, ctr[1] + r_out, phase[1], st).astype(np.float32)
    dx = xs - np.float32(ctr[0])
    dy = ys - np.float32(ctr[1])
    if xs.size < 3 or ys.size < 3:
        return None, thr
    iy, ix = _annulus_points(dx.astype(float), dy.astype(float), st, r_in, r_out)
    if iy.size < 20:
        return None, thr
    shape = (ys.size, xs.size)
    jx = jy = 0.0
    if jitter > 0:        # 프린터 축 위치 잡음: 실제로 읽는 위치만 흔들리고 경계점 좌표는 명목 격자
        jx = (jitter * rng.standard_normal(ix.size)).astype(np.float32)
        jy = (jitter * rng.standard_normal(ix.size)).astype(np.float32)
    zz, nn = patch.sample(xs[ix] + jx - np.float32(true_c[0]), ys[iy] + jy - np.float32(true_c[1]))
    if m.measures_z and noise is not None:
        zz = zz + noise(xs[ix], ys[iy])
    lab = np.full((shape[0] + 2, shape[1] + 2), -2, np.int8)   # -2 ROI 밖, -1 결측, 0 빈 쪽, 1 재료 쪽
    iy, ix = iy + 1, ix + 1                                     # 테두리 1칸 덧댐
    if m.measures_z:
        if thr is None:
            v = zz[~nn]
            if v.size < 20:
                return None, thr
            mid = (np.percentile(v, 5) + np.percentile(v, 95)) / 2
            hi, lo = v[v > mid], v[v <= mid]
            if hi.size < 5 or lo.size < 5:
                return None, thr
            thr = (np.median(hi) + np.median(lo)) / 2
        lab[iy, ix] = np.where(nn, -1, (zz > thr).astype(np.int8))
    else:
        lab[iy, ix] = (zz > 0.5).astype(np.int8)
    me = lab[iy, ix]
    nb = [lab[iy - 1, ix], lab[iy + 1, ix], lab[iy, ix - 1], lab[iy, ix + 1]]
    b_hi = (me == 1) & np.logical_or.reduce([(q == 0) | (q == -1) for q in nb])
    b_lo = (me == 0) & np.logical_or.reduce([(q == 1) | (q == -1) for q in nb])
    fits = []
    for b in (b_hi, b_lo):
        if b.sum() >= MIN_BOUNDARY_PTS:
            fits.append(kasa(dx[ix[b] - 1].astype(float), dy[iy[b] - 1].astype(float)))
    if not fits:
        return None, thr
    return tuple(np.nanmean(np.array(fits), axis=0)), thr


def _annulus_points(dx, dy, st, r_in, r_out):
    """균등 격자(dx: 열 좌표, dy: 행 좌표, 간격 st) 중 r_in ≤ r ≤ r_out 인 칸의 (행, 열) 번호.
    행마다 두 구간을 해석적으로 구해 전체 사각형을 만들지 않는다."""
    xo = np.sqrt(np.clip(r_out ** 2 - dy ** 2, 0, None))
    xi = np.sqrt(np.clip(r_in ** 2 - dy ** 2, 0, None))
    x0 = dx[0]
    nx = dx.size

    def jr(lo, hi):
        a = np.clip(np.ceil((lo - x0) / st - 1e-9), 0, nx).astype(np.int64)
        b = np.clip(np.floor((hi - x0) / st + 1e-9) + 1, 0, nx).astype(np.int64)
        return a, np.maximum(b, a)

    inside = np.abs(dy) <= r_out
    hole = (xi > 0) & inside
    a1, b1 = jr(-xo, np.where(hole, -xi, xo))
    a2, b2 = jr(xi, xo)
    b2 = np.where(hole, b2, a2)                 # 안쪽 원이 행에 안 걸리면 구간 하나
    a1, b1 = np.where(inside, a1, 0), np.where(inside, b1, 0)
    b2 = np.where(inside, b2, a2)
    rows, cols = [], []
    for a, b in ((a1, b1), (a2, b2)):
        n = b - a
        tot = int(n.sum())
        if tot == 0:
            continue
        r = np.repeat(np.arange(dy.size), n)
        start = np.repeat(a - np.concatenate([[0], np.cumsum(n)[:-1]]), n)
        rows.append(r)
        cols.append(np.arange(tot) + start)
    if not rows:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    return np.concatenate(rows), np.concatenate(cols)


PIN_CENTERS = [(i * PIN_PITCH, j * PIN_PITCH) for j in (-1, 0, 1) for i in (-1, 0, 1)]


# ---------------------------------------------------------------- MC 실행
# 패치별 높이 범위 [µm]: 측정 깊이(depth_mm)보다 크면 그 패치는 '측정 불가' (2D 방식은 무관)
PATCH_RELIEF = {"step": STEP_UPPER, "line": LINE_H, "hole": PLATE_T, "pin": PIN_H, "flat": FLAT_H}


def _safe(f, *a, n=1):
    """점이 모자라거나(점 측정 후보 등) 맞춤이 퇴화하면 오류 대신 NaN."""
    try:
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return f(*a)
    except (ValueError, IndexError, ZeroDivisionError, np.linalg.LinAlgError, FloatingPointError):
        return np.nan if n == 1 else (np.nan,) * n


def depth_ok(m: Model, key):
    return (not m.measures_z) or PATCH_RELIEF[key] <= m.depth


def run_once(parts, m: Model, rng, cons=False):
    """MC 1회 → {오차종류: 추정 오차}. 위치는 (dx, dy), 국소높이·국소선폭은 셀/구간 배열."""
    ctx = make_ctx(m, rng, cons)
    phase = rng.uniform(0, m.step, 2)
    out = {"단차": _safe(measure_step, parts["step"], m, rng, phase, ctx) if depth_ok(m, "step") else np.nan}
    if depth_ok(m, "line"):
        res = _safe(measure_line, parts["line"], m, rng, phase, ctx, n=2)
        out["선폭"], out["국소선폭"] = (res if isinstance(res, tuple) and len(res) == 2
                                     else (np.nan, np.array([np.nan])))
    else:
        out["선폭"], out["국소선폭"] = np.nan, np.array([np.nan])
    if np.ndim(out["국소선폭"]) == 0:
        out["국소선폭"] = np.array([out["국소선폭"]])
    out["국소높이"] = _safe(measure_flat, m, rng, phase, ctx) if depth_ok(m, "flat") else np.array([np.nan])
    if np.ndim(out["국소높이"]) == 0:
        out["국소높이"] = np.array([np.nan])
    r = np.nan
    if depth_ok(m, "hole"):
        cx, cy, r = _safe(measure_circle, parts["hole"], m, rng, phase, (0.0, 0.0), POS_ERR, ctx, n=3)
    out["구멍지름"] = 2 * r - HOLE_D_NOM if np.isfinite(r) else np.nan
    out["경계"] = -(2 * r - HOLE_D_NOM) / 2 if np.isfinite(r) else np.nan
    d = []
    if depth_ok(m, "pin"):
        for c in PIN_CENTERS:
            tc = (c[0] + POS_ERR[0], c[1] + POS_ERR[1])
            px, py, pr = _safe(measure_circle, parts["pin"], m, rng, phase, c, tc, ctx, n=3)
            if np.isfinite(px) and np.isfinite(py):
                d.append((px - c[0], py - c[1]))
    out["위치"] = tuple(np.mean(d, axis=0)) if len(d) >= 5 else (np.nan, np.nan)
    return out


def build_parts(m: Model):
    return {"step": build_step(m), "line": build_line(m),
            "hole": Patch2D("hole", m), "pin": Patch2D("pin", m)}


def grade(q, lim4, lim10):
    if not np.isfinite(q):
        return "측정 불가"
    if q <= lim10:
        return "10:1 통과"
    if q <= lim4:
        return "4:1 통과"
    return "불합격"


def _summ(group, truth, l4, l10, bias, sd, valid, q=None, **extra):
    if q is None:
        q = abs(bias) + 2 * sd if (np.isfinite(bias) and np.isfinite(sd)) else np.nan
    return dict(group=group, truth_um=truth, bias_um=bias, sd2_um=2 * sd if np.isfinite(sd) else np.nan,
                Q_um=q, lim4_um=l4, lim10_um=l10, grade=grade(q, l4, l10), valid_frac=valid, **extra)


def length_sd(m: Model, cons: bool):
    """길이 40 mm 해석 판정의 표준편차.
    경계 위치 잡음 2개(각 xy_step/√12, 양자화) + [보수] 배율 40 mm·u_s + seam XY 랜덤워크 √n·σ_xy.
    점 측정은 경계 잡음 대신 z_sigma 2개."""
    e = m.z_sigma if m.point else m.step / np.sqrt(12)
    v = 2 * e * e
    if cons:
        v += (SPEC_LEN * m.u_s) ** 2 + m.n_seams * m.seam_xy ** 2
    return float(np.sqrt(v))


def point_summary(m: Model, cons: bool):
    """점 측정 방식(CMM·수동 계측) 해석 판정 (보수 지시 B-4). 치우침 0, Q = 2σ."""
    z, us = m.z_sigma, (m.u_s if cons else 0.0)
    out = {}
    for name, g, t, l4, l10 in ERROR_TYPES:
        sd = np.nan
        if name == "단차":
            sd = z * np.sqrt(2)
        elif name == "국소높이":
            sd = z if m.xy_step < CELL else np.nan            # 셀마다 점이 없으면 측정 불가
        elif name in ("선폭", "국소선폭"):
            sd = np.nan if 2 * m.xy_blur > LINE_W_NOM else float(np.hypot(z * np.sqrt(2), LINE_W_NOM * us))
        elif name == "구멍지름":
            sd = float(np.hypot(z * np.sqrt(2 / POINT_N_HOLE), HOLE_D_NOM * us))
        elif name == "경계":
            sd = float(np.hypot(z * np.sqrt(2 / POINT_N_HOLE), HOLE_D_NOM * us)) / 2
        elif name == "길이40":
            sd = length_sd(m, cons)
        elif name == "위치":
            sd = float(np.hypot(z * np.sqrt(2 / POINT_N_HOLE), PIN_PITCH * us))   # 원 중심 축별 σ ≈ z·√(2/N)
        ok = np.isfinite(sd)
        out[name] = _summ(g, t, l4, l10, 0.0 if ok else np.nan, sd, 1.0 if ok else 0.0, note="해석 판정")
    return out


def summarize(runs, m: Model, cons: bool):
    summary = {}
    for name, group, truth, l4, l10 in ERROR_TYPES:
        if name == "길이40":
            summary[name] = _summ(group, truth, l4, l10, 0.0, length_sd(m, cons), 1.0, note="해석 계산")
            continue
        if name == "위치":
            e = np.array([r["위치"] for r in runs], float) - np.array(POS_ERR)
            ok = np.all(np.isfinite(e), axis=1)
            e = e[ok]
            if ok.mean() < VALID_FRAC_MIN or len(e) < 2:
                bias = sd = np.nan
                q = np.nan
            else:
                bias = float(np.hypot(*e.mean(axis=0)))
                sd = float(np.max(e.std(axis=0, ddof=1)))
                q = bias + 2 * sd
            summary[name] = _summ(group, truth, l4, l10, bias, sd, float(ok.mean()), q=q,
                                  bias_x_um=float(e[:, 0].mean()) if len(e) else np.nan,
                                  bias_y_um=float(e[:, 1].mean()) if len(e) else np.nan)
            continue
        if name in ("국소높이", "국소선폭"):
            arrs = [np.asarray(r[name], float) for r in runs]
            ok = np.array([a.size > 0 and np.isfinite(a).mean() >= 0.5 for a in arrs])
            pooled = np.concatenate([a[np.isfinite(a)] for a, o in zip(arrs, ok) if o]) if ok.any() else np.array([])
            e = pooled - truth
        else:
            v = np.array([r[name] for r in runs], float)
            ok = np.isfinite(v)
            e = v[ok] - truth
        if ok.mean() < VALID_FRAC_MIN or len(e) < 2:
            bias = sd = np.nan
        else:
            bias, sd = float(e.mean()), float(e.std(ddof=1))
        summary[name] = _summ(group, truth, l4, l10, bias, sd, float(ok.mean()))
    return summary


def simulate(m: Model, n_mc=50, seed=0, cons=False, parts=None):
    """→ (요약 dict {종류: {...}}, 원시 리스트). cons=True 면 보수 시나리오.
    판정량 Q = |bias| + 2σ. 국소 지표는 모든 회차의 셀/구간 오차를 모아 계산."""
    if m.point:
        return point_summary(m, cons), []
    rng = np.random.default_rng(seed + (7919 if cons else 0))
    if parts is None:
        parts = build_parts(m)
    runs = [run_once(parts, m, rng, cons) for _ in range(n_mc)]
    return summarize(runs, m, cons), runs


def unmeasurable_summary(reason=""):
    return {name: _summ(g, t, l4, l10, np.nan, np.nan, 0.0) for name, g, t, l4, l10 in ERROR_TYPES}
