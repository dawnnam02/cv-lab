# E3. 시편(테스트 아티팩트) 설계 — 오차 종류마다 그것을 드러내는 형상

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: E. 측정 대상(시편)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-29 ~ 2027-01-11 (W13-14) |
| 우선순위 | 높음 |
| 트랙 | 실험·품질 |
| 선행 요소 | [A1 오차의 정의](../A-goals/A1-error-definition.md) · [A2 요구 정밀도](../A-goals/A2-precision-spec.md) · [B1 삼각측량 원리](../B-optics/B1-triangulation-principle.md) (FOV, δx) · [C3 기준 마커](../C-mechanics/C3-fiducials.md) · [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) · [G3 마스크·높이맵](../G-reference/G3-mask-heightmap.md) · [E1 표면 광학](./E1-surface-optics.md) (재료) · [E2 가림·엣지](./E2-occlusion-edges.md) (간격·방향 규칙) |
| 후행 요소 | [H5 높이 지표](../H-analysis/H5-height-metrics.md) · [H6 윤곽 지표](../H-analysis/H6-contour-metrics.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) · [H8 통계](../H-analysis/H8-statistics.md) · [I2 MSA](../I-reliability/I2-msa.md) · [I3 교차검증](../I-reliability/I3-cross-validation.md) · [G5 CAD 기준과의 관계](../G-reference/G5-cad-relation.md) |
| 관련 마일스톤 | **M4** (시편 1개 전체 파이프라인 완주) — 이 요소의 E3-A 시편이 M4의 "시편 1개" |

---

## 1. 목적

1. **A1의 오차 종류(높이·윤곽·치수·위치·배율·선·표면)마다 그것을 잘 드러내는 형상**을 하나 이상 담은 시편을 설계합니다.
2. 모든 형상이 **위에서 보이고(2.5D)**, **FOV 안에 들어가고**, **가림·엣지 띠를 빼고도 평가 영역이 남도록** 설계 단계에서 숫자로 점검합니다 (E2 규칙 적용).
3. 시편 CAD·형상 목록·슬라이서 프로파일·G코드를 **버전 관리되는 하나의 묶음**으로 만들어, 본 실험(W18-21)과 MSA(I2)에서 **같은 G코드로 반복 출력**할 수 있게 합니다.
4. 형상 목록(CSV)을 분석 코드(H5~H7)가 그대로 읽어 **형상별로 지표를 나눠 계산**할 수 있게 합니다.

## 2. 배경 지식 (초보자용)

### 2.1 테스트 아티팩트란

공정의 "능력"을 재기 위해 일부러 다양한 형상을 모아 둔 표준 시편입니다. 적층제조(AM)에서는 **NIST가 공개한 AM 테스트 아티팩트**와 국제표준 **ISO/ASTM 52902** (적층제조 시스템의 기하 능력 평가용 테스트 아티팩트)가 대표적입니다. 이들은 계단, 핀, 구멍, 얇은 벽, 슬롯, 경사면 등을 한 판에 배치합니다. 이 과제에서는 그 아이디어를 따르되, **레이저 삼각측량 + 2.5D + FOV 약 20 mm** 라는 우리 측정 조건에 맞게 줄이고 배치를 바꿉니다.

### 2.2 우리 측정 조건이 주는 제약

| 제약 | 숫자 | 설계에 주는 영향 |
|---|---|---|
| FOV (X 방향 측정 폭) | B1 예: **19.9 mm** | 시편 폭 **16 mm** (양쪽 1.95 mm 여유로 베드가 보여야 H3 기준면을 잡을 수 있음) |
| 스캔 길이 (Y) | 스테이지 행정에 따라 | Y로는 길게 가능 (100 mm, 0.02 mm 간격이면 5,000장, 2 mm/s로 50초) |
| X 점 간격 δx | **13.8 µm** | 가장 작은 형상(0.2 mm 슬롯)에도 14.5점 → A2의 "최소 5~10점" 만족 |
| 카메라 그림자 | **h · tanθ**, θ = 30° | 높이 2 mm 형상 뒤(+Y 쪽) 1.155 mm가 안 보임 → **Y 방향 간격 규칙** |
| 엣지 띠 | **0.25 mm** (E2) | 폭 0.5 mm 미만 형상은 높이 평가 영역이 0 → 윤곽·치수로만 평가 |
| 위에서만 봄 | 2.5D | 돌출부 아래(오버행), 옆면 경사, 언더컷은 측정 불가 → 넣지 않음 |

### 2.3 왜 "피라미드"가 아니라 "한 방향 계단"인가

청사진 표의 "계단 피라미드"는 사방으로 단차가 있습니다. 그러면 **카메라 쪽 반대편 단차 뒤**에 그림자(2 mm 단차면 1.155 mm)가 생겨 계단 면의 상당 부분이 사라집니다. **X 방향으로만 오르는 계단**(단차 벽이 Y와 나란)으로 만들면 카메라 그림자가 생기지 않고, 레이저 팬 그림자(약 0.1 mm)만 남습니다. 단차값은 청사진과 같이 **0.2 / 0.4 / 1.0 / 2.0 mm** 입니다. 피라미드가 꼭 필요하면 θ를 작게(20°) 하거나 180° 돌린 2회 스캔(E2)을 씁니다.

### 2.4 좁은 형상은 Y 방향으로 길게

카메라 그림자는 Y 방향으로만 생기므로(E2), **슬롯·얇은 벽·벽 사이 틈은 Y 방향으로 길게** 놓습니다. 그러면 폭 방향(X)으로는 가림이 거의 없고, 슬롯 바닥도 볼 수 있습니다.

### 2.5 STL 파일이란

3D 형상을 **삼각형 면들의 목록**으로 저장하는 가장 단순한 형식입니다. ASCII STL은 사람이 읽을 수 있는 글자 파일입니다.

