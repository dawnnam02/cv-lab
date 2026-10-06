# D4. 센서 ↔ 기계(G코드) 좌표 변환

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: D. 캘리브레이션

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-15 ~ 2026-12-28 (W11-12) |
| 우선순위 | 높음 |
| 트랙 | 하드웨어 |
| 선행 요소 | [D3 스캔 축](D3-scan-axis.md) · [D5 검증·이력 관리](D5-calibration-verification.md) · [C3 지그·기준 마커](../C-mechanics/C3-fiducials.md) · [C4 좌표계 체계](../C-mechanics/C4-coordinate-frames.md) · [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) |
| 후행 요소 | [H4 정합](../H-analysis/H4-registration.md) · [H7 치수·형상 지표](../H-analysis/H7-dimensional-metrics.md) · [J3 합성 데이터 테스트](../J-software/J3-synthetic-tests.md) · [I1 측정 불확도](../I-reliability/I1-uncertainty.md) |
| 관련 마일스톤 | **M3** — 합성 데이터에서 알려진 변형(이동·회전·배율·높이)을 허용오차 안에서 복원 |

---

## 1. 목적

측정 좌표계 {M}(D3 결과)의 점을 **G코드 좌표계 {G}** 로 옮기는 4×4 변환 행렬 `T_G_M` 을 구합니다. BLUEPRINT C4 규칙대로 **비교는 항상 {G} 에서** 하므로, 이 변환이 틀리면 모든 위치 오차가 틀립니다.

- `T_G_M` 은 **기준 마커(정밀 구)** 로 구하므로, ICP 같은 "최대한 겹치기" 정합과 달리 **시편 전체가 밀린 위치 오차를 지우지 않습니다** (H4 방법 1).
- 이를 위해 먼저 **기준 구의 G 좌표**를 알아야 하는데, C3 의 **좌표 교정 판**(G코드 좌표를 아는 원기둥 격자)을 출력·측정해서 정합니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 동차 변환 행렬과 이름 규칙
회전 R(3×3)과 이동 t(3)를 한 행렬로 묶은 것입니다.

```
T_G_M = [[R, t],      X_G = R · X_M + t
         [0, 1]]      이름 읽는 법: "M 좌표를 G 좌표로 바꾸는 행렬"
```
- 역변환: `T_M_G = inv(T_G_M)`.
- 연결: `T_G_C = T_G_M @ T_M_C` (아래 첨자가 맞물려야 올바른 순서).

### 2.2 강체 변환(Kabsch)과 거울 반전
대응점 쌍 A(측정), B(G코드)가 있을 때 `B ≈ R·A + t` 를 최소제곱으로 푸는 방법이 Kabsch(SVD) 방법입니다. 점이 3개 이상이고 **한 줄에 놓이지 않아야** 합니다. 계산 중 `det(R) = −1`(거울상)이 나올 수 있어 이를 막는 줄(`D = diag(1, 1, sign(det))`)이 필수입니다.

### 2.3 왜 배율(scale)을 허용하지 않나
배율까지 허용하는 닮음 변환(Umeyama)을 쓰면, 프린터의 **수축·배율 오차가 변환 속으로 사라집니다**. 그래서:
- `T_G_M` = **강체(회전 + 이동)만**
- 배율은 **진단용으로 따로 계산해서 결과로 보고** (BLUEPRINT H4 "흔한 실수")

### 2.4 FRE, FLE, TRE — 정합이 얼마나 정확한가
| 용어 | 뜻 | 이 과제 기준 |
|---|---|---|
| FLE (마커 위치 오차) | 구 중심 하나를 측정할 때의 오차 | 2~5 µm 예상 |
| **FRE** (정합 잔차) | 변환 후 마커들이 G 좌표와 얼마나 어긋나는지 RMS | **≤ 10 µm** (BLUEPRINT H4) |
| **TRE** (목표점 오차) | 마커가 아닌 **시편 위치**에서의 변환 오차 | 시편 중앙에서 ≤ 10 µm 목표 |

