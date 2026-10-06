# K6. 학습 로드맵

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: K. 프로젝트 운영

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2027-03-22 (W1-24, 상시) |
| 우선순위 | 보통 (단, W1~W8은 이후 모든 소프트웨어 작업의 전제) |
| 트랙 | 관리·기획 |
| 선행 요소 | [K1 일정](K1-schedule.md) (학습 순서를 일정에 맞춤), [K2 역할](K2-roles.md) (역할별 학습 범위) |
| 후행 요소 | 모든 소프트웨어 요소: [G1](../G-reference/G1-gcode-parsing.md), [F1](../F-acquisition/F1-line-extraction.md), [D2](../D-calibration/D2-laser-plane.md), [H1](../H-analysis/H1-gridding.md), [H4](../H-analysis/H4-registration.md), [J3](../J-software/J3-synthetic-tests.md), [H8](../H-analysis/H8-statistics.md) 등 |
| 관련 마일스톤 | 매 마일스톤 (해당 시기 코드 작업의 준비), 최종 M6 |

## 1. 목적

Python을 **처음 배우는 사람**이 24주 동안 과제에 필요한 만큼만, **필요한 시점보다 1~2주 먼저** 배우도록 주차별 계획을 세웁니다.

- 문법 책을 끝까지 읽고 시작하지 않습니다. **이번 주(또는 다음 주) 과제의 작은 조각을 목표로** 필요한 문법만 배웁니다 (청사진 K6 공부 팁).
- 매주 **연습문제 1개**를 풉니다. 모든 연습문제는 이 과제의 실제 계산(B1 공식, G코드 파싱, 무게중심, 평면 맞춤, 정합, 지표, 통계)의 축소판이며, 풀이 코드는 실행해서 확인한 것입니다.
- 각 풀이는 마지막에 `assert` 로 정답을 스스로 검사하고 "통과"를 출력합니다. 이 습관이 J3 테스트로 이어집니다.

## 2. 배경 지식 (초보자용)

**Python 설치와 가상환경** (W1 첫날, 1시간)

```bash
# 1) Python 3.10 이상 설치 (python.org 또는 연구실 표준 배포판). Windows는 설치 시 "Add to PATH" 체크
python --version

# 2) 과제 폴더에서 가상환경(venv) 만들기: 과제마다 라이브러리를 따로 관리
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate

# 3) 라이브러리 설치
pip install numpy scipy matplotlib pandas pyyaml statsmodels shapely opencv-python pytest
```

**편집기**: VS Code + Python 확장을 권장합니다. 탐색은 Jupyter 노트북, 최종 처리는 `.py` 스크립트로 합니다 (J1 원칙).

**막혔을 때 순서**
1. 오류 메시지의 **마지막 줄**을 읽습니다 (예: `KeyError: 'X'` → 사전에 'X' 키가 없음).
2. `print()` 로 변수의 값과 `type()`, numpy 배열은 `.shape`, `.dtype` 을 찍어 봅니다.
3. 공식 문서에서 함수 이름을 검색합니다.
4. 30분 이상 막히면 혼자 붙잡지 말고 주간 회의 전이라도 동료/선배에게 묻습니다.

**배우는 라이브러리 지도**

| 라이브러리 | 하는 일 | 이 과제에서 |
|---|---|---|
| numpy | 숫자 배열 계산 | 높이맵, 마스크, 지표 (거의 모든 곳) |
| matplotlib | 그림 | 경로, 히트맵, 히스토그램 |
| shapely | 2D 도형 연산 | G3 선폭 입힌 기준 형상 |
| OpenCV (`cv2`) | 이미지 처리, 카메라 캘리브레이션 | D1, D2, F1 |
| scipy | 과학 계산 (격자화, 최적화, 통계) | H1, H4, H8 |
| pandas | 표 데이터 | 실험 조건표, 결과 요약 |
| statsmodels | 통계 모형 (ANOVA) | H8, I2 |
| pytest | 자동 테스트 | J3 |
| PyYAML | 설정 파일 | J2 |
| Open3D (선택) | 점군, ICP | H4 최적맞춤 정합 |

## 3. 입력과 산출물

| 구분 | 내용 | 형식 / 위치 |
|---|---|---|
| 입력 | 참여자별 사전 경험 (없음/조금/있음) | K2 면담 |
| 입력 | K1 일정 (언제 어떤 코드가 필요한지) | [K1](K1-schedule.md) |
| 산출물 | 주차별 연습문제 풀이 | `notebooks/learning/` 또는 `learning/exNN.py` |
| 산출물 | 학습 기록표 (10절) | `docs/learning_log.md` |
| 산출물 | 실제 과제 코드의 첫 버전 (연습이 그대로 자람) | `src/cvlab/` |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 학습 방식 | 문법 전체 먼저 / 과제 중심 | **과제 중심 (필요한 것만, 1~2주 앞서)** | 청사진 K6 공부 팁. 동기 유지 |
| 주당 학습 시간 | – | **W1~W8: 6~8시간, W9 이후: 3~4시간** | 초반 기초가 이후 속도를 결정 |
| 기본 교재 | 유료 강의 / 무료 웹북 | **「점프 투 파이썬」(무료 웹북) 2~5장** + 각 라이브러리 공식 튜토리얼 | 한국어, 무료, 초보 친화 |
| 작업 환경 | 노트북만 / 스크립트만 | **노트북으로 탐색 → `.py` 로 옮기기** | 재현성 (J1) |
| 확인 방법 | 눈으로 / 자동 | **`assert` + 이후 pytest** | J3 테스트 습관 |
| 역할별 범위 | 모두 같은 범위 / 역할별 | **W1~W6 공통**, 이후 HW는 W7~W9(OpenCV·평면 맞춤) 중심, QA는 W15~W19(통계) 중심, SW는 전부 | K2 역할 |
| 코드 공유 | 개인 PC / Git | **W2부터 Git** | 인수인계·백업 (K2) |

### 4.1 주차별 학습 계획 (24주)

