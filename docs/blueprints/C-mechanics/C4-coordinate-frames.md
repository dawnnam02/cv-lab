# C4. 좌표계 체계

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: C. 기구·환경·안전

| 항목 | 내용 |
|---|---|
| 기간 | 2026-11-03 ~ 2026-11-16 (W5-6) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [B2 기하 배치](../B-optics/B2-geometry.md) · [C1 스캔 이동 장치](C1-scan-stage.md) · [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) |
| 후행 요소 | [D2 레이저 평면](../D-calibration/D2-laser-plane.md) · [D3 스캔 축](../D-calibration/D3-scan-axis.md) · [D4 센서↔기계 좌표](../D-calibration/D4-sensor-to-gcode.md) · [C3 기준 마커](C3-fiducials.md) · [H1 점→격자](../H-analysis/H1-gridding.md) · [H4 정합](../H-analysis/H4-registration.md) |
| 관련 마일스톤 | M3 (합성 데이터에서 변형을 허용오차 내 복원, W11-12) |

## 1. 목적

측정 파이프라인에는 픽셀, 카메라, 센서, 스테이지, G코드 등 여러 좌표계가 등장합니다. 이 요소의 목적은

1. 좌표계마다 **이름·원점·축 방향·단위**를 문서로 고정하고,
2. 변환 행렬의 **이름 규칙**(`T_G_M`)과 저장 형식을 정하며,
3. 높이맵 배열의 **인덱스 ↔ mm 좌표 규칙**을 정하고,
4. 축 뒤집힘·뒤바뀜을 **비대칭 L자 시편**과 코드 검사로 잡아내는 것입니다.

좌표계 실수는 결과를 "조용히" 틀리게 만듭니다(오류 메시지 없이 그림이 거울상이 되거나 0.8° 돌아감). W5-6에 규칙을 정해 두면 D·G·H 영역이 같은 규칙으로 코드를 짭니다.

## 2. 배경 지식 (초보자용)

**좌표계란?** "원점이 어디이고, x·y·z 축이 어느 방향을 가리키는가"의 약속입니다. 같은 점이라도 카메라 기준으로는 (1, 2, 120) mm, 베드 기준으로는 (101, 52, 0.4) mm처럼 숫자가 다릅니다.

**이 과제의 좌표계 (필수 5개)**

| 기호 | 이름 | 원점 | 축 방향 | 단위 | 만들어지는 곳 |
|---|---|---|---|---|---|
| {I} | 이미지 | 이미지 왼쪽 위 픽셀 중심 | u: 오른쪽(열), v: 아래(행) | px | 카메라 |
| {C} | 카메라 | 렌즈 광학 중심 | x: 이미지 오른쪽, y: 이미지 아래, z: 카메라가 보는 방향 (OpenCV 규칙) | mm | D1 |
| {S} | 센서(프로파일) | 레이저 평면 위 기준점 | x: 레이저 선 방향, z: **위쪽(높이)**, y: 레이저 평면의 법선(스캔 방향) | mm | D2 |
| {M} | 측정 | 스캔 시작 위치의 {S} 원점 | x = {S}의 x, y: 스캔 진행 방향(+), z: 위쪽 | mm | D3 |
| {G} | G코드 | 프린터 원점 (G28 후 기계 좌표) | 프린터의 X, Y, Z (Z 위쪽, 베드 면 Z=0) | mm | 프린터 |

**모든 좌표계는 오른손 좌표계**입니다. 오른손 엄지 = x, 검지 = y, 중지 = z. x와 y를 정하면 z 방향은 자동으로 정해집니다. 왼손 좌표계(거울상)가 섞이면 회전 행렬의 행렬식(det)이 −1이 되므로 코드로 잡을 수 있습니다.

**변환 행렬 이름 규칙**: `T_G_M` = "**M 좌표의 점을 G 좌표로** 바꾸는 4×4 행렬". 읽는 순서는 "G ← M"입니다.

