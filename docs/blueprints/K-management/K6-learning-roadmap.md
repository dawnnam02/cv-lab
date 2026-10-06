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

@@FILE:k6_exercises.md@@

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
