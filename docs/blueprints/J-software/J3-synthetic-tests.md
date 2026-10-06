# J3. 테스트 — 정답을 아는 합성 데이터로 검증

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: J. 소프트웨어

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-15 ~ 2026-12-28 (W11-12) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [J1 구조](J1-software-structure.md), [J2 설정·재현성](J2-config-reproducibility.md), [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md), [G3 마스크·높이맵](../G-reference/G3-mask-heightmap.md), [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md), [H4 정합](../H-analysis/H4-registration.md) (같은 기간 병행) |
| 후행 요소 | [H5 높이 지표](../H-analysis/H5-height-metrics.md), [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md), [J4 시각화·리포트](J4-visualization-report.md), [I1 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | **M3** (W12 말): 합성 데이터에서 변형을 허용오차 내 복원 |

## 1. 목적

- 실측 데이터에는 정답이 없습니다. 그래서 **정답을 알고 만든 가짜(합성) 높이맵**을 넣어 코드가 그 정답을 되찾는지 먼저 확인합니다. 코드 버그와 측정 오차가 섞이기 전에 코드 버그를 0으로 만드는 것이 목적입니다.
- 청사진 J3의 4가지 단위 테스트(파서 · IoU · 강체 변환 · 합성 복원)를 **pytest 자동 테스트**로 만들어, 코드를 고칠 때마다 1–2초 안에 전체가 다시 검증되게 합니다.
- **M3 통과 판정**을 숫자로 정의합니다: 이동 (0.20, −0.10) mm · 회전 0.5° · 배율 0.996 · 높이 +0.03 mm 를 σ = 5 µm 노이즈, 결측 2 %, 엣지 스파이크가 있는 상태에서 **이동 ≤ 5 µm, 회전 ≤ 0.03°, 배율 ≤ 0.05 %(5×10⁻⁴), 높이 ≤ 2 µm** 오차로 복원.
- 노이즈·결측을 키워 가며 **알고리즘이 어디서부터 실패하는지(한계)** 를 표로 남깁니다. 이 한계는 I1 불확도 예산과 E2(가림) 해석의 근거가 됩니다.

## 2. 배경 지식 (초보자용)

**테스트란**: "이 함수에 이 입력을 넣으면 이 출력이 나와야 한다"를 코드로 적어 둔 것입니다. 사람이 그림을 보고 "맞는 것 같다"고 판단하는 대신, 컴퓨터가 매번 같은 기준으로 판정합니다.

**pytest**: Python 테스트 도구입니다. 규칙은 세 가지뿐입니다.
1. 파일 이름은 `test_*.py`, 함수 이름은 `test_*`.
2. 함수 안에서 `assert 조건` — 조건이 거짓이면 실패.
3. 터미널에서 `python -m pytest` → 모든 테스트를 찾아 실행하고 통과/실패를 보고.

자주 쓰는 도구:

| 도구 | 용도 | 예 |
|---|---|---|
| `pytest.approx` | 실수 비교 (부동소수점 오차 허용) | `assert x == pytest.approx(0.2, abs=0.005)` |
| `@pytest.mark.parametrize` | 같은 테스트를 여러 입력으로 | 시드 0, 1, 2 로 각각 실행 |
| `tmp_path` | 테스트마다 새 임시 폴더 | 손으로 쓴 G코드를 파일로 저장 |
| `pytest.raises` | 에러가 **나야** 정상인 경우 | 잘못된 설정 → `ConfigError` |
| `@pytest.mark.slow` | 오래 걸리는 테스트 표시 | `pytest -m "not slow"` 로 제외 |

**왜 `==` 가 아니라 `approx` 인가**: 컴퓨터 실수 계산은 `0.1 + 0.2 == 0.3` 이 거짓일 정도로 작은 오차가 있습니다. 허용오차(`abs=`)는 "물리적으로 의미 있는 크기"로 정합니다. 예: 이동 허용오차 5 µm = 격자 0.02 mm의 1/4, A2 목표 Z 반복성 5 µm와 같은 크기.

**합성 데이터 시험의 논리**

```
정답 변형 T (이동·회전·배율·높이)
   │
기준 형상 ──T 적용──▶ 가짜 측정 ──노이즈·결측·스파이크──▶ 파이프라인 ──▶ 추정 T̂
                                                                   │
                                     |T̂ − T| ≤ 허용오차 ?  ◀────────┘
```
- 통과하면: 코드는 (적어도 이 조건에서) 맞습니다. 실측에서 이상한 값이 나오면 원인은 측정·캘리브레이션 쪽일 가능성이 큽니다.
- 실패하면: 코드 버그(축 뒤집힘, 단위 실수, 부호 반대 등)를 실측 전에 잡은 것입니다. 청사진 K4 위험표의 "단위·축 실수" 대응이 바로 이것입니다.

**이 문서의 복원 방법 (마스크 모멘트법)**: 측정·기준 높이맵을 각각 "높이 > 1.0 mm(블록 높이 2 mm의 절반)" 마스크로 바꾸고,
- **이동** = 두 마스크 도심(무게중심)의 차이,
- **회전** = 2차 모멘트로 구한 주축 방향의 차이 (그래서 시편은 **비대칭 L자**여야 함, C4),
- **배율** = √(측정 면적 / 기준 면적),
- **높이 오프셋** = 경계 0.25 mm(13칸)를 뺀 윗면 높이 중앙값의 차이 (부호: 측정 − 기준, + = 재료 과다).

이 방법은 **H4 "방법 2: 최적 맞춤"의 간이판**이며, 진짜 정합 코드(ECC·ICP)를 만들었을 때도 같은 합성 데이터·같은 테스트로 검증합니다. 테스트 데이터와 판정 기준을 먼저 고정해 두는 것이 이 요소의 핵심입니다.

**결측 처리 원칙**: 측정 안 된 칸은 `NaN` 으로 둡니다(청사진 E2·H1: 보간 금지). 다만 "모양(마스크)"을 만들 때만 3×3 이웃 다수결로 NaN 칸의 재료 여부를 정합니다. 높이 지표에는 NaN을 그대로 제외합니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 / 위치 | 설명 |
|---|---|---|---|
| 입력 | G1 파서 | `src/cvlab/gcode_parser.py` | 청사진 G1 기초 파서 + `seg_length` |
| 입력 | 윤곽 지표 | `src/cvlab/metrics.py` | `iou_dice` (H6) |
| 입력 | 정합 함수 | `src/cvlab/registration.py` | `rigid_transform` (H4) + 마스크 모멘트 닮음 추정 |
| 입력 | 설정 | `config/default.yaml` | 격자 0.02 mm, 경계 띠 0.25 mm (J2) |
| 산출물 | 합성 데이터 생성기 | `src/cvlab/synthetic.py` | `Truth` 데이터클래스, `make_synthetic()` → (H_ref, H_meas, xs, ys), 700×700, 0.02 mm |
| 산출물 | pytest 설정 | `pytest.ini` (또는 `pyproject.toml` 의 `[tool.pytest.ini_options]`) | `pythonpath = src`, `slow` 마커 |
| 산출물 | 테스트 4개 파일 / 20개 케이스 | `tests/test_gcode_parser.py`, `test_metrics.py`, `test_registration.py`, `test_synthetic_recovery.py` | 전체 실행 ≈ 2 s |
| 산출물 | 한계 탐색 스크립트 | `scripts/sweep_noise.py` | σ 4단계 × 결측 4단계 × 시드 3개 = 48회 |
| 산출물 | 한계 표 | `results/j3_sweep.csv` | 열: sigma_mm, missing, shift_mm, rot_deg, scale, dz_mm, all_pass |
| 산출물 | M3 판정 기록 | `docs/milestones/M3.md` (10절 양식) | 허용오차·결과·서명 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 테스트 도구 | unittest / **pytest** | pytest | 문법이 단순(`assert` 만), 청사진 K6 W11–12 학습 항목 |
| 합성 기준 형상 | 정사각형 / 원 / **L자** / 실제 G코드 | **L자 블록** (10×3 + 3×10 mm, 높이 2 mm) + 이후 실제 G코드 시편 | 정사각형·원은 대칭이라 회전·뒤집힘을 못 잡음 (C4 비대칭 시편 원칙) |
| 변형 중심 | 원점 / **기준 형상 도심** | 도심 | 원점 기준이면 회전이 이동과 섞여 정답 해석이 복잡 |
| 형상 래스터화 | 영상 회전(보간) / **폴리곤을 변형한 뒤 격자 판정** | shapely `affinity` + `contains_xy` | 영상 보간은 경계를 흐려 "정답" 자체에 오차를 만듦 |
| 기본 정답값 | — | 이동 (0.20, −0.10) mm, 회전 0.5°, 배율 0.996, 높이 +0.03 mm | 청사진 J3 그대로 |
| 기본 노이즈 | — | σ = 5 µm, 결측 2 %, 엣지 스파이크 50개 × ±0.3 mm | 청사진 J3. σ = A2 목표 Z 반복성 |
| 허용오차 | — | 이동 5 µm · 회전 0.03° · 배율 5×10⁻⁴ · 높이 2 µm | 이동 = 격자/4. 회전 0.03° = 10 mm 길이에서 5 µm. 배율 0.05 % = 측정할 수축(0.4 %)의 1/8. 높이 2 µm = 확장불확도 16 µm(I1 예시)의 1/8 |
| 시드 | 1개 / **3개 이상** | 0, 1, 2 | 한 시드에서 우연히 통과하는 것 방지 |
| 한계 탐색 범위 | — | σ ∈ {5, 50, 200, 400} µm, 결측 ∈ {2, 10, 20, 30} % | 실측에서 생길 수 있는 범위 + 확실히 실패하는 지점까지 |
| 느린 테스트 | 항상 실행 / **마커로 분리** | `@pytest.mark.slow` | 매번 실행은 빠르게(< 5 s) |
| 테스트 실행 시점 | 가끔 / **커밋 전마다** | 커밋 전 `python -m pytest`, 실패 시 커밋 금지 | 회귀(고친 뒤 다른 곳이 깨짐) 방지 |

## 5. 수행 절차

**1단계 (W11, 1일차) — pytest 환경**
- [ ] `pip install pytest` (J1 requirements에 이미 포함) → `python -m pytest --version`.
- [ ] 6.1절 `pytest.ini` 저장. J1에서 `pyproject.toml` 에 `[tool.pytest.ini_options]` 를 이미 넣었다면 거기에 `markers` 만 추가 (둘 중 한 곳만 사용).

**2단계 (W11, 1–2일차) — 파서 테스트 (G1)**
- [ ] 6.3절 `test_gcode_parser.py` 작성: 손으로 쓴 10 mm 정사각형 G코드 (절대·상대 좌표 두 버전).
- [ ] 판정: 압출 선분 **4개**, 길이 합 **40.000 mm**, ΣΔE **2.0** (리트랙션 제외), 층 번호 {0}, 종류 {WALL-OUTER}, Z = 0.2 mm.
- [ ] 상대 좌표(G91/M83) 버전이 절대 좌표 버전과 같은 선분을 내는지 확인.

**3단계 (W11, 2일차) — IoU 테스트 (H6)**
- [ ] 6.3절 `test_metrics.py`: 100×100칸 정사각형 두 개를 50칸 어긋나게 → IoU **1/3**, Dice **1/2** (손 계산: 교집합 5000, 합집합 15000).
- [ ] mm 격자판: 10×10 mm 정사각형 두 개(5 mm 어긋남)를 0.02 mm로 래스터화 → shapely 정확값 1/3과 **±0.001** 이내.
- [ ] 같은 마스크 → (1, 1), 안 겹치는 마스크 → (0, 0).

**4단계 (W11, 3일차) — 강체 변환 테스트 (H4)**
- [ ] 6.3절 `test_registration.py`: 마커 4개를 회전 {0, 0.5, 30, −170}° + 이동 (0.20, −0.10, 0) mm → R, t 를 **1e-9** 이내 복원.
- [ ] 마커 중심에 σ = 2 µm 노이즈 → 정합 잔차(FRE) RMS **< 5 µm**, yaw 0.5° ± 0.01°.
- [ ] 평면 위 점들(z = 0)에서도 det(R) = +1 (거울 반전 없음).

**5단계 (W11, 4–5일차) — 합성 데이터 생성기**
- [ ] 6.2절 `synthetic.py` 를 `src/cvlab/` 에 저장, `python -m cvlab.synthetic` 실행 → 격자 (700, 700), 결측 ≈ 2 %.
- [ ] matplotlib으로 H_ref 와 `H_meas − H_ref` 를 나란히 `imshow` (`origin="lower"` 필수): H_ref 는 정상적인 'L' 모양(세로 막대 왼쪽, 가로 막대 아래)이어야 하고, 차이 영상에서는 이동 (+0.20, −0.10) mm 때문에 **오른쪽·아래 경계에 + 띠(재료 과다), 왼쪽·위 경계에 − 띠**가 보여야 함.

**6단계 (W12, 1–2일차) — 합성 복원 테스트 (M3 핵심)**
- [ ] 6.3절 `test_synthetic_recovery.py`: 시드 0, 1, 2 각각에서 4개 변형량이 허용오차 이내.
- [ ] 항등 변환(변형 없음) → 모든 추정값이 0(배율 1) 근처.
- [ ] **부호 규칙 테스트**: 높이 +0.05 → 추정 양수, −0.05 → 음수 (청사진 A1: 오차 = 측정 − 기준, + = 재료 과다).
- [ ] 결측이 `0` 이 아니라 `NaN` 으로 표시되는지 (2 % ± 0.5 %p).

**7단계 (W12, 3일차) — 한계 탐색**
- [ ] 6.4절 `sweep_noise.py` 실행 → `results/j3_sweep.csv`.
- [ ] 표에서 처음으로 `all_pass = False` 가 되는 σ와 결측률을 10절 양식에 기록.
- [ ] 실측 조건(F1 반복성, E2 결측률)이 한계보다 **2배 이상 안전한지** 확인. 아니면 H4 정합 방법을 강화(ECC/ICP, 결측 많은 영역 제외).

**8단계 (W12, 4일차) — 실제 G코드로 확장**
- [ ] L자 대신 G1→G2→G3로 만든 실제 시편(E3 계단 피라미드 등)의 기준 높이맵에 같은 `Truth` 변형을 적용하는 버전을 추가 (`make_synthetic` 의 `ref_poly` 를 G3 층 폴리곤으로 교체).
- [ ] 다층 형상에서는 `flat_top_offset` 대신 "기준 높이맵을 추정 변환으로 옮긴 뒤 차이의 중앙값"으로 높이 오프셋을 구하도록 H4·H5와 함께 수정.

**9단계 (W12, 5일차) — M3 판정과 운영 규칙**
- [ ] 전체 `python -m pytest` → **20 passed** (+ 추가한 테스트), 소요 < 5 s.
- [ ] 10절 M3 판정 기록 작성, 지도교수/선임 확인.
- [ ] 규칙 공지: **커밋 전에 pytest 통과 필수**, 버그를 고칠 때는 그 버그를 재현하는 테스트를 먼저 추가.

## 6. Python 구현

폴더 배치 (J1 구조 그대로):
```text
cv-lab/
├── pytest.ini
├── src/cvlab/{__init__.py, gcode_parser.py, metrics.py, registration.py, synthetic.py}
├── tests/{test_gcode_parser.py, test_metrics.py, test_registration.py, test_synthetic_recovery.py}
└── scripts/sweep_noise.py
```

### 6.1 `pytest.ini`

```ini
[pytest]
pythonpath = src
testpaths = tests
addopts = -ra
markers =
    slow: 시간이 오래 걸리는 테스트 (pytest -m "not slow" 로 제외 가능)
```

### 6.2 테스트 대상 모듈

`src/cvlab/synthetic.py` — 합성 데이터 생성기
```python
"""synthetic.py — 정답을 알고 만드는 합성 높이맵 (J3).

기준: L자 블록(높이 2.0 mm). 측정: 기준 형상에 알려진 변형(이동·회전·배율·높이)을
적용하고 노이즈·결측·엣지 스파이크를 넣는다. 변형은 '기준 형상의 도심(centroid)'을
중심으로 p' = c + s·R(θ)·(p − c) + t 로 정의한다.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import shapely
from scipy import ndimage
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union


@dataclass
class Truth:
    """정답 변형 + 노이즈 조건. 청사진 J3 의 기본값."""
    shift_x_mm: float = 0.20
    shift_y_mm: float = -0.10
    rot_deg: float = 0.5
    scale: float = 0.996
    dz_mm: float = 0.03            # + 는 재료 과다 (측정 − 기준)
    noise_sigma_mm: float = 0.005  # 가우시안 σ = 5 µm
    missing_frac: float = 0.02     # 무작위 결측 2 %
    n_spikes: int = 50             # 엣지 스파이크 개수
    spike_mm: float = 0.3          # 스파이크 크기 (±)


def make_grid(size_mm=14.0, res_mm=0.02):
    """격자 칸 중심 좌표 xs, ys [mm] 와 meshgrid X, Y."""
    n = int(round(size_mm / res_mm))
    xs = (np.arange(n) + 0.5) * res_mm
    ys = (np.arange(n) + 0.5) * res_mm
    X, Y = np.meshgrid(xs, ys)          # 행 = y, 열 = x
    return xs, ys, X, Y


def l_block():
    """L자 윤곽(위에서 본 모양). 비대칭이라 회전·뒤집힘을 확인할 수 있다 (C4)."""
    return unary_union([box(2, 2, 12, 5), box(2, 2, 5, 12)])


def rasterize(poly, height, X, Y):
    """폴리곤 안 = height, 밖 = 0(베드)."""
    shapely.prepare(poly)
    return np.where(shapely.contains_xy(poly, X, Y), height, 0.0)


def apply_similarity(poly, truth: Truth):
    """기준 도심을 중심으로 배율·회전 후 이동."""
    c = poly.centroid
    p = affinity.scale(poly, truth.scale, truth.scale, origin=c)
    p = affinity.rotate(p, truth.rot_deg, origin=c, use_radians=False)
    return affinity.translate(p, truth.shift_x_mm, truth.shift_y_mm)


def make_synthetic(truth: Truth = Truth(), height_mm=2.0, res_mm=0.02, seed=0):
    """(H_ref, H_meas, xs, ys) 반환. H_meas 의 NaN = 측정 안 된 칸."""
    rng = np.random.default_rng(seed)
    xs, ys, X, Y = make_grid(res_mm=res_mm)
    ref_poly = l_block()
    H_ref = rasterize(ref_poly, height_mm, X, Y)

    meas_poly = apply_similarity(ref_poly, truth)
    H = rasterize(meas_poly, height_mm + truth.dz_mm, X, Y)
    H = H + rng.normal(0.0, truth.noise_sigma_mm, H.shape)

    # 엣지 스파이크: 측정 형상의 경계 칸 중 일부에 큰 값을 더한다 (E2 엣지 효과 흉내)
    m = H > height_mm / 2
    edge = m ^ ndimage.binary_erosion(m)
    iy, ix = np.nonzero(edge)
    pick = rng.choice(iy.size, size=min(truth.n_spikes, iy.size), replace=False)
    H[iy[pick], ix[pick]] += rng.choice([-1, 1], size=pick.size) * truth.spike_mm

    H[rng.random(H.shape) < truth.missing_frac] = np.nan
    return H_ref, H, xs, ys


if __name__ == "__main__":
    H_ref, H_meas, xs, ys = make_synthetic()
    print("격자:", H_ref.shape, "간격 0.02 mm")
    print("정답:", asdict(Truth()))
    print("결측 비율: %.2f %%" % (100 * np.isnan(H_meas).mean()))
```

`src/cvlab/registration.py` — 강체 변환(청사진 H4) + 마스크 모멘트 닮음 추정 + 윗면 높이 차
```python
"""registration.py — 정합 관련 함수 (H4 일부, J3 테스트 대상)."""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def rigid_transform(A, B):
    """대응점 A, B (N,3) → B ≈ R @ A + t 를 만족하는 회전 R, 이동 t (Kabsch/SVD, 청사진 H4)."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    ca, cb = A.mean(axis=0), B.mean(axis=0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])   # 거울 반전 방지
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def material_mask(H, threshold_mm):
    """높이 > 기준값 인 칸 = True. NaN 칸은 3×3 이웃 중 유효 칸의 다수결로 채운다
    (마스크 '모양'을 위한 처리일 뿐, 높이 지표에는 NaN 그대로 쓴다)."""
    valid = ~np.isnan(H)
    mat = np.zeros(H.shape, bool)
    mat[valid] = H[valid] > threshold_mm
    k = np.ones((3, 3))
    n_mat = ndimage.convolve(mat.astype(float), k, mode="constant")
    n_val = ndimage.convolve(valid.astype(float), k, mode="constant")
    fill = ~valid & (n_mat > n_val / 2)
    return mat | fill


def _moments(mask, xs, ys):
    iy, ix = np.nonzero(mask)
    x, y = xs[ix], ys[iy]
    area = mask.sum() * (xs[1] - xs[0]) * (ys[1] - ys[0])
    cx, cy = x.mean(), y.mean()
    mu20, mu02 = ((x - cx) ** 2).mean(), ((y - cy) ** 2).mean()
    mu11 = ((x - cx) * (y - cy)).mean()
    theta = 0.5 * np.arctan2(2 * mu11, mu20 - mu02)       # 주축 방향 [rad]
    return area, np.array([cx, cy]), theta


def similarity_from_masks(M_ref, M_meas, xs, ys):
    """두 마스크의 면적·도심·주축으로 닮음 변환(이동, 회전, 배율)을 추정한다.
    반환 dict: shift_x_mm, shift_y_mm (도심 차이), rot_deg, scale."""
    a0, c0, t0 = _moments(M_ref, xs, ys)
    a1, c1, t1 = _moments(M_meas, xs, ys)
    d = np.degrees(t1 - t0)
    d = (d + 90) % 180 - 90                                # 주축은 180° 모호 → ±90° 로
    return {"shift_x_mm": c1[0] - c0[0], "shift_y_mm": c1[1] - c0[1],
            "rot_deg": d, "scale": float(np.sqrt(a1 / a0))}


def flat_top_offset(H_ref, H_meas, M_ref, M_meas, edge_px):
    """평평한 윗면의 높이 차이 = median(측정 윗면) − median(기준 윗면). 경계 edge_px 칸 제외."""
    inner_m = ndimage.binary_erosion(M_meas, iterations=edge_px)
    inner_r = ndimage.binary_erosion(M_ref, iterations=edge_px)
    return float(np.nanmedian(H_meas[inner_m]) - np.median(H_ref[inner_r]))
```

`src/cvlab/metrics.py` — IoU/Dice (청사진 H6)
```python
"""metrics.py — 윤곽 지표 일부 (H6, J3 테스트 대상)."""
import numpy as np


def iou_dice(A, B):
    """A = 기준 마스크, B = 측정 마스크 (bool 배열). (IoU, Dice) 반환."""
    A, B = np.asarray(A, bool), np.asarray(B, bool)
    inter, union = (A & B).sum(), (A | B).sum()
    return inter / union, 2 * inter / (A.sum() + B.sum())
```

`src/cvlab/gcode_parser.py` — 청사진 G1 기초 파서 + 선분 길이
```python
"""gcode_parser.py — 청사진 G1 의 기초 파서 (G2/G3 원호 미지원)."""
import math


def parse_gcode(path):
    pos = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
    abs_xyz, abs_e = True, True
    feature, layer = None, -1
    segments = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            if raw.startswith(";TYPE:"):                       # 경로 종류 주석
                feature = raw[6:].strip()
            if raw.startswith((";LAYER:", ";LAYER_CHANGE")):   # 층 변경 주석
                layer += 1
            line = raw.split(";")[0].strip().upper()           # 주석 제거
            if not line:
                continue
            words = line.split()
            cmd = words[0]
            args = {w[0]: float(w[1:]) for w in words[1:] if len(w) > 1 and w[0] in "XYZE"}
            if cmd == "G90": abs_xyz = True
            elif cmd == "G91": abs_xyz = False
            elif cmd == "M82": abs_e = True
            elif cmd == "M83": abs_e = False
            elif cmd == "G92": pos.update(args)
            elif cmd in ("G0", "G1", "G00", "G01"):
                new = dict(pos)
                for k, val in args.items():
                    if k == "E":
                        new["E"] = val if abs_e else pos["E"] + val
                    else:
                        new[k] = val if abs_xyz else pos[k] + val
                moved_xy = (new["X"], new["Y"]) != (pos["X"], pos["Y"])
                if moved_xy and new["E"] > pos["E"]:              # 압출하며 이동한 선분
                    segments.append({
                        "x0": pos["X"], "y0": pos["Y"], "x1": new["X"], "y1": new["Y"],
                        "z": new["Z"], "de": new["E"] - pos["E"],
                        "layer": layer, "type": feature,
                    })
                pos = new
    return segments


def seg_length(s):
    return math.hypot(s["x1"] - s["x0"], s["y1"] - s["y0"])
```

`src/cvlab/__init__.py` 는 빈 파일(또는 J1에서 만든 한 줄 설명)이면 됩니다.

### 6.3 테스트 파일

`tests/test_gcode_parser.py`
```python
"""G1 파서 테스트: 손으로 쓴 10 mm 정사각형 G코드."""
import pytest

from cvlab.gcode_parser import parse_gcode, seg_length

SQUARE_ABS = """; 손으로 쓴 테스트용 G코드 — 10 mm 정사각형 1층
G21            ; mm 단위
G90            ; 절대 좌표
M82            ; E 절대
G92 E0
;LAYER:0
;TYPE:WALL-OUTER
G0 X0 Y0 Z0.2  ; 공이동 (압출 없음)
G1 X10 Y0 E0.5
G1 X10 Y10 E1.0
G1 X0 Y10 E1.5
G1 X0 Y0 E2.0
G1 E1.2        ; 리트랙션 (E 감소)
G0 X20 Y20     ; 공이동
"""

SQUARE_REL = """G91
M83
;LAYER:0
;TYPE:WALL-OUTER
G1 Z0.2
G1 X10 E0.5
G1 Y10 E0.5
G1 X-10 E0.5
G1 Y-10 E0.5
"""


@pytest.fixture
def write(tmp_path):
    """문자열을 임시 .gcode 파일로 저장해 경로를 돌려주는 도우미."""
    def _w(text, name="t.gcode"):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p
    return _w


def test_square_absolute(write):
    segs = parse_gcode(write(SQUARE_ABS))
    assert len(segs) == 4                                   # 압출 선분만 4개
    assert sum(seg_length(s) for s in segs) == pytest.approx(40.0)
    assert sum(s["de"] for s in segs) == pytest.approx(2.0)  # 리트랙션은 포함 안 됨
    assert {s["layer"] for s in segs} == {0}
    assert {s["type"] for s in segs} == {"WALL-OUTER"}
    assert all(s["z"] == pytest.approx(0.2) for s in segs)


def test_square_relative_gives_same_geometry(write):
    a = parse_gcode(write(SQUARE_ABS, "a.gcode"))
    b = parse_gcode(write(SQUARE_REL, "b.gcode"))
    assert len(b) == 4
    for sa, sb in zip(a, b):
        for k in ("x0", "y0", "x1", "y1", "z"):
            assert sa[k] == pytest.approx(sb[k])


def test_comment_only_and_blank_lines(write):
    assert parse_gcode(write("; only comment\n\n   \n")) == []
```

`tests/test_metrics.py`
```python
"""H6 IoU/Dice 테스트: 절반 겹치는 두 정사각형 → IoU = 1/3, Dice = 1/2."""
import numpy as np
import pytest
import shapely
from shapely.geometry import box

from cvlab.metrics import iou_dice


def test_iou_exact_pixels():
    A = np.zeros((100, 200), bool); A[0:100, 0:100] = True     # 100×100 칸
    B = np.zeros((100, 200), bool); B[0:100, 50:150] = True    # 오른쪽으로 50칸 이동
    iou, dice = iou_dice(A, B)
    assert iou == pytest.approx(1 / 3)
    assert dice == pytest.approx(0.5)


def test_iou_on_mm_grid_matches_geometry():
    """10×10 mm 정사각형 두 개(5 mm 어긋남)를 0.02 mm 격자로 래스터화 → 기하 계산 1/3 과 일치."""
    xs = (np.arange(1000) + 0.5) * 0.02                          # 0~20 mm
    X, Y = np.meshgrid(xs, xs[:600])                             # 0~12 mm
    a, b = box(1, 1, 11, 11), box(6, 1, 16, 11)
    A, B = shapely.contains_xy(a, X, Y), shapely.contains_xy(b, X, Y)
    exact = a.intersection(b).area / a.union(b).area
    assert exact == pytest.approx(1 / 3)
    iou, _ = iou_dice(A, B)
    assert iou == pytest.approx(exact, abs=1e-3)


def test_identical_and_disjoint():
    A = np.zeros((10, 10), bool); A[2:5, 2:5] = True
    assert iou_dice(A, A) == (1.0, 1.0)
    B = np.zeros((10, 10), bool); B[6:9, 6:9] = True
    assert iou_dice(A, B) == (0.0, 0.0)
```

`tests/test_registration.py`
```python
"""H4 rigid_transform 테스트: 알려진 R, t 로 옮긴 점에서 R, t 를 복원."""
import numpy as np
import pytest

from cvlab.registration import rigid_transform


def rot_z(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


@pytest.mark.parametrize("deg", [0.0, 0.5, 30.0, -170.0])
def test_recover_yaw_and_shift(deg):
    rng = np.random.default_rng(1)
    A = rng.uniform(0, 50, (4, 3))                     # 기준 마커 4개 [mm]
    R_true, t_true = rot_z(deg), np.array([0.20, -0.10, 0.0])
    B = A @ R_true.T + t_true
    R, t = rigid_transform(A, B)
    assert np.allclose(R, R_true, atol=1e-9)
    assert np.allclose(t, t_true, atol=1e-9)
    assert np.linalg.det(R) == pytest.approx(1.0)      # 거울 반전 아님


def test_noisy_markers_fre():
    """마커 중심에 σ = 2 µm 노이즈 → 정합 잔차(FRE) RMS 가 수 µm 수준."""
    rng = np.random.default_rng(2)
    A = np.array([[0, 0, 0], [60, 0, 0], [0, 60, 0], [60, 60, 0]], float)
    B = A @ rot_z(0.5).T + [0.2, -0.1, 0] + rng.normal(0, 0.002, A.shape)
    R, t = rigid_transform(A, B)
    fre = np.sqrt(((A @ R.T + t - B) ** 2).sum(axis=1).mean())
    assert fre < 0.005                                 # 5 µm 미만
    yaw = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
    assert yaw == pytest.approx(0.5, abs=0.01)


def test_no_reflection_for_planar_points():
    """점이 모두 한 평면(z=0)에 있어도 det(R)=+1 이어야 함 (거울 반전 방지 D 행렬)."""
    A = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0]], float)
    R, _ = rigid_transform(A, A @ rot_z(10).T)
    assert np.linalg.det(R) == pytest.approx(1.0)
```

`tests/test_synthetic_recovery.py`
```python
"""J3 핵심: 정답을 아는 합성 높이맵에서 이동·회전·배율·높이를 복원하는지 (마일스톤 M3)."""
from dataclasses import replace

import numpy as np
import pytest

from cvlab.registration import flat_top_offset, material_mask, similarity_from_masks
from cvlab.synthetic import Truth, make_synthetic

TOL = {"shift_mm": 0.005, "rot_deg": 0.03, "scale": 0.0005, "dz_mm": 0.002}


def run_recovery(truth, seed):
    H_ref, H_meas, xs, ys = make_synthetic(truth, seed=seed)
    M_ref, M_meas = H_ref > 1.0, material_mask(H_meas, 1.0)
    est = similarity_from_masks(M_ref, M_meas, xs, ys)
    est["dz_mm"] = flat_top_offset(H_ref, H_meas, M_ref, M_meas, edge_px=13)
    return est


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_default_truth_is_recovered(seed):
    t = Truth()                                         # 청사진 J3 기본 조건
    est = run_recovery(t, seed)
    assert est["shift_x_mm"] == pytest.approx(t.shift_x_mm, abs=TOL["shift_mm"])
    assert est["shift_y_mm"] == pytest.approx(t.shift_y_mm, abs=TOL["shift_mm"])
    assert est["rot_deg"] == pytest.approx(t.rot_deg, abs=TOL["rot_deg"])
    assert est["scale"] == pytest.approx(t.scale, abs=TOL["scale"])
    assert est["dz_mm"] == pytest.approx(t.dz_mm, abs=TOL["dz_mm"])


def test_identity_gives_zero():
    t = replace(Truth(), shift_x_mm=0, shift_y_mm=0, rot_deg=0, scale=1.0, dz_mm=0)
    est = run_recovery(t, seed=0)
    assert abs(est["shift_x_mm"]) < TOL["shift_mm"] and abs(est["shift_y_mm"]) < TOL["shift_mm"]
    assert abs(est["rot_deg"]) < TOL["rot_deg"]
    assert abs(est["scale"] - 1) < TOL["scale"]
    assert abs(est["dz_mm"]) < TOL["dz_mm"]


@pytest.mark.parametrize("dz", [+0.05, -0.05])
def test_sign_convention(dz):
    """오차 = 측정 − 기준. 재료 과다(+)면 양수, 부족(−)이면 음수가 나와야 한다 (A1)."""
    est = run_recovery(replace(Truth(), dz_mm=dz), seed=0)
    assert np.sign(est["dz_mm"]) == np.sign(dz)


def test_missing_data_is_nan_not_zero():
    _, H_meas, _, _ = make_synthetic(Truth(), seed=0)
    frac = np.isnan(H_meas).mean()
    assert 0.015 < frac < 0.025                         # 2 % ± 0.5 %p


@pytest.mark.slow
def test_breakdown_is_detected():
    """결측 40 % 에서는 배율 복원이 허용오차를 넘는다 → 한계가 실제로 존재함을 기록."""
    est = run_recovery(replace(Truth(), missing_frac=0.40), seed=0)
    assert abs(est["scale"] - Truth().scale) > TOL["scale"]
```

실행 예시와 기대 출력:
```text
$ python -m pytest -v
tests/test_gcode_parser.py::test_square_absolute PASSED                  [  5%]
tests/test_gcode_parser.py::test_square_relative_gives_same_geometry PASSED [ 10%]
tests/test_gcode_parser.py::test_comment_only_and_blank_lines PASSED     [ 15%]
tests/test_metrics.py::test_iou_exact_pixels PASSED                      [ 20%]
tests/test_metrics.py::test_iou_on_mm_grid_matches_geometry PASSED       [ 25%]
tests/test_metrics.py::test_identical_and_disjoint PASSED                [ 30%]
tests/test_registration.py::test_recover_yaw_and_shift[0.0] PASSED       [ 35%]
tests/test_registration.py::test_recover_yaw_and_shift[0.5] PASSED       [ 40%]
tests/test_registration.py::test_recover_yaw_and_shift[30.0] PASSED      [ 45%]
tests/test_registration.py::test_recover_yaw_and_shift[-170.0] PASSED    [ 50%]
tests/test_registration.py::test_noisy_markers_fre PASSED                [ 55%]
tests/test_registration.py::test_no_reflection_for_planar_points PASSED  [ 60%]
tests/test_synthetic_recovery.py::test_default_truth_is_recovered[0] PASSED [ 65%]
tests/test_synthetic_recovery.py::test_default_truth_is_recovered[1] PASSED [ 70%]
tests/test_synthetic_recovery.py::test_default_truth_is_recovered[2] PASSED [ 75%]
tests/test_synthetic_recovery.py::test_identity_gives_zero PASSED        [ 80%]
tests/test_synthetic_recovery.py::test_sign_convention[0.05] PASSED      [ 85%]
tests/test_synthetic_recovery.py::test_sign_convention[-0.05] PASSED     [ 90%]
tests/test_synthetic_recovery.py::test_missing_data_is_nan_not_zero PASSED [ 95%]
tests/test_synthetic_recovery.py::test_breakdown_is_detected PASSED      [100%]
============================== 20 passed in 1.67s ==============================

$ python -m pytest -q -m "not slow"          # 느린 테스트 제외
19 passed, 1 deselected in 1.25s
```

실패하면 pytest가 이렇게 알려 줍니다 (예: 허용오차를 넘었을 때). `E` 줄에 실제값과 기대값이 나오므로 어느 변형량이 틀렸는지 바로 보입니다.
```text
>       assert abs(est["scale"] - Truth().scale) > TOL["scale"]
E       assert 0.000386089478692786 > 0.0005
```

### 6.4 한계 탐색 — `scripts/sweep_noise.py`

```python
"""sweep_noise.py — 노이즈·결측을 키워 가며 복원이 어디서 무너지는지 찾는다 (J3 절차 5).

실행:  python sweep_noise.py      (PYTHONPATH=src 필요, 또는 pip install -e .)
결과:  화면 표 + results/j3_sweep.csv
"""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from cvlab.registration import flat_top_offset, material_mask, similarity_from_masks
from cvlab.synthetic import Truth, make_synthetic

# 합격 허용오차 (이 문서 7절과 같은 값)
TOL = {"shift_mm": 0.005, "rot_deg": 0.03, "scale": 0.0005, "dz_mm": 0.002}


def recover(truth, seed):
    H_ref, H_meas, xs, ys = make_synthetic(truth, seed=seed)
    M_ref = H_ref > 1.0                              # 높이 2 mm 의 절반을 기준값으로
    M_meas = material_mask(H_meas, 1.0)
    est = similarity_from_masks(M_ref, M_meas, xs, ys)
    dz = flat_top_offset(H_ref, H_meas, M_ref, M_meas, edge_px=13)   # 0.25 mm ≈ 13칸
    err = {
        "shift_mm": max(abs(est["shift_x_mm"] - truth.shift_x_mm),
                        abs(est["shift_y_mm"] - truth.shift_y_mm)),
        "rot_deg": abs(est["rot_deg"] - truth.rot_deg),
        "scale": abs(est["scale"] - truth.scale),
        "dz_mm": abs(dz - truth.dz_mm),
    }
    err["pass"] = all(err[k] <= TOL[k] for k in TOL)
    return err


def main():
    rows = []
    for sigma in [0.005, 0.05, 0.2, 0.4]:
        for miss in [0.02, 0.10, 0.20, 0.30]:
            t = replace(Truth(), noise_sigma_mm=sigma, missing_frac=miss)
            errs = [recover(t, seed) for seed in range(3)]          # 시드 3개
            worst = {k: max(e[k] for e in errs) for k in TOL}
            rows.append({"sigma_mm": sigma, "missing": miss, **worst,
                         "all_pass": all(e["pass"] for e in errs)})
    df = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True)
    df.to_csv("results/j3_sweep.csv", index=False)
    with pd.option_context("display.width", 120, "display.float_format", "{:.5f}".format):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
```

실행 예시 (`PYTHONPATH=src python scripts/sweep_noise.py`, Windows PowerShell은 `$env:PYTHONPATH="src"` 후 실행; J1의 `pip install -e .` 를 했다면 PYTHONPATH 불필요). 값은 시드 3개 중 **최악**값, 약 6초:
```text
 sigma_mm  missing  shift_mm  rot_deg   scale   dz_mm  all_pass
  0.00500  0.02000   0.00059  0.01504 0.00001 0.00003      True
  0.00500  0.10000   0.00061  0.01843 0.00006 0.00003      True
  0.00500  0.20000   0.00078  0.01577 0.00028 0.00004      True
  0.00500  0.30000   0.00100  0.01914 0.00056 0.00004     False
  0.05000  0.02000   0.00059  0.01504 0.00001 0.00029      True
  0.05000  0.10000   0.00061  0.01843 0.00006 0.00027      True
  0.05000  0.20000   0.00078  0.01577 0.00028 0.00043      True
  0.05000  0.30000   0.00100  0.01914 0.00056 0.00045     False
  0.20000  0.02000   0.00062  0.01540 0.00001 0.00115      True
  0.20000  0.10000   0.00064  0.01880 0.00006 0.00103      True
  0.20000  0.20000   0.00078  0.01577 0.00028 0.00171      True
  0.20000  0.30000   0.00100  0.01977 0.00056 0.00179     False
  0.40000  0.02000   0.03575  0.06425 0.00629 0.00908     False
  0.40000  0.10000   0.03329  0.06564 0.00575 0.00800     False
  0.40000  0.20000   0.02998  0.04665 0.00490 0.00996     False
  0.40000  0.30000   0.02623  0.04283 0.00404 0.00865     False
```

**결과 해석**
- 기본 조건(σ 5 µm, 결측 2 %)에서 오차: 이동 0.6 µm, 회전 0.015°, 배율 1×10⁻⁵, 높이 0.03 µm → 허용오차 대비 여유는 회전 2배, 이동 8배, 배율·높이 40배 이상. **M3 기준 충족.**
- 회전 오차 0.015°는 노이즈가 아니라 **격자 양자화**(경계가 0.02 mm 칸 단위로 끊김) 때문입니다. 노이즈를 줄여도 줄지 않습니다. 이 값이 마스크 방식의 바닥 한계입니다.
- **결측률이 먼저 무너집니다**: 30 %에서 배율 오차 5.6×10⁻⁴ 로 허용오차(5×10⁻⁴) 초과. 무작위 결측이 몰린 곳은 다수결로도 채워지지 않아 면적이 줄기 때문입니다. 실측의 가림(E2)은 무작위가 아니라 **벽 옆에 띠 모양으로 몰리므로** 더 불리합니다 → 실측 결측률이 10 %를 넘는 시편은 배율 결과에 경고를 붙입니다.
- 높이 노이즈는 σ = 0.2 mm(블록 높이의 10 %)까지 버팁니다. 마스크 기준값(1.0 mm)이 노이즈보다 훨씬 크기 때문입니다. σ = 0.4 mm에서는 베드 칸이 마스크로 잘못 들어와 전부 실패합니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 파서 | `test_gcode_parser.py` | 선분 4개, 길이 합 40 ± 1e-9 mm, ΣΔE 2.0, 절대·상대 동일 |
| IoU | `test_metrics.py` | 픽셀판 IoU = 1/3, Dice = 1/2 (정확), mm 격자판 \|IoU − 1/3\| ≤ 0.001 |
| 강체 변환 | `test_registration.py` | 노이즈 없음: R, t 오차 ≤ 1e-9. σ 2 µm: FRE < 5 µm, yaw 오차 ≤ 0.01° |
| **합성 복원 (M3)** | `test_synthetic_recovery.py` 시드 3개 | 이동 ≤ **0.005 mm**, 회전 ≤ **0.03°**, 배율 ≤ **5×10⁻⁴**, 높이 ≤ **0.002 mm** (3/3 시드) |
| 부호 규칙 | `test_sign_convention` | +0.05 → 양수, −0.05 → 음수 |
| 결측 표현 | `test_missing_data_is_nan_not_zero` | NaN 비율 1.5–2.5 % |
| 한계 확인 | `sweep_noise.py` | 실패 지점이 표에 존재(결측 30 % 또는 σ 0.4 mm), 실측 조건 대비 2배 이상 여유 |
| 속도 | `python -m pytest` | 전체 < 5 s (W12 기준 1.7 s) |
| 회귀 방지 | 커밋 전 실행 기록 | W12 이후 main 브랜치의 모든 커밋에서 0 failed |
| 실제 G코드 확장 | 8단계 | E3 시편 1종 이상에서 같은 허용오차 통과 (W14까지, M4 전) |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 정답 생성과 복원에 같은 함수를 씀 | 버그가 있어도 양쪽이 똑같이 틀려서 통과 | 생성은 shapely 폴리곤 변형, 복원은 영상 모멘트처럼 **다른 경로**로 계산 |
| 대칭 형상(정사각형)으로만 테스트 | X·Y 뒤바뀜, 180° 회전 버그를 못 잡음 | L자 등 비대칭 형상 (C4) |
| `imshow` 에 `origin="lower"` 누락 | 그림에서 Y축이 뒤집혀 보여 "회전 방향이 반대"로 오해 | 높이맵 그림은 항상 `origin="lower"` + `extent` (mm) |
| 허용오차를 결과 보고 정함 | 테스트가 무의미 (무엇이든 통과) | 허용오차는 4절처럼 **물리적 근거로 먼저** 정하고, 결과가 안 맞으면 코드를 고침 |
| 시드 1개로만 테스트 | 운 좋은 시드에서만 통과 | 시드 ≥ 3개 parametrize |
| 결측을 0으로 표시 | 높이 오차가 −2 mm로 계산되어 평균이 크게 음수 | 결측은 항상 NaN, 지표에서는 `~np.isnan` 으로 제외 |
| 실수를 `==` 로 비교 | `0.30000000000000004 != 0.3` 으로 실패 | `pytest.approx(값, abs=허용오차)` |
| 테스트 파일 이름이 `tests_parser.py` | pytest가 찾지 못해 "no tests ran" | `test_` 로 시작 |
| `ModuleNotFoundError: cvlab` | 테스트 import 실패 | `pytest.ini` 의 `pythonpath = src` 또는 `pip install -e .` |
| 테스트가 실제 데이터 파일에 의존 | 다른 PC에서 실패 | 테스트 데이터는 코드로 생성하거나 `tmp_path` 에 작성 |
| 느린 테스트를 매번 실행 | 30초 이상 걸려 아무도 안 돌림 | `@pytest.mark.slow` 분리, 매 커밋은 `-m "not slow"` |
| 알고리즘을 바꾸고 테스트를 안 돌림 | 다른 지표가 조용히 깨짐 | 커밋 전 pytest 필수 규칙 (9단계) |

## 9. 위험 요소

- **합성 데이터가 너무 깨끗함**: 실제 측정에는 반투명 침투(E1), 띠 모양 가림(E2), 스테이지 직진도 오차(C1)처럼 **무작위가 아닌 계통 오차**가 있습니다. 합성 테스트 통과는 "코드가 맞다"는 뜻일 뿐 "측정이 맞다"는 뜻이 아닙니다. 측정 검증은 D5·I1·I2·I3이 담당합니다.
- **허용오차가 격자 양자화와 가까움**: 회전 오차의 바닥(0.015°)이 허용오차(0.03°)의 절반입니다. 격자를 0.04 mm로 거칠게 하면 통과하지 못할 수 있습니다. 격자를 바꾸면 이 테스트를 반드시 다시 돌립니다.
- **마스크 모멘트법의 한계**: 결측이 한쪽에 몰리면 도심이 치우칩니다(무작위 30 %에서 이미 배율 실패). 실측에서는 결측 패턴을 G4 가림 예측과 비교해 정합 신뢰도를 판단하고, H4 본 정합(기준 마커 + ECC/ICP)으로 교체합니다.
- **G1 파서 테스트 범위**: 기초 파서는 G2/G3 원호, 줄 번호(`N…`), `G20` inch 단위를 처리하지 않습니다. 슬라이서 설정이 바뀌어 원호가 나오면 테스트를 먼저 추가하고 파서를 확장합니다.
- **일정**: W11–12는 C3 기준 마커 설치, H4 정합과 겹칩니다. M3 실패 시 H5 이후(W13~) 지표 작업이 의미를 잃으므로 J3을 H4보다 먼저 끝냅니다.

## 10. 기록 양식

**M3 판정 기록** (`docs/milestones/M3.md`)

| 항목 | 정답 | 허용오차 | 시드 0 | 시드 1 | 시드 2 | 판정 |
|---|---|---|---|---|---|---|
| 이동 X [mm] | 0.20 | ±0.005 | | | | |
| 이동 Y [mm] | −0.10 | ±0.005 | | | | |
| 회전 [°] | 0.5 | ±0.03 | | | | |
| 배율 | 0.996 | ±0.0005 | | | | |
| 높이 [mm] | +0.03 | ±0.002 | | | | |
| git 커밋 | | | | | | |
| 확인자 / 날짜 | | | | | | |

**한계 탐색 결과 요약** (`results/j3_sweep.csv` 에서 발췌)
```yaml
date: 2026-12-24
git_commit: ""
grid_mm: 0.02
first_failure:
  missing_frac: 0.30      # 이 결측률에서 처음 실패한 지표: scale
  noise_sigma_mm: 0.4     # 이 노이즈에서 처음 실패
measured_conditions:      # 실측 값 (F1, E2에서 가져옴)
  noise_sigma_mm: null
  missing_frac: null
safety_factor_ok: null    # 실측 조건이 한계의 1/2 이하인가
```

**테스트 추가 이력**

| 날짜 | 테스트 이름 | 잡은 버그 / 목적 | 관련 요소 | 작성자 |
|---|---|---|---|---|
| | | | | |

## 11. 참고 자료

- pytest 공식 문서 (docs.pytest.org) — "Get Started", "How to use fixtures"(`tmp_path`), "How to parametrize", "Working with custom markers", `pytest.approx`
- Python 공식 문서 — `unittest`, `dataclasses`
- NumPy 문서 — `numpy.random.Generator`, `numpy.nanmedian`
- Shapely 2.x 문서 — `shapely.affinity`, `shapely.contains_xy`, `shapely.prepare`
- SciPy 문서 — `scipy.ndimage.binary_erosion`, `scipy.ndimage.convolve`
- Arun, Huang, Blostein, "Least-Squares Fitting of Two 3-D Point Sets", IEEE TPAMI (1987) — SVD 강체 변환
- 영상 모멘트(image moments)와 주축 방향: Gonzalez & Woods, *Digital Image Processing* (표현과 기술 장)