```
p_G = T_G_M · p_M
T_G_S = T_G_M · T_M_S        ← 가운데 글자(M)가 맞닿아 지워짐
T_M_G = inverse(T_G_M)
```

가운데 글자가 맞지 않는 곱(`T_M_S · T_G_M`)은 의미가 없습니다. 6절 코드는 이런 곱을 자동으로 거부합니다.

**4×4 동차 변환**: 회전 R(3×3)과 이동 t(3×1)를 한 행렬에 넣은 것입니다.

```
        ┌ R  t ┐        p' = R·p + t
  T  =  └ 0  1 ┘
```

**높이맵 배열 규칙 (H1, G3 공통)**: 높이맵 `H`는 2D numpy 배열이고 `H[iy, ix]`로 읽습니다 (행 = Y, 열 = X).

```
x = x0 + ix · res       y = y0 + iy · res       (칸의 중심 좌표, res = 0.02 mm)
```

`matplotlib.pyplot.imshow`는 기본적으로 0번 행을 **위쪽**에 그립니다. 그러면 Y가 아래로 증가하는 것처럼 보여 그림이 위아래로 뒤집힙니다. 이 과제에서는 항상 `origin="lower"`와 `extent=[x0, x1, y0, y1]`을 씁니다.

**각도 단위**: 내부 계산은 라디안, 보고서·설정 파일은 도(°)로 씁니다. 함수 이름이나 키 이름에 `_deg`, `_rad`를 붙여 구분합니다.

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일명 | 비고 |
|---|---|---|---|
| 입력 | 기하 배치 (카메라·레이저 방향) | B2 결과 | {C}, {S} 방향 결정 |
| 입력 | 스캔 방향·장치 | C1 결과 | {M}의 +y 방향 |
| 입력 | 프린터 좌표 규칙 | 프린터 펌웨어 설정, G1 파서 | {G} 원점·축 |
| 산출물 | 좌표계 정의서 | `docs/hardware/C4_frames.md` | 2절 표 + 사진에 축 화살표 표시 |
| 산출물 | 변환 클래스·검사 함수 | `src/cvlab/frames.py` | 6절 코드 |
| 산출물 | 변환 저장 형식 | `config/calibration/<CAL-ID>/T_*.yaml` | 10절 양식 |
| 산출물 | L자 축 검사 시편 | `data/gcode/C4_L_check.gcode` | 긴 팔 40 mm(+X), 짧은 팔 25 mm(+Y), 높이 2 mm |
| 산출물 | 축 검사 결과 | `results/hw_tests/C4_axis_check.yaml` | 통과/실패, 그림 |
| 산출물 | 단위 테스트 | `tests/test_frames.py` | 왕복 변환, 잘못된 곱, det 검사 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 비교 좌표계 | {M}에서 비교 / {G}에서 비교 | **{G}** | 기준(G코드)을 바꾸지 않고 측정을 옮김 → 기준 높이맵 재계산 불필요 |
| 길이 단위 | mm / µm | **mm** (보고서 표에서만 µm 허용) | 혼용 시 1000배 실수 |
| 각도 단위 | 내부 rad / deg | **내부 rad, 설정·보고 deg** | numpy 삼각함수는 rad |
| 변환 이름 | `T_G_M` / `M_to_G` / 자유 | **`T_<to>_<from>`** | 곱셈 연결 시 가운데 글자 확인 가능 |
| 변환 저장 | 4×4 행렬 / 오일러각+이동 | **4×4 행렬 + 사람이 읽는 yaw_deg, t_mm 병기** | 행렬은 정확, 각도는 확인용 |
| 높이 방향 | z 위 + / z 아래 + | **z 위쪽 +** (모든 좌표계에서 높이) | 오차 부호(+ = 재료 과다)와 직관 일치 |
| 높이맵 인덱스 | `H[iy, ix]` / `H[ix, iy]` | **`H[iy, ix]`** | numpy `meshgrid` 기본(`indexing="xy"`)과 일치 |
| 격자 좌표 | 칸 중심 / 칸 모서리 | **칸 중심** | G3·H1이 같은 규칙을 써야 반 칸(0.01 mm) 어긋남 방지 |
| 그림 규칙 | imshow 기본 / origin lower | **`origin="lower"`, `extent` 지정** | 상하 반전 방지 |

