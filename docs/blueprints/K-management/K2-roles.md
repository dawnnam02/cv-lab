# K2. 역할 분담

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: K. 프로젝트 운영

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-12 (W1) — 인원 변동 시 갱신 |
| 우선순위 | 보통 |
| 트랙 | 관리·기획 |
| 선행 요소 | 없음 (K1과 동시) |
| 후행 요소 | [K1 일정](K1-schedule.md)의 담당 배정, [K6 학습](K6-learning-roadmap.md)의 역할별 학습 범위, 모든 요소 |
| 관련 마일스톤 | M0 (2026-10-19) |

## 1. 목적

55개 요소 각각에 대해 **누가 하고(R), 누가 최종 책임지고(A), 누구와 미리 상의하고(C), 누구에게 알리는지(I)** 를 표로 정합니다.

- "다들 내가 아니라 저 사람이 하는 줄 알았다"는 공백을 없앱니다.
- 하드웨어와 소프트웨어가 만나는 **경계 요소**(C3 기준 마커, C4 좌표계, D4 센서↔G코드, H4 정합)에서 책임을 분명히 합니다.
- 인원이 바뀌거나(졸업, 휴학) 혼자 진행하게 될 때를 대비한 **인수인계 규칙**을 정합니다.

## 2. 배경 지식 (초보자용)

**RACI 매트릭스**는 작업(행) × 사람(열) 표에 네 글자 중 하나를 적는 방법입니다.

| 글자 | 영어 | 뜻 | 규칙 |
|---|---|---|---|
| **R** | Responsible | 실제로 손을 움직여 수행하는 사람 | 요소마다 1명 이상 |
| **A** | Accountable | 결과를 승인하고 최종 책임지는 사람 | 요소마다 **정확히 1명** |
| **C** | Consulted | 시작 전·중간에 의견을 구해야 하는 사람 (양방향) | 필요한 만큼만 |
| **I** | Informed | 끝나면 결과를 알려 줘야 하는 사람 (한 방향) | 나머지 모두 |

`A/R` 은 한 사람이 수행과 책임을 모두 맡는다는 뜻입니다. 소규모 연구실에서는 흔합니다.

**역할 4개** (청사진 K2 기준, 2~4명 연구실)

| 역할 코드 | 이름 | 담당 영역 (청사진) | 필요한 역량 |
|---|---|---|---|
| PI | 총괄 (지도교수/선임) | A, K, 중간 점검, 결과 해석 | 연구 방향 결정, 예산 승인 |
| HW | 광학·하드웨어 | B, C, D | 광학 정렬, 기구 조립, 캘리브레이션 |
| SW | 소프트웨어 | F, G, H, J | Python, numpy, OpenCV |
| QA | 실험·품질 | E, I, 실험 기록, 데이터 관리 | 실험 설계, 통계, 기록 습관 |

## 3. 입력과 산출물

| 구분 | 내용 | 형식 / 위치 |
|---|---|---|
| 입력 | 요소 목록·트랙 | `docs/blueprints/.meta.txt` |
| 입력 | 참여 인원, 주당 가능 시간 | 면담 |
| 산출물 | RACI 표 (55행) | `results/raci.csv` + 이 문서 4.1절 |
| 산출물 | 인원 배정표 (역할 → 이름) | 10절 양식 |
| 산출물 | 인수인계 체크리스트 | 5.3절 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| R 배정 기준 | 영역별 / 트랙별 | **`.meta.txt` 의 트랙 기준** | 일정(K1)과 같은 기준이라 주별 부하 계산이 일치 |
| A 배정 기준 | 트랙 / 영역 소유자 | **영역 소유자** (청사진 K2 표) | 영역 전체의 일관성을 한 사람이 책임 |
| 진행/중단 승인 | 실무자 / 총괄 | **총괄(PI)**: B3, D5(M2), I2(M5), K5(M6) | 예산·범위가 걸린 결정 |
| 경계 요소 | 한쪽 단독 / 공동 R | **공동 R** (C3, D4, H4, E3, I3) | 하드웨어 측정과 소프트웨어 계산이 함께 필요 |
| 인원 3명일 때 | QA를 별도 / 겸임 | **QA를 HW가 겸임**, 데이터 관리는 SW | 실험은 장비 옆에서 하는 사람이 수행 |
| 혼자일 때 | 24주 / 1.5배 | **약 36주, 지도교수가 A** | 청사진 K2 |
| 백업 담당 | 없음 / 지정 | **요소마다 보조 1명 지정** (임계 경로 요소는 필수) | 결원 시 인수인계 |