| 주 | 기간 | 배울 것 | 이번 주 과제와 연결 | 자료 | 시간 |
|---|---|---|---|---|---|
| W1 | 10-06 ~ 10-12 | 설치, 변수, 숫자, 함수, `import math` | B1 사양 계산 | 점프 투 파이썬 1~2장, 4장(함수) | 8 h |
| W2 | 10-13 ~ 10-19 | 리스트, 딕셔너리, for, if, f-문자열 / Git 기초 | B4·B5 부품 비교 (M0) | 점프 투 파이썬 2~3장, Pro Git 1~2장 | 8 h |
| W3 | 10-20 ~ 10-26 | 문자열 메서드(`split`, `strip`, `upper`), 사전 컴프리헨션 | G1 파서 | 점프 투 파이썬 2장(문자열), 4장(파일) | 6 h |
| W4 | 10-27 ~ 11-02 | 파일 읽기, **numpy 배열**, `np.diff`, `np.linalg.norm`, matplotlib `plot`·`savefig` | G1 압출량 검증, 경로 그림 | NumPy: the absolute basics for beginners, Matplotlib Quick start guide | 8 h |
| W5 | 11-03 ~ 11-09 | `np.meshgrid`, **불리언 마스크**, `np.where`, NaN 다루기(`np.nanmean`) | G3·G4 마스크 | NumPy 인덱싱 문서 | 6 h |
| W6 | 11-10 ~ 11-16 | shapely `LineString`, `buffer`, `unary_union`, `contains_xy` | G2·G3 기준 형상 | Shapely User Manual | 6 h |
| W7 | 11-17 ~ 11-23 | OpenCV `imread`·`imwrite`·`GaussianBlur`, 이미지 = numpy 배열, `argmax(axis=0)` | F1, D1 | OpenCV-Python Tutorials (Getting Started with Images) | 6 h |
| W8 | 11-24 ~ 11-30 | 서브픽셀 무게중심, 노이즈 시뮬레이션(`np.random.default_rng`) / OpenCV Camera Calibration 튜토리얼 읽기 | F1, D1 (M1) | OpenCV "Camera Calibration" 튜토리얼 | 6 h |
| W9 | 12-01 ~ 12-07 | `np.linalg.svd`, 평면 맞춤, 잔차 RMS | D2·D3 검증, H3 | NumPy linalg 문서 | 4 h |
| W10 | 12-08 ~ 12-14 | `scipy.stats.binned_statistic_2d`, 중앙값 vs 평균 | H1, H2 (M2) | SciPy User Guide | 4 h |
| W11 | 12-15 ~ 12-21 | 회전 행렬, Kabsch(SVD), `scipy.optimize.least_squares` 맛보기 / (선택) Open3D ICP 튜토리얼 | H4 정합 | SciPy optimize 문서, Open3D 튜토리얼 | 4 h |
| W12 | 12-22 ~ 12-28 | **pytest**: 테스트 파일·함수 규칙, `assert` | J3 합성 테스트 (M3) | pytest Get Started | 4 h |
| W13 | 12-29 ~ 01-04 | 지표 계산, `np.percentile`, `ddof` 의미 | H5 | NumPy statistics 문서 | 3 h |
| W14 | 01-05 ~ 01-11 | IoU/Dice, `imshow`·`colorbar`·`vmin`/`vmax` | H6, J4 (M4) | Matplotlib colormaps 문서 | 3 h |
| W15 | 01-12 ~ 01-18 | **pandas** `DataFrame`, `groupby`, `agg` | H8 분석 단위, I2 데이터 정리 | 10 minutes to pandas | 4 h |
| W16 | 01-19 ~ 01-25 | `scipy.stats`: t 분포, 신뢰구간, `sem` | I1, H8 | SciPy stats 문서 | 3 h |
| W17 | 01-26 ~ 02-01 | statsmodels `ols`, `anova_lm` | H8, I2 Gage R&R (M5) | statsmodels ANOVA 예제 | 4 h |
| W18 | 02-02 ~ 02-08 | `pathlib`, `json`, 폴더 일괄 처리 | 본 실험 일괄 처리, F3 | Python 공식 문서 pathlib, json | 3 h |
| W19 | 02-09 ~ 02-15 | Bland–Altman 계산·그림 | I3 | Bland & Altman (1986) 논문 | 3 h |
| W20 | 02-16 ~ 02-22 | `argparse`, 함수 → 모듈 → 스크립트 정리 | J1 `scripts/` 정리 | Python argparse Tutorial | 3 h |
| W21 | 02-23 ~ 03-01 | PyYAML, 설정 병합 | J2 | PyYAML 문서 | 2 h |
| W22 | 03-02 ~ 03-08 | 논문용 그림 (크기, 300 dpi, 단위) | K5 그림 | Matplotlib savefig 문서 | 3 h |
| W23 | 03-09 ~ 03-15 | 결과표 자동 생성 (`값 ± U`) | K5 표 | – | 2 h |
| W24 | 03-16 ~ 03-22 | `hashlib`, `subprocess`, 재현성 기록 | K5 공개 준비 (M6) | Python 공식 문서 hashlib | 2 h |

## 5. 수행 절차

1. **준비 (W1 첫날)**
   - [ ] 2절 설치 명령으로 Python·가상환경·라이브러리 설치
   - [ ] `python -c "import numpy, scipy, matplotlib, pandas, yaml, statsmodels, shapely, cv2; print('ok')"` 가 `ok` 를 출력하는지 확인
   - [ ] 학습 기록표(10절) 만들기
2. **매주 반복 (W1~W24)**
   - [ ] 월~수: 4.1 표의 자료로 "배울 것" 학습 (자료의 예제를 **직접 타이핑**, 복사·붙여넣기 금지)
   - [ ] 목: 6절 연습문제를 **풀이를 보지 않고** 풀기 (30분~2시간)
   - [ ] 금: 풀이와 비교, `assert` 통과 확인, 기록표 작성
   - [ ] 주간 회의에서 막힌 점 1개 공유
3. **연습 → 실제 코드로 키우기**
   - [ ] W3·W4 연습 → `src/cvlab/gcode_parser.py` 첫 버전
   - [ ] W8 연습 → `triangulation.py` 의 라인 추출 함수
   - [ ] W11·W12 연습 → `registration.py` + `tests/test_registration.py`
   - [ ] W13·W14 연습 → `metrics.py`
4. **마일스톤 점검**
   - [ ] M1(W8): W1~W8 연습 8개 모두 통과
   - [ ] M3(W12): pytest로 자기 코드 테스트 1개 이상 작성
   - [ ] M5(W17): pandas·statsmodels로 시편 단위 분석 가능

## 6. Python 구현

주차별 연습문제와 **실행해서 확인한 풀이**입니다. 각 풀이는 독립된 파일로 저장해서 `python exNN.py` 로 실행합니다. 같은 폴더에서 실행하면 연습용 파일(`square.gcode`, `laser.png`, `meta_demo/` 등)이 생깁니다. 무작위 수는 시드를 고정했으므로 출력이 아래와 같아야 합니다 (W24의 버전 정보와 git 커밋은 환경마다 다름).

**풀이를 먼저 보지 마세요.** "과제"만 읽고 직접 짠 뒤, 막히면 풀이를 펼칩니다.

#### W1 (10-06 ~ 10-12) · 변수·함수·import