```
solid 이름
  facet normal nx ny nz        ← 면의 바깥 방향(법선)
    outer loop
      vertex x1 y1 z1          ← 삼각형 꼭짓점 3개 (바깥에서 볼 때 반시계 방향)
      vertex x2 y2 z2
      vertex x3 y3 z3
    endloop
  endfacet
  ...
endsolid 이름
```

**올바른(슬라이서가 문제없이 읽는) STL 조건**: ① 물샐틈없음(watertight): 모든 변이 정확히 두 삼각형에 공유되고, 두 삼각형에서 서로 반대 방향으로 쓰임 ② 법선이 바깥을 향함 → 부피를 계산하면 **양수** ③ 넓이가 0인 삼각형이 없음.

### 2.6 형상 목록(feature list)이 중요한 이유

분석 코드는 "어디가 원기둥 Ø6이고 어디가 슬롯 0.4인지"를 알아야 형상별 지표(H5 "영역별 계산")를 낼 수 있습니다. 형상 목록 CSV(이름·목적·좌표·높이)를 **설계의 단일 기준(single source of truth)**으로 두고, CAD와 분석 코드가 모두 이 표를 따르게 합니다.

## 3. 입력과 산출물

| 구분 | 항목 | 형식 / 파일명 | 비고 |
|---|---|---|---|
| 입력 | 주요 오차 종류 | A1 (높이·윤곽·치수·위치 + 배율·선·표면) | 형상 선택 근거 |
| 입력 | FOV, δx, θ, 선폭 | B1/B2/D2 결과, `config/default.yaml` | 설계 점검 수치 |
| 입력 | 본 실험 재료 | E1 결론 메모 | 기본: 회색 불투명 PLA |
| 입력 | 간격·방향·엣지 띠 규칙 | E2 (`masks.edge_band_mm`) | |
| 입력 | 기준 마커 배치 | C3 (구 3~4개, FOV 안) | |
| 산출물 | 형상 목록 | `data/gcode/E3A_features_v1.csv` | 6.1 코드가 생성. 26개 형상 |
| 산출물 | 설계 점검 결과 | `results/E3/E3A_design_check_v1.txt` | FOV·샘플링·간격·형상별 평가 가능 % |
| 산출물 | CAD·STL | `data/gcode/E3A_artifact_v1.step`(CAD 원본), `E3A_artifact_v1.stl` | CAD 도구(FreeCAD, OpenSCAD 등)로 형상 목록대로 모델링 |
| 산출물 | 계단 블록 단독 STL | `data/gcode/step_block_v1.stl` | 6.2 코드로 생성 (D5·E2 검증용 소형 시편) |
| 산출물 | 슬라이서 프로파일 | `data/gcode/E3A_artifact_v1.ini` (또는 슬라이서의 프로파일 내보내기 파일) | **G코드와 같이 버전 관리** |
| 산출물 | G코드 | `data/gcode/E3A_artifact_v1.gcode` + SHA-256 해시 | 모든 반복 출력은 이 파일 하나로 |
| 산출물 | 슬라이싱 확인 결과 | `results/E3/E3A_slicing_check_v1.csv` | 형상별 "설계 vs G코드 기준" 면적 비 |
| 산출물 | 출력 기록 | `data/experiments.csv` 행 추가 (S01~S03) | 출력 일시, 재료 로트, 온도 |
| 산출물 | 보조 시편 | E3-B 선 트랙 시편, E3-C 핀 격자 판 | 5절 참고 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 시편 구성 | 큰 판 1개 / **용도별 소형 시편 3종** | **E3-A 형상 시편(16 x 100 mm) + E3-B 선 트랙 시편 + E3-C 핀 격자 판** | FOV 20 mm 안에 넣으면 이어 붙이기(스티칭) 오차가 없음 (청사진 E3 관리 원칙). 핀 격자는 베드 전역이 필요하므로 분리 |
| 시편 폭 (X) | 18 / **16** / 14 mm | **16 mm** | FOV 19.9 mm에서 양쪽 1.95 mm 베드 노출 (H3) |
| 바닥판 두께 | 1 / **2** / 3 mm | **2 mm** (0.2 mm 층 x 10) | 휨 억제, 관통 구멍 깊이 2 mm (Ø2 구멍 바닥도 0.85 mm 보임) |
| 형상 높이 (바닥판 위) | 1 / **2** / 3 mm | **2 mm** (윗면 z = 4.0 mm), 계단만 최대 3.6 mm | 그림자 1.155 mm로 제한, 층 수 10개로 층별 측정(C2) 확장 가능 |
| 계단 형태 | 피라미드 / **한 방향 계단** | **X 방향으로 오르는 계단** (단차 0.2/0.4/1.0/2.0 mm, 면 폭 3 mm) | 2.3절. 엣지 띠 제외 후에도 면마다 2.5 mm 폭 평가 가능 |
| 평면 패드 크기 | 15 x 15 / **12 x 12** mm | **12 x 12 mm** | 청사진 예시 15 x 15는 폭 16 mm 안에서 여유가 없음 |
| 원기둥·구멍 지름 | 청사진 Ø2, 4, 6, 10 | **그대로** | 원기둥은 돌출(외경), 구멍은 바닥판 관통(내경) |
| 얇은 벽 | 1~4줄 | **선폭 0.42 mm x 1, 2, 3, 4 = 0.42/0.84/1.26/1.68 mm**, Y 방향 길이 6 mm, 벽 사이 0.8 mm | 벽 두께가 선폭의 정수배여야 슬라이서가 의도대로 채움 |
| 슬롯 | 0.2~1.0 mm | **0.2/0.4/0.6/0.8/1.0 mm, 깊이 1 mm, Y 방향 길이 8 mm** | 0.2·0.4 mm는 슬라이서가 막을 수 있음 → 그 자체가 결과(G5 슬라이싱 오차) |
| 날카로운 모서리 | 90/60/30° | **꼭짓점이 +X를 향한 삼각 돌출, 변 길이 4 mm** | 모서리 반경(H7) 측정 |
| 비대칭 표식 | L자 / 문자 | **L자 (X 다리 6 mm, Y 다리 4 mm, 다리 폭 1.5 mm, 높이 1 mm)** 를 원점 모서리에 | C4 축 방향 확인. **두 다리 길이를 다르게** 해야 X↔Y 뒤바뀜이 보임. 문자보다 단순하고 윤곽 지표에도 쓸 수 있음 |
| 형상 간 Y 간격 | – | **≥ h·tanθ + 2 x 엣지 띠** (2 mm 형상: ≥ 1.66 mm, 계단 최고 3.6 mm: ≥ 2.58 mm) | E2 규칙. 6.1 코드가 자동 점검 |
| 기준 마커 위치 | – | **시편 양 끝(Y < 0, Y > 100) 바깥, X = 2.5와 13.5에 구 4개** (같은 스캔에 포함) | C3: FOV 안·같은 스캔·일직선 아님 |
| 출력 개수 | 1 / **3** / 5 | **E3-A 3개(S01~S03), 같은 G코드** | M4는 1개로 충분, 나머지는 반복성(H8)·I2 준비 |
| 출력 방식 | 베드 위 측정 / 떼어 측정 | **베드 위에서 측정** (C2 1단계) | 위치 오차까지 측정 가능 |