### 4.1 RACI 매트릭스 (전체 55개 요소)

아래 표는 6절 스크립트가 `.meta.txt` 에서 자동 생성한 결과입니다. 연구실 사정에 맞게 바꾸려면 코드의 규칙 사전을 고치고 다시 생성합니다 (표를 손으로 고치면 CSV와 어긋납니다).

| 요소 | 기간 | PI | HW | SW | QA |
|---|---|---|---|---|---|
| A1 error-definition | W1 | A/R | C | C | C |
| A2 precision-spec | W1-2 | A/R | C | C | C |
| A3 process | W1 | A/R | C | C | C |
| B1 triangulation-principle | W1-2 | C | A/R | C | I |
| B2 geometry | W1-2 | C | A/R | C | I |
| B3 commercial-vs-diy | W1-2 | A/R | I | C | I |
| B4 camera | W2-4 | C | A/R | C | I |
| B5 lens | W2-4 | C | A/R | C | I |
| B6 laser | W2-4 | C | A/R | C | I |
| B7 filter | W2-4 | C | A/R | C | I |
| C1 scan-stage | W3-4 | I | A/R | C | C |
| C2 measurement-timing | W3-4 | I | A/R | C | C |
| C3 fiducials | W11-12 | I | A/R | R | C |
| C4 coordinate-frames | W5-6 | I | A | R | C |
| C5 ambient-light | W5-6 | I | A/R | C | C |
| C6 temperature | W5-6 | I | A/R | C | C |
| C7 vibration | W5-6 | I | A/R | C | C |
| C8 laser-safety | W5-6 | I | A/R | C | C |
| D1 camera-intrinsics | W7-8 | I | A/R | C | C |
| D2 laser-plane | W7-8 | I | A/R | C | C |
| D3 scan-axis | W9-10 | I | A/R | C | C |
| D4 sensor-to-gcode | W11-12 | I | A/R | R | C |
| D5 calibration-verification | W9-10 | A | I | C | R |
| E1 surface-optics | W13-14 | I | C | C | A/R |
| E2 occlusion-edges | W13-14 | I | C | C | A/R |
| E3 test-artifact | W13-14 | I | C | R | A/R |
| F1 line-extraction | W7-8 | I | C | A/R | I |
| F2 acquisition-params | W9-10 | I | R | A | I |
| F3 data-storage | W9-10 | I | C | A/R | I |
| G1 gcode-parsing | W3-4 | I | I | A/R | C |
| G2 bead-model | W5-6 | I | I | A/R | C |
| G3 mask-heightmap | W5-6 | I | I | A/R | C |
| G4 evaluation-masks | W5-6 | I | I | A/R | C |
| G5 cad-relation | W5-6 | I | I | A/R | C |
| H1 gridding | W9-10 | I | I | A/R | C |
| H2 outliers | W9-10 | I | I | A/R | C |
| H3 bed-leveling | W9-10 | I | I | A/R | C |
| H4 registration | W11-12 | I | R | A/R | C |
| H5 height-metrics | W13-14 | I | I | A/R | C |
| H6 contour-metrics | W13-14 | I | I | A/R | C |
| H7 dimensional-metrics | W13-14 | I | I | A/R | C |
| H8 statistics | W15-17 | I | I | A | R |
| I1 uncertainty | W15-17 | I | C | C | A/R |
| I2 msa | W15-17 | A | C | C | R |
| I3 cross-validation | W18-21 | I | C | R | A/R |
| J1 software-structure | W1-2 | I | I | A/R | C |
| J2 config-reproducibility | W1-2 | I | I | A/R | C |
| J3 synthetic-tests | W11-12 | I | I | A/R | C |
| J4 visualization-report | W13-14 | I | I | A/R | C |
| K1 schedule | W1-2 | A/R | C | C | C |
| K2 roles | W1 | A/R | C | C | C |
| K3 budget | W1-2 | A/R | C | C | C |
| K4 risks | W1-24 | A/R | R | R | R |
| K5 deliverables-paper | W22-24 | A/R | R | R | R |
| K6 learning-roadmap | W1-24 | A/R | R | R | R |