FRE 가 작아도 TRE 가 작다는 보장은 없습니다(마커가 시편에서 멀거나 한쪽에 몰리면 TRE 가 커짐). 그래서 **leave-one-out**(마커 하나를 빼고 맞춘 뒤 그 마커를 예측)과 **TRE 근사식**(Fitzpatrick)을 함께 봅니다.

### 2.5 두 단계 구조
| 단계 | 언제 | 무엇을 | 결과 |
|---|---|---|---|
| 1. 마커 좌표 확정 | 베드·마커를 조립했을 때 한 번 | 좌표 교정 판(5×5 원기둥) + 기준 구를 함께 스캔 → 원기둥 25쌍으로 변환 → 구의 G 좌표 계산 | `fiducials_G` (구 4개의 G 좌표) |
| 2. 매 측정 정합 | 시편을 측정할 때마다 | 시편과 기준 구를 함께 스캔 → 구 4쌍으로 `T_G_M` | `T_G_M`, FRE |

원기둥 25개를 평균하므로 프린터의 랜덤 위치 오차(예: 15 µm)가 1/√25 로 줄어듭니다.

### 2.6 센서를 프린터 헤드·갠트리에 다는 경우
센서가 프린터 헤드와 함께 움직이면 측정 순간의 기계 좌표 p(헤드 위치)를 이용해:

```
T_G_M(p) = T_G_H(p) @ T_H_M       H: 헤드 좌표계, T_G_H(p) = 위치 p 로의 이동(회전 없음 가정)
```
`T_H_M`(헤드↔센서 오프셋)을 위 두 단계 방법으로 한 번 구해 두면, 이후에는 기계 좌표만으로 {G} 에 연결됩니다. 그래도 **기준 구로 주기적으로(예: 측정 세션마다) 확인**합니다.

---

## 3. 입력과 산출물

| 구분 | 이름 | 형식·위치 | 설명 |
|---|---|---|---|
| 입력 | 센서 캘리브레이션 | `config/calibration/CAL-2026-12-08-A/` (D1~D3, D5 합격) | {M} 점군 생성 |
| 입력 | 좌표 교정 판 G코드 | `data/gcode/coord_plate_5x5_v1.gcode` + 슬라이서 프로파일 | Ø 2 mm × 높이 2 mm 원기둥, x 간격 4 mm, y 간격 8 mm |
| 입력 | 교정 판 + 구 스캔 | `data/raw/calib/FID-2026-12-22-A/plate_r01.npz` | 한 스캔 안에 원기둥 25개 + 구 4개 |
| 입력 | 기준 구 | Ø 6 mm 무광 세라믹, 4개, 비대칭 배치 | C3 |
| 산출물 | **기준 구 G 좌표** | `config/fiducials/FID-2026-12-22-A/fiducials_G.yaml` | 구 4개 (mm), 판 잔차, 배율 진단 |
| 산출물 | **측정별 변환** | `results/<scan_id>/T_G_M.yaml` | 4×4 행렬, FRE, leave-one-out, TRE 예측 |
| 산출물 | 이력 | `config/fiducials/history.csv` | FID ID, 날짜, FRE, 조립 메모 |

> ID 규칙: 센서 캘리브레이션은 `CAL-…`, **베드·마커 조립 상태**는 `FID-YYYY-MM-DD-A`. 베드나 마커를 다시 조립하면 새 FID ID 를 만듭니다 (C3 3번).

---

## 4. 결정 사항