## 5. 수행 절차

1. **형상 목록 확정 (1일 차)**
   - [ ] 6.1 코드의 `features()` 를 검토해 A1의 오차 종류별로 최소 1개 형상이 있는지 표로 확인 (아래 "형상-지표 대응표")
   - [ ] 실행해서 `E3A_features_v1.csv` 생성, 설계 점검 결과를 `E3A_design_check_v1.txt` 로 저장
   - [ ] 점검 1~3이 모두 OK인지 확인. NG면 좌표를 고치고 다시 실행

   **형상-지표 대응표 (E3-A)**

   | ID | 형상 | A1 오차 종류 | 주 지표 (H) | 비고 (6.1 평가 가능 %) |
   |---|---|---|---|---|
   | F01 | L자 표식 | 위치·축 방향 | 윤곽(H6), 축 확인(C4) | 62 % |
   | F02-1~4 | 얇은 벽 1~4줄 | 선(비드)·최소 형상 | 벽 폭(H7), 윤곽 | 1줄은 높이 평가 0 % → **폭으로만** |
   | F03-1~4 | 계단 면 4개 | 높이 | 단차 높이(H7), 높이 편차(H5) | 각 78 % |
   | F04 | 평면 패드 | 표면·높이 | 평면도 P-V(H7), RMS(H5) | 92 % |
   | F05-2~10 | 원기둥 Ø2/4/6/10 | 치수 | 지름·원형도(H7) | 54~90 % |
   | F06-2~10 | 구멍 Ø2/4/6/10 | 치수 (구멍 수축) | 지름·원형도(H7) | 17~80 % (바닥은 그림자) |
   | F07 | 슬롯 0.2~1.0 | 윤곽 (최소 틈·과충진) | 슬롯 폭, 과충진 면적(H6) | 0.2·0.4 mm는 높이 평가 0 % |
   | F08 | 모서리 90/60/30° | 윤곽 (모서리 뭉개짐) | 모서리 반경(H7), HD95(H6) | 44~61 % |
   | (바닥판) | 바닥판 윗면 | 배율·높이 | 바닥판 길이 100 mm 방향 배율(H4), 높이 | 길이 측정은 D3 스캔축 검증과 함께 |

2. **CAD 모델링 (1~2일 차)**
   - [ ] CAD 도구에서 형상 목록 좌표 그대로 모델링 (원점 = 바닥판 왼쪽 아래 모서리, X = 폭 16 mm, Y = 길이 100 mm)
   - [ ] STL로 내보낸 뒤 6.2의 `check_mesh()` 로 검사 (watertight, 부피 양수)
   - [ ] 계단 블록 단독 STL(`step_block_v1.stl`)은 6.2 코드로 바로 생성 → E2 그림자 검증, D5 보조 점검용
3. **슬라이싱 (2일 차)**
   - [ ] 슬라이서 프로파일 고정: 층 높이 0.2 mm, 선폭 0.42 mm, 외벽 2줄, 윗면 5층, 채움 20 %, **스커트는 시편에서 5 mm 이상 떨어뜨림**(G4에서 제외), 브림·서포트 **없음**, 얇은 벽 감지 설정 기록
   - [ ] G코드 생성 → SHA-256 해시 기록 (`sha256sum` 또는 Python `hashlib`)
   - [ ] G1 파서로 읽고 G3로 기준 높이맵 생성 → 6.1의 설계 높이맵과 **형상별 면적 비교**: 면적 비가 0.9 미만이거나 형상이 사라진 경우 목록화 (예: 0.2 mm 슬롯이 G코드에서 막힘). 이것은 "슬라이싱 오차"로 G5에 기록하고 **비교 기준은 G코드**임을 유지
4. **보조 시편 설계 (2~3일 차)**
   - [ ] **E3-B 선 트랙 시편**: 베드 위 1층(0.2 mm) 단일 선. 방향 0°(X, 길이 16 mm — FOV 제한), 45°, 90°(Y, 길이 20 mm), 선 사이 3 mm. 선(비드) 폭·경로 이탈(H7)
   - [ ] **E3-C 핀 격자 판**: 5 x 5 원기둥(Ø4, 높이 3 mm), 간격 20 mm (80 x 80 mm 영역). C3의 "좌표 교정 판"과 같은 것으로 겸용. 위치·배율 오차 화살표 지도(H7, J4). FOV보다 크므로 **열마다 스캔**하고 각 스캔에 기준 마커가 들어가게 하거나, 센서가 프린터 축에 달린 경우 D4 변환으로 연결
5. **출력 (3~5일 차)**
   - [ ] E1 결론 재료(기본 GRY, 같은 로트) 사용. 베드 위치는 기준 마커 사이 같은 자리
   - [ ] 출력 전 베드 청소, 첫 층 확인. 출력 순서·일시·실내 온도·노즐/베드 온도를 `experiments.csv` 에 기록
   - [ ] 출력 후 **베드를 끄고 실온까지 식힌 뒤**(C6) 떼지 않고 측정