**역할별 부하 요약** (R = 수행 요소 수, A = 책임 요소 수)

| 역할 | R | A | 비고 |
|---|---|---|---|
| PI | 10 | 12 | A 영역·K 영역 직접 수행, 진행/중단 승인 |
| HW | 22 | 18 | W1~W12에 집중 → W13 이후 QA 실험 보조로 이동 |
| SW | 26 | 20 | 가장 많음 → W13~14(H5~H7, J4) 과부하 주의 |
| QA | 11 | 5 | W13 이후 본격 시작 → 그 전에는 D5·데이터 관리 규칙 준비 |

### 4.2 경계 요소에서의 책임 나누기

| 요소 | HW가 하는 일 | SW가 하는 일 | 인계물 |
|---|---|---|---|
| C3 기준 마커 | 구 고정, 좌표 교정 판 출력·측정 | 원기둥 중심 → 최소제곱 변환 계산 | 측정 높이맵 + 마커 설계 좌표 |
| C4 좌표계 | 축 방향 실물 확인 (L자 시편) | `T_G_M` 명명 규칙, 변환 코드 | 좌표계 정의 문서 |
| D4 센서↔G코드 | 노즐↔센서 오프셋 측정 | 변환 적용·검증 코드 | CAL-ID 붙은 YAML |
| H4 정합 | 마커 스캔 품질 확보 | 구 맞춤, Kabsch, ICP | FRE 보고 |
| E3 시편 | (QA) 설계·출력 | 시편 G코드 → 기준 높이맵 생성 확인 | CAD + 슬라이서 프로파일 + G코드 |
| I3 교차검증 | (QA) 외부 장비 측정 | 같은 위치 지표 추출, Bland–Altman | 측정 위치 목록 |

### 4.3 혼자 진행하는 경우 (1인 변형)

| 항목 | 2~4명 | 1인 |
|---|---|---|
| R | 역할별 분담 | 모두 본인 |
| A | 영역 소유자 | **지도교수** (최소 B3, D5, I2, K5 승인) |
| C | 동료 | **2주마다 지도교수/선배 30분 검토** + 체크리스트 자가 점검 |
| 일정 | 24주 | 약 36주 (2027년 6월 말 전후). 또는 범위 축소: C2 층별 측정·G5 CAD 비교·E1 재질 비교를 "향후 과제"로 |
| 진행 방식 | 트랙 병행 | **오전 하드웨어 / 오후 소프트웨어** 처럼 하루를 나누거나, 장비 대기 시간(배송, 출력 중)에 소프트웨어 작업 |
| 재현성(I2) | 측정자 2~3명 | 측정자 재현성은 **다른 연구실원 1~2명에게 1시간씩 측정 부탁**. 불가하면 재장착 재현성만 평가하고 한계로 명시 |

## 5. 수행 절차

1. **인원과 시간 파악 (W1 초)**
   - [ ] 참여자 이름, 주당 가능 시간, 기간(졸업·휴학 예정) 수집
   - [ ] 각자 Python·광학·통계 경험을 "없음/조금/있음"으로 기록 (K6 학습 계획에 사용)