**과제** (B1): B1 공식을 함수 `z_resolution_um()` 으로 만들고 청사진 B1 계산 예(f=25 mm, WD=125 mm, p=3.45 µm, θ=30°)의 δz(1 px) = 27.6 µm를 재현하기

<details><summary>풀이 (`ex01.py`)</summary>

```python
# W1: 변수와 함수 — B1 삼각측량 공식으로 분해능 계산
import math

def z_resolution_um(f_mm, wd_mm, pixel_um, theta_deg, subpixel=1):
    M = f_mm / (wd_mm - f_mm)                       # 광학 배율
    return pixel_um / (M * math.sin(math.radians(theta_deg))) / subpixel

dz1 = z_resolution_um(25, 125, 3.45, 30)
dz10 = z_resolution_um(25, 125, 3.45, 30, subpixel=10)
print(f"dz(1px) = {dz1:.1f} um, dz(1/10px) = {dz10:.2f} um")
assert abs(dz1 - 27.6) < 0.05                       # 청사진 B1 계산 예와 일치
print("통과")
```

실행: `python ex01.py`

```text
dz(1px) = 27.6 um, dz(1/10px) = 2.76 um
통과
```

</details>

#### W2 (10-13 ~ 10-19) · 리스트·딕셔너리·for·if

**과제** (A2, B5): 렌즈 후보 3개(f = 16, 25, 35 mm) 중 FOV ≥ 20 mm 이고 δz(1/10 px) ≤ 5 µm 인 것을 골라, Z 여유가 가장 큰 후보 찾기

<details><summary>풀이 (`ex02.py`)</summary>

```python
# W2: 리스트·딕셔너리·for·if — 렌즈 후보 중 사양(A2)을 만족하는 것 고르기
import math

candidates = [
    {"name": "f16", "f": 16, "wd": 125},
    {"name": "f25", "f": 25, "wd": 125},
    {"name": "f35", "f": 35, "wd": 125},
]
pixel_um, n_cols, theta = 3.45, 1440, 30
ok = {}                                             # 통과한 후보: 이름 -> dz
for c in candidates:
    M = c["f"] / (c["wd"] - c["f"])
    fov_mm = n_cols * pixel_um / M / 1000
    dz_sub = pixel_um / (M * math.sin(math.radians(theta))) / 10
    print(f'{c["name"]}: FOV {fov_mm:.1f} mm, dz(1/10px) {dz_sub:.2f} um')
    if fov_mm >= 20 * 0.99 and dz_sub <= 5:        # FOV ≥ 20 mm(1 % 여유), dz ≤ 5 µm
        ok[c["name"]] = dz_sub
print("사양 만족:", list(ok))
best = min(ok, key=ok.get)                          # dz가 가장 작은 = Z 여유가 큰 후보
print("Z 여유가 가장 큰 후보:", best)
assert list(ok) == ["f16", "f25"] and best == "f25"
print("통과")
```

실행: `python ex02.py`

```text
f16: FOV 33.8 mm, dz(1/10px) 4.70 um
f25: FOV 19.9 mm, dz(1/10px) 2.76 um
f35: FOV 12.8 mm, dz(1/10px) 1.77 um
사양 만족: ['f16', 'f25']
Z 여유가 가장 큰 후보: f25
통과
```

</details>

#### W3 (10-20 ~ 10-26) · 문자열 처리

**과제** (G1): G코드 한 줄 `G1 X10.5 Y20 E0.123 ; outer wall` 을 명령과 숫자 사전으로 바꾸고, 주석만 있는 줄은 `(None, {})` 반환

<details><summary>풀이 (`ex03.py`)</summary>

```python
# W3: 문자열 처리 — G코드 한 줄을 명령과 숫자 사전으로 바꾸기 (G1 준비)
def parse_line(raw):
    line = raw.split(";")[0].strip().upper()       # 주석 제거, 대문자
    if not line:
        return None, {}
    words = line.split()
    args = {w[0]: float(w[1:]) for w in words[1:]}
    return words[0], args

cmd, args = parse_line("G1 X10.5 Y20 E0.123 ; outer wall")
print(cmd, args)
assert cmd == "G1" and args == {"X": 10.5, "Y": 20.0, "E": 0.123}
assert parse_line("; only comment") == (None, {})
print("통과")
```

실행: `python ex03.py`

```text
G1 {'X': 10.5, 'Y': 20.0, 'E': 0.123}
통과
```

</details>

#### W4 (10-27 ~ 11-02) · 파일 읽기·numpy·matplotlib

**과제** (G1, J3): 10 mm 정사각형 G코드 파일을 만들어 읽고, 선분 4개·길이 합 40 mm를 numpy로 계산, 경로 그림을 PNG로 저장

<details><summary>풀이 (`ex04.py`)</summary>

```python
# W4: 파일 읽기 + numpy + matplotlib — 10 mm 정사각형 G코드의 선분 길이와 경로 그림
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

gcode = """G90
M82
G92 E0
G0 X0 Y0 Z0.2
G1 X10 Y0 E0.5
G1 X10 Y10 E1.0
G1 X0 Y10 E1.5
G1 X0 Y0 E2.0
"""
Path("square.gcode").write_text(gcode)

pts = [(0.0, 0.0)]
for raw in Path("square.gcode").read_text().splitlines():
    w = raw.split()
    if w and w[0] == "G1":
        a = {s[0]: float(s[1:]) for s in w[1:]}
        pts.append((a["X"], a["Y"]))
P = np.array(pts)                                   # (5, 2) 배열
seg_len = np.linalg.norm(np.diff(P, axis=0), axis=1)  # 이웃 점 사이 거리
print("선분 수:", len(seg_len), "길이 합:", seg_len.sum(), "mm")

fig, ax = plt.subplots(figsize=(3, 3))
ax.plot(P[:, 0], P[:, 1], "-o")
ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]"); ax.set_aspect("equal")
fig.savefig("square_path.png", dpi=100)
assert len(seg_len) == 4 and seg_len.sum() == 40.0  # J3 단위 테스트 예와 동일
print("통과")
```

실행: `python ex04.py`

```text
선분 수: 4 길이 합: 40.0 mm
통과
```

</details>

#### W5 (11-03 ~ 11-09) · numpy 불리언 마스크

**과제** (G3, G4): 0.02 mm 격자에 2 × 1 mm 사각형 마스크를 만들고 면적이 2.000 mm²인지 확인, 마스크 밖은 NaN인 높이맵 만들기

<details><summary>풀이 (`ex05.py`)</summary>