6. **첫 측정과 파이프라인 완주 (6~9일 차, M4)**
   - [ ] S01을 스캔 → H1~H4 → E2 마스크 → H5~H7 형상별 지표 → J4 리포트
   - [ ] 형상별 평가 영역 %가 6.1 설계 점검값과 ±10 %p 안에 드는지 확인 (크게 낮으면 E1 표면·E2 그림자 원인 조사)
   - [ ] L자 표식이 리포트 그림에서 올바른 방향(원점 모서리, 긴 다리 6 mm가 +X, 짧은 다리 4 mm가 +Y)인지 눈으로 확인
7. **교차검증 준비 (10일 차)**
   - [ ] 마이크로미터·캘리퍼스로 잴 수 있는 항목 표시: 계단 단차(하이트 게이지), 원기둥 Ø10 지름(마이크로미터), 바닥판 길이 100 mm(캘리퍼스) → I3에서 Bland–Altman 비교

## 6. Python 구현

### 6.1 형상 목록 + 설계 점검 (`scripts/e3_artifact.py`)

형상을 shapely 도형으로 정의하고, 0.02 mm 격자 설계 높이맵을 만든 뒤 E2와 같은 방법(누적 최댓값 그림자 + 엣지 띠)으로 **형상별 평가 가능 면적 %**를 계산합니다.

```python
"""E3 시편(테스트 아티팩트) E3-A 설계 점검 도구
  1) 형상 목록(feature list) -> E3A_features_v1.csv
  2) 설계 높이맵(2.5D) 생성 -> 측정 가능성 점검 (FOV, 점 개수, 카메라 그림자, 엣지 띠)
실행: python e3_artifact.py
좌표: X = 레이저 선 방향(FOV 방향), Y = 스캔 방향, Z = 위. 원점 = 시편 바닥판 왼쪽 아래 모서리. 단위 mm
"""
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon, Point, box
from scipy import ndimage

BASE_W, BASE_L, BASE_Z = 16.0, 100.0, 2.0   # 바닥판 16 x 100 x 2 mm
FOV_X, DX = 19.9, 0.0138                    # B1 계산 예: FOV 19.9 mm, δx 13.8 µm
THETA, LINE_W, BAND = 30.0, 0.42, 0.25      # 삼각측량 각도, 선폭, 엣지 띠 폭


def tri_corner(apex_x, yc, angle_deg, L=4.0):
    """꼭짓점 각도가 angle_deg 인 삼각형 (꼭짓점이 +X 쪽을 향함)"""
    h = np.radians(angle_deg / 2)
    return Polygon([(apex_x, yc), (apex_x - L * np.cos(h), yc + L * np.sin(h)),
                    (apex_x - L * np.cos(h), yc - L * np.sin(h))])


def features():
    """(id, 이름, 목적=A1 오차 종류, 도형, 윗면 z[mm], 종류 add=돌출 / cut=파냄)"""
    F = [("F01", "L자 비대칭 표식", "좌표축 방향 확인",
          Polygon([(1.5, 1.5), (7.5, 1.5), (7.5, 3), (3, 3), (3, 5.5), (1.5, 5.5)]), 3.0, "add")]
    x = 8.8
    for n in range(1, 5):                              # 얇은 벽: 1~4줄 두께, Y 방향으로 길게
        w = n * LINE_W
        F.append((f"F02-{n}", f"얇은 벽 {n}줄({w:.2f} mm)", "최소 형상·선폭",
                  box(x, 1.5, x + w, 7.5), 4.0, "add"))
        x += w + 0.8
    for k, (x0, x1, z) in enumerate([(2, 5, 2.2), (5, 8, 2.6), (8, 11, 3.6), (11, 14, 5.6)]):
        F.append((f"F03-{k + 1}", f"계단 {z:.1f} mm 면", "Z 단차 정확도",
                  box(x0, 10, x1, 20), z, "add"))     # 단차 0.2/0.4/1.0/2.0 mm, X 방향으로 오름
    F.append(("F04", "평면 패드 12x12", "평면도·높이 오차", box(2, 23, 14, 35), 4.0, "add"))
    F.append(("F05-10", "원기둥 Ø10", "지름·원형도", Point(8, 43).buffer(5, quad_segs=64), 4.0, "add"))
    for d, xc in [(2, 2.0), (4, 6.0), (6, 12.0)]:
        F.append((f"F05-{d}", f"원기둥 Ø{d}", "지름·원형도",
                  Point(xc, 54).buffer(d / 2, quad_segs=64), 4.0, "add"))
    for d, xc, yc in [(2, 2.5, 62), (4, 6.5, 62), (6, 12.0, 62), (10, 8.0, 73)]:
        F.append((f"F06-{d}", f"구멍 Ø{d} (관통)", "구멍 수축",
                  Point(xc, yc).buffer(d / 2, quad_segs=64), 0.0, "cut"))
    x = 2.0
    for w in [0.2, 0.4, 0.6, 0.8, 1.0]:                # 슬롯: 깊이 1 mm, Y 방향으로 길게
        F.append((f"F07-{w}", f"슬롯 {w:.1f} mm", "최소 틈·과충진", box(x, 81, x + w, 89), 1.0, "cut"))
        x += w + 1.5
    for a, ax in [(90, 4.33), (60, 9.46), (30, 14.86)]:
        F.append((f"F08-{a}", f"모서리 {a}°", "모서리 뭉개짐", tri_corner(ax, 95, a), 4.0, "add"))
    return F


def heightmap(F, res):
    xs = np.arange(0, BASE_W, res) + res / 2
    ys = np.arange(0, BASE_L, res) + res / 2
    X, Y = np.meshgrid(xs, ys)
    H = np.full(X.shape, BASE_Z)                       # 바닥판 윗면
    for kind in ("add", "cut"):                        # 돌출 먼저, 파냄은 나중에 덮어씀
        for fid, name, purpose, geom, z, k in F:
            if k == kind:
                H[shapely.contains_xy(geom, X, Y)] = z
    return H, xs, ys, X, Y


def camera_visible(H, res, theta_deg):                 # E2 와 같은 cummax 방법 (카메라 -Y 쪽)
    g = H + np.arange(H.shape[0])[:, None] * res / np.tan(np.radians(theta_deg))
    return g >= np.maximum.accumulate(g, axis=0) - 1e-9


def edge_band(H, res, band_mm, step_mm=0.1):           # E2 와 같은 엣지 띠
    d = np.zeros(H.shape, bool)
    dy, dx = np.abs(np.diff(H, axis=0)) > step_mm, np.abs(np.diff(H, axis=1)) > step_mm
    d[:-1] |= dy; d[1:] |= dy; d[:, :-1] |= dx; d[:, 1:] |= dx
    return ndimage.distance_transform_edt(~d) * res <= band_mm


if __name__ == "__main__":
    F = features()
    pd.DataFrame([{"id": f[0], "name": f[1], "purpose": f[2], "kind": f[5], "z_top_mm": f[4],
                   "xmin": round(f[3].bounds[0], 3), "ymin": round(f[3].bounds[1], 3),
                   "xmax": round(f[3].bounds[2], 3), "ymax": round(f[3].bounds[3], 3),
                   "area_mm2": round(f[3].area, 3)} for f in F]
                 ).to_csv("E3A_features_v1.csv", index=False, encoding="utf-8-sig")
    print(f"형상 수: {len(F)}  -> E3A_features_v1.csv")

    # 점검 1: FOV 안에 들어가는가 (양쪽 여유 >= 1 mm 이면 베드도 함께 보여 H3 기준면 확보)
    margin = (FOV_X - BASE_W) / 2
    print(f"[FOV] 시편 폭 {BASE_W} mm / FOV {FOV_X} mm -> 양쪽 여유 {margin:.2f} mm",
          "OK" if margin >= 1.0 else "NG")

    # 점검 2: 가장 작은 형상에 점이 5개 이상 찍히는가 (A2 샘플링 규칙)
    print(f"[샘플링] 최소 형상 0.2 mm 슬롯 -> {0.2 / DX:.1f} 점/폭",
          "OK" if 0.2 / DX >= 5 else "NG")

    # 점검 3: 형상 사이 간격 (높이 h 인 형상 뒤 카메라 그림자 h·tanθ + 엣지 띠 2개)
    adds = sorted([f for f in F if f[5] == "add"], key=lambda f: f[3].bounds[1])
    worst = []
    for a in adds:
        for b in adds:
            ax0, ay0, ax1, ay1 = a[3].bounds; bx0, by0, bx1, by1 = b[3].bounds
            overlap_x = min(ax1, bx1) > max(ax0, bx0)
            if overlap_x and by0 >= ay1 and a[4] > BASE_Z:     # b 가 a 의 +Y 쪽(그림자 쪽)에 있음
                need = (a[4] - BASE_Z) * np.tan(np.radians(THETA)) + 2 * BAND
                gap = by0 - ay1
                if gap < 1e-9:                                 # 맞닿은 형상(계단 등)은 제외
                    continue
                worst.append((gap - need, a[0], b[0], gap, need))
    worst.sort()
    m, a, b, gap, need = worst[0]
    print(f"[간격] 가장 빠듯한 쌍 {a}->{b}: 간격 {gap:.2f} mm, 필요 {need:.2f} mm",
          "OK" if m >= 0 else "NG")

    # 점검 4: 형상별 '평가 가능 면적' 비율 = 보임 ∧ ¬엣지띠 (높이맵 0.02 mm)
    res = 0.02
    H, xs, ys, X, Y = heightmap(F, res)
    ok = camera_visible(H, res, THETA) & ~edge_band(H, res, BAND)
    rows = []
    for fid, name, purpose, geom, z, kind in F:
        inside = shapely.contains_xy(geom, X, Y)
        rows.append((fid, name, 100 * ok[inside].mean()))
    t = pd.DataFrame(rows, columns=["id", "name", "eval_pct"]).round(1)
    print(t.to_string(index=False))
    print(f"[전체] 높이맵 {H.shape}, 평가 가능 {100 * ok.mean():.1f} %")
```

