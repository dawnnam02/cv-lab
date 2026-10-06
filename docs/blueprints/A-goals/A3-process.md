# A3. 가공 공정 확정

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: A. 목표·요구사항

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-12 (W1) |
| 우선순위 | 긴급 |
| 트랙 | 관리·기획 |
| 선행 요소 | 없음 (프로젝트 첫 주 결정). [A1 오차의 정의](A1-error-definition.md)와 같은 주에 병행 |
| 후행 요소 | [A2 요구 정밀도와 사양 도출](A2-precision-spec.md) · [C2 측정 시점](../C-mechanics/C2-measurement-timing.md) · [E1 표면 광학 특성](../E-specimen/E1-surface-optics.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) · [G2 비드/공구 형상 모델](../G-reference/G2-bead-model.md) · [G5 CAD 기준과의 관계](../G-reference/G5-cad-relation.md) |
| 관련 마일스톤 | **M0** (2026-10-19: 사양표 + 부품 목록 확정). 공정이 정해져야 A2 사양표와 G1 파서(W3–4) 작업이 시작됨 |

---

## 1. 목적

G코드를 실행할 **장비(공정)의 종류**를 확정하고, 그 장비의 **고정 조건**(기종, 펌웨어, 슬라이서/CAM 버전, 노즐·공구, 재료)을 문서로 남깁니다.

공정이 중요한 이유는 **G코드 선(두께 없는 경로)을 실제 기준 형상으로 바꾸는 규칙이 공정마다 다르기** 때문입니다(G2).

| 공정 | G코드 경로의 의미 | 기준 형상 규칙 | 오차의 대표 원인 |
|---|---|---|---|
| **FDM 3D프린터** | 노즐 중심 경로 | 경로 + **선폭 w** + **층 높이 h** → 재료가 **쌓이는** 형상 | 과/미압출, 수축, 모서리 뭉개짐, 층 밀림 |
| **CNC 밀링** | 공구 중심(또는 끝) 경로 | 경로 + **공구 반경/형상** → 재료가 **깎이는** 형상 | 공구 휨, 마모, 백래시, 열변형 |
| **레이저 가공/마킹** | 빔 중심 경로 | 경로 + **커프(kerf) 폭** → 재료가 **제거되는** 형상 | 커프 변화, 초점 이탈, 열영향부 |