| ID | 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|---|
| D4-1 | 마커 수 | 3 / **4** / 5+ | 4개 | 3개면 leave-one-out 불가. 4개로 이상 마커 검출 가능 |
| D4-2 | 마커 배치 | 한쪽 몰림 / **시편을 둘러싸는 비대칭 사각형** | 시편 앞뒤(스캔 방향)·좌우에 분산, 비대칭 | FOV 가로 약 20 mm 라 좌우보다 **스캔 방향으로 넓게** 벌림. 비대칭이면 번호 혼동 방지 |
| D4-3 | 구 중심 맞춤 | 반지름 함께 / **반지름 고정** | 고정 | 윗부분만 보여 함께 추정 시 불안정 (BLUEPRINT H4) |
| D4-4 | 변환 종류 | **강체 6자유도** / 3자유도(x, y, yaw) / 닮음 | 강체 6자유도로 계산하고 yaw·pitch·roll 을 보고 | pitch·roll 이 0.1° 이상이면 H3 기준화 확인 신호 |
| D4-5 | 배율 처리 | 변환에 포함 / **따로 진단** | 따로 | 수축 오차를 숨기지 않기 위해 (2.3절) |
| D4-6 | 교정 판 크기 | 3×3 / **5×5** | 5×5, Ø 2 mm 원기둥 | BLUEPRINT C3. 평균으로 프린터 랜덤 오차 감소 |
| D4-7 | 교정 판 반복 | 1장 / **2장 출력** | 2장 각각 측정 후 구 G 좌표 비교 | 차이 < 10 µm 이면 평균 사용 |
| D4-8 | 유효 기간 | – | **베드·마커 재조립 전까지** + 세션마다 FRE 확인 | C3 3번 |

---

## 5. 수행 절차

1. **마커 설치 (C3 와 함께, W11)**
   - [ ] 구 4개를 베드(또는 지그)에 접착·고정. 시편 영역 앞뒤로 배치(예: {M} 기준 (−6.5, −6), (6, −4.5), (−5, 46), (6.5, 44) mm)
   - [ ] 접착제 경화 24시간 후 사용, FID ID 부여
2. **좌표 교정 판 출력과 측정**
   - [ ] 판 G코드 작성: 원기둥 25개 중심 G 좌표를 표로 저장 (G1 파서로 재확인)
   - [ ] 시편과 **같은 재료·같은 조건**으로 출력, 베드에서 떼지 않음 (C2 "공정 후, 베드 위")
   - [ ] 베드 실온까지 냉각 (C6) 후 판 + 구 4개를 한 번에 스캔
   - [ ] 원기둥 윗면 원 맞춤 → 중심 (x, y), 윗면 중앙값 높이 → z
3. **단계 1 계산**
   - [ ] 원기둥 25쌍으로 강체 변환 → 판 잔차 RMS (출력 랜덤 오차 수준, 예상 15~40 µm)
   - [ ] 닮음 변환 배율을 진단값으로 기록 (프린터 배율 오차)
   - [ ] 구 4개의 G 좌표 계산 → `fiducials_G.yaml` 저장
   - [ ] 판 2장째로 반복 → 구 G 좌표 차이 < 10 µm 확인
4. **단계 2 (매 측정)**
   - [ ] 시편 + 구 4개 스캔 → 반지름 고정 구 맞춤 → `T_G_M`
   - [ ] FRE ≤ 10 µm, leave-one-out ≤ 25 µm 확인. 어느 구 하나만 크면 그 구 표면 오염·손상 점검
   - [ ] yaw·pitch·roll 과 이동량 기록
5. **축 방향 검증**
   - [ ] L자 시편(C4)을 출력·측정해 {G} 에서 L 모양이 G코드 미리보기와 같은 방향인지 확인
   - [ ] `det(R) = +1` 확인 (코드가 자동으로 보장)

---

## 6. Python 구현

### 6.1 두 단계 전체 (`d4_sensor_to_gcode.py`)
정답 변환과 프린터 배율 오차(−0.15 %), 출력 랜덤 오차(15 µm), 구 중심 계통 오차(3 µm)를 넣은 합성 데이터로 실행합니다.