## 5. 수행 절차

1. **좌표계 정의서 작성 (W5 월~화)**
   - [ ] 2절 표를 `C4_frames.md`로 옮기고, 실제 측정대 사진 위에 {S}, {M}, {G}의 x·y·z 화살표를 그려 넣는다.
   - [ ] 프린터에서 `G28` 후 `G1 X10`, `G1 Y10`을 실행해 **+X, +Y가 실제로 어느 쪽인지** 눈으로 확인하고 사진에 표시한다 (프린터마다 베드가 움직이는 방향이 다름).
   - [ ] 센서의 +x(레이저 선 방향)가 {G}의 +X와 대략 같은 방향이 되도록 카메라 방향을 정한다. 반대이면 정의서에 "x_S ≈ −X_G"를 명시한다.

2. **변환 코드 작성 (W5 수~목)**
   - [ ] 6절 `Tf` 클래스를 `src/cvlab/frames.py`로 저장한다.
   - [ ] 단위 테스트 3개를 작성한다: ① `T.inv() @ T`가 단위행렬(오차 < 1e-12), ② 이름이 안 맞는 곱은 `ValueError`, ③ det(R) = −1이면 `ValueError`.
   - [ ] `pytest tests/test_frames.py` 통과.

3. **높이맵 격자 규칙 고정 (W5 금)**
   - [ ] `config/default.yaml`에 `grid.origin_mm`, `grid.resolution_mm: 0.02`, `grid.index_order: "yx"`, `grid.cell: "center"`를 추가한다.
   - [ ] G3(기준 높이맵)과 H1(측정 높이맵) 담당자와 규칙을 확인한다(같은 함수 `grid_coords()`를 공유).

4. **L자 축 검사 시편 (W6 월~수)**
   - [ ] L자 시편(긴 팔 40 mm는 +X, 짧은 팔 25 mm는 +Y, 폭 5 mm, 높이 2 mm)을 출력하고 베드 위에서 스캔한다.
   - [ ] 측정 높이맵에서 높이 > 1 mm인 마스크를 만들고, G코드 기준 마스크와 6절 `axis_check`로 비교한다.
   - [ ] 결과가 "회전0°"(변환 없음)이 아니면 어느 축이 뒤집혔는지 찾아 **센서→측정 변환 정의를 고친 뒤** 다시 검사한다 (데이터를 손으로 뒤집지 않는다).
   - [ ] 높이맵을 `origin="lower"`로 그리고 기준 경로를 겹쳐 그린 그림을 `results/hw_tests/C4_axis_check.png`로 저장한다.

5. **인계 (W6 목~금)**
   - [ ] D2(레이저 평면)에 {C}→{S} 정의, D3에 {S}→{M} 정의, D4·H4에 {M}→{G} 이름 규칙을 넘긴다.
   - [ ] 측정 메타데이터(F3)에 `frames_doc_version`을 추가한다.

## 6. Python 구현

이름 붙은 변환 클래스(`Tf`)는 **잘못된 순서의 곱과 거울 반전 행렬을 자동으로 거부**합니다. L자 검사는 측정 마스크를 8가지(0/90/180/270° 회전 × 좌우 거울)로 바꿔 보고 기준과 가장 잘 겹치는 경우를 찾습니다. 정상이라면 "변환 없음(회전0°)"이 최적이어야 합니다.