2. **역할 배정 (W1)**
   - [ ] 역할 코드(PI/HW/SW/QA) → 사람 이름 대응표 작성 (10절)
   - [ ] 사람 수가 역할 수보다 적으면 4.1 결정 규칙대로 겸임
3. **RACI 생성·검토 (W1)**
   - [ ] 6절 스크립트 실행, "규칙 위반: 없음" 확인
   - [ ] 경계 요소(4.2) 인계물을 당사자끼리 합의
   - [ ] 임계 경로 요소(K1: A3, B7, C5, D1, D5, C3, E3, I2, I3, K5)에 백업 담당 지정
4. **공유와 승인 (W1 끝)**
   - [ ] 지도교수 승인 후 저장소에 커밋
   - [ ] 연구실 게시판이나 공유 폴더에도 1장으로 출력
5. **운영 중 갱신 (W1~W24)**
   - [ ] 주간 회의에서 "이번 주 R이 막혔는가"를 확인
   - [ ] 인원 변동 시 5.3 인수인계 절차 수행 후 RACI 재생성

### 5.3 인수인계 규칙

인수인계는 **"떠나는 사람이 없어도 다음 사람이 혼자 재현할 수 있는가"** 가 기준입니다.

- [ ] **코드**: 모든 코드가 Git에 커밋·푸시되어 있음. 개인 PC에만 있는 파일 0개
- [ ] **실행 방법**: `README` 에 설치 → 실행 명령 → 기대 출력이 적혀 있음. 인수자가 **직접 실행해서** 같은 출력을 확인 (지켜보기만 하면 안 됨)
- [ ] **장비**: 렌즈 잠금 상태, 케이블 연결, 레이저 안전 수칙을 현장에서 시연. 사진으로 기록
- [ ] **캘리브레이션**: 현재 유효한 CAL-ID, 다음 재교정 예정일, 최근 D5 검증 결과
- [ ] **데이터**: `data/raw` 위치, 백업 위치 3곳, `experiments.csv` 최신 상태
- [ ] **진행 중 작업**: 미완료 요소, 막힌 이유, 다음 단계 (회의록 링크)
- [ ] **계정·권한**: 저장소, 공유 드라이브, 장비 예약 시스템 권한 이전
- [ ] **겹침 기간**: 최소 1주는 두 사람이 함께 작업 (임계 경로 요소는 2주)

## 6. Python 구현

`.meta.txt` 의 트랙으로 R을, 영역 규칙으로 A·C를 정하고, "A는 정확히 1명, R은 1명 이상" 규칙을 자동 검사합니다.