```python
"""
D4. 센서(측정 좌표 {M}) ↔ G코드 좌표 {G} 변환 T_G_M 구하기 — 합성 데이터
---------------------------------------------------------------------
단계 1 (한 번만): 좌표 교정 판(5x5 원기둥, G코드 좌표를 앎) + 기준 구 4개를 함께 스캔
                 → 원기둥 25쌍으로 T_G_M 추정 → 기준 구 4개의 G 좌표를 확정해서 저장
단계 2 (매 측정): 시편과 기준 구 4개를 함께 스캔 → 구 중심(반지름 고정 맞춤)
                 → 구 4쌍으로 T_G_M 추정 + FRE + leave-one-out 검사
실행:  python3 d4_sensor_to_gcode.py
"""
import numpy as np
import yaml
from scipy.optimize import least_squares

rng = np.random.default_rng(11)


# ------------------------------------------------------------------ 기본 함수
def rot_zyx(yaw_deg, pitch_deg, roll_deg):
    """Z(yaw)·Y(pitch)·X(roll) 순서 회전 행렬"""
    y, p, r = np.radians([yaw_deg, pitch_deg, roll_deg])
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    Ry = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]])
    return Rz @ Ry @ Rx


def to_T(R, t):
    """회전 R(3x3) + 이동 t(3) → 4x4 동차 변환 행렬"""
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t
    return T


def apply_T(T, P):
    """점들 P (N,3) 에 4x4 변환 적용"""
    return P @ T[:3, :3].T + T[:3, 3]


def rigid_transform(A, B):
    """Kabsch: B ≈ R A + t (A, B: 대응점 N x 3). 거울 반전 방지 포함"""
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def similarity_transform(A, B):
    """Umeyama: B ≈ s R A + t  (배율 s 진단용 — T_G_M 에는 쓰지 않음)"""
    ca, cb = A.mean(0), B.mean(0)
    A0, B0 = A - ca, B - cb
    U, S, Vt = np.linalg.svd(A0.T @ B0)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    s = (S * np.diag(D)).sum() / (A0**2).sum()
    return s, R, cb - s * R @ ca


def fit_sphere_fixed_r(P, R):
    """반지름을 인증값 R 로 고정하고 중심만 추정 (윗부분만 보여도 안정적)"""
    A = np.hstack([2 * P, np.ones((len(P), 1))])
    sol, *_ = np.linalg.lstsq(A, (P**2).sum(1), rcond=None)       # 선형 맞춤으로 초깃값
    fun = lambda c: np.linalg.norm(P - c, axis=1) - R
    return least_squares(fun, sol[:3]).x


def angles_from_R(R):
    """회전 행렬 → (yaw, pitch, roll) [deg]  (보고서용)"""
    pitch = -np.arcsin(R[2, 0])
    return np.degrees([np.arctan2(R[1, 0], R[0, 0]), pitch, np.arctan2(R[2, 1], R[2, 2])])


def tre_estimate(fid, target, fle):
    """Fitzpatrick 근사식: 목표점 위치의 정합 오차(TRE) 기대값. fle: 마커 위치 오차 RMS"""
    c = fid.mean(0); F = fid - c
    _, _, Vt = np.linalg.svd(F)
    ratio = 0.0
    for k in range(3):                       # 주축 k 에 대해 (목표점 거리² / 마커 분포 RMS²)
        ax = Vt[k]
        d2 = np.sum((target - c) ** 2) - ((target - c) @ ax) ** 2
        f2 = np.mean(np.sum(F**2, 1) - (F @ ax) ** 2)
        ratio += d2 / f2
    return np.sqrt(fle**2 / len(fid) * (1 + ratio / 3))


# ------------------------------------------------------------------ 합성용 정답
T_G_M_TRUE = to_T(rot_zyx(1.2, 0.05, -0.08), np.array([92.40, 75.10, -0.150]))
T_M_G_TRUE = np.linalg.inv(T_G_M_TRUE)
R_FID = 3.000                                                       # Ø 6 mm 무광 세라믹 구
FID_M_TRUE = np.array([[-6.5, -6.0, 3.0], [6.0, -4.5, 3.0],
                       [-5.0, 46.0, 3.0], [6.5, 44.0, 3.0]])       # 측정 좌표 구 중심 (비대칭 배치)


def synth_sphere_cap(center, R, noise_um=4.0, min_elev_deg=30):
    """구 윗부분(앙각 30° 이상)만 보이는 점군 (0.02 mm 간격 수준)"""
    n = 6000
    el = np.radians(rng.uniform(min_elev_deg, 90, n)); az = rng.uniform(0, 2 * np.pi, n)
    dirs = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], 1)
    return center + dirs * (R + rng.normal(0, noise_um / 1000, (n, 1)))


def measure_fiducials(fid_true_M, bias_um=3.0):
    """스캔 1회: 구 점군 → 반지름 고정 맞춤으로 중심 측정.
    bias_um: 구 형상 오차·표면·센서 계통오차로 생기는 중심 오차 (구마다 다름, 현실적 크기 2~5 µm)"""
    out = []
    for c in fid_true_M:
        c_seen = c + rng.normal(0, bias_um / 1000, 3)
        out.append(fit_sphere_fixed_r(synth_sphere_cap(c_seen, R_FID), R_FID))
    return np.array(out)


def main():
    # ============ 단계 1: 좌표 교정 판으로 기준 구의 G 좌표 확정 =========================
    gx, gy = np.meshgrid(np.arange(-8, 8.1, 4.0), np.arange(2, 34.1, 8.0))
    plate_G_nom = np.stack([gx.ravel() + 100, gy.ravel() + 80, np.full(gx.size, 2.0)], 1)  # G코드 좌표
    c0 = plate_G_nom.mean(0)
    S_PRINTER = 0.9985                                              # 프린터 배율 오차 −0.15 % (정답)
    printed_G = c0 + S_PRINTER * (plate_G_nom - c0)
    printed_G[:, :2] += rng.normal(0, 0.015, (len(printed_G), 2))   # 원기둥마다 출력 랜덤 오차 15 µm
    plate_M = apply_T(T_M_G_TRUE, printed_G) + rng.normal(0, 0.003, printed_G.shape)  # 측정 3 µm
    fid_M_1 = measure_fiducials(FID_M_TRUE)

    R1, t1 = rigid_transform(plate_M, plate_G_nom)                   # 강체 맞춤 (배율 허용 안 함)
    T1 = to_T(R1, t1)
    res1 = np.linalg.norm(apply_T(T1, plate_M) - plate_G_nom, axis=1)
    s_diag, _, _ = similarity_transform(plate_M, plate_G_nom)
    fid_G = apply_T(T1, fid_M_1)                                    # ← 기준 구의 G 좌표 (저장)
    fid_G_true = apply_T(T_G_M_TRUE, FID_M_TRUE)
    print("[단계 1] 좌표 교정 판 (원기둥 25개)")
    print(f"  강체 맞춤 잔차 RMS = {np.sqrt((res1**2).mean())*1000:.1f} µm, 최대 = {res1.max()*1000:.1f} µm")
    print(f"  진단: 닮음 변환 배율 = {s_diag:.5f} → 프린터 배율 오차 {100*(1/s_diag-1):+.3f} % (정답 {100*(S_PRINTER-1):+.3f} %)")
    print(f"  기준 구 G 좌표 오차(정답 대비) 최대 = {np.abs(fid_G - fid_G_true).max()*1000:.1f} µm")

    # ============ 단계 2: 매 측정 — 기준 구 4개로 T_G_M =================================
    shift = to_T(rot_zyx(0.3, 0, 0), np.array([0.8, -0.5, 0.0]))    # 이번 스캔은 센서 위치가 조금 다름
    T_M_G_now = shift @ T_M_G_TRUE
    fid_M_now_true = apply_T(T_M_G_now, fid_G_true)
    fid_M_now = measure_fiducials(fid_M_now_true)

    R2, t2 = rigid_transform(fid_M_now, fid_G)
    T_G_M = to_T(R2, t2)
    fre_each = np.linalg.norm(apply_T(T_G_M, fid_M_now) - fid_G, axis=1)
    fre = np.sqrt((fre_each**2).mean())
    print("[단계 2] 측정 스캔의 기준 구 4개")
    print(f"  FRE (정합 잔차 RMS) = {fre*1000:.1f} µm, 구별 = {np.round(fre_each*1000, 1)} µm")
    yaw, pitch, roll = angles_from_R(R2)
    print(f"  T_G_M: 이동 = {np.round(t2, 3)} mm, yaw = {yaw:.3f}°, pitch = {pitch:.3f}°, roll = {roll:.3f}°")

    # leave-one-out: 구 하나를 빼고 나머지 3개로 맞춘 뒤 빠진 구를 예측
    loo = []
    for k in range(4):
        m = np.arange(4) != k
        Rk, tk = rigid_transform(fid_M_now[m], fid_G[m])
        loo.append(np.linalg.norm(Rk @ fid_M_now[k] + tk - fid_G[k]))
    print(f"  leave-one-out 예측 오차 = {np.round(np.array(loo)*1000, 1)} µm")

    # 시편 중앙(측정 좌표 (0, 20, 2))에서의 실제 오차와 TRE 예측
    target_M = np.array([0.0, 20.0, 2.0])
    target_true_G = apply_T(np.linalg.inv(T_M_G_now), target_M[None])[0]
    err_target = np.linalg.norm(apply_T(T_G_M, target_M[None])[0] - target_true_G)
    tre = tre_estimate(fid_M_now, target_M, fre * np.sqrt(4 / 2))   # FLE ≈ FRE·√(N/(N−2))
    u_fidG = np.sqrt((res1**2).mean()) / np.sqrt(len(plate_M))      # 단계 1 기여 ≈ 판 잔차/√25
    print(f"  시편 중앙 실제 위치 오차 = {err_target*1000:.1f} µm | 예측: 단계2 TRE {tre*1000:.1f} µm, "
          f"단계1 기여 {u_fidG*1000:.1f} µm → 합성 {np.hypot(tre, u_fidG)*1000:.1f} µm")

    out = {
        "fiducial_set_id": "FID-2026-12-22-A",          # 베드·마커 조립 상태의 ID
        "sensor_calibration_id": "CAL-2026-12-08-A",    # 사용한 센서 캘리브레이션 (D1~D3)
        "element": "D4",
        "T_G_M": T_G_M.round(9).tolist(),
        "fre_um": round(float(fre * 1000), 2),
        "fiducial_radius_mm": R_FID,
        "fiducials_G_mm": fid_G.round(5).tolist(),
        "plate_rigid_rms_um": round(float(np.sqrt((res1**2).mean()) * 1000), 2),
        "plate_similarity_scale": round(float(s_diag), 6),
        "valid_until": "베드·마커 재조립 전까지",
    }
    with open("T_G_M.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    print("저장: T_G_M.yaml")


if __name__ == "__main__":
    main()
```