```python
"""C4 좌표계 체계: 이름 붙은 4×4 변환, 변환 연결 검사, L자 시편으로 축 뒤집힘 검사"""
import numpy as np

class Tf:
    """T_to_from: 'from' 좌표계의 점을 'to' 좌표계로 바꾸는 4×4 동차 변환 (단위 mm)"""
    def __init__(self, to, frm, R=np.eye(3), t=(0, 0, 0)):
        self.to, self.frm = to, frm
        self.M = np.eye(4)
        self.M[:3, :3], self.M[:3, 3] = R, t
        if not np.isclose(np.linalg.det(R), 1.0, atol=1e-6):   # 회전이 아니면 (거울/배율) 거부
            raise ValueError(f"T_{to}_{frm}: det(R)={np.linalg.det(R):.4f} ≠ 1 (오른손 좌표계 아님)")

    @property
    def name(self):
        return f"T_{self.to}_{self.frm}"

    def __matmul__(self, other):
        """T_a_b @ T_b_c = T_a_c. 가운데 이름(b)이 다르면 오류"""
        if self.frm != other.to:
            raise ValueError(f"{self.name} @ {other.name}: 연결 불가 ({self.frm} ≠ {other.to})")
        out = Tf(self.to, other.frm)
        out.M = self.M @ other.M
        return out

    def inv(self):
        R, t = self.M[:3, :3], self.M[:3, 3]
        return Tf(self.frm, self.to, R.T, -R.T @ t)

    def apply(self, P):
        P = np.atleast_2d(P)
        return P @ self.M[:3, :3].T + self.M[:3, 3]

def rot_z(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])

def l_shape_mask(n=100):
    """비대칭 L자 마스크 (행=Y, 열=X). 긴 팔은 +X 방향, 짧은 팔은 +Y 방향"""
    m = np.zeros((n, n), bool)
    m[10:25, 10:90] = True     # 아래쪽(작은 Y) 가로 막대: X 방향 80칸
    m[10:60, 10:25] = True     # 왼쪽 세로 막대: Y 방향 50칸
    return m

def axis_check(meas, ref):
    """측정 마스크를 8가지(회전 0/90/180/270 × 거울 유무)로 바꿔 기준과의 IoU 비교"""
    results = {}
    for flip in (False, True):
        base = meas[:, ::-1] if flip else meas
        for k in range(4):
            cand = np.rot90(base, k)
            iou = (cand & ref).sum() / (cand | ref).sum()
            results[("X뒤집힘+" if flip else "") + f"회전{90*k}°"] = iou
    best = max(results, key=results.get)
    return best, results

if __name__ == "__main__":
    # 변환 사슬: {S} 센서 → {M} 측정 → {G} G코드
    T_M_S = Tf("M", "S", np.eye(3), (0.0, 12.34, 0.0))     # 예: 스테이지 위치 y = 12.34 mm
    T_G_M = Tf("G", "M", rot_z(0.8), (-95.3, -72.1, 0.0))  # 기준마커 정합 결과 (C3, H4)
    T_G_S = T_G_M @ T_M_S
    print("만든 변환:", T_G_S.name)
    p_S = np.array([[1.0, 0.0, 0.25]])                      # 센서 좌표의 점 (x, y=0, z)
    p_G = T_G_S.apply(p_S)
    print("p_G =", np.round(p_G, 4))
    print("왕복 검사 오차 [mm]:", float(np.abs(T_G_S.inv().apply(p_G) - p_S).max()))

    try:
        T_M_S @ T_G_M                                       # 잘못된 순서
    except ValueError as e:
        print("오류 감지:", e)
    try:
        Tf("G", "M", np.diag([-1, 1, 1]))                   # X축 뒤집힌 행렬
    except ValueError as e:
        print("오류 감지:", e)

    # L자 시편 축 검사: 측정 데이터의 X가 뒤집혀 들어온 상황을 흉내
    ref = l_shape_mask()
    meas_ok = ref.copy()
    meas_bad = ref[:, ::-1]
    for name, m in [("정상 데이터", meas_ok), ("X 뒤집힌 데이터", meas_bad)]:
        best, res = axis_check(m, ref)
        verdict = "통과" if best == "회전0°" else f"실패 → {best} 를 적용해야 일치"
        print(f"{name}: 변환 없음 IoU={res['회전0°']:.3f}, 최적={best} ({res[best]:.3f}) → {verdict}")
```