**실행 예시와 기대 출력** (높이맵 5000 x 800, 약 10초)

```
$ python e3_artifact.py
형상 수: 26  -> E3A_features_v1.csv
[FOV] 시편 폭 16.0 mm / FOV 19.9 mm -> 양쪽 여유 1.95 mm OK
[샘플링] 최소 형상 0.2 mm 슬롯 -> 14.5 점/폭 OK
[간격] 가장 빠듯한 쌍 F03-4->F04: 간격 3.00 mm, 필요 2.58 mm OK
     id             name  eval_pct
    F01        L자 비대칭 표식      61.5
  F02-1 얇은 벽 1줄(0.42 mm)       0.0
  F02-2 얇은 벽 2줄(0.84 mm)      34.8
  F02-3 얇은 벽 3줄(1.26 mm)      53.6
  F02-4 얇은 벽 4줄(1.68 mm)      63.1
  F03-1      계단 2.2 mm 면      78.4
  F03-2      계단 2.6 mm 면      78.4
  F03-3      계단 3.6 mm 면      78.4
  F03-4      계단 5.6 mm 면      78.4
    F04      평면 패드 12x12      91.5
 F05-10          원기둥 Ø10      89.8
  F05-2           원기둥 Ø2      54.4
  F05-4           원기둥 Ø4      75.4
  F05-6           원기둥 Ø6      83.3
  F06-2       구멍 Ø2 (관통)      17.0
  F06-4       구멍 Ø4 (관통)      53.4
  F06-6       구멍 Ø6 (관통)      68.0
 F06-10      구멍 Ø10 (관통)      80.4
F07-0.2        슬롯 0.2 mm       0.0
F07-0.4        슬롯 0.4 mm       0.0
F07-0.6        슬롯 0.6 mm      12.0
F07-0.8        슬롯 0.8 mm      31.4
F07-1.0        슬롯 1.0 mm      43.1
 F08-90          모서리 90°      61.0
 F08-60          모서리 60°      59.9
 F08-30          모서리 30°      44.3
[전체] 높이맵 (5000, 800), 평가 가능 81.4 %
```