```python
# W5: 불리언 마스크 — 0.02 mm 격자에 2 x 1 mm 사각형 마스크 만들고 면적 계산
import numpy as np

res = 0.02
xs = np.arange(0, 4, res) + res / 2                # 칸 중심 좌표
ys = np.arange(0, 3, res) + res / 2
X, Y = np.meshgrid(xs, ys)
mask = (X >= 1) & (X < 3) & (Y >= 1) & (Y < 2)      # 사각형 안 = True
area = mask.sum() * res * res
print("마스크 크기:", mask.shape, "True 칸 수:", mask.sum(), f"면적: {area:.3f} mm^2")
H = np.where(mask, 0.6, np.nan)                     # 높이맵: 재료 있는 곳 0.6 mm, 없으면 NaN
print("높이 평균(NaN 무시):", np.nanmean(H))
assert abs(area - 2.0) < 1e-9
print("통과")
```

실행: `python ex05.py`

```text
마스크 크기: (150, 200) True 칸 수: 5000 면적: 2.000 mm^2
높이 평균(NaN 무시): 0.6
통과
```

</details>

#### W6 (11-10 ~ 11-16) · shapely buffer·union

**과제** (G2, G3): 길이 10 mm 선에 선폭 0.42 mm를 입혀 면적이 `L·w + π(w/2)²` 와 0.1 % 이내로 맞는지, 겹친 두 줄을 합치면 면적이 두 배보다 작은지 확인

<details><summary>풀이 (`ex06.py`)</summary>

```python
# W6: shapely — 선분에 선폭을 입혀 면적 확인 (G3 기준 형상)
import math
from shapely.geometry import LineString
from shapely.ops import unary_union

w = 0.42
line = LineString([(0, 0), (10, 0)])
bead = line.buffer(w / 2, cap_style="round")        # 양 끝 반원
expected = 10 * w + math.pi * (w / 2) ** 2
print(f"면적 {bead.area:.4f} mm^2 (이론 {expected:.4f})")
two = unary_union([bead, LineString([(0, 0.4), (10, 0.4)]).buffer(w / 2)])
print(f"0.4 mm 간격 두 줄 합친 면적 {two.area:.4f} (겹침 때문에 두 배보다 작음)")
assert abs(bead.area - expected) / expected < 0.001  # 원 근사 오차 0.1 % 이내
assert two.area < 2 * bead.area
print("통과")
```

실행: `python ex06.py`

```text
면적 4.3383 mm^2 (이론 4.3385)
0.4 mm 간격 두 줄 합친 면적 8.4750 (겹침 때문에 두 배보다 작음)
통과
```

</details>

#### W7 (11-17 ~ 11-23) · OpenCV 이미지 입출력

**과제** (F1): 계단 모양 합성 레이저 이미지를 만들어 PNG로 저장·흑백으로 다시 읽고, 열마다 가장 밝은 행이 정답(40/50/60)과 같은지 확인

<details><summary>풀이 (`ex07.py`)</summary>

```python
# W7: OpenCV 기초 — 합성 레이저 이미지 저장·읽기, 열마다 가장 밝은 행 찾기
import numpy as np
import cv2

H, W = 100, 60
img = np.zeros((H, W), np.uint8)
true_row = 40 + (np.arange(W) // 20) * 10           # 계단 모양: 40, 50, 60 행
img[true_row, np.arange(W)] = 255
img = cv2.GaussianBlur(img, (0, 0), sigmaX=1.0, sigmaY=1.5)  # 선을 두껍게
cv2.imwrite("laser.png", img)
back = cv2.imread("laser.png", cv2.IMREAD_GRAYSCALE)  # 흑백으로 읽기
peak = back.argmax(axis=0)                          # 열마다 최대 밝기 행
print("이미지 크기:", back.shape, "dtype:", back.dtype)
print("열 0, 25, 59의 피크 행:", peak[[0, 25, 59]])
assert np.array_equal(peak, true_row)
print("통과")
```

실행: `python ex07.py`

```text
이미지 크기: (100, 60) dtype: uint8
열 0, 25, 59의 피크 행: [40 50 60]
통과
```

</details>

#### W8 (11-24 ~ 11-30) · 서브픽셀 무게중심

**과제** (F1, D2): 참 중심이 50.3 행인 가우시안 선(노이즈 포함)에서 무게중심으로 중심을 찾아 오차 < 0.1 px 확인

<details><summary>풀이 (`ex08.py`)</summary>

```python
# W8: 서브픽셀 무게중심 — 참 중심 50.3 행인 가우시안 선을 1/10 px보다 정확히 찾기 (F1)
import numpy as np

rng = np.random.default_rng(0)
rows = np.arange(100)
true_v = 50.3
profile = 200 * np.exp(-0.5 * ((rows - true_v) / 1.5) ** 2) + rng.normal(0, 2, 100)

def cog(col, threshold=30, half_win=5):
    p = int(col.argmax())
    r0, r1 = p - half_win, p + half_win + 1
    w = np.clip(col[r0:r1] - threshold, 0, None)    # 임계값 이하는 0
    return r0 + (w * np.arange(r1 - r0)).sum() / w.sum()

v = cog(profile)
print(f"최대 픽셀: {profile.argmax()}, 무게중심: {v:.3f}, 오차: {v - true_v:+.3f} px")
assert abs(v - true_v) < 0.1
print("통과")
```

실행: `python ex08.py`

```text
최대 픽셀: 50, 무게중심: 50.274, 오차: -0.026 px
통과
```

</details>

#### W9 (12-01 ~ 12-07) · SVD 평면 맞춤

**과제** (D2): 30° 기운 평면 위 500점(노이즈 3 µm)에서 법선 n과 d를 구하고 잔차 RMS < 5 µm 확인 (M1 기준과 같은 숫자)

<details><summary>풀이 (`ex09.py`)</summary>

```python
# W9: SVD 평면 맞춤 — 레이저 평면 점들에서 법선 n, 상수 d 구하기 (D2)
import numpy as np

rng = np.random.default_rng(1)
n_true = np.array([0.0, np.sin(np.radians(30)), np.cos(np.radians(30))])
d_true = -150.0
uv = rng.uniform(-10, 10, (500, 2))
# 평면 위 점 만들기: n·X + d = 0 을 만족하도록 z 결정
x, y = uv[:, 0], uv[:, 1]
z = -(d_true + n_true[0] * x + n_true[1] * y) / n_true[2]
P = np.column_stack([x, y, z]) + rng.normal(0, 0.003, (500, 3))   # 3 µm 노이즈

c = P.mean(axis=0)
_, _, Vt = np.linalg.svd(P - c)
n = Vt[-1] * np.sign(Vt[-1] @ n_true)               # 방향(부호) 맞추기
d = -n @ c
res = (P @ n + d) * 1000                            # 잔차 [µm]
print("n =", np.round(n, 4), " d =", round(d, 3))
print(f"잔차 RMS = {np.sqrt((res ** 2).mean()):.2f} um")
assert np.allclose(n, n_true, atol=1e-3) and np.sqrt((res ** 2).mean()) < 5
print("통과")
```