**실행 방법**: `python src/cvlab/frames.py` (또는 scratch 폴더에서 `python c4_frames.py`)

**기대 출력**

```
만든 변환: T_G_S
p_G = [[-94.4724 -59.7472   0.25  ]]
왕복 검사 오차 [mm]: 0.0
오류 감지: T_M_S @ T_G_M: 연결 불가 (S ≠ G)
오류 감지: T_G_M: det(R)=-1.0000 ≠ 1 (오른손 좌표계 아님)
정상 데이터: 변환 없음 IoU=1.000, 최적=회전0° (1.000) → 통과
X 뒤집힌 데이터: 변환 없음 IoU=0.533, 최적=X뒤집힘+회전0° (1.000) → 실패 → X뒤집힘+회전0° 를 적용해야 일치
```

**해석**
- `p_G` 계산 확인: x = cos0.8°·1 − sin0.8°·12.34 − 95.3 ≈ −94.4724 mm. 손 계산과 일치합니다.
- X가 뒤집힌 데이터는 그대로 비교하면 IoU 0.533밖에 안 됩니다. 만약 이 상태로 ICP 같은 최적맞춤을 돌리면 엉뚱한 위치에 억지로 맞춰 "오차가 큰 시편"으로 잘못 보고됩니다. 그래서 **정합 전에 축 검사를 먼저** 합니다.
- L자 시편이 대칭(정사각형, 원)이면 이 검사가 불가능합니다. 반드시 팔 길이가 다른 L자나 문자 형태를 씁니다.

**단위 테스트** (`tests/test_frames.py`, 실행: `pytest -q tests/test_frames.py`)

```python
# tests/test_frames.py — 실제 저장소에서는 from cvlab.frames import Tf, rot_z
import numpy as np
import pytest
from c4_frames import Tf, rot_z

def test_roundtrip():
    T = Tf("G", "M", rot_z(0.8), (-95.3, -72.1, 0.0))
    assert np.allclose((T.inv() @ T).M, np.eye(4), atol=1e-12)

def test_wrong_chain_rejected():
    T_G_M = Tf("G", "M")
    T_M_S = Tf("M", "S")
    with pytest.raises(ValueError):
        T_M_S @ T_G_M

def test_mirror_rejected():
    with pytest.raises(ValueError):
        Tf("G", "M", np.diag([-1.0, 1.0, 1.0]))
```

기대 출력: `3 passed`

## 7. 검증 방법과 완료 기준