**출력 읽는 법**
- 점검 1~3이 모두 OK입니다. 가장 빠듯한 간격은 계단 최고면(3.6 mm 높이) 뒤의 평면 패드로, 간격 3.00 mm ≥ 필요 2.58 mm 입니다.
- `eval_pct` 는 "카메라에 보이고 엣지 띠 밖인 면적의 비율"입니다. 얇은 벽 1줄(0.42 mm)과 슬롯 0.2·0.4 mm가 0 %인 것은 **실패가 아니라 설계 의도**입니다. 이 형상들은 폭이 0.5 mm(엣지 띠 2개) 미만이라 높이 지표 대상이 아니고, 윤곽·치수(H6, H7)로 평가합니다.
- 구멍 Ø2가 17 %로 낮은 것은 깊이 2 mm 구멍 바닥의 절반 이상이 그림자이기 때문입니다 (2 − 1.155 = 0.845 mm만 보임). 구멍 지름은 **윗면 가장자리 윤곽**으로 재므로 문제없습니다.

### 6.2 계단 블록 ASCII STL 쓰기·다시 읽기·검사 (`scripts/e3_stl.py`)

계단 단면(X-Z)을 Y 방향으로 밀어낸 입체를 numpy만으로 만듭니다. 오른쪽 아래 꼭짓점에서는 계단 단면의 모든 꼭짓점이 보이므로, 그 점에서 부채꼴로 삼각형을 나누면 됩니다.

```python
"""E3 계단 블록(단차 0.2/0.4/1.0/2.0 mm)을 numpy 만으로 ASCII STL 로 쓰고, 다시 읽어서 검사
실행: python e3_stl.py   -> step_block_v1.stl
원리: X-Z 평면의 계단 모양 단면(다각형)을 Y 방향으로 D 만큼 밀어낸(extrude) 입체
"""
import numpy as np
from collections import Counter

X_EDGES = [0, 2, 5, 8, 11, 14]          # 계단 경계 X [mm]
Z_TOPS = [2.0, 2.2, 2.6, 3.6, 5.6]      # 각 칸의 윗면 높이 [mm] (단차 0.2, 0.4, 1.0, 2.0)
DEPTH = 10.0                            # Y 방향 길이 [mm]


def stair_profile(xe, zt):
    """반시계 방향 단면 꼭짓점 (x, z) 목록"""
    n = len(zt)
    pts = [(xe[0], 0.0), (xe[n], 0.0), (xe[n], zt[n - 1])]
    for i in range(n - 1, 0, -1):       # 오른쪽 위에서 왼쪽으로 계단을 내려옴
        pts += [(xe[i], zt[i]), (xe[i], zt[i - 1])]
    pts.append((xe[0], zt[0]))
    return np.array(pts)


def extrude(profile, depth):
    """단면을 Y 방향으로 밀어 닫힌 삼각형 메시 (N, 3, 3) 를 만듦. 모든 법선은 바깥쪽"""
    P0 = np.c_[profile[:, 0], np.zeros(len(profile)), profile[:, 1]]  # y = 0 면
    P1 = P0 + [0, depth, 0]                                           # y = depth 면
    tris, n = [], len(profile)
    # 양 끝 뚜껑: 오른쪽 아래 꼭짓점(1번)에서 부채꼴로 나눔 (계단 단면은 이 점에서 모두 보임)
    order = [2 + k for k in range(n - 2)] + [0]
    for a, b in zip(order[:-1], order[1:]):
        tris.append([P0[1], P0[a], P0[b]])          # y=0 뚜껑, 법선 -Y
        tris.append([P1[1], P1[b], P1[a]])          # y=depth 뚜껑, 법선 +Y (순서 반대)
    # 옆면: 단면의 각 변마다 사각형 1개 = 삼각형 2개
    for i in range(n):
        j = (i + 1) % n
        tris.append([P0[i], P1[j], P0[j]])
        tris.append([P0[i], P1[i], P1[j]])
    return np.array(tris)


def write_ascii_stl(path, tris, name="step_block"):
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for t in tris:
            nrm = np.cross(t[1] - t[0], t[2] - t[0])
            nrm /= np.linalg.norm(nrm)
            f.write(f"  facet normal {nrm[0]:.6e} {nrm[1]:.6e} {nrm[2]:.6e}\n    outer loop\n")
            for v in t:
                f.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {name}\n")


def read_ascii_stl(path):
    """ASCII STL 을 읽어 (삼각형 (N,3,3), 파일에 적힌 법선 (N,3)) 반환"""
    verts, normals = [], []
    with open(path) as f:
        for line in f:
            w = line.split()
            if w[:2] == ["facet", "normal"]:
                normals.append([float(v) for v in w[2:5]])
            elif w and w[0] == "vertex":
                verts.append([float(v) for v in w[1:4]])
    return np.array(verts).reshape(-1, 3, 3), np.array(normals)


def check_mesh(tris, normals):
    """STL 유효성 검사 결과를 dict 로 반환"""
    key = lambda v: tuple(np.round(v, 6))
    edges = Counter()
    for t in tris:                                   # 방향 있는 변(a->b) 개수 세기
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            edges[(key(t[a]), key(t[b]))] += 1
    # 닫힌(물샐틈없는) 메시: 모든 변이 정확히 1번, 그 반대 방향 변도 정확히 1번
    watertight = all(c == 1 and edges.get((b, a), 0) == 1 for (a, b), c in edges.items())
    vol = np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6
    calc_n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    calc_n /= np.linalg.norm(calc_n, axis=1, keepdims=True)
    agree = np.einsum("ij,ij->i", calc_n, normals).min()
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    return {"n_facets": len(tris), "watertight": watertight, "volume_mm3": vol,
            "normal_agree_min": agree, "min_area_mm2": area.min(),
            "bbox_min": tris.reshape(-1, 3).min(0), "bbox_max": tris.reshape(-1, 3).max(0)}


if __name__ == "__main__":
    prof = stair_profile(X_EDGES, Z_TOPS)
    tris = extrude(prof, DEPTH)
    write_ascii_stl("step_block_v1.stl", tris)
    tris2, nrm2 = read_ascii_stl("step_block_v1.stl")
    r = check_mesh(tris2, nrm2)
    expected = sum((X_EDGES[i + 1] - X_EDGES[i]) * Z_TOPS[i] for i in range(len(Z_TOPS))) * DEPTH
    print(f"단면 꼭짓점 {len(prof)}개, 삼각형 {r['n_facets']}개")
    print(f"물샐틈없음(watertight): {r['watertight']}")
    print(f"부피 {r['volume_mm3']:.4f} mm³ (기대 {expected:.4f}) -> 양수면 법선이 바깥쪽")
    print(f"법선 일치(최소 코사인) {r['normal_agree_min']:.6f}, 최소 삼각형 면적 {r['min_area_mm2']:.3f} mm²")
    print("경계 상자", r["bbox_min"], "~", r["bbox_max"])
    assert r["watertight"] and abs(r["volume_mm3"] - expected) < 1e-3 and r["normal_agree_min"] > 0.999
    print("STL 검사 통과")
```