실행: `python ex09.py`

```text
n = [0.    0.5   0.866]  d = -150.001
잔차 RMS = 3.08 um
통과
```

</details>

#### W10 (12-08 ~ 12-14) · scipy binned_statistic_2d

**과제** (H1, H2): 흩어진 5000점(이상치 1 %)을 0.1 mm 격자 중앙값 높이맵으로 만들고, 평균(mean)으로 했을 때와 비교

<details><summary>풀이 (`ex10.py`)</summary>

```python
# W10: scipy binned_statistic_2d — 흩어진 점을 0.1 mm 격자 중앙값 높이맵으로 (H1)
import numpy as np
from scipy.stats import binned_statistic_2d

rng = np.random.default_rng(2)
x = rng.uniform(0, 1, 5000)
y = rng.uniform(0, 1, 5000)
z = 0.2 + rng.normal(0, 0.005, 5000)
z[:50] = 5.0                                        # 이상치 1 %
edges = np.arange(0, 1.0001, 0.1)
Hm, _, _, _ = binned_statistic_2d(x, y, z, statistic="median", bins=[edges, edges])
print("격자 크기:", Hm.shape, f"중앙값 높이맵 평균: {np.nanmean(Hm):.4f} mm")
print(f"평균(mean) 높이맵이었다면: {np.nanmean(binned_statistic_2d(x, y, z, 'mean', bins=[edges, edges])[0]):.4f} mm")
assert abs(np.nanmean(Hm) - 0.2) < 0.002            # 중앙값은 이상치에 강함
print("통과")
```

실행: `python ex10.py`

```text
격자 크기: (10, 10) 중앙값 높이맵 평균: 0.2001 mm
평균(mean) 높이맵이었다면: 0.2464 mm
통과
```

</details>

#### W11 (12-15 ~ 12-21) · 선형대수 (Kabsch)

**과제** (H4, J3): 마커 4개를 회전 0.5°·이동 (0.20, −0.10) mm 옮긴 뒤 `rigid_transform()` 으로 정확히 복원

<details><summary>풀이 (`ex11.py`)</summary>

```python
# W11: 강체 변환 복원 (Kabsch) — 알려진 회전·이동을 되찾기 (H4)
import numpy as np

def rigid_transform(A, B):
    ca, cb = A.mean(axis=0), B.mean(axis=0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca

a = np.radians(0.5)                                 # Z축 회전 0.5°
R_true = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
t_true = np.array([0.20, -0.10, 0.0])
A = np.array([[0, 0, 0], [80, 0, 0], [0, 60, 0], [80, 60, 3.0]])   # 마커 4개 [mm]
B = A @ R_true.T + t_true
R, t = rigid_transform(A, B)
yaw = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
print(f"복원 이동: {np.round(t, 4)}, 회전: {yaw:.4f} deg")
assert np.allclose(t, t_true, atol=1e-9) and abs(yaw - 0.5) < 1e-9
print("통과")
```

실행: `python ex11.py`

```text
복원 이동: [ 0.2 -0.1  0. ], 회전: 0.5000 deg
통과
```

</details>

#### W12 (12-22 ~ 12-28) · pytest

**과제** (J3): IoU 함수에 대한 테스트 2개(같은 마스크 = 1, 절반 겹침 = 1/3)를 작성하고 `pytest` 로 실행

<details><summary>풀이 (`test_ex12.py`)</summary>

```python
# W12: pytest — 테스트 파일 이름은 test_ 로 시작, 함수도 test_ 로 시작
import numpy as np


def iou(A, B):
    return (A & B).sum() / (A | B).sum()


def test_iou_identical():
    A = np.ones((4, 4), bool)
    assert iou(A, A) == 1.0


def test_iou_half_overlap():
    A = np.zeros((4, 8), bool); A[:, 0:4] = True
    B = np.zeros((4, 8), bool); B[:, 2:6] = True     # 절반 겹침
    assert abs(iou(A, B) - 1 / 3) < 1e-12            # 손 계산: 8 / 24
```

실행: `python -m pytest -q test_ex12.py`

```text
..                                                                       [100%]
2 passed in 0.xx s
```

</details>

#### W13 (12-29 ~ 01-04) · 지표 계산

**과제** (H5, A1): 0.03 mm 재료 부족 + 노이즈 높이맵에서 mean, std, RMS, P95를 구하고 `RMS² = mean² + std²` 확인. NaN 칸 제외

<details><summary>풀이 (`ex13.py`)</summary>

```python
# W13: 높이 오차 지표 — RMS² = 평균² + 표준편차² 확인 (H5)
import numpy as np

rng = np.random.default_rng(3)
H_ref = np.full((50, 50), 2.0)
H_meas = H_ref - 0.03 + rng.normal(0, 0.01, H_ref.shape)   # 0.03 mm 재료 부족 + 노이즈
H_meas[0, :5] = np.nan                                      # 측정 안 된 칸
e = H_meas - H_ref                                          # 부호: 측정 − 기준
e = e[~np.isnan(e)]
mean, std, rms = e.mean(), e.std(), np.sqrt((e ** 2).mean())
p95 = np.percentile(np.abs(e), 95)
print(f"n={e.size} mean={mean:+.4f} std={std:.4f} rms={rms:.4f} P95={p95:.4f} mm")
assert abs(rms ** 2 - (mean ** 2 + std ** 2)) < 1e-12        # ddof=0 일 때 정확히 성립
assert mean < 0                                              # − 는 재료 부족
print("통과")
```

실행: `python ex13.py`

```text
n=2495 mean=-0.0297 std=0.0099 rms=0.0313 P95=0.0459 mm
통과
```

</details>

#### W14 (01-05 ~ 01-11) · 윤곽 지표·히트맵 규칙

**과제** (H6, J4): 절반 겹친 두 마스크의 IoU = 1/3, Dice = 1/2 확인, `RdBu_r`·±0.2 mm 고정 범위 히트맵 저장

<details><summary>풀이 (`ex14.py`)</summary>