이 프로젝트는 청사진 권장대로 **FDM을 기본 공정**으로 하되(부록1 #1 "FDM (확인 필요)"), 이번 주에 **실제 연구실 장비로 확인**하고 확정합니다.

---

## 2. 배경 지식 (초보자용)

### 2.1 G코드란
G코드는 장비에게 "어디로, 얼마나 빠르게, 무엇을 하면서 움직여라"를 한 줄씩 지시하는 텍스트 파일입니다.

```gcode
G21            ; 단위 mm
G90            ; 절대 좌표
M83            ; 압출(E)은 상대값
G1 Z0.2 F600   ; Z = 0.2 mm 로 이동 (층 높이)
G1 X30 Y10 E0.665 F1800  ; (30,10)까지 이동하면서 필라멘트 0.665 mm 밀어냄
```
- `G0/G1`: 직선 이동, `G2/G3`: 원호 이동, `E`: 압출량(FDM), `M3/M4 S…`: 스핀들 또는 레이저 출력(CNC/레이저), `;` 뒤는 주석
- **같은 G코드라도 펌웨어(Marlin, Klipper, RepRapFirmware, GRBL 등)에 따라 해석이 조금씩 다릅니다.** 그래서 펌웨어 종류와 버전을 기록합니다.

### 2.2 쌓는 공정과 깎는 공정의 부호
A1의 부호 규칙 `오차 = 측정 − 기준 (+ = 재료 과다)` 은 공정과 관계없이 같습니다. 다만 의미가 달라 보일 수 있습니다.
- FDM: + 는 "필요보다 많이 쌓임"(과압출)
- CNC: + 는 "덜 깎임"(공구 휨 등) — 재료가 남아 있으므로 역시 + 입니다.

### 2.3 이 프로젝트가 위에서 보는(2.5D) 측정이라는 점
레이저 삼각측량은 위에서 보이는 면만 측정합니다. FDM은 **층별 측정(C2 2단계)** 으로 내부 층까지 볼 수 있다는 장점이 있고, CNC는 깎인 바닥과 측벽 일부만 보입니다. 공정 선택은 측정 가능한 오차 종류(A1)와 직결됩니다.

### 2.4 "통제 변수"라는 개념
실험에서 바꾸는 것(예: 출력 속도)을 **독립변수**, 바꾸지 않고 고정하는 것(장비, 재료, 노즐, 슬라이서 버전, 실내 온도)을 **통제 변수**라고 합니다. 통제 변수가 실험 중에 몰래 바뀌면(펌웨어 자동 업데이트, 노즐 교체) 결과 차이가 어디서 왔는지 알 수 없습니다. A3의 산출물은 바로 이 **통제 변수 목록**입니다.

---

## 3. 입력과 산출물

| 구분 | 항목 | 형식·파일명 | 비고 |
|---|---|---|---|
| 입력 | 연구실 보유 장비 목록 | 장비명, 기종, 위치, 사용 가능 시간 | 공동기기 포함 |
| 입력 | 연구 질문 초안 | A1 단계 1 | 어떤 공정 변수를 바꿀지 |
| 입력 | 샘플 G코드 | 슬라이서/CAM이 생성한 `.gcode` / `.nc` 파일 1개 이상 | 6장 스크립트로 요약 |
| 산출물 | **공정 결정서** | `docs/decisions/A3-process-decision.md` (10장 양식) | 공정, 기종, 펌웨어, 슬라이서 버전, 재료, 노즐/공구 |
| 산출물 | 고정 슬라이서 프로파일 | `specimens/profiles/<프로파일명>.ini` (또는 `.3mf`/`.json`, 슬라이서 형식대로) | E3 시편 관리와 공유 |
| 산출물 | 샘플 G코드 요약 | `docs/decisions/A3-gcode-summary.txt` (6.2 출력) | G1 파서 요구사항 |
| 산출물 | 기준 형상 파라미터 | `config/default.yaml` 의 `gcode:` 블록 (`line_width_mm: 0.42`, `layer_height_mm: 0.2`, `width_model`) | J2, G2 |
| 산출물 | 공정 선택 점수표 | `docs/decisions/A3-decision-matrix.csv` | 6.1 출력 |

---

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 공정 | FDM / CNC 밀링 / 레이저 가공·마킹 | **FDM** (장비 확인 후 확정) | 접근성·반복 제작 비용, 층별 측정 가능, 청사진 기본 예시 |
| 장비 대수 | 1대 / 2대 이상 | **1대 고정** | 장비 간 차이가 섞이지 않게. 장비 비교는 별도 실험 요인으로만 |
| 펌웨어 | 현재 버전 유지 / 업데이트 | **현재 버전 기록 후 동결** (실험 기간 중 업데이트 금지) | 가감속·압출 보정 설정이 바뀌면 오차가 변함 |
| 슬라이서 | 종류·버전 | **한 가지 슬라이서, 한 버전 고정**, 프로파일 파일 저장 | 같은 STL도 버전마다 G코드가 다름 |
| 원호 명령(G2/G3) | 허용 / 끔 | **끔 권장** (슬라이서의 arc fitting 해제) | G1 파서를 단순하게. 허용하면 G1 파서가 원호를 지원해야 함 |
| 압출 모드 | 절대(M82) / 상대(M83) | 어느 쪽이든 **기록** (파서가 둘 다 처리) | G2 압출량 기반 선폭 계산에 필요 |
| 노즐 / 선폭 / 층 높이 | 0.4 mm 노즐, 0.42 mm 선폭, 0.2 mm 층 | **0.4 / 0.42 / 0.2 mm** | 청사진 G2, J2 설정 예시 |
| 재료 | PLA 색·종류 | **회색 불투명 PLA, 한 제조사·한 로트** | E1: 반투명·광택은 측정 오차가 큼 |
| 측정 시점 | 공정 후 베드 위 / 떼어 냄 / 층별 | **1단계: 공정 후 베드 위** | C2: 좌표계 유지 → 위치 오차 측정 가능 |
| 베드 | 고정 / 탈착식 | 탈착식이면 **키네마틱 마운트** 검토 | C3: 재장착 반복성 |
| CNC/레이저 선택 시 | – | 공구 지름·종류 또는 커프 폭을 **실측**해서 기록 | G2 기준 형상 파라미터 |

---

## 5. 수행 절차

### 단계 1. 사용 가능 장비 조사 (W1 월–화)
- [ ] 연구실·공동기기원의 FDM/CNC/레이저 장비 목록 작성 (기종, 빌드/작업 영역 mm, 위치)
- [ ] 장비별로 "주 10시간 이상 사용 가능한가", "펌웨어 설정을 바꿀 권한이 있는가", "센서를 장착할 공간(위쪽 ≥ 150 mm)이 있는가" 확인
- [ ] 장비 앞에 측정대를 둘 수 있는지 사진으로 기록

### 단계 2. 공정 선택 점수표 작성 (W1 화)
- [ ] 6.1 `a3_decision.py` 의 기준·가중치·점수를 팀이 직접 매김 (1 = 나쁨 … 5 = 좋음)
- [ ] 1순위와 2순위 차이가 **0.3점 미만**이면 지도교수와 논의 후 결정
- [ ] 점수표를 `A3-decision-matrix.csv` 로 저장

### 단계 3. 장비 고정 조건 기록 (W1 수)
- [ ] 기종, 일련번호, 펌웨어 종류·버전 (프린터 화면 또는 `M115` 응답)
- [ ] 노즐 지름(0.4 mm), 노즐 재질, 마지막 교체일
- [ ] 슬라이서 이름·버전, 프로파일 파일 내보내기 → `specimens/profiles/`
- [ ] 재료: 제조사, 색, 로트 번호, 필라멘트 지름 실측값(캘리퍼스로 5곳 평균, 예: 1.75 ± 0.02 mm)
- [ ] 베드 온도(예: 60 °C), 노즐 온도(예: 210 °C), 측정 전 냉각 규칙(C6: 실온까지 냉각)

### 단계 4. 샘플 G코드 생성과 점검 (W1 목)
- [ ] 20×20×2 mm 사각 블록을 고정 프로파일로 슬라이스
- [ ] 6.2 `a3_process_check.py` 로 요약: 단위(G21), 좌표 모드(G90), 압출 모드(M82/M83), 층 높이, 선폭, 원호 명령 개수, Z 높이 목록
- [ ] 원호 명령이 0개인지 확인 (아니면 슬라이서에서 arc fitting 해제 후 재생성)
- [ ] 경로 종류 주석(`;TYPE:` 등) 이 있는지 확인 → G4 경로 종류별 마스킹에 필요

### 단계 5. 기준 형상 파라미터 확정 (W1 목)
- [ ] 6.3 `reference_model_params()` 로 공정별 기준 형상 파라미터 출력
- [ ] FDM: 명목 선폭 0.42 mm 와 압출량 기반 선폭 w_eff 를 비교 (차이가 ±5 % 를 넘으면 슬라이서 압출 배율·필라멘트 지름 설정 재확인)
- [ ] `config/default.yaml` 의 `gcode:` 블록에 반영

### 단계 6. 시험 출력 1회 (W1 금)
- [ ] 단계 4의 블록을 출력, 출력 시간·실내 온도 기록
- [ ] 캘리퍼스로 외형 3방향 측정 (예: 20.0 mm 설계 → 측정 기록). 치수 차이가 ±0.3 mm 를 넘으면 장비 상태 점검(벨트 장력, E-스텝 보정) 후 재출력
- [ ] 같은 G코드로 2회 더 출력해서 캘리퍼스 치수 범위가 0.1 mm 이내인지 확인 (장비 자체 반복성의 대략 확인)

### 단계 7. 결정서 확정 (W1 금–일, 2026-10-12)
- [ ] 10장 양식 작성, 버전 v1.0, 지도교수 승인
- [ ] 장비에 "실험 기간 중 펌웨어 업데이트·노즐 교체 시 담당자 통보" 표지 부착
- [ ] A2 담당에게 층 높이·선폭·최소 형상 크기 전달, G1 담당에게 G코드 요약 전달

---

## 6. Python 구현

### 6.1 공정 선택 가중 점수표 (`a3_decision.py`)

```python
# a3_decision.py — 공정 선택 가중 점수표 (점수는 연구실이 직접 매김: 1=나쁨 … 5=좋음)
import pandas as pd

criteria = {            # 기준: 가중치 (합 = 1.0)
    "장비 접근성": 0.25,
    "시편 반복 제작 비용": 0.20,
    "레이저 측정 적합성(표면)": 0.20,
    "기준 모델 구현 난이도(낮을수록 5)": 0.15,
    "연구 질문과의 관련성": 0.20,
}
scores = pd.DataFrame({
    "FDM":    [5, 5, 4, 4, 4],
    "CNC":    [3, 2, 2, 3, 4],
    "레이저": [2, 4, 3, 4, 3],
}, index=list(criteria))

weights = pd.Series(criteria)
assert abs(weights.sum() - 1.0) < 1e-9, "가중치 합이 1이 아님"
total = scores.mul(weights, axis=0).sum().sort_values(ascending=False)
print(scores.assign(가중치=weights))
print("\n가중 합계(5점 만점):")
print(total.round(2).to_string())
print("\n1순위:", total.index[0], "/ 2순위와 차이: %.2f" % (total.iloc[0] - total.iloc[1]))
```

**줄별 핵심 설명**
- `criteria`: 판단 기준과 가중치. 가중치 합이 1.0 이어야 하므로 `assert` 로 확인합니다(틀리면 실행이 멈춤).
- `scores`: 팀이 매긴 1~5점. 아래 숫자는 **예시**이며, 연구실 사정에 맞게 바꿉니다.
- `scores.mul(weights, axis=0)`: 각 행(기준)의 점수에 그 기준의 가중치를 곱합니다. `.sum()` 으로 공정별 합계.

**실행 예시와 기대 출력**
```
$ python3 a3_decision.py
                      FDM  CNC  레이저   가중치
장비 접근성                  5    3    2  0.25
시편 반복 제작 비용             5    2    4  0.20
레이저 측정 적합성(표면)          4    2    3  0.20
기준 모델 구현 난이도(낮을수록 5)    4    3    4  0.15
연구 질문과의 관련성             4    4    3  0.20

가중 합계(5점 만점):
FDM    4.45
레이저    3.10
CNC    2.80

1순위: FDM / 2순위와 차이: 1.35
```
(표의 열 정렬은 터미널 글꼴에 따라 조금 어긋나 보일 수 있습니다.)

### 6.2 샘플 G코드 요약 (`a3_process_check.py`)

슬라이서/CAM이 만든 G코드를 훑어서 공정 추정, 단위, 압출 모드, 층 높이, 원호 명령 유무를 요약합니다. 파일 경로를 주지 않으면 내장 샘플을 사용합니다.

```python
# a3_process_check.py — G코드 파일을 훑어보고 공정 종류와 핵심 설정을 기록용으로 요약
import re
import sys
from pathlib import Path

SAMPLE = """; generated by PrusaSlicer 2.7.1
; layer_height = 0.2
; first_layer_height = 0.2
; extrusion_width = 0.42
; filament_diameter = 1.75
; nozzle_diameter = 0.4
M104 S210
M140 S60
G21 ; mm 단위
G90 ; 절대 좌표
M83 ; 압출 상대 모드
G28
G1 Z0.2 F600
;TYPE:Skirt
G1 X10 Y10 F3000
G1 X30 Y10 E0.665
;TYPE:External perimeter
G1 X30 Y30 E0.665
G1 X10 Y30 E0.665
G1 X10 Y10 E0.665
G1 Z0.4 F600
G1 X10 Y30 E0.665
G2 X20 Y40 I10 J0 E0.52
"""


def summarize_gcode(text):
    info = {"comments": {}, "counts": {}}
    # 슬라이서가 주석으로 남긴 설정값: "; key = value"
    for key in ["layer_height", "first_layer_height", "extrusion_width",
                "filament_diameter", "nozzle_diameter"]:
        m = re.search(r"^;\s*%s\s*=\s*([0-9.]+)" % key, text, re.M)
        info["comments"][key] = float(m.group(1)) if m else None
    m = re.search(r"^;\s*generated by (.+)$", text, re.M | re.I)
    info["slicer"] = m.group(1).strip() if m else "알 수 없음"

    code_lines = [ln.split(";")[0].strip().upper() for ln in text.splitlines()]
    code_lines = [ln for ln in code_lines if ln]
    c = info["counts"]
    c["G0/G1"] = sum(bool(re.match(r"G0?[01]\b", ln)) for ln in code_lines)
    c["G2/G3(원호)"] = sum(bool(re.match(r"G0?[23]\b", ln)) for ln in code_lines)
    c["E 포함 이동"] = sum(bool(re.match(r"G0?[0-3]\b", ln)) and " E" in " " + ln
                         for ln in code_lines)
    c["스핀들/레이저 M3·M4"] = sum(bool(re.match(r"M0?[34]\b", ln)) for ln in code_lines)
    zs = [float(z) for ln in code_lines for z in re.findall(r"Z(-?[0-9.]+)", ln)]
    info["z_levels"] = sorted(set(zs))
    info["units"] = "mm" if "G21" in code_lines else ("inch" if "G20" in code_lines else "미지정(펌웨어 기본)")
    info["extrusion_mode"] = "상대(M83)" if "M83" in code_lines else (
        "절대(M82)" if "M82" in code_lines else "미지정")

    # 공정 추정 규칙(참고용 — 최종 판단은 사람이 장비를 보고 확정)
    if c["E 포함 이동"] > 0:
        guess = "FDM(적층)"
    elif c["스핀들/레이저 M3·M4"] > 0 and len(info["z_levels"]) <= 2:
        guess = "레이저 가공/마킹 가능성"
    elif c["스핀들/레이저 M3·M4"] > 0:
        guess = "CNC 밀링 가능성"
    else:
        guess = "판단 불가"
    info["process_guess"] = guess
    return info


if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text(errors="ignore") if len(sys.argv) > 1 else SAMPLE
    s = summarize_gcode(text)
    print("슬라이서/CAM :", s["slicer"])
    print("공정 추정    :", s["process_guess"])
    print("단위         :", s["units"], "/ 압출 모드:", s["extrusion_mode"])
    for k, v in s["comments"].items():
        print("  %-20s %s" % (k, v))
    for k, v in s["counts"].items():
        print("  %-20s %d" % (k, v))
    print("Z 높이 목록  :", s["z_levels"])
    if s["counts"]["G2/G3(원호)"]:
        print("주의: 원호(G2/G3) 명령이 있음 → G1 파서가 원호를 지원해야 함")
```

**줄별 핵심 설명**
- `re.search(r"^;\s*%s\s*=\s*([0-9.]+)" ...)`: `; layer_height = 0.2` 같은 **슬라이서 설정 주석**을 찾습니다. 키 이름은 슬라이서마다 다를 수 있으므로(예: 다른 슬라이서는 `;Layer height: 0.2` 형식), 연구실 슬라이서의 주석을 열어 보고 키를 맞춥니다.
- `ln.split(";")[0]`: 주석을 떼어 낸 명령 부분만 남깁니다.
- `re.match(r"G0?[01]\b", ln)`: `G1`, `G01`, `G0`, `G00` 을 모두 직선 이동으로 셉니다. `\b` 는 `G10` 같은 다른 명령과 구분합니다.
- 공정 추정 규칙은 **참고용**입니다. 최종 판단은 장비를 보고 사람이 확정합니다.

**실행 예시와 기대 출력**
```
$ python3 a3_process_check.py
슬라이서/CAM : PrusaSlicer 2.7.1
공정 추정    : FDM(적층)
단위         : mm / 압출 모드: 상대(M83)
  layer_height         0.2
  first_layer_height   0.2
  extrusion_width      0.42
  filament_diameter    1.75
  nozzle_diameter      0.4
  G0/G1                8
  G2/G3(원호)            1
  E 포함 이동              6
  스핀들/레이저 M3·M4        0
Z 높이 목록  : [0.2, 0.4]
주의: 원호(G2/G3) 명령이 있음 → G1 파서가 원호를 지원해야 함
```
실제 파일은 `python3 a3_process_check.py specimens/gcode/block_20x20x2.gcode > docs/decisions/A3-gcode-summary.txt` 처럼 실행해 결과를 저장합니다. (내장 샘플의 헤더 주석은 형식 예시일 뿐, 특정 슬라이서 출력과 완전히 같다는 뜻은 아닙니다.)

### 6.3 공정 → 기준 형상 파라미터 (`a3_reference_model.py`)

선택한 공정을 G2/G3가 쓸 "G코드 선 → 기준 형상" 변환 파라미터로 바꿉니다. FDM은 압출량 기반 유효 선폭(청사진 G2 공식)도 계산합니다.

```python
# a3_reference_model.py — 선택한 공정을 "G코드 선 → 기준 형상" 변환 파라미터로 바꿔 주는 함수
import math


def reference_model_params(process, **p):
    """공정 이름과 설정값을 받아 G2/G3에서 쓸 기준 형상 파라미터 딕셔너리를 돌려준다."""
    process = process.upper()
    if process == "FDM":
        w, h = p["line_width_mm"], p["layer_height_mm"]
        area = (w - h) * h + math.pi * (h / 2) ** 2          # 사각형 + 양 끝 반원 (G2)
        return {
            "geometry": "additive",                          # 재료가 쌓임
            "path_offset_mm": w / 2,                         # 경로 양쪽으로 w/2 만큼 buffer
            "top_z_rule": "top = Z (노즐 높이)",
            "bottom_z_rule": "bottom = Z - h",
            "bead_area_mm2": round(area, 5),
            "material_sign": "+ = 재료 과다(쌓인 것이 많음)",
        }
    if process == "CNC":
        r = p["tool_diameter_mm"] / 2
        tool = p.get("tool_type", "flat")
        return {
            "geometry": "subtractive",                       # 재료가 깎임
            "path_offset_mm": r,                             # 공구 반경만큼 깎이는 폭
            "top_z_rule": "깎인 바닥 = 공구 끝 Z",
            "profile": "평평한 바닥" if tool == "flat" else "반지름 %.3f mm 원호" % r,
            "material_sign": "+ = 덜 깎임(재료 과다)",
        }
    if process == "LASER":
        kerf = p["kerf_mm"]
        return {
            "geometry": "cut_or_mark",
            "path_offset_mm": kerf / 2,                      # 빔 경로 양쪽으로 커프/2
            "top_z_rule": "Z 변화 거의 없음 (마킹 깊이는 별도 측정)",
            "material_sign": "+ = 덜 제거됨(재료 과다)",
        }
    raise ValueError("지원하지 않는 공정: %s" % process)


def extrusion_width(dE_mm, L_mm, h_mm, filament_d_mm=1.75):
    """압출량 기반 유효 선폭 w_eff (G2 공식): A = V/L, w = (A - πh²/4)/h + h"""
    V = dE_mm * math.pi * (filament_d_mm / 2) ** 2
    A = V / L_mm
    return (A - math.pi * h_mm ** 2 / 4) / h_mm + h_mm


if __name__ == "__main__":
    for proc, kw in [("FDM", {"line_width_mm": 0.42, "layer_height_mm": 0.2}),
                     ("CNC", {"tool_diameter_mm": 3.0, "tool_type": "ball"}),
                     ("LASER", {"kerf_mm": 0.15})]:
        print(proc, reference_model_params(proc, **kw))
    # 20 mm 선분, 층 0.2 mm, 압출 0.665 mm → 유효 선폭
    w = extrusion_width(0.665, 20.0, 0.2)
    print("압출량 기반 w_eff = %.3f mm (명목 0.42 mm 대비 %+.1f %%)" % (w, 100 * (w - 0.42) / 0.42))
```

**줄별 핵심 설명**
- `path_offset_mm`: G코드 경로를 양쪽으로 얼마나 넓혀(shapely `buffer`) 기준 영역을 만들지. FDM은 w/2, CNC는 공구 반경 r, 레이저는 커프/2.
- `bead_area_mm2`: FDM 비드 단면적 `A = (w − h)·h + π·(h/2)²` (사각형 + 양 끝 반원).
- `extrusion_width`: 압출 부피 `V = ΔE·π(d_f/2)²` → 단면적 `A = V/L` → `w_eff = (A − πh²/4)/h + h`.
- 지원하지 않는 공정 이름이 들어오면 `ValueError` 로 즉시 알려 줍니다(조용히 틀린 값을 쓰지 않도록).

**실행 예시와 기대 출력**
```
$ python3 a3_reference_model.py
FDM {'geometry': 'additive', 'path_offset_mm': 0.21, 'top_z_rule': 'top = Z (노즐 높이)', 'bottom_z_rule': 'bottom = Z - h', 'bead_area_mm2': 0.07542, 'material_sign': '+ = 재료 과다(쌓인 것이 많음)'}
CNC {'geometry': 'subtractive', 'path_offset_mm': 1.5, 'top_z_rule': '깎인 바닥 = 공구 끝 Z', 'profile': '반지름 1.500 mm 원호', 'material_sign': '+ = 덜 깎임(재료 과다)'}
LASER {'geometry': 'cut_or_mark', 'path_offset_mm': 0.075, 'top_z_rule': 'Z 변화 거의 없음 (마킹 깊이는 별도 측정)', 'material_sign': '+ = 덜 제거됨(재료 과다)'}
압출량 기반 w_eff = 0.443 mm (명목 0.42 mm 대비 +5.4 %)
```
**해석**: 20 mm 선분에서 명목 선폭 0.42 mm 에 정확히 해당하는 압출량은 `0.07542 × 20 / (π·0.875²) ≈ 0.627 mm` 입니다. 샘플 G코드의 0.665 mm 는 약 6 % 많으므로 w_eff 가 0.443 mm 로 나옵니다. 실제 G코드에서 이 차이가 ±5 % 를 넘으면 단계 5의 점검 대상입니다. 이처럼 **명목/압출량 기반 두 기준을 모두 계산**하는 것이 청사진 G2·부록1 #12 의 권장입니다.

---

## 7. 검증 방법과 완료 기준

| 확인 항목 | 방법 | 합격 기준 |
|---|---|---|
| 공정 확정 | 공정 결정서 | 공정·기종·일련번호·펌웨어 버전·슬라이서 버전이 모두 기재, 지도교수 승인 (2026-10-12) |
| 통제 변수 목록 | 결정서 10.1 | 노즐, 재료(제조사·색·로트), 필라멘트 지름 실측값, 베드/노즐 온도, 냉각 규칙 기재 |
| 프로파일 보존 | 파일 확인 | `specimens/profiles/` 에 프로파일 파일 존재, 같은 STL을 다시 슬라이스하면 G코드가 **바이트 단위로 동일** (`sha256sum` 비교, 날짜 주석 줄 제외) |
| G코드 형식 | 6.2 요약 | 단위 mm(G21), 절대 좌표(G90), 원호 명령 0개(또는 G1 파서 원호 지원 계획 명시), 경로 종류 주석 존재 |
| 선폭 일관성 | 6.3 | 압출량 기반 w_eff 가 명목 선폭의 ±5 % 이내 |
| 장비 기본 상태 | 시험 출력 3회, 캘리퍼스 | 20 mm 치수 오차 ±0.3 mm 이내, 3회 범위 ≤ 0.1 mm |
| 후속 인계 | 회의록 | A2(층 높이·선폭·최소 형상), G1(G코드 요약), E1/E3(재료) 담당자에게 전달 완료 |

---

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 슬라이서 버전을 기록하지 않음 | 몇 달 뒤 같은 STL에서 다른 G코드가 나와 재현 불가 | 버전 기록 + 자동 업데이트 끄기 + 설치 파일 보관 |
| 실험 도중 노즐 교체·펌웨어 업데이트 | 특정 날짜 이후 결과가 일정하게 달라짐 | 장비 표지, 변경 시 기록, 변경 전후 기준 시편 재측정 |
| 필라멘트 지름을 공칭 1.75 mm 로 가정 | 압출량 기반 선폭이 계통적으로 어긋남 | 캘리퍼스로 5곳 실측, 평균값을 설정·기록 |
| arc fitting 이 켜져 있음 | G1만 처리하는 파서에서 경로 일부 누락 → 기준 마스크에 구멍 | 슬라이서에서 해제 또는 파서에서 G2/G3 지원 |
| 상대/절대 압출 모드 혼동 | 압출량이 누적값으로 계산되어 선폭이 수십 mm로 나옴 | M82/M83 확인 후 파서 설정, 6.2 요약에서 표시 |
| 색이 다른 필라멘트를 섞어 사용 | 같은 조건인데 측정 높이가 수십 µm 차이 | 한 제조사·한 색·한 로트 고정 (E1) |
| 베드가 뜨거운 상태로 측정 | 열팽창으로 치수가 커 보임 (PLA 50 mm, 5 °C → 약 17 µm) | 실온까지 냉각 후 측정 (C6) |
| CNC/레이저인데 FDM 비드 모델을 그대로 사용 | 기준 형상 폭이 완전히 틀림 | `reference_model_params()` 로 공정별 분기, 공구 지름·커프 실측 |

---

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 연구실 FDM 장비 사용 시간 부족 (공용 장비) | 중 | 중 | 실험 시간대 예약, 장비 전용 기간을 K1 일정에 반영 |
| 장비 상태 불량 (벨트, 노즐 막힘)으로 반복성이 낮음 | 중 | 높음 | 단계 6 시험 출력으로 조기 확인, 정비 후 재확인 |
| 측정 센서를 장비에 장착할 공간 부족 | 중 | 중 | C1/C2: 공정 후 탈착 측정으로 전환 시 위치 오차는 측정 불가함을 명시 |
| 공정을 늦게 바꿈 (예: FDM → CNC) | 낮음 | 높음 | 기준 모델을 `reference_model_params()` 처럼 공정별로 분리해 코드 변경 범위 최소화 |
| 재료 로트 소진 | 중 | 중 | 실험 전체 필요량(시편 수 × 무게 × 1.5배) 일괄 구매 (K3 견적) |
| 펌웨어 종류에 따라 G코드 해석 차이 | 낮음 | 중 | 펌웨어 기록, 사용하는 명령을 G0/G1/G90/G91/G92/M82/M83 위주로 제한 |

---

## 10. 기록 양식

### 10.1 공정 결정서 (`docs/decisions/A3-process-decision.md` 내 YAML 블록)

```yaml
version: "1.0"
date: "2026-10-12"
approved_by: ""
process: FDM                  # FDM | CNC | LASER
machine:
  model: ""                   # 기종
  serial: ""
  location: ""
  firmware: {name: "", version: "", frozen_from: "2026-10-12"}
slicer:
  name: ""
  version: ""
  profile_file: "specimens/profiles/"
  arc_fitting: false
  extrusion_mode: ""          # M82 | M83
fdm:
  nozzle_diameter_mm: 0.4
  nozzle_replaced_on: ""
  line_width_mm: 0.42
  layer_height_mm: 0.2
  first_layer_height_mm: 0.2
  width_model: [nominal, extrusion]
  nozzle_temp_c: 210
  bed_temp_c: 60
  cool_to_room_before_scan: true
material:
  type: PLA
  color: grey_opaque
  manufacturer: ""
  lot: ""
  filament_diameter_measured_mm: null   # 5곳 실측 평균
cnc:        # CNC 선택 시만
  tool_type: null             # flat | ball
  tool_diameter_measured_mm: null
laser:      # 레이저 선택 시만
  kerf_measured_mm: null
measurement_timing: post_process_on_bed   # C2 1단계
```

### 10.2 장비 시험 출력 기록

| 회차 | 날짜·시각 | 실내 온도 [°C] | 출력 시간 | X 치수 [mm] | Y 치수 [mm] | Z 높이 [mm] | 설계 대비 최대 차이 [mm] | 비고 |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 범위 | | | | | | | | 3회 범위 ≤ 0.1 mm ? |

### 10.3 통제 변수 변경 이력 (실험 기간 내내 유지)

| 날짜 | 변경 항목 (노즐/펌웨어/재료 로트/슬라이서) | 이전 | 이후 | 이유 | 변경 후 기준 시편 재측정 여부 | 기록자 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 11. 참고 자료

- ISO/ASTM 52900, *Additive manufacturing — General principles — Fundamentals and vocabulary* — 적층제조 공정 분류와 용어(재료 압출 = FDM 계열)
- ISO 6983-1, *Automation systems and integration — Numerical control of machines — Program format and definitions of address words* — G코드 형식의 기본
- 사용하는 펌웨어의 공식 G코드 문서 (예: Marlin 문서 https://marlinfw.org/docs/gcode/G000-G001.html , Klipper 문서 https://www.klipper3d.org/G-Codes.html)
- 사용하는 슬라이서의 공식 매뉴얼 (선폭·압출 배율·arc fitting 설정 항목)
- NIST의 적층제조 표준 시편(AM Test Artifact) 관련 공개 보고서 — 공정 비교와 시편 설계
- 교과서 주제: 생산가공론(절삭·적층 공정 원리), 실험계획법(독립변수·통제 변수)
- pandas 공식 문서: https://pandas.pydata.org/docs/