**실행 예시와 기대 출력**

```
$ python e3_stl.py
단면 꼭짓점 12개, 삼각형 44개
물샐틈없음(watertight): True
부피 460.0000 mm³ (기대 460.0000) -> 양수면 법선이 바깥쪽
법선 일치(최소 코사인) 1.000000, 최소 삼각형 면적 1.000 mm²
경계 상자 [0. 0. 0.] ~ [14.  10.   5.6]
STL 검사 통과
```

- 부피 460 mm³ = (2 x 2.0 + 3 x 2.2 + 3 x 2.6 + 3 x 3.6 + 3 x 5.6) x 10. 손 계산과 일치하고 **양수**이므로 법선이 모두 바깥을 향합니다.
- 삼각형 44개 = 뚜껑 2 x 10 + 옆면 12변 x 2.
- 만든 STL을 슬라이서에 열어 계단 높이(2.0/2.2/2.6/3.6/5.6 mm)가 층 미리보기와 맞는지 한 번 더 확인합니다.

### 6.3 STL 검사 단위 테스트 (`tests/test_e3_stl.py`)

```python
import numpy as np
from e3_stl import stair_profile, extrude, write_ascii_stl, read_ascii_stl, check_mesh


def test_single_box_is_valid(tmp_path):
    # 계단 1칸 = 직육면체 10 x 5 x 2 -> 부피 100 mm³, 삼각형 12개
    tris = extrude(stair_profile([0, 10], [2.0]), 5.0)
    p = tmp_path / "box.stl"
    write_ascii_stl(p, tris)
    r = check_mesh(*read_ascii_stl(p))
    assert r["n_facets"] == 12 and r["watertight"]
    assert abs(r["volume_mm3"] - 100.0) < 1e-6


def test_broken_mesh_is_detected():
    tris = extrude(stair_profile([0, 2, 5], [1.0, 2.0]), 3.0)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    r = check_mesh(tris[:-1], nrm[:-1])          # 삼각형 하나를 빼면 구멍이 생김
    assert not r["watertight"]
```

```
$ python -m pytest -q test_e3_stl.py
..                                                                       [100%]
2 passed
```

두 번째 테스트는 "일부러 망가뜨린 메시를 검사기가 잡아내는가"를 확인합니다. 검사 코드 자체를 검사하는 습관이 중요합니다 (J3).

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 오차 종류 커버리지 | 형상-지표 대응표 | A1의 7개 오차 종류 모두 ≥ 1개 형상 (E3-A/B/C 합산) |
| FOV | 6.1 점검 1 | 시편 폭 + 2 x 1.0 mm ≤ FOV |
| 샘플링 | 6.1 점검 2 | 가장 작은 형상 폭 / δx ≥ 5점 (A2) |
| 그림자 간격 | 6.1 점검 3 | 모든 형상 쌍 Y 간격 ≥ h·tanθ + 2 x 엣지 띠 |
| 높이 평가 대상 형상 | 6.1 형상별 eval_pct | 평면 패드·계단 면·원기둥 Ø6/Ø10 ≥ 75 % |
| STL 유효성 | 6.2 `check_mesh()` + 6.3 pytest | watertight, 부피 오차 < 0.001 mm³, 법선 일치 > 0.999 |
| 슬라이싱 확인 | 설계 vs G코드 기준 높이맵 형상별 면적 비 | 0.5 mm 이상 형상은 0.9~1.1. 벗어난 형상은 목록화(G5) |
| 버전 묶음 | 파일 점검 | CAD·STL·프로파일·G코드·해시·형상 목록이 같은 `_v1` 로 저장 |
| 실측 평가 영역 | S01 첫 측정 | 형상별 평가 영역 %가 설계 점검값 ±10 %p |
| M4 | S01 전체 파이프라인 | 형상별 H5~H7 지표표 + J4 그림 자동 생성 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 시편을 FOV보다 크게 설계 | 여러 번 스캔해 이어 붙여야 함, 이음매 오차 | 폭 16 mm 이하, Y로 길게. 큰 것은 E3-C처럼 별도 시편 |
| 형상을 빽빽하게 배치 | 앞 형상 그림자가 뒤 형상을 덮어 평가 영역 소실 | 6.1 점검 3 (간격 규칙) 통과할 때까지 재배치 |
| 좁은 슬롯·벽을 X 방향으로 길게 | 슬롯 바닥·벽 사이가 모두 그림자 | Y 방향으로 길게 (2.4절) |
| 오버행·언더컷 형상 포함 | 2.5D 높이맵에 표현 불가, 기준과 비교 불가 | 위에서 보이는 형상만 사용 |
| 벽 두께를 선폭과 무관하게 (예: 0.5 mm) | 슬라이서가 벽을 빼먹거나 이상한 채움 | 선폭 정수배 (0.42, 0.84 …) |
| 출력마다 G코드를 다시 슬라이싱 | 같은 시편인데 경로가 미묘하게 달라짐 | G코드 1개 + SHA-256 해시 고정, 메타데이터에 해시 기록 |
| 슬라이서 프로파일 미보관 | 몇 달 뒤 같은 G코드를 재현 못 함 | 프로파일 파일을 G코드와 같은 폴더·같은 버전명으로 |
| CAD와 형상 목록 불일치 | 분석 코드가 엉뚱한 영역을 원기둥으로 계산 | 형상 목록 CSV를 단일 기준으로, 슬라이싱 확인 단계에서 면적 비교 |
| 스커트·브림이 시편에 붙음 | 경계 근처 과충진처럼 보임 | 스커트 5 mm 이상 띄우고 G4 `M_type` 으로 제외 |
| 비대칭 표식 없음 | X·Y 뒤집힘을 모름 | L자 표식 필수, 리포트 그림에서 눈으로 확인 |
| L자 두 다리 길이를 같게 | 대각선 대칭이라 X↔Y 뒤바뀜(전치)을 구분 못 함 | 다리 길이를 6 mm / 4 mm 처럼 다르게 |
| 출력 직후 뜨거운 상태로 측정 | PLA 50 mm에서 5 °C당 약 17 µm 팽창 (C6) | 베드 끄고 실온 도달 후 측정, 온도 기록 |