```python
# W14: 윤곽 지표 + 히트맵 규칙 — IoU/Dice 손 계산 확인, 0이 흰색인 고정 범위 그림 (H6, J4)
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

A = np.zeros((4, 8), bool); A[:, 0:4] = True
B = np.zeros((4, 8), bool); B[:, 2:6] = True
inter, union = (A & B).sum(), (A | B).sum()
iou, dice = inter / union, 2 * inter / (A.sum() + B.sum())
print(f"IoU={iou:.4f} Dice={dice:.4f}")
assert abs(iou - 1 / 3) < 1e-12 and abs(dice - 0.5) < 1e-12

e = np.random.default_rng(4).normal(0, 0.05, (40, 40))
fig, ax = plt.subplots()
im = ax.imshow(e, cmap="RdBu_r", vmin=-0.2, vmax=0.2)       # 대칭 고정 범위
fig.colorbar(im, label="deviation (meas - ref) [mm]")
fig.savefig("heatmap.png", dpi=300)
print("통과")
```

실행: `python ex14.py`

```text
IoU=0.3333 Dice=0.5000
통과
```

</details>

#### W15 (01-12 ~ 01-18) · pandas groupby

**과제** (H8): 조건 2개 × 시편 3개 × 스캔 3회 데이터를 시편 단위로 먼저 평균한 뒤 조건별 요약 (표본 수 = 3 확인)

<details><summary>풀이 (`ex15.py`)</summary>

```python
# W15: pandas groupby — 점이 아니라 '시편 단위' 요약값 만들기 (H8 유사반복 방지)
import numpy as np
import pandas as pd

rng = np.random.default_rng(5)
rows = []
for cond, bias in [("speed40", 0.00), ("speed80", 0.03)]:
    for s in range(3):                              # 시편 3개
        for r in range(3):                          # 스캔 3회
            rows.append({"condition": cond, "specimen": f"{cond}_S{s}", "scan": r,
                         "rms_mm": 0.05 + bias + rng.normal(0, 0.004)})
df = pd.DataFrame(rows)
per_specimen = df.groupby(["condition", "specimen"], as_index=False)["rms_mm"].mean()
summary = per_specimen.groupby("condition")["rms_mm"].agg(["count", "mean", "std"])
print(summary.round(4))
assert list(summary["count"]) == [3, 3]             # 조건당 표본 수 = 시편 수 3
print("통과")
```

실행: `python ex15.py`

```text
           count    mean     std
condition                       
speed40        3  0.0494  0.0027
speed80        3  0.0794  0.0029
통과
```

</details>

#### W16 (01-19 ~ 01-25) · scipy.stats 신뢰구간

**과제** (H8, I1): 시편 5개 RMS의 평균 95 % 신뢰구간을 공식으로 직접 계산하고 `stats.t.interval` 과 일치 확인

<details><summary>풀이 (`ex16.py`)</summary>

```python
# W16: scipy.stats — 평균의 95 % 신뢰구간 (t 분포)
import numpy as np
from scipy import stats

x = np.array([0.052, 0.047, 0.055, 0.049, 0.051])   # 시편 5개의 RMS [mm]
n, m, s = len(x), x.mean(), x.std(ddof=1)
half = stats.t.ppf(0.975, df=n - 1) * s / np.sqrt(n)
print(f"평균 {m:.4f} mm, 95% CI [{m - half:.4f}, {m + half:.4f}] (반폭 {half:.4f})")
lo, hi = stats.t.interval(0.95, df=n - 1, loc=m, scale=stats.sem(x))
assert abs(lo - (m - half)) < 1e-12 and abs(hi - (m + half)) < 1e-12
print("통과")
```

실행: `python ex16.py`

```text
평균 0.0508 mm, 95% CI [0.0470, 0.0546] (반폭 0.0038)
통과
```

</details>

#### W17 (01-26 ~ 02-01) · statsmodels 분산분석

**과제** (H8, I2): 세 조건(각 시편 5개)의 일원 ANOVA 표를 만들고 p < 0.05 판정

<details><summary>풀이 (`ex17.py`)</summary>

```python
# W17: statsmodels — 일원 분산분석 (세 조건의 시편 단위 RMS 비교)
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols

rng = np.random.default_rng(6)
df = pd.DataFrame({
    "cond": np.repeat(["A", "B", "C"], 5),
    "rms": np.concatenate([rng.normal(m, 0.004, 5) for m in (0.050, 0.051, 0.065)]),
})
model = ols("rms ~ C(cond)", data=df).fit()
table = sm.stats.anova_lm(model, typ=2)
print(table.round(6))
p = table.loc["C(cond)", "PR(>F)"]
print(f"p = {p:.2e} -> {'조건 간 차이 있음' if p < 0.05 else '차이 없음'}")
assert p < 0.05
print("통과")
```

실행: `python ex17.py`

```text
            sum_sq    df          F    PR(>F)
C(cond)   0.000417   2.0  10.921925  0.001987
Residual  0.000229  12.0        NaN       NaN
p = 1.99e-03 -> 조건 간 차이 있음
통과
```

</details>

#### W18 (02-02 ~ 02-08) · pathlib·json 일괄 처리

**과제** (F3, D5): 메타데이터 JSON 3개를 폴더에서 모두 읽어 표로 만들고 CAL-ID 누락 스캔 찾기

<details><summary>풀이 (`ex18.py`)</summary>

```python
# W18: 일괄 처리 — 폴더 안 메타데이터 JSON을 모두 읽어 표로 만들고 누락 검사 (F3)
import json
from pathlib import Path
import pandas as pd

d = Path("meta_demo"); d.mkdir(exist_ok=True)
for i, cal in enumerate(["CAL-2026-11-30-A", "CAL-2026-11-30-A", None], start=1):
    meta = {"scan_id": f"S01_r0{i}", "room_temp_C": 22.0 + i / 10}
    if cal:
        meta["calibration_id"] = cal
    (d / f"S01_r0{i}.json").write_text(json.dumps(meta))

records = [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))]
df = pd.DataFrame(records)
print(df)
missing = df[df["calibration_id"].isna()]["scan_id"].tolist()
print("CAL-ID 누락 스캔:", missing)
assert missing == ["S01_r03"]
print("통과")
```

실행: `python ex18.py`

```text
   scan_id  room_temp_C    calibration_id
0  S01_r01         22.1  CAL-2026-11-30-A
1  S01_r02         22.2  CAL-2026-11-30-A
2  S01_r03         22.3               NaN
CAL-ID 누락 스캔: ['S01_r03']
통과
```

</details>

#### W19 (02-09 ~ 02-15) · Bland–Altman

**과제** (I3): 우리 장비와 마이크로미터 6쌍 비교: 상관계수는 1에 가깝지만 평균 차이 약 +10 µm 치우침이 있음을 보이기

<details><summary>풀이 (`ex19.py`)</summary>