**실행 예시와 기대 출력** (1초 미만)

```
$ python3 d4_sensor_to_gcode.py
[단계 1] 좌표 교정 판 (원기둥 25개)
  강체 맞춤 잔차 RMS = 28.1 µm, 최대 = 53.1 µm
  진단: 닮음 변환 배율 = 1.00171 → 프린터 배율 오차 -0.171 % (정답 -0.150 %)
  기준 구 G 좌표 오차(정답 대비) 최대 = 8.1 µm
[단계 2] 측정 스캔의 기준 구 4개
  FRE (정합 잔차 RMS) = 5.1 µm, 구별 = [4.7 4.5 5.8 5.1] µm
  T_G_M: 이동 = [91.585 75.587 -0.15 ] mm, yaw = 0.891°, pitch = 0.086°, roll = -0.077°
  leave-one-out 예측 오차 = [19.2 17.5 17.9 16.3] µm
  시편 중앙 실제 위치 오차 = 3.0 µm | 예측: 단계2 TRE 3.6 µm, 단계1 기여 5.6 µm → 합성 6.7 µm
저장: T_G_M.yaml
```

**출력 읽는 법**
- 판 강체 잔차 28 µm 는 출력 랜덤 오차(15 µm)와 배율 오차가 합쳐진 값입니다. 이것은 "변환이 나빠서"가 아니라 **프린터의 오차**이며, 닮음 변환 배율(−0.171 %, 정답 −0.150 %)로 따로 보고합니다.
- 25개 평균 덕분에 구 G 좌표 오차는 최대 8.1 µm 로 줄었습니다.
- FRE 5.1 µm → 기준 10 µm 합격. leave-one-out 은 구 3개로 외삽하므로 16~19 µm 로 더 큽니다(기준 25 µm).
- 시편 중앙 실제 오차 3.0 µm, 예측 합성값 6.7 µm → 예측이 실제를 덮으므로 불확도 예산(I1)에 **6.7 µm 를 위치 정합 불확도**로 넣는 것이 안전합니다.