| 항목 | 방법 | 합격 기준 |
|---|---|---|
| 정의서 완성 | 2절 표 5개 좌표계 + 사진 화살표 | 빈 칸 0개, 지도교수 확인 |
| 왕복 변환 정확도 | `T.inv()` 왕복 | 최대 오차 < 1e-9 mm |
| 잘못된 연결 감지 | 단위 테스트 | 이름 불일치 곱 100 % `ValueError` |
| 거울 반전 감지 | 단위 테스트 | det(R) = −1 입력 시 `ValueError` |
| L자 축 검사 | 실제 측정 마스크 vs 기준 | 최적 = 회전0°, IoU(변환 없음) ≥ 0.9 |
| L자 방향 육안 확인 | `origin="lower"` 그림 | 긴 팔 +X, 짧은 팔 +Y로 보임 |
| 격자 규칙 일치 | G3·H1이 같은 `grid_coords()` 사용 | 합성 사각형 마스크 중심 차이 < 0.001 mm |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| `T_G_M`과 `T_M_G` 혼동 | 데이터가 엉뚱한 곳으로 수 mm~수십 mm 이동 | 이름 규칙 + `Tf` 클래스 사용, 알려진 점으로 왕복 확인 |
| imshow 기본값 사용 | 그림이 위아래 뒤집혀 보임 → 데이터를 손으로 뒤집음 | 항상 `origin="lower"`, 데이터는 손대지 않음 |
| `H[ix, iy]`로 인덱싱 | 그림이 대각선 대칭으로 뒤집힘 | `H[iy, ix]` 규칙, 정사각형이 아닌 격자로 테스트 |
| 각도를 deg로 `np.cos`에 넣음 | 0.8°가 0.8 rad(≈ 46°)로 계산 | 변수명에 `_deg`/`_rad`, `np.radians` 사용 |
| µm와 mm 혼용 | 결과가 1000배 크거나 작음 | 내부 mm 고정, 보고 직전에만 변환 |
| 칸 모서리/중심 혼용 | 기준과 측정이 반 칸(10 µm) 어긋남 → 경계 오차 | 칸 중심 규칙, 공유 함수 사용 |
| 대칭 시편으로 축 검사 | 뒤집혀도 검사 통과 | 비대칭 L자 시편 |
| OpenCV의 y(아래) 방향을 높이로 착각 | 높이가 음수로 나오거나 부호 반전 | {S}·{M}·{G}에서 z는 항상 위쪽 + |

## 9. 위험 요소

- **조용한 오류**: 좌표계 실수는 에러 없이 그럴듯한 숫자를 냅니다. 합성 데이터 테스트(J3)에서 알려진 이동·회전을 넣어 복원되는지 반드시 확인합니다(M3).
- **프린터마다 다른 축 방향**: 베드가 Y로 움직이는 프린터는 "+Y 명령 시 베드가 앞으로" 움직여 노즐이 상대적으로 뒤로 갑니다. 반드시 실제 동작으로 확인합니다.
- **사양 변경 시 재검사**: 카메라를 돌려 달거나 스캔 방향을 바꾸면 L자 검사를 다시 합니다.
- **정의서와 코드 불일치**: 정의서를 고치면 `frames_doc_version`을 올리고 관련 테스트를 다시 돌립니다.

## 10. 기록 양식

**변환 저장 파일** (`config/calibration/CAL-YYYY-MM-DD-A/T_G_M.yaml`)

```yaml
name: T_G_M            # M 좌표 → G 좌표
to: G
from: M
units: mm
matrix_4x4:
  - [1.0, 0.0, 0.0, 0.0]
  - [0.0, 1.0, 0.0, 0.0]
  - [0.0, 0.0, 1.0, 0.0]
  - [0.0, 0.0, 0.0, 1.0]
readable:              # 사람 확인용 (계산에는 matrix_4x4 사용)
  yaw_deg: 0.0
  t_mm: [0.0, 0.0, 0.0]
source: "fiducial registration (H4)"
fid_id: FID-YYYY-MM-DD-A
calibration_id: CAL-YYYY-MM-DD-A
residual_fre_um: null
created: ""
```

**축 검사 결과** (`results/hw_tests/C4_axis_check.yaml`)

```yaml
date: ""
specimen: C4_L_check
best_transform: ""          # 회전0° 이면 통과
iou_identity: null
iou_best: null
pass: null
figure: results/hw_tests/C4_axis_check.png
action_taken: ""
```

## 11. 참고 자료

- OpenCV 공식 문서: "Camera Calibration and 3D Reconstruction" 모듈 (카메라 좌표계 규칙: x 오른쪽, y 아래, z 앞)
- 로보틱스 교과서의 "동차 변환(homogeneous transformation)"과 좌표계 표기 단원
- ROS REP 103 "Standard Units of Measure and Coordinate Conventions" (단위·오른손 좌표계 관례의 좋은 예)
- matplotlib 공식 문서: `imshow`의 `origin`, `extent` 설명 ("origin and extent in imshow" 튜토리얼)
- numpy 공식 문서: `numpy.meshgrid`의 `indexing` 인자