## 9. 위험 요소

- **슬라이서가 작은 형상을 제거**: 0.2/0.4 mm 슬롯, 1줄 벽은 슬라이서 설정에 따라 사라지거나 막힙니다. 비교 기준이 G코드이므로 사라진 형상은 기준에도 없어서 "오차 0"처럼 보일 수 있습니다 → 슬라이싱 확인 단계에서 반드시 목록화하고, 보고서에 "G코드 단계에서 제거된 형상"을 따로 적습니다.
- **바닥판 휨**: 100 mm 길이 바닥판이 식으면서 휘면(모서리 들뜸) 모든 높이 지표에 섞입니다 → H3의 베드 기준은 시편 **주변 베드**로 잡고, 바닥판 윗면 평면도를 별도 지표로 보고합니다. 휨이 크면 바닥판을 3 mm로 늘리는 v2를 검토합니다.
- **FOV 실측이 설계와 다름**: 실제 FOV가 19.9 mm보다 작으면 폭 16 mm가 빠듯해집니다 → D1/D2 후 실제 FOV를 확인하고, 여유 < 1 mm면 폭 14 mm 버전(형상 축소)을 준비합니다.
- **기준 마커와 시편 간섭**: 구 마커가 시편 그림자 영역이나 스커트와 겹치면 중심 추정이 나빠집니다 → 마커와 시편 사이 Y 간격 ≥ 5 mm.
- **설계 변경의 연쇄 효과**: v1 → v2로 바꾸면 이전 데이터와 직접 비교가 어려워집니다 → 본 실험(W18) 전에 설계를 동결하고, 이후 변경은 새 버전 ID로만 합니다.

## 10. 기록 양식

**`data/gcode/E3A_features_v1.csv`** (6.1 코드 출력 + 손으로 `main_metric` 열 추가)

```csv
id,name,purpose,kind,z_top_mm,xmin,ymin,xmax,ymax,area_mm2,main_metric
F01,L자 비대칭 표식,좌표축 방향 확인,add,3.0,1.5,1.5,7.5,5.5,12.75,H6 윤곽 / C4 축
```

**`data/gcode/E3A_artifact_v1.yaml`** (버전 묶음 정보)

```yaml
artifact_id: E3A
version: v1
design_frozen: false            # 본 실험 전 true 로
cad_file: E3A_artifact_v1.step
stl_file: E3A_artifact_v1.stl
features_csv: E3A_features_v1.csv
slicer: ""                      # 슬라이서 이름과 버전
slicer_profile: E3A_artifact_v1.ini
gcode_file: E3A_artifact_v1.gcode
gcode_sha256: ""
layer_height_mm: 0.2
line_width_mm: 0.42
material: ""                    # E1 결론 (제조사·색·로트)
fiducials: "C3 구 4개: (2.5,-8) (13.5,-8) (2.5,108) (13.5,108) mm"
removed_by_slicer: []           # 슬라이싱 확인에서 사라진 형상 ID
notes: ""
```

**`results/E3/E3A_slicing_check_v1.csv`**

```csv
feature_id,design_area_mm2,gcode_ref_area_mm2,ratio,status,notes
```

**출력 기록 (`data/experiments.csv` 추가 열 예)**

```csv
specimen_id,artifact_version,gcode_sha256,print_datetime,material_lot,nozzle_temp_C,bed_temp_C,room_temp_C,bed_position,operator,notes
S01,E3A_v1,,,,,,,,,
```

## 11. 참고 자료

- ISO/ASTM 52902 — Additive manufacturing — Test artifacts — Geometric capability assessment of additive manufacturing systems
- NIST AM Test Artifact (미국 국립표준기술연구소가 공개한 적층제조 표준 테스트 아티팩트 설계와 관련 보고서)
- ISO/ASTM 52900 — Additive manufacturing — General principles — Fundamentals and vocabulary (용어)
- VDI/VDE 2634 Part 2 — Optical 3-D measuring systems (광학 측정용 시험 형상 개념)
- STL 형식: 3D Systems의 StereoLithography Interface Specification (ASCII/바이너리 STL 정의)
- Shapely 2.x 공식 문서 — `Polygon`, `Point.buffer`, `shapely.contains_xy`
- 상위 문서: [BLUEPRINT.md](../../BLUEPRINT.md) A1, A2, B1, C3, C4, E2, E3, G4, G5, H5~H7