```python
# W19: Bland–Altman — 우리 장비 vs 마이크로미터의 평균 차이와 일치 한계 (I3)
import numpy as np

ours = np.array([1.012, 2.008, 5.015, 10.011, 1.998, 4.020])   # [mm]
ref = np.array([1.000, 2.000, 5.004, 10.002, 1.990, 4.009])
diff = ours - ref
bias, sd = diff.mean(), diff.std(ddof=1)
loa = (bias - 1.96 * sd, bias + 1.96 * sd)
r = np.corrcoef(ours, ref)[0, 1]
print(f"상관계수 r = {r:.6f}  <- 높아도 일치한다는 뜻은 아님")
print(f"평균 차이 = {bias * 1000:+.1f} um, 일치 한계 = [{loa[0] * 1000:+.1f}, {loa[1] * 1000:+.1f}] um")
assert r > 0.999 and bias > 0.005                    # 상관은 높지만 약 +10 µm 치우침
print("통과")
```

실행: `python ex19.py`

```text
상관계수 r = 1.000000  <- 높아도 일치한다는 뜻은 아님
평균 차이 = +9.8 um, 일치 한계 = [+6.5, +13.2] um
통과
```

</details>

#### W20 (02-16 ~ 02-22) · argparse

**과제** (J1): 분석 스크립트가 `scan_id`, `--res`, `--tol` 인자를 받도록 만들기

<details><summary>풀이 (`ex20.py`)</summary>

```python
# W20: argparse — 노트북 코드를 명령줄 스크립트로 바꾸기 (J1 scripts/)
import argparse

def build_parser():
    ap = argparse.ArgumentParser(description="한 시편 분석")
    ap.add_argument("scan_id")
    ap.add_argument("--res", type=float, default=0.02, help="격자 간격 [mm]")
    ap.add_argument("--tol", type=float, default=0.1, help="공차 [mm]")
    return ap

# 실제로는 build_parser().parse_args() — 연습에서는 목록을 직접 넣어 확인
args = build_parser().parse_args(["S03_r02", "--tol", "0.05"])
print(args)
assert args.scan_id == "S03_r02" and args.res == 0.02 and args.tol == 0.05
print("통과")
```

실행: `python ex20.py`

```text
Namespace(scan_id='S03_r02', res=0.02, tol=0.05)
통과
```

</details>

#### W21 (02-23 ~ 03-01) · YAML 설정

**과제** (J2): 기본 설정(J2 예시)에 실험별 설정(공차 0.05 mm)을 덮어쓰는 `merge()` 작성

<details><summary>풀이 (`ex21.py`)</summary>

```python
# W21: YAML 설정 — 기본 설정에 실험별 설정을 덮어쓰기 (J2)
import yaml

default = yaml.safe_load("""
grid: {resolution_mm: 0.02}
masks: {edge_band_mm: 0.25}
metrics: {tolerance_mm: 0.1}
random_seed: 42
""")
override = yaml.safe_load("metrics: {tolerance_mm: 0.05}")

def merge(base, new):
    out = dict(base)
    for k, v in new.items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and k in base else v
    return out

cfg = merge(default, override)
print(yaml.safe_dump(cfg, sort_keys=False).strip())
assert cfg["metrics"]["tolerance_mm"] == 0.05 and cfg["grid"]["resolution_mm"] == 0.02
print("통과")
```

실행: `python ex21.py`

```text
grid:
  resolution_mm: 0.02
masks:
  edge_band_mm: 0.25
metrics:
  tolerance_mm: 0.05
random_seed: 42
통과
```

</details>

#### W22 (03-02 ~ 03-08) · 논문용 그림

**과제** (J4, K5): 편차 히스토그램 + 공차선 ±0.1 mm + 단위 라벨, 300 dpi 저장 후 dpi 확인

<details><summary>풀이 (`ex22.py`)</summary>

```python
# W22: 논문용 그림 — 300 dpi, 축 단위, 공차 선, 저장 후 dpi 확인 (J4, K5)
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

e = np.random.default_rng(7).normal(-0.02, 0.03, 2000)
fig, ax = plt.subplots(figsize=(3.5, 2.6))          # 학술지 한 단 폭 정도
ax.hist(e, bins=40, color="gray")
for x in (-0.1, 0.1):
    ax.axvline(x, color="red", ls="--", lw=1)        # 공차 ±0.1 mm
ax.axvline(e.mean(), color="black", lw=1)
ax.set_xlabel("Height deviation (meas - ref) [mm]")
ax.set_ylabel("Count")
fig.tight_layout()
fig.savefig("fig_hist.png", dpi=300)
dpi = Image.open("fig_hist.png").info["dpi"][0]
print(f"저장된 dpi: {round(dpi)}")
assert round(dpi) >= 300
print("통과")
```

실행: `python ex22.py`

```text
저장된 dpi: 300
통과
```

</details>

#### W23 (03-09 ~ 03-15) · 결과표 만들기

**과제** (I1, K5): 형상별 평균 오차를 `값 ± U (k=2)` 마크다운 표로 만들고 \|오차\| < U 이면 '구별 불가' 판정

<details><summary>풀이 (`ex23.py`)</summary>

```python
# W23: 결과표 — DataFrame을 '값 ± U' 형식의 마크다운 표 문자열로 (K5 T3)
import pandas as pd

df = pd.DataFrame({
    "feature": ["top_plane", "step_1mm", "hole_6mm"],
    "mean_mm": [-0.012, 0.021, -0.084],
    "U_mm": [0.016, 0.016, 0.020],                   # 확장불확도 k=2
})
lines = ["| 형상 | 평균 오차 [mm] (k=2) | 판정 |", "|---|---|---|"]
for r in df.itertuples():
    verdict = "구별 불가" if abs(r.mean_mm) < r.U_mm else "유의"
    lines.append(f"| {r.feature} | {r.mean_mm:+.3f} ± {r.U_mm:.3f} | {verdict} |")
table = "\n".join(lines)
print(table)
assert table.count("구별 불가") == 1
print("통과")
```

실행: `python ex23.py`

```text
| 형상 | 평균 오차 [mm] (k=2) | 판정 |
|---|---|---|
| top_plane | -0.012 ± 0.016 | 구별 불가 |
| step_1mm | +0.021 ± 0.016 | 유의 |
| hole_6mm | -0.084 ± 0.020 | 유의 |
통과
```

</details>

#### W24 (03-16 ~ 03-22) · 재현성 기록

**과제** (J2, K5): G코드 파일의 SHA-256, Python·numpy 버전, git 커밋을 `run_info.json` 으로 저장

<details><summary>풀이 (`ex24.py`)</summary>