### 6.2 단위 테스트 (`test_d4_rigid.py`)
J3 의 "정합: 알려진 R, t 로 옮긴 점 → `rigid_transform` 이 R, t 를 복원" 테스트입니다.

```python
"""D4 단위 테스트: 알려진 R, t 로 옮긴 점에서 rigid_transform 이 R, t 를 복원하는지 (J3)"""
import numpy as np
from d4_sensor_to_gcode import rigid_transform, rot_zyx, similarity_transform


def test_rigid_recovers_known_transform():
    rng = np.random.default_rng(0)
    A = rng.uniform(-20, 20, (4, 3))
    R_true, t_true = rot_zyx(1.2, 0.05, -0.08), np.array([92.4, 75.1, -0.15])
    B = A @ R_true.T + t_true
    R, t = rigid_transform(A, B)
    assert np.allclose(R, R_true, atol=1e-12) and np.allclose(t, t_true, atol=1e-10)
    assert np.isclose(np.linalg.det(R), 1.0)               # 거울 반전 아님


def test_similarity_scale():
    rng = np.random.default_rng(1)
    A = rng.uniform(-20, 20, (25, 3))
    s, R, t = similarity_transform(A, 0.9985 * A + [1, 2, 3])
    assert abs(s - 0.9985) < 1e-12
```

