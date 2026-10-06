# E2. 가림(Occlusion)과 엣지 효과 — 측정할 수 없는 곳과 믿을 수 없는 곳

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: E. 측정 대상(시편)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 보통 |
| 트랙 | 실험·품질 |
| 선행 요소 | [B2 기하 배치](../B-optics/B2-geometry.md) (θ, 배치 방식) · [D2 레이저 평면](../D-calibration/D2-laser-plane.md) (실제 θ 값) · [G3 마스크·높이맵](../G-reference/G3-mask-heightmap.md) (기준 높이맵) · [G4 비교 영역](../G-reference/G4-evaluation-masks.md) (M_valid, M_edge 정의) · [H1 점→격자](../H-analysis/H1-gridding.md) |
| 후행 요소 | [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [E3 시편 설계](./E3-test-artifact.md) (형상 간격 규칙) · [I1 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | M4 (시편 1개 전체 파이프라인 완주) — 평가 마스크 `M_eval` 에 들어가는 `M_valid`(가림 제외)와 `M_edge` 를 확정 |

---

## 1. 목적

위에서 한 방향으로 비스듬히 보는 삼각측량은 **구조적으로 볼 수 없는 곳(가림)**과 **보이지만 값이 부정확한 곳(엣지)**을 만듭니다. 이 요소의 목적은 다음과 같습니다.

1. 기준 높이맵(G3)과 삼각측량 각도 θ로 **가림 영역을 미리 예측**하는 코드를 만들고, 실제 측정의 결측과 비교해 **"예상된 결측"과 "예상 밖 결측(반사·저신뢰)"을 구분**합니다.
2. 단차 경계에서 제외할 **엣지 띠 폭을 수치로 확정**합니다 (청사진 권장 출발값: 선폭/2 + 2·δx = 0.21 + 0.028 ≈ **0.25 mm**, J2 `masks.edge_band_mm`).
3. 높이 지표(H5)에서 가림·엣지가 빠졌을 때 **평가 영역이 전체의 몇 %인지** 항상 보고하는 체계를 만듭니다.
4. E3 시편 설계에 **형상 방향·간격 규칙**을 넘겨줍니다.

## 2. 배경 지식 (초보자용)

### 2.1 두 가지 그림자

권장 배치(B2 (a)): **레이저는 수직(위→아래)**, 카메라는 레이저와 **θ 기울어져** Y 쪽에서 비스듬히 봅니다. 레이저 선은 X 방향, 스캔은 Y 방향입니다.

```
       옆에서 본 모습 (Y-Z 단면)                      용어
   카메라                                    - 레이저 그림자: 빛이 닿지 않음
     \  θ                                    - 카메라 그림자: 빛은 닿지만
      \       레이저 |                          카메라에서 안 보임
       \             |                       
        \    ┌───────┤ 높이 h                 이 배치에서는 레이저가 수직이라
   ──────\───┘       └──────────── 바닥      레이저 그림자는 작고(팬 각도만큼),
              ◀ 그림자 ▶                      카메라 그림자가 주된 문제입니다.
          (벽의 반대쪽, 길이 h·tanθ)
```

- **카메라 그림자 길이 = h · tanθ.** θ = 30° 에서 tan30° = 0.577 → 높이 2 mm 벽 뒤로 **1.155 mm**가 안 보입니다.
- **홈·슬롯·구멍**: 폭 w, 깊이 h인 홈은 바닥 중 `w − h·tanθ` 만큼만 보입니다. 즉 **w > h·tanθ 일 때만 바닥까지 측정**됩니다 (청사진 E2 규칙).
- **레이저 팬 그림자**: 레이저 선은 한 점에서 부채꼴로 퍼지므로 FOV 가장자리에서는 광선이 약간 기울어 있습니다. 레이저에서 수평으로 d 만큼 떨어진 곳의 기울기는 d / WD_laser 입니다. 예: d = 8 mm, WD = 150 mm, 벽 높이 2 mm → 그림자 2·8/148 ≈ **0.108 mm**. 작지만 0은 아닙니다.
- **방향이 중요**: 카메라가 Y-Z 평면 안에 있으므로 카메라 그림자는 **Y 방향으로만** 생깁니다. 그래서 **Y 방향으로 길게 놓인 홈·벽**(홈의 폭이 X 방향)은 카메라 그림자가 거의 없습니다. 이 성질을 E3 설계에 이용합니다.

### 2.2 "누적 최댓값"으로 그림자 계산하기

높이맵의 한 열(X 고정)을 따라 Y 방향으로 생각합니다. 점 (y, h)에서 카메라 쪽으로 수평 s 만큼 가면 시선은 s/tanθ 만큼 올라갑니다. 그래서

```
g(y) = h(y) + y / tanθ        (카메라가 −Y 쪽에 있을 때)
점 y가 보인다  ⇔  g(y) ≥ (y 보다 카메라 쪽에 있는 모든 점의 g 중 최댓값)
```

"앞에서부터의 최댓값"은 numpy의 `np.maximum.accumulate` 한 줄로 계산됩니다. 반복문 없이 100만 칸 높이맵도 1초 안에 끝납니다.

### 2.3 엣지 효과 — 경계에서 값이 이상해지는 이유

1. **혼합 픽셀**: 레이저 선은 폭(30~100 µm)이 있어서, 단차 경계에 걸치면 위·아래 면 빛이 한 열에 섞여 중심이 중간 높이로 나옵니다 → 경계가 **둥글게 뭉개짐**.
2. **스파이크**: 경계에서 반사·회절로 피크가 2개 생기면 엉뚱한 피크가 선택되어 **튀는 값**이 생깁니다.
3. **다중 반사**: 오목한 안쪽 모서리(벽과 바닥이 만나는 곳)에서 빛이 벽에 한 번 더 반사되어 **가짜 점**이 생깁니다. 특히 예측 그림자 안에 값이 있으면 거의 확실히 가짜입니다.
4. **실제 비드 형상**: FDM 비드의 가장자리는 둥근 모양(반지름 ≈ 층높이/2)이라, G코드 기준(G2 사각+반원 모델)과 경계 근처에서 원래 차이가 큽니다.

→ 그래서 **높이 지표(H5)는 경계에서 일정 폭을 빼고 계산**하고, **경계 자체는 윤곽 지표(H6)**로 따로 평가합니다 (G4: `M_eval = M_ref ∧ M_valid ∧ M_type ∧ ¬M_edge`).

### 2.4 보간 금지

측정이 안 된 곳(NaN)을 주변 값으로 채우고 오차를 계산하면, **측정하지 않은 값을 측정값처럼 보고**하게 됩니다. 시각화용 지도에만 보간을 쓰고 지표 계산에는 쓰지 않습니다 (H1).

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일명 | 비고 |
|---|---|---|---|
| 입력 | 기준 높이맵 | `data/processed/<시편>/H_ref.npy` + 격자 원점·간격 | G3. 재료 없는 곳은 바닥 높이 0으로 채워 사용 |
| 입력 | 측정 높이맵 | `data/processed/<scan_id>/H_meas.npy` | H1~H4 후 {G} 좌표계 |
| 입력 | 실제 θ, 레이저 위치·높이 | `config/calibration/<CAL-ID>/laser_plane.yaml` | D2 결과에서 계산 (설계값 30°를 그대로 쓰지 않음) |
| 입력 | 선폭, δx | `config/default.yaml` (`gcode.line_width_mm`, B1 계산) | 엣지 띠 폭 계산 |
| 산출물 | 가림·엣지 모듈 | `src/cvlab/masks.py` 의 `camera_visible()`, `laser_lit()`, `edge_band()` | 6절 코드 |
| 산출물 | 예측 그림자·엣지 마스크 | `data/processed/<scan_id>/E2_masks.npz` (`M_shadow_pred`, `M_edge`, `xs`, `ys`, `res`, `theta_deg`) | 불리언 배열 |
| 산출물 | 결측 대조표 | `results/<scan_id>/E2_missing_table.csv` | 예측 보임/그림자 x 측정 있음/없음 (%) |
| 산출물 | 엣지 띠 민감도표 | `results/E2/E2_band_sensitivity.csv` + `.png` | 띠 폭별 n, mean, RMS, P95 |
| 산출물 | 그림자 검증 기록 | `results/E2/E2_shadow_validation.csv` | E3 시편 단차·슬롯에서 예측 vs 실측 길이 |
| 산출물 | 설정값 확정 | `config/default.yaml` 의 `masks.edge_band_mm`, `masks.shadow_dilate_px` | 결정 근거를 주석으로 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 가림 대응 방식 | ① 180° 돌려 2회 스캔 ② 카메라 2대 ③ 제외하고 비율 보고 | **③ 기본 + 필요한 시편만 ①** | ③은 추가 장비·정합 오차가 없음. 합성 장면에서 1회 92.2 % → 2회 98.3 %로 늘지만, 두 스캔을 정합(H4)하는 새 오차가 생김 |
| 그림자 예측 사용 | 사용 / 미사용(측정 NaN만 사용) | **사용** | 예상 밖 결측과 그림자 속 가짜 점을 구분할 수 있음 (G4 "가림 영역 예측") |
| 그림자 속 측정값 | 유지 / 제거 | **제거** (예측 그림자를 2칸 넓혀서 그 안의 값은 `M_valid` 에서 제외) | 다중 반사 가짜 점일 가능성이 높음. θ 오차로 경계가 1~2칸 어긋날 수 있어 여유를 둠 |
| θ 값 출처 | 설계값 / 캘리브레이션 값 | **D2 캘리브레이션 결과** | 설계 30°가 실제 28°이면 2 mm 단차 그림자 길이가 1.155 → 1.063 mm로 달라짐 |
| 엣지 판정 문턱 (step_mm) | 0.05 / **0.1** / 0.2 mm | **0.1 mm (= 층 높이 0.2 mm의 절반)** | 층 하나 높이 차이도 경계로 잡되, 노이즈(5 µm 수준)는 무시 |
| 엣지 띠 폭 | 0.15 / **0.25** / 0.35 mm | **0.25 mm 출발 → 민감도 분석으로 확정** | 선폭/2 + 2·δx = 0.238 mm. 실제 비드 둥근 가장자리·선 두께에 따라 넓혀야 할 수 있음 |
| 띠 폭 확정 규칙 | – | **띠를 넓혀도 mean·RMS 변화가 1 µm 미만이 되는 가장 작은 폭** (안정 구간 시작점) + 0.05 mm 여유 | 너무 넓히면 평가 면적만 줄고, 너무 좁으면 엣지 값이 섞임 |
| 시편 형상 방향 (E3로 전달) | – | **좁은 홈·얇은 벽은 Y(스캔) 방향으로 길게**, 단차 벽도 Y와 나란히 | 카메라 그림자가 Y 방향으로만 생기므로 |
| 형상 간 간격 (E3로 전달) | – | **Y 방향 간격 ≥ h·tanθ + 2 x 엣지 띠** (h = 앞 형상 높이) | 그림자가 이웃 형상의 평가 영역을 덮지 않게 |
| 보고 항목 | – | **평가 영역 비율 %, 예상 밖 결측 %, 제거한 그림자 속 점 수** | G4 "평가 영역이 전체의 몇 %인지" 규칙 |

## 5. 수행 절차

1. **코드 준비 (1~2일 차)**
   - [ ] 6.1 `e2_occlusion.py` 를 실행해 합성 장면에서 이론값과 일치하는지 확인 (그림자 길이 오차 ≤ 1칸 = 0.02 mm)
   - [ ] 세 함수를 `src/cvlab/masks.py` 로 옮기고 J3 단위 테스트 추가: "높이 2 mm 블록, θ = 30° → 카메라 그림자 1.155 ± 0.02 mm"
2. **실제 기하값 확보 (2일 차)**
   - [ ] D2 결과에서 θ(레이저 평면 법선과 카메라 광축 사이 각), 레이저 출사점의 X 위치와 높이(WD_laser)를 계산해 YAML에 기록
   - [ ] 카메라가 −Y 쪽인지 +Y 쪽인지 **실물로 확인**하고 `camera_side` 로 기록 (반대로 넣으면 그림자가 벽 반대편에 예측됨)
3. **그림자 예측 검증 (3~4일 차, E3 시편 사용)**
   - [ ] E3 계단 블록(단차 벽이 X와 나란하게 일부러 90° 돌려 놓고)과 슬롯을 스캔
   - [ ] 단차 높이 0.2 / 0.4 / 1.0 / 2.0 mm 각각에서 실측 그림자 길이(NaN 띠 폭)를 열 20개에서 측정, 평균
   - [ ] 예측 `h·tanθ` 와 비교 → `E2_shadow_validation.csv`. 기준: 차이 ≤ 0.05 mm 또는 ≤ 10 %
   - [ ] 차이가 크면 θ 값, `camera_side`, 높이맵 격자 방향(행 = Y)을 차례로 확인
4. **결측 대조표 (4일 차)**
   - [ ] 6.2 `e2_check.py` 방식으로 스캔마다 4칸 대조표 작성
   - [ ] **예상 밖 결측 > 2 %** 이면 원인 조사: 광택·포화(E1), 저신뢰 점 제거 문턱(F1), 초점 밖(B2) 순서로 확인
   - [ ] 예측 그림자 속 측정값 수를 기록하고 `M_valid` 에서 제외
5. **엣지 띠 폭 확정 (5~6일 차)**
   - [ ] 실제 스캔 3개(E3 시편의 평면 패드·계단 면 포함)에 대해 띠 폭 0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50 mm로 H5 지표 계산
   - [ ] mean·RMS가 안정되는 가장 작은 폭을 찾고 0.05 mm 여유를 더해 확정 (예: 안정 시작 0.20 → 0.25 mm)
   - [ ] 확정값을 `config/default.yaml` 의 `masks.edge_band_mm` 에 넣고 근거를 주석으로 기록
   - [ ] 띠 폭을 ±0.1 mm 바꿨을 때의 지표 변화를 H2·H5 민감도 분석 결과로 함께 보고
6. **2회 스캔 필요성 판단 (7일 차)**
   - [ ] E3 시편에서 1회 스캔 평가 영역 비율 계산. 형상별 비율이 50 % 미만인 형상이 주요 지표에 쓰이면, 해당 시편만 180° 돌린 2회 스캔을 검토
   - [ ] 2회 스캔 시 두 스캔 모두 기준 마커로 {G}에 정합(H4)한 뒤, 겹치는 곳은 두 값의 평균이 아니라 **각각 유효한 쪽**을 쓰고 둘 다 유효하면 차이를 기록(정합 품질 지표)
7. **보고 체계 반영 (8일 차)**
   - [ ] H5 결과표에 `eval_area_pct`, `unexpected_missing_pct`, `shadow_points_removed` 열 추가 (J4 리포트)

## 6. Python 구현

### 6.1 그림자 예측 + 엣지 띠 + 효과 확인 (`e2_occlusion.py`)

합성 장면(20 x 20 mm, 격자 0.02 mm): 높이 2 mm 블록 1개와, 폭 0.4/0.8/1.2/1.6 mm·깊이 1 mm 슬롯 4개가 있는 판. 슬롯은 **일부러 X 방향으로 길게**(폭이 Y 방향) 놓아 카메라 그림자가 최대가 되게 했습니다.

```python
"""E2 가림(그림자) 예측 + 엣지 띠 마스크 생성 + 엣지 띠의 효과 확인 (합성 데이터)
실행: python e2_occlusion.py   -> 결과 출력 + E2_masks.npz 저장

좌표 약속 (B2 권장 배치 (a): 레이저 수직 + 카메라 경사)
  - 높이맵 H[iy, ix] : 행 = Y(스캔 방향), 열 = X(레이저 선 방향), 단위 mm, 바닥(베드) = 0
  - 레이저 평면 = X-Z 평면. 카메라는 Y-Z 평면 안에서 레이저와 θ 각도로 기울어져 있음
  - camera_side="-y" : 카메라가 Y가 작은 쪽에 있음 -> 벽의 +Y 쪽 뒤에 카메라 그림자가 생김
"""
import numpy as np
from scipy import ndimage


def camera_visible(H, res, theta_deg, camera_side="-y"):
    """카메라에서 보이는 칸 = True.
    원리: 점 (y, h)에서 카메라 쪽으로 수평 s 만큼 가면 시선 높이는 s/tanθ 만큼 올라간다.
    g = h + y/tanθ 로 두면 '앞쪽(카메라 쪽) 어떤 점의 g 가 내 g 보다 크면 가려짐'.
    -> 누적 최댓값(cummax) 한 번으로 계산 끝."""
    cot = 1.0 / np.tan(np.radians(theta_deg))
    Hc = H if camera_side == "-y" else H[::-1]          # +y 쪽 카메라는 뒤집어서 같은 식 사용
    y = np.arange(Hc.shape[0])[:, None] * res
    g = Hc + y * cot
    vis = g >= np.maximum.accumulate(g, axis=0) - 1e-9
    return vis if camera_side == "-y" else vis[::-1]


def laser_lit(H, xs, res, x_laser, wd_laser):
    """레이저가 닿는 칸 = True. 레이저는 x_laser 위 높이 wd_laser 에서 부채꼴(팬)로 퍼짐.
    수직에서 벗어난 만큼(팬 각도) X 방향으로 기울어진 광선이 벽에 막히는지 확인."""
    lit = np.ones(H.shape, bool)
    dist = np.abs(x_laser - xs)[None, :]                # 각 열의 레이저까지 수평 거리
    step = np.sign(x_laser - xs).astype(int)[None, :]   # 레이저 쪽으로 가는 방향 (+1/-1)
    slope = (wd_laser - H) / np.maximum(dist, 1e-9)     # 수평 1 mm 당 광선 높이 증가
    kmax = int(np.ceil(np.nanmax(H) * np.max(dist) / (wd_laser - np.nanmax(H)) / res)) + 1
    ix = np.arange(H.shape[1])[None, :].repeat(H.shape[0], 0)
    iy = np.arange(H.shape[0])[:, None].repeat(H.shape[1], 1)
    for k in range(1, kmax + 1):                        # 레이저 쪽으로 한 칸씩 걸어감
        j = np.clip(ix + k * step, 0, H.shape[1] - 1)
        ray_h = H + k * res * slope
        lit &= ~((H[iy, j] > ray_h + 1e-9) & (k * res < dist))
    return lit


def edge_band(H, res, band_mm, step_mm=0.1):
    """높이가 step_mm 이상 급변하는 경계에서 band_mm 이내인 칸 = True (M_edge)"""
    d = np.zeros(H.shape, bool)
    dy = np.abs(np.diff(H, axis=0)) > step_mm
    dx = np.abs(np.diff(H, axis=1)) > step_mm
    d[:-1] |= dy; d[1:] |= dy; d[:, :-1] |= dx; d[:, 1:] |= dx   # 단차 양쪽 칸 모두 표시
    dist = ndimage.distance_transform_edt(~d) * res             # 가장 가까운 경계까지 거리 mm
    return dist <= band_mm


def make_scene(res):
    """20 x 20 mm 합성 장면: 블록 1개 + Y 방향으로 늘어선 슬롯 4개가 있는 판"""
    xs = np.arange(0, 20, res) + res / 2
    ys = np.arange(0, 20, res) + res / 2
    X, Y = np.meshgrid(xs, ys)
    H = np.zeros(X.shape)
    H[(X > 2) & (X < 8) & (Y > 2) & (Y < 8)] = 2.0              # 블록 A, 높이 2 mm
    plate = (X > 11) & (X < 18) & (Y > 2) & (Y < 18)
    H[plate] = 2.0
    slots, y0 = [], 4.0
    for w in [0.4, 0.8, 1.2, 1.6]:                               # X 방향으로 긴 홈 (폭은 Y 방향)
        H[plate & (Y > y0) & (Y < y0 + w)] = 1.0                 # 깊이 1 mm
        slots.append((w, y0)); y0 += w + 2.5
    return H, xs, ys, slots


if __name__ == "__main__":
    res, theta = 0.02, 30.0
    H, xs, ys, slots = make_scene(res)
    tan = np.tan(np.radians(theta))

    vis1 = camera_visible(H, res, theta, "-y")
    vis2 = vis1 | camera_visible(H, res, theta, "+y")             # 180° 돌려 한 번 더 스캔
    lit = laser_lit(H, xs, res, x_laser=10.0, wd_laser=150.0)
    meas1, meas2 = vis1 & lit, vis2 & lit

    # (1) 블록 A 뒤(+Y 쪽) 카메라 그림자 길이: 이론 h·tanθ
    col = np.argmin(np.abs(xs - 5.0))
    behind = (ys > 8) & ~vis1[:, col]
    print(f"[카메라 그림자] 이론 {2 * tan:.3f} mm / 계산 {behind.sum() * res:.3f} mm")

    # (2) 레이저 팬 그림자: 블록 A 왼쪽(x<2), 이론 h·(x_L-x)/(WD-h)
    row = np.argmin(np.abs(ys - 5.0))
    sh = (xs < 2) & ~lit[row]
    print(f"[레이저 그림자] 이론 {2 * 8 / 148:.3f} mm / 계산 {sh.sum() * res:.3f} mm")

    # (3) 슬롯 바닥이 보이는 폭: 이론 max(0, w - h·tanθ), 깊이 h = 1 mm
    col = np.argmin(np.abs(xs - 14.5))
    for w, y0 in slots:
        inside = (ys > y0) & (ys < y0 + w)
        seen = (meas1[:, col] & inside).sum() * res
        print(f"[슬롯 w={w:.1f}] 이론 {max(0, w - 1.0 * tan):.3f} mm / 계산 {seen:.3f} mm")

    # (4) 측정 가능 비율
    print(f"[측정 가능 비율] 1회 스캔 {100 * meas1.mean():.2f} % / 양방향 2회 {100 * meas2.mean():.2f} %")

    # (5) 엣지 띠 폭 = 선폭/2 + 2·δx = 0.21 + 2*0.0138 -> 0.25 mm 로 올림 (J2 edge_band_mm)
    band = 0.42 / 2 + 2 * 0.0138
    M_edge = edge_band(H, res, band_mm=0.25)
    print(f"[엣지 띠] 계산 폭 {band:.3f} mm -> 사용 0.25 mm, 전체의 {100 * M_edge.mean():.1f} %")

    # (6) 엣지 띠 효과: 합성 측정 = 기준 + 블록 윗면 +10 µm(재료 과다) + 경계 뭉개짐 + 노이즈 + 스파이크
    rng = np.random.default_rng(42)
    H_meas = ndimage.gaussian_filter(H, sigma=1.5)               # 혼합 픽셀로 경계가 뭉개짐
    H_meas[H >= 2.0] += 0.010
    H_meas += rng.normal(0, 0.005, H.shape)
    edge_px = np.argwhere(edge_band(H, res, band_mm=0.04))
    pick = edge_px[rng.random(len(edge_px)) < 0.02]
    H_meas[pick[:, 0], pick[:, 1]] += rng.choice([-0.3, 0.3], len(pick))  # 가짜 튀는 값
    H_meas[~meas1] = np.nan                                      # 가려진 곳은 측정값 없음
    M_ref = H > 0
    M_valid = ~np.isnan(H_meas)
    top = H >= 2.0                                               # 윗면 2 mm 영역만 평가
    for name, m in [("엣지 띠 미적용", M_ref & M_valid & top),
                    ("엣지 띠 적용  ", M_ref & M_valid & top & ~M_edge)]:
        e = (H_meas - H)[m]
        print(f"[{name}] n={e.size:7d} mean={1000 * e.mean():+6.1f} µm "
              f"RMS={1000 * np.sqrt((e ** 2).mean()):6.1f} µm  P95={1000 * np.percentile(abs(e), 95):6.1f} µm")
    np.savez_compressed("E2_masks.npz", M_shadow_pred=~meas1, M_edge=M_edge,
                        xs=xs, ys=ys, res=res, theta_deg=theta)
```

**실행 예시와 기대 출력** (약 1초)

```
$ python e2_occlusion.py
[카메라 그림자] 이론 1.155 mm / 계산 1.140 mm
[레이저 그림자] 이론 0.108 mm / 계산 0.100 mm
[슬롯 w=0.4] 이론 0.000 mm / 계산 0.000 mm
[슬롯 w=0.8] 이론 0.223 mm / 계산 0.240 mm
[슬롯 w=1.2] 이론 0.623 mm / 계산 0.640 mm
[슬롯 w=1.6] 이론 1.023 mm / 계산 1.040 mm
[측정 가능 비율] 1회 스캔 92.16 % / 양방향 2회 98.25 %
[엣지 띠] 계산 폭 0.238 mm -> 사용 0.25 mm, 전체의 15.6 %
[엣지 띠 미적용] n= 300000 mean=  -7.2 µm RMS=  90.0 µm  P95=  41.9 µm
[엣지 띠 적용  ] n= 227356 mean= +10.0 µm RMS=  11.2 µm  P95=  18.2 µm
```

**출력 읽는 법**
- 그림자 길이·슬롯 바닥 폭이 이론값과 **격자 1칸(0.02 mm) 이내**로 일치합니다. 차이는 격자 양자화 때문입니다.
- 폭 0.4 mm 슬롯(깊이 1 mm)은 0.4 < 0.577 이므로 바닥이 전혀 안 보입니다 → 이런 슬롯은 **높이가 아니라 윤곽(폭)으로만** 평가합니다.
- 정답은 "윗면 +10 µm(재료 과다)". 엣지 띠를 안 빼면 평균이 **−7.2 µm로 부호까지 뒤집히고** RMS가 90 µm로 부풀어 오릅니다. 엣지 띠를 빼면 +10.0 µm를 정확히 되찾습니다. 엣지 띠가 왜 필요한지 보여 주는 핵심 결과입니다.

### 6.2 결측 대조표 + 엣지 띠 민감도 (`e2_check.py`)

6.1 파일과 같은 폴더에 두고 실행합니다. 일부러 두 가지 "사고"를 넣었습니다: ① 블록 위 정반사로 생긴 원형 결측(예상 밖 결측), ② 그림자 속 가짜 점 5 %(다중 반사).

```python
"""E2 (2) 엣지 띠 폭 민감도 + '예측 그림자 vs 실제 결측' 대조표
실행: python e2_check.py    (같은 폴더에 e2_occlusion.py 가 있어야 함)
"""
import numpy as np
import pandas as pd
from scipy import ndimage
from e2_occlusion import make_scene, camera_visible, laser_lit, edge_band

res, theta = 0.02, 30.0
H, xs, ys, slots = make_scene(res)
pred_ok = camera_visible(H, res, theta, "-y") & laser_lit(H, xs, res, 10.0, 150.0)

# ---- 합성 측정 높이맵 (e2_occlusion.py 와 같은 방식) + 두 가지 '사고'를 일부러 넣음 ----
rng = np.random.default_rng(7)
H_meas = ndimage.gaussian_filter(H, 1.5) + rng.normal(0, 0.005, H.shape)
H_meas[H >= 2.0] += 0.010                                   # 정답: 윗면 +10 µm
H_meas[~pred_ok] = np.nan
X, Y = np.meshgrid(xs, ys)
glare = (X - 5) ** 2 + (Y - 5) ** 2 < 0.8 ** 2               # 사고 1: 정반사로 생긴 예상 밖 결측
H_meas[glare] = np.nan
fake = (~pred_ok) & (rng.random(H.shape) < 0.05)             # 사고 2: 그림자 속 가짜 점(다중 반사)
H_meas[fake] = H[fake] + 0.5

# ---- (1) 대조표: 예측과 실제를 4칸으로 나눔 ----
meas_ok = ~np.isnan(H_meas)
tab = pd.DataFrame({"측정값 있음": [np.sum(pred_ok & meas_ok), np.sum(~pred_ok & meas_ok)],
                    "측정값 없음": [np.sum(pred_ok & ~meas_ok), np.sum(~pred_ok & ~meas_ok)]},
                   index=["예측: 보임", "예측: 그림자"])
print((100 * tab / H.size).round(2).to_string())
print(f"예상 밖 결측 = 보여야 하는데 없음: {100 * np.sum(pred_ok & ~meas_ok) / pred_ok.sum():.2f} %")
print(f"그림자 속 값 = 가짜 의심 점: {np.sum(~pred_ok & meas_ok)} 개 -> M_valid 에서 제외")

# 그림자 예측 경계는 θ 오차 때문에 1~2칸 어긋날 수 있으므로, 2칸 넓힌 그림자 안의 값만 버림
shadow_wide = ndimage.binary_dilation(~pred_ok, iterations=2)
M_valid = meas_ok & ~(shadow_wide & ~pred_ok)

# ---- (2) 엣지 띠 폭 민감도: 띠를 넓혀 가며 지표가 안정되는 지점을 찾음 ----
top = H >= 2.0
rows = []
for band in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50]:
    m = top & M_valid & ~edge_band(H, res, band)
    e = (H_meas - H)[m]
    rows.append({"band_mm": band, "n": e.size, "mean_um": 1000 * e.mean(),
                 "rms_um": 1000 * np.sqrt(np.mean(e ** 2)),
                 "p95_um": 1000 * np.percentile(np.abs(e), 95)})
print(pd.DataFrame(rows).round({"band_mm": 2, "mean_um": 1, "rms_um": 1, "p95_um": 1}).to_string(index=False))
```

**실행 예시와 기대 출력**

```
$ python e2_check.py
         측정값 있음  측정값 없음
예측: 보임    91.66    0.50
예측: 그림자    0.38    7.45
예상 밖 결측 = 보여야 하는데 없음: 0.55 %
그림자 속 값 = 가짜 의심 점: 3805 개 -> M_valid 에서 제외
 band_mm      n  mean_um  rms_um  p95_um
    0.00 289100      3.6    36.8    21.5
    0.05 277492      9.7    11.1    18.2
    0.10 260440     10.0    11.2    18.2
    0.15 249312     10.0    11.2    18.2
    0.20 232980     10.0    11.2    18.2
    0.25 222332     10.0    11.2    18.2
    0.35 196552     10.0    11.2    18.2
    0.50 157800     10.0    11.2    18.2
```

**출력 읽는 법**
- 대조표 4칸 중 **"예측 보임 + 측정 없음"(0.50 %)** 이 조사 대상이고, **"예측 그림자 + 측정 있음"(0.38 %)** 은 버릴 대상입니다.
- 민감도표에서 0.10 mm부터 mean·RMS가 변하지 않습니다(안정 구간). 이 합성 데이터는 경계 뭉개짐을 σ = 0.03 mm로 가정했기 때문에 안정 구간이 일찍 옵니다. **실제 데이터는 비드 가장자리와 선 두께 때문에 더 넓을 수 있으므로** 반드시 실제 스캔으로 이 표를 다시 만들어 띠 폭을 확정합니다.
- 띠를 0.50 mm로 넓혀도 지표는 같지만 평가 점 수가 222,332 → 157,800 (−29 %)으로 줄어듭니다. 작은 형상에서는 평가 영역이 사라질 수 있으므로 필요 이상으로 넓히지 않습니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 그림자 계산 코드 | 6.1 합성 장면 | 카메라·레이저 그림자, 슬롯 바닥 폭이 이론값 ± 1칸(0.02 mm) |
| 단위 테스트 | pytest (J3) | 블록 그림자 테스트 + `camera_side` 반대 테스트 통과 |
| 실측 그림자 검증 | E3 단차 0.2/0.4/1.0/2.0 mm, 열 20개 평균 | \|실측 − h·tanθ\| ≤ max(0.05 mm, 10 %) |
| 예상 밖 결측 | 결측 대조표 | 기준 재료(E1 GRY) 시편에서 ≤ 2 % |
| 엣지 띠 확정 | 실제 스캔 3개 민감도표 | 확정 폭 ±0.1 mm 범위에서 H5 mean 변화 ≤ 2 µm, RMS 변화 ≤ 10 % |
| 엣지 띠 효과 | 띠 적용 전후 비교 | 적용 후 RMS가 적용 전보다 작고, mean이 띠 폭 안정 구간 값과 일치 |
| 보고 체계 | H5 결과표 | 모든 결과 행에 평가 영역 % 기재 |

**완료 정의**: 실측 그림자 검증과 엣지 띠 확정이 합격이고, `config/default.yaml` 에 `edge_band_mm` 확정값이 근거 주석과 함께 반영되어 있으면 완료입니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| NaN을 보간해서 채운 뒤 오차 계산 | 슬롯 바닥·벽 뒤에 그럴듯한 값 → 지표가 실제보다 좋아 보임 | 지표 계산은 항상 NaN 제외. 보간 지도는 그림용 파일에만 |
| `camera_side` 반대로 설정 | 그림자가 벽의 엉뚱한 쪽에 예측되고 예상 밖 결측이 수 % 이상 | 블록 하나를 스캔해서 실제 NaN 띠가 벽의 어느 쪽에 생기는지 눈으로 확인 |
| 높이맵 행·열(Y·X)을 바꿔 사용 | 그림자가 X 방향으로 예측됨 | `H[iy, ix]` (행 = Y) 규칙을 코드 주석과 J3 테스트로 고정 |
| 기준 높이맵의 NaN(재료 없음)을 그대로 넣음 | `np.maximum.accumulate` 결과가 NaN 투성이 | 그림자 계산용으로는 NaN → 0(베드 높이)로 바꾼 복사본 사용 |
| 엣지 띠를 윤곽 지표에도 적용 | IoU·윤곽 거리가 경계 정보를 잃음 | 윤곽 지표(H6)는 `M_edge` 를 빼지 않음 (`M_valid` 만 적용) |
| 엣지 띠 폭을 형상마다 다르게 조절 | 결과를 원하는 쪽으로 맞춘다는 의심 | 한 값으로 고정, 바꾸면 전체 재계산 + 민감도 보고 |
| 단차 경계 판정 문턱을 너무 낮게 (예: 0.01 mm) | 노이즈만으로 경계가 잡혀 평가 영역이 사라짐 | 기준 높이맵(노이즈 없음)에서만 경계를 잡고, 문턱 = 층 높이/2 |
| 그림자 속 측정값을 진짜로 사용 | 안쪽 모서리 근처 + 튀는 값 | 예측 그림자(2칸 확장) 안의 값은 `M_valid` 에서 제외 |

## 9. 위험 요소

- **θ 캘리브레이션 오차**: θ가 2° 틀리면 2 mm 단차의 예측 그림자 길이가 약 0.1 mm 달라집니다 → 2칸 확장(0.04 mm)으로 부족할 수 있으니, 실측 검증(절차 3)에서 차이가 크면 확장 칸 수를 늘리거나 D2를 재점검합니다.
- **2회 스캔의 정합 오차**: 180° 돌려 합치면 측정 영역은 늘지만 두 스캔의 정합 잔차(수 µm~10 µm, H4 FRE)가 새 오차원이 됩니다. 2회 스캔 결과에는 FRE를 함께 보고합니다.
- **작은 형상의 평가 영역 소멸**: 폭 < 2 x 엣지 띠(0.5 mm)인 얇은 벽·슬롯은 높이 평가 영역이 0이 됩니다 → 이런 형상은 H6·H7(폭·윤곽)으로만 평가하도록 E3 형상 목록에 "주 지표"를 명시합니다.
- **안쪽 모서리 다중 반사**: 그림자 예측 밖에서도 생길 수 있습니다. H2 스파이크 제거(k·MAD)와 함께 써야 하며, 반사 패턴이 많으면 E1의 무광 처리를 검토합니다.
- **층별 측정(C2 2단계)으로 확장 시**: 매 층 높이맵이 달라지므로 그림자 마스크도 층마다 다시 계산해야 합니다 (계산은 빠르므로 문제는 없음).

## 10. 기록 양식

**`results/E2/E2_shadow_validation.csv`**

```csv
scan_id,calibration_id,theta_deg,camera_side,feature_id,step_height_mm,orientation,n_columns,shadow_meas_mm,shadow_meas_sd_mm,shadow_pred_mm,diff_mm,pass
```

**`results/<scan_id>/E2_missing_table.csv`**

```csv
scan_id,pred_visible_meas_ok_pct,pred_visible_meas_nan_pct,pred_shadow_meas_ok_pct,pred_shadow_meas_nan_pct,unexpected_missing_pct,shadow_points_removed,eval_area_pct
```

**`results/E2/E2_band_sensitivity.csv`**

```csv
scan_id,band_mm,n,mean_um,rms_um,p95_um,eval_area_pct
```

**`config/default.yaml` 반영 예**

```yaml
masks:
  edge_band_mm: 0.25        # E2 민감도: 안정 구간 시작 0.20 + 여유 0.05 (results/E2/E2_band_sensitivity.csv)
  edge_step_mm: 0.10        # 층 높이 0.2 mm 의 절반
  shadow_dilate_px: 2       # θ 오차 대비 예측 그림자 확장 칸 수
  camera_side: "-y"         # 실물 확인 YYYY-MM-DD
```

## 11. 참고 자료

- VDI/VDE 2634 Part 2 — Optical 3-D measuring systems: Optical systems based on area scanning (측정 가능 영역·형상 시험 개념)
- ISO 10360-8 — CMMs with optical distance sensors (광학 센서의 형상·크기 오차 시험)
- ISO 25178-2 — Geometrical product specifications (GPS): Surface texture: Areal — 용어와 매개변수 (경계·결측 처리의 일반 개념)
- NumPy 공식 문서 — `numpy.ufunc.accumulate` (`np.maximum.accumulate`)
- SciPy 공식 문서 — `scipy.ndimage.distance_transform_edt`, `scipy.ndimage.binary_dilation`, `scipy.ndimage.gaussian_filter`
- 상위 문서: [BLUEPRINT.md](../../BLUEPRINT.md) B2, E2, G4, H1, H5, H6, J2