```python
# W24: 재현성 기록 — 파일 SHA-256, 라이브러리 버전, git 커밋을 결과와 함께 저장 (J2, K5)
import hashlib
import json
import platform
import subprocess
from pathlib import Path
import numpy as np

Path("demo.gcode").write_text("G1 X10 Y0 E0.5\n")
sha = hashlib.sha256(Path("demo.gcode").read_bytes()).hexdigest()
try:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True, check=True).stdout.strip()
except (subprocess.CalledProcessError, FileNotFoundError):
    commit = "no-git"                                # git 저장소 밖에서 실행한 경우
record = {"gcode_sha256": sha, "python": platform.python_version(),
          "numpy": np.__version__, "git_commit": commit}
Path("run_info.json").write_text(json.dumps(record, indent=2))
print("gcode_sha256:", sha[:16], "...")
assert sha == hashlib.sha256(b"G1 X10 Y0 E0.5\n").hexdigest()
print("통과")
```

실행: `python ex24.py`

```text
gcode_sha256: 417f55064e22ba46 ...
통과
```

</details>

## 7. 검증 방법과 완료 기준

| 검증 | 방법 | 기준 |
|---|---|---|
| 연습 완료 | 24개 풀이 파일 실행 | 모두 "통과" 출력 |
| 이해도 | 주간 회의에서 이번 주 코드 한 줄씩 설명 | 모든 줄의 역할을 말할 수 있음 |
| 적용 | 연습이 실제 코드로 옮겨졌는지 (5절 3단계) | `src/cvlab/` 에 해당 함수 존재 |
| 습관 | 새 함수마다 테스트 작성 | W12 이후 작성한 함수의 테스트 비율 ≥ 50 % |

**K6 완료 기준 (M6)**: 24개 연습 통과 기록, 그리고 학습자가 `scripts/run_analysis.py` 를 처음부터 끝까지 읽고 각 단계가 어느 요소(G, H, I)에 해당하는지 설명할 수 있음.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 들여쓰기 혼용 (탭/공백) | `IndentationError` | 편집기에서 "공백 4칸" 설정 |
| 가상환경 활성화 안 함 | `ModuleNotFoundError` | 터미널 앞에 `(.venv)` 표시 확인 |
| 파일 이름을 `numpy.py`, `json.py` 로 저장 | 라이브러리 대신 내 파일이 import됨 | 라이브러리 이름과 같은 파일명 금지 |
| 정수 나눗셈·정수 배열 | 이미지 `uint8` 끼리 빼서 음수가 255 근처로 뒤집힘 | 계산 전 `.astype(np.float32)` (F1 코드 참고) |
| 행/열 혼동 | 이미지 `img[v, u]` 인데 `img[u, v]` 로 접근 | 이미지는 (행=v, 열=u). `shape` 를 먼저 출력 |
| NaN이 섞인 평균 | 결과가 `nan` | `np.nanmean` 또는 마스크로 제외 (단, 보간으로 채우지 않기, E2) |
| `std` 의 `ddof` 무시 | 표본 표준편차가 작게 나옴 | 표본 통계는 `ddof=1`, `RMS² = mean² + std²` 확인은 `ddof=0` |
| 노트북 셀을 순서 없이 실행 | 다시 실행하면 결과가 다름 | "Restart & Run All"로 확인 후 `.py` 로 옮기기 |
| 풀이를 먼저 봄 | 따라 할 수는 있어도 혼자 못 짬 | 과제만 보고 30분 이상 시도 |
| 단위 혼동 (mm vs µm) | 1000배 오차 | 변수 이름에 단위 (`dz_um`, `res_mm`) |

## 9. 위험 요소

- **학습 지연이 임계 경로를 늦춤** (K4 R10): 특히 W7~W8 OpenCV·캘리브레이션. 대응: W5~W6에 OpenCV 튜토리얼을 미리 읽고, D1 실습은 합성 이미지로 먼저 해 봄.
- **한 사람만 코드를 이해함** (K4 R13): 대응: W1~W6 연습은 전원 공통, 주간 회의에서 코드 설명 차례를 돌아가며.
- **라이브러리 버전 차이** (K4 R19): shapely 2.x와 1.x, OpenCV ArUco 모듈 API가 버전에 따라 다름. 대응: `requirements.txt` 에 버전 고정 (J2).
- **연습에 시간을 너무 씀**: 연습은 주 2시간 상한. 넘으면 풀이를 보고 이해하는 쪽으로 전환.

## 10. 기록 양식

**학습 기록표** (`docs/learning_log.md`)

| 주 | 이름 | 학습 시간 | 연습 통과 (O/X) | 풀이를 본 부분 | 막힌 점 / 질문 | 실제 코드에 적용한 곳 |
|---|---|---|---|---|---|---|
| W1 | | 7 h | O | 없음 | `math.radians` 를 몰랐음 | – |
| W4 | | | | | | `src/cvlab/gcode_parser.py` |

**오류 노트** (자주 만난 오류를 모아 두면 다음 사람에게 큰 도움)

| 날짜 | 오류 메시지 마지막 줄 | 원인 | 해결 |
|---|---|---|---|
| | `ValueError: operands could not be broadcast together with shapes (100,60) (60,100)` | 행/열 뒤바뀜 | `.T` 또는 meshgrid 순서 확인 |

## 11. 참고 자료

**Python 기초 (한국어)**
- 박응용, 「점프 투 파이썬」 — 무료 웹북 (위키독스, https://wikidocs.net/book/1)
- Python 공식 자습서 한국어판 (https://docs.python.org/ko/3/tutorial/)

**라이브러리 공식 문서**
- NumPy: "NumPy: the absolute basics for beginners" (https://numpy.org/doc/stable/user/absolute_beginners.html)
- Matplotlib: Quick start guide, Tutorials (https://matplotlib.org/stable/)
- SciPy User Guide (https://docs.scipy.org/doc/scipy/)
- pandas: "10 minutes to pandas" (https://pandas.pydata.org/docs/user_guide/10min.html)
- statsmodels 문서 (https://www.statsmodels.org/)
- Shapely User Manual (https://shapely.readthedocs.io/)
- OpenCV-Python Tutorials, "Camera Calibration" (https://docs.opencv.org/)
- pytest: Get Started (https://docs.pytest.org/)
- Open3D 튜토리얼 (https://www.open3d.org/docs/)
- PyYAML 문서

**도구**
- Scott Chacon, Ben Straub, *Pro Git* — 무료 공개, 한국어 번역판 있음 (https://git-scm.com/book/ko/v2)

**통계·측정**
- Bland, J. M., & Altman, D. G. (1986). "Statistical methods for assessing agreement between two methods of clinical measurement." *The Lancet*.
- JCGM 100:2008 (GUM)

- 상위 문서: [BLUEPRINT.md K6](../../BLUEPRINT.md#k6-python-학습-로드맵-완전-초보-기준-k1-일정에-맞춤)