```python
"""K2 RACI 생성기: .meta.txt -> 55개 요소의 RACI 표(CSV/마크다운) + 역할별 부하 검사

R = 실제로 수행 (Responsible), A = 최종 책임·승인 (Accountable, 요소당 정확히 1명)
C = 사전 협의 (Consulted),     I = 결과 통보 (Informed)

사용법:  python k2_raci.py docs/blueprints/.meta.txt --out results/raci.csv [--md]
"""
import argparse
import pandas as pd

ROLES = ["PI", "HW", "SW", "QA"]   # 총괄(지도교수/선임), 광학·하드웨어, 소프트웨어, 실험·품질
TRACK_TO_R = {"하드웨어": "HW", "소프트웨어": "SW", "실험·품질": "QA", "관리·기획": "PI"}
AREA_OWNER = {"A": "PI", "B": "HW", "C": "HW", "D": "HW", "E": "QA", "F": "SW",
              "G": "SW", "H": "SW", "I": "QA", "J": "SW", "K": "PI"}   # 청사진 K2 표
AREA_CONSULT = {"A": ["HW", "SW", "QA"], "B": ["SW", "PI"], "C": ["SW", "QA"],
                "D": ["SW", "QA"], "E": ["HW", "SW"], "F": ["HW"], "G": ["QA"],
                "H": ["QA"], "I": ["HW", "SW"], "J": ["QA"], "K": ["HW", "SW", "QA"]}
# 요소별 예외 (영역 규칙보다 우선)
OVERRIDE_A = {"B3": "PI", "D5": "PI", "I2": "PI", "K5": "PI"}   # 진행/중단·대외 산출물은 총괄 승인
EXTRA_R = {"C3": ["SW"], "D4": ["SW"], "H4": ["HW"], "E3": ["SW"], "I3": ["SW"],
           "K5": ["HW", "SW", "QA"], "K4": ["HW", "SW", "QA"], "K6": ["HW", "SW", "QA"]}


def build(meta_path):
    df = pd.read_csv(meta_path, sep="|")
    rows = []
    for _, m in df.iterrows():
        k, area = m["key"], m["key"][0]
        cell = {r: "" for r in ROLES}
        R = {TRACK_TO_R[m["track"]], *EXTRA_R.get(k, [])}
        A = OVERRIDE_A.get(k, AREA_OWNER[area])
        for r in R:
            cell[r] = "R"
        cell[A] = "A/R" if cell[A] == "R" else "A"
        for r in AREA_CONSULT[area]:
            if cell[r] == "":
                cell[r] = "C"
        for r in ROLES:
            if cell[r] == "":
                cell[r] = "I"
        rows.append({"key": k, "slug": m["slug"], "weeks": m["weeks"], **cell})
    return pd.DataFrame(rows)


def validate(t):
    """규칙: 요소마다 A는 정확히 1개, R(또는 A/R)은 1개 이상"""
    errs = []
    for _, r in t.iterrows():
        cells = [r[x] for x in ROLES]
        n_a = sum(c.startswith("A") for c in cells)
        n_r = sum("R" in c for c in cells)
        if n_a != 1:
            errs.append(f"{r['key']}: A가 {n_a}개")
        if n_r < 1:
            errs.append(f"{r['key']}: R 없음")
    return errs


def load(t):
    """역할별로 R(수행)·A(책임)를 맡은 요소 수"""
    out = {}
    for r in ROLES:
        out[r] = {"R": int(t[r].str.contains("R").sum()),
                  "A": int(t[r].str.startswith("A").sum())}
    return pd.DataFrame(out).T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta", nargs="?", default="docs/blueprints/.meta.txt")
    ap.add_argument("--out", default="results/raci.csv")
    ap.add_argument("--md", action="store_true", help="마크다운 표도 출력")
    a = ap.parse_args()
    t = build(a.meta)
    t.to_csv(a.out, index=False, encoding="utf-8-sig")   # 엑셀에서 한글이 안 깨지게
    errs = validate(t)
    print(f"요소 {len(t)}개, 규칙 위반: {errs if errs else '없음'}")
    print(load(t).to_string())
    if a.md:
        print("| 요소 | 기간 | PI | HW | SW | QA |\n|---|---|---|---|---|---|")
        for _, r in t.iterrows():
            print(f"| {r['key']} {r['slug']} | {r['weeks']} | " +
                  " | ".join(r[x] for x in ROLES) + " |")


if __name__ == "__main__":
    main()
```

**실행 예시** (저장소 루트에서)

```bash
python scripts/raci.py docs/blueprints/.meta.txt --out results/raci.csv
```

**기대 출력**

```text
요소 55개, 규칙 위반: 없음
     R   A
PI  10  12
HW  22  18
SW  26  20
QA  11   5
```

`--md` 를 붙이면 4.1절의 마크다운 표가 이어서 출력됩니다. CSV는 `utf-8-sig` 로 저장해서 엑셀에서 열어도 한글이 깨지지 않습니다.