```
$ python3 -m pytest -q test_d4_rigid.py
2 passed
```

### 6.3 변환 파일 사용법 (다른 모듈에서)

```python
import numpy as np, yaml
T_G_M = np.array(yaml.safe_load(open("T_G_M.yaml"))["T_G_M"])
P_G = P_M @ T_G_M[:3, :3].T + T_G_M[:3, 3]      # P_M: (N,3) 측정 좌표 점 → G 코드 좌표
```

---

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 | 6.1 합성 결과 |
|---|---|---|---|
| FRE | 구 4개 정합 잔차 RMS | **≤ 10 µm** | 5.1 µm |
| leave-one-out | 구 하나 빼고 예측 | 각 ≤ 25 µm | 16.3 ~ 19.2 µm |
| 시편 위치 TRE 예측 | Fitzpatrick 근사 + 단계 1 기여 | ≤ 10 µm | 6.7 µm |
| 구 G 좌표 재현성 | 교정 판 2장 비교 | 구별 차이 < 10 µm | (실측 시 기록) |
| 판 배율 진단 | 닮음 변환 배율 | 기록만 (H4 배율 결과와 같은 부호·크기인지 비교) | −0.171 % |
| 축 방향 | L자 시편 + det(R) | 방향 일치, det = +1 | 테스트 통과 |
| 단위 테스트 | pytest | 모두 통과 | 2 passed |
| M3 연계 | J3 합성 파이프라인에서 이동 (0.20, −0.10) mm, 회전 0.5° 복원 | 이동 오차 < 10 µm, 회전 오차 < 0.01° | J3 참조 |