**규칙을 바꾸는 예**: H8 통계를 QA가 책임지게 하려면 `OVERRIDE_A = {..., "H8": "QA"}` 를 추가하고 다시 실행합니다. 실수로 A를 두 명 주는 구조는 코드상 생길 수 없지만, 표를 손으로 편집한 CSV를 검사하려면 `validate(pd.read_csv(...))` 를 그대로 쓰면 됩니다.

## 7. 검증 방법과 완료 기준

| 검증 | 방법 | 기준 |
|---|---|---|
| 형식 | `validate()` | 55행 모두 A 1개, R ≥ 1개 |
| 공백 | 각 역할 열에 이름이 배정됨 | 미배정 역할 0개 |
| 부하 균형 | 역할별 R 수 + K1 주별 부하 | 한 사람이 같은 주에 임계 경로 요소 2개 이상을 단독 R로 맡지 않음 |
| 합의 | 지도교수 승인 | 회의록 기록 |
| 인수인계 | 5.3 체크리스트 | 인수자가 직접 실행해 같은 결과 확인 |

**K2 완료 기준 (W1 끝)**: RACI CSV + 역할-이름 대응표 + 백업 담당이 커밋되어 있고, 모든 참여자가 자기 R 요소 목록을 말할 수 있음.

## 8. 흔한 실수와 대응

| 실수 | 결과 | 대응 |
|---|---|---|
| A를 여러 명에게 줌 | 결정이 미뤄짐 | 요소당 A 1명 (코드가 검사) |
| 지도교수를 모든 요소의 A로 | 승인 병목 | 진행/중단·예산·대외 산출물만 PI |
| 경계 요소의 인계물을 정하지 않음 | "데이터는 줬는데 형식이 다르다" | 4.2 표의 인계물·파일 형식 합의 |
| C를 너무 많이 | 회의만 늘어남 | 결과에 영향받는 역할만 C, 나머지는 I |
| 데이터 관리 담당 없음 | 메타데이터 누락, 백업 없음 | QA(또는 SW)를 F3·데이터 관리 R로 명시 |
| 인수인계를 말로만 | 졸업 후 재현 불가 | 5.3 체크리스트 + 인수자가 직접 실행 |
| 혼자인데 C를 비워 둠 | 실수를 아무도 못 잡음 | 2주마다 외부 검토 일정 고정 |

## 9. 위험 요소

- **핵심 인원 이탈** (졸업, 휴학, 병가): 임계 경로 요소 백업 담당 + 문서화로 완화 ([K4](K4-risks.md) 위험 등록부).
- **SW 역할 과부하** (R 26개): W13~14에 H5~H7·J4가 몰림 → HW가 J4 시각화를 보조하도록 미리 학습 ([K6](K6-learning-roadmap.md)).
- **레이저 안전 책임 불명확**: C8의 A는 HW지만 **연구실 안전관리자에게 I** 를 반드시 포함 (학교 규정 확인).

## 10. 기록 양식

**역할 – 이름 대응표**

| 역할 | 이름 | 주당 시간 | 참여 기간 | 백업 | 연락처 |
|---|---|---|---|---|---|
| PI | | | 2026-10-06 ~ 2027-03-22 | | |
| HW | | | | SW | |
| SW | | | | HW | |
| QA | | | | HW | |

**인수인계 기록**

| 날짜 | 요소 | 인계자 | 인수자 | 체크리스트 완료 항목 수 / 8 | 인수자 직접 실행 결과 | 서명 |
|---|---|---|---|---|---|---|
| | | | | | | |

## 11. 참고 자료

- Project Management Institute, *PMBOK Guide* — 책임 배정 매트릭스(RAM/RACI)
- 소속 대학 연구실 안전관리 규정 (레이저 취급 책임자 지정)
- pandas 공식 문서: `DataFrame.to_csv` (https://pandas.pydata.org/docs/)
- 상위 문서: [BLUEPRINT.md K2](../../BLUEPRINT.md#k2-역할-분담-소규모-24명-기준-예시)