**완료 판정**: FRE·leave-one-out·TRE 예측이 합격하고, `fiducials_G.yaml` 과 이력이 저장되며, L자 시편 확인을 마치면 완료.

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| ICP 결과를 `T_G_M` 으로 사용 | 위치 오차가 항상 0 근처 | 기준 구 정합(방법 1)으로 `T_G_M`, ICP 는 형상 비교용으로 분리 (H4) |
| 변환에 배율 허용 | 수축 오차가 사라짐 | 강체만, 배율은 진단값으로 따로 |
| 구 번호 대응이 뒤바뀜 | FRE 가 수 mm | 비대칭 배치 + 가까운 G 좌표로 자동 대응 후 FRE 확인 |
| 마커가 한쪽에 몰림 | FRE 는 작은데 시편 위치 오차 큼 | 시편을 둘러싸도록 배치, TRE 계산 |
| 베드 재조립 후 예전 `fiducials_G` 사용 | 위치 오차가 수십 µm 계통적으로 바뀜 | 재조립 = 새 FID ID, 단계 1 반복 |
| 교정 판을 베드에서 떼어 측정 | G 좌표 연결이 끊김 | 베드에서 떼지 않고 측정 (C2) |
| 뜨거운 베드에서 측정 | 판이 팽창해 배율 진단이 틀림 | 실온 냉각 후 측정 (C6) |
| 행렬 곱 순서 혼동 (`T_M_G` 를 `T_G_M` 처럼 사용) | 점들이 엉뚱한 곳으로 이동 | 이름 규칙(2.1) 준수, 단위 테스트 |
| 거울 반전 방지 줄 삭제 | 드물게 좌우가 뒤집힌 결과 | `D = diag(1,1,sign(det))` 유지, `det(R)=+1` 검사 |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| FOV 가 좁아(약 20 mm) 마커와 시편을 한 스캔에 넣기 어려움 | 높음 | 높음 | 마커를 스캔 방향 앞뒤로 배치, 시편 크기를 FOV 안으로 (E3) |
| 교정 판 출력 품질(실 끌림, 첫 층 뭉개짐) | 중 | 중 | 원기둥 윗면만 사용, 2장 출력 비교 |
| 접착한 구의 미세 이동(온도·충격) | 중 | 높음 | 세션마다 FRE 감시, 증가 추세면 재고정 + 새 FID |
| 갠트리 장착 시 헤드 위치 반복성 부족 | 중 | 중 | 기준 구 확인을 매 세션 유지 |
| 프린터 좌표 원점 변경(펌웨어·홈 스위치) | 낮음 | 높음 | 홈 위치 변경 시 새 FID, 이력 기록 |

---

## 10. 기록 양식

`config/fiducials/FID-2026-12-22-A/fiducials_G.yaml`

```yaml
fiducial_set_id: FID-2026-12-22-A
sensor_calibration_id: CAL-2026-12-08-A
date: 2026-12-22
operator: ""
bed_assembly_note: ""          # 베드·지그 조립 상태 메모
spheres: {diameter_mm: 6.000, material: "matte ceramic", count: 4}
coord_plate:
  gcode_file: coord_plate_5x5_v1.gcode
  gcode_sha256: ""
  prints: 2
  rigid_rms_um: [null, null]
  similarity_scale: [null, null]
fiducials_G_mm:                # 구 4개 중심 (G 좌표)
  - [null, null, null]
  - [null, null, null]
  - [null, null, null]
  - [null, null, null]
plate_repeat_max_diff_um: null
L_specimen_check: ""           # 정상 / 이상
valid_until: "베드·마커 재조립 전까지"
```

측정마다 `results/<scan_id>/T_G_M.yaml` 의 FRE 를 모으는 `config/fiducials/history.csv`

| date | scan_id | fiducial_set_id | fre_um | loo_max_um | yaw_deg | pitch_deg | roll_deg | 비고 |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

---

## 11. 참고 자료

- W. Kabsch, "A solution for the best rotation to relate two sets of vectors" (1976) — Kabsch 알고리즘
- S. Umeyama, "Least-squares estimation of transformation parameters between two point patterns" (IEEE TPAMI, 1991) — 닮음 변환
- J. M. Fitzpatrick 외, "Predicting error in rigid-body point-based registration" (IEEE TMI, 1998) — FRE·FLE·TRE 관계
- SciPy 문서: `scipy.optimize.least_squares` (구 중심 맞춤)
- 로봇공학 교과서의 동차 변환·좌표계 표기법 (예: 변환 행렬 아래 첨자 규칙)
- 상위 기준: [BLUEPRINT.md D4, C3, C4, H4](../../BLUEPRINT.md)
