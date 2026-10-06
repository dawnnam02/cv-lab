# K5. 산출물 · 논문 구성

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: K. 프로젝트 운영

| 항목 | 내용 |
|---|---|
| 기간 | 2027-03-02 ~ 2027-03-22 (W22-24) — 그림·방법 절은 W13부터 점진 작성 |
| 우선순위 | 높음 |
| 트랙 | 관리·기획 |
| 선행 요소 | [I3 교차검증](../I-reliability/I3-cross-validation.md), [H8 통계](../H-analysis/H8-statistics.md), [I1 불확도](../I-reliability/I1-uncertainty.md), [J4 시각화·리포트](../J-software/J4-visualization-report.md), [K4 위험](K4-risks.md) |
| 후행 요소 | 없음 (프로젝트 최종 산출물) |
| 관련 마일스톤 | **M6 (2027-03-22)**: 최종 보고서 |

## 1. 목적

과제가 끝났을 때 **무엇을 내놓아야 하는지**(산출물 6종)와 **각각이 "완성"이라고 판단하는 기준**을 정하고, 결과 보고서/논문의 **절별 내용·그림 목록·작성 일정**을 정합니다.

- 측정 결과만큼 중요한 것은 **"이 측정을 믿을 수 있다"는 증거**(캘리브레이션, 불확도, Gage R&R, 교차검증)입니다. 논문 구성도 이 증거를 중심에 둡니다.
- 다른 사람이 데이터와 코드로 **같은 숫자를 다시 만들 수 있게** 공개 준비를 합니다.

## 2. 배경 지식 (초보자용)

| 용어 | 뜻 |
|---|---|
| 산출물 (deliverable) | 과제가 끝나면 남겨야 하는 결과물. 문서, 코드, 데이터, 장비 |
| 수용 기준 (acceptance criteria) | 산출물이 "완성"인지 판단하는 확인 가능한 조건 |
| IMRaD | 서론(Introduction)·방법(Methods)·결과(Results)·고찰(Discussion) 순서의 일반적인 논문 구조 |
| 재현 가능성 | 같은 데이터와 코드로 같은 숫자를 다시 얻을 수 있는 성질 |
| 체크섬 (SHA-256) | 파일 내용으로 계산한 고유 문자열. 파일이 1비트라도 바뀌면 값이 바뀜 → 공개한 데이터가 변하지 않았음을 증명 |
| DOI | 데이터나 논문에 붙는 영구 식별 번호. 데이터 저장소(예: Zenodo)에 올리면 받을 수 있음 |
| 라이선스 | 코드·데이터를 다른 사람이 어떻게 쓸 수 있는지 정한 조건 (예: 코드 MIT, 데이터 CC BY 4.0) |

**논문 쓰기의 핵심 원칙**: 마지막 3주에 처음부터 쓰지 않습니다. **그림을 먼저** 만들고(W13~), 방법 절은 **해당 요소가 끝날 때마다** 메모로 적어 둡니다. W22~24는 "모으고 다듬는" 기간입니다.

## 3. 입력과 산출물

| 구분 | 내용 | 출처 |
|---|---|---|
| 입력 | 캘리브레이션 결과·이력 | D1~D5, `config/calibration/` |
| 입력 | 시편별 지표표, 요약표 | H5~H7, `results/summary.csv` |
| 입력 | 통계 결과 | H8 |
| 입력 | 불확도 예산, Gage R&R, Bland–Altman | I1~I3 |
| 입력 | 그림 묶음 | J4 |
| 입력 | 발생한 위험·이슈 기록 | K4 |
| 산출물 | 6종 산출물 (4.1 표) | 저장소 + 공유 드라이브 |
| 산출물 | 결과 보고서/논문 | `paper/` |
| 산출물 | 공개 점검 결과, 체크섬 목록 | `results/SHA256SUMS.txt` |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 최종 형태 | 내부 보고서 / 학위논문 / 학술지·학회 논문 | **내부 보고서를 학술지 논문 구조로** 작성 | 이후 투고로 바로 전환 가능 |
| 작성 도구 | 워드 / LaTeX / 마크다운 | 연구실 관행에 따름. 그림은 **스크립트로 생성한 PNG(300 dpi) 또는 PDF** | 그림 재생성 가능 |
| 코드 공개 | 비공개 / 연구실 내부 / 공개 | **최소 연구실 내부 저장소 + 태그**, 가능하면 공개 | 재현성 |
| 데이터 공개 범위 | 원본 이미지 전체 / 프로파일·높이맵 / 요약표 | **높이맵 + 메타데이터 + 요약표**, 원본 이미지는 샘플만 | 원본은 스캔당 약 3.9 GB (F3) |
| 라이선스 | – | 코드 MIT 또는 BSD-3, 데이터 CC BY 4.0 (지도교수·기관 확인) | 널리 쓰이는 조건 |
| 오차 부호 | – | **측정값 − 기준값, + 재료 과다, − 재료 부족** (A1) | 문서·코드·그림에서 하나만 사용 |
| 불확도 표기 | – | "−0.05 ± 0.016 mm (k=2)" 형식 (I1) | GUM 표기 |

### 4.1 산출물 목록과 수용 기준

| # | 산출물 | 수용 기준 (모두 충족) | 담당 (K2) | 위치 |
|---|---|---|---|---|
| D1 | **측정 시스템** (하드웨어 + 조립 도면 + 사진) | ① 조립 도면에 각도 θ, 작동거리 WD, 부품 모델명 표기 ② 정면·측면 사진 ③ 레이저 안전 등급·경고 표지 사진 ④ 부품 목록(K3 구매 기록과 일치) | HW | `docs/hardware/` |
| D2 | **캘리브레이션 절차서 + 결과** | ① 처음 하는 사람이 절차서만 보고 D1~D4를 수행 가능 (다른 연구실원이 시험) ② 최종 CAL-ID의 재투영 RMS < 0.2 px, 평면 잔차 < 5 µm ③ D5 검증표(단차 < 10 µm, 평면도 P-V < 10 µm, 길이 < 0.1 %) ④ 이력 표 | HW | `docs/calibration_procedure.md`, `config/calibration/` |
| D3 | **분석 소프트웨어** | ① 새 PC에서 README대로 설치 → `run_analysis.py` 실행 → 요약표 숫자 일치 ② `pytest` 전부 통과 (J3 합성 테스트 포함) ③ `requirements.txt` 버전 고정 ④ 릴리스 태그 (예: `v1.0`) | SW | Git 저장소 |
| D4 | **불확도 예산 + MSA 보고서** | ① 높이·XY 불확도 예산표 (요인별 u_i, u_c, U k=2) ② Gage R&R: %GRR, ndc ③ 치우침·직선성·안정성 결과 ④ Bland–Altman 그림과 일치 한계 | QA | `results/msa/` |
| D5 | **실험 데이터셋** | ① `experiments.csv` 의 모든 행에 대응하는 메타데이터 JSON ② 모든 스캔에 CAL-ID, G코드 SHA-256 기록 ③ 백업 3곳 확인 ④ 체크섬 목록 | QA | `data/` |
| D6 | **결과 보고서 / 논문** | ① 4.2 구성의 모든 절 ② 4.3 필수 그림 전부, 300 dpi 이상, 축 라벨 단위 ③ 모든 오차 수치에 불확도 또는 신뢰구간 ④ 지도교수 최종 검토 완료 | PI (작성 R: 전원) | `paper/` |

### 4.2 논문 구성 (절별 내용)

| 절 | 분량 (대략) | 담아야 할 내용 | 근거 요소 |
|---|---|---|---|
| 초록 | 200~250 단어 | 목적, 방법(레이저 삼각측량 + G코드 마스킹 기준), 측정 시스템 성능(Z 반복성, U), 주요 결과(오차 크기), 의의 | 전체 |
| 1. 서론 | 1.5~2쪽 | 적층제조/가공 형상 오차 측정의 필요성, 기존 방법(CMM, 공초점, 상용 프로파일러)의 장단점, **G코드 기준 비교의 차별점**(CAD가 아닌 G코드 → 장비·공정 오차 분리), 기여 3가지 | A1, G5 |
| 2. 측정 시스템 | 2~3쪽 | 삼각측량 원리·공식(δx, δz), 배치(레이저 수직 + 카메라 θ), 부품 사양, 필터·차광·온도·진동 대책, 안전 | B1~B7, C1, C5~C8 |
| 2.x 캘리브레이션 | 1.5~2쪽 | 카메라 내부(ChArUco), 레이저 평면(평면 타깃 + SVD), 스캔축, 센서↔G코드(기준 구 + 좌표 교정 판), 검증 결과 | D1~D5, C3, C4 |
| 3. 기준 모델 | 1.5~2쪽 | G코드 파싱(압출 판정, 층·경로 종류), 비드 단면 모델(명목/압출량 기반 선폭), 층별 마스크·기준 높이맵, 평가 마스크 `M_eval` 정의와 평가 영역 비율 | G1~G4 |
| 4. 처리·분석 | 2쪽 | 격자화(중앙값, NaN 유지), 이상치 처리와 제거 비율, 바닥 기준화, **정합 두 방법(마커 기준 vs 최적맞춤) 분리 보고**, 지표 정의(높이·윤곽·치수·위치, 부호 규칙) | H1~H7 |
| 5. 측정 시스템 검증 | 2~3쪽 | 합성 데이터 복원 결과, 불확도 예산, Gage R&R, 교차검증(Bland–Altman) → "이 장비로 구별 가능한 최소 오차" | J3, I1~I3 |
| 6. 실험 및 결과 | 3~4쪽 | 시편 설계, 실험 조건·반복 수(시편 3 × 스캔 3)·무작위화, 형상별·경로 종류별·층별 결과, 위치·배율 오차 지도, 통계 검정(시편 단위) | E1~E3, H8 |
| 7. 고찰 | 1.5~2쪽 | 결과 해석(불확도보다 큰 차이만 의미), 오차 원인 추정, **한계**: 2.5D(윗면만), 표면 광학 의존성, 가림 영역, 열 상태, 발생한 위험과 영향 | E1, E2, C6, K4 |
| 8. 결론 | 0.5쪽 | 기여 요약, 향후 과제(층별 측정, CAD 비교, 다른 공정) | C2, G5, A3 |
| 부록 | – | 설정 파일, 캘리브레이션 이력, 데이터·코드 위치와 체크섬 | J2, F3 |

### 4.3 그림·표 목록 (필수 ★)

| # | 그림/표 | 내용 | 만드는 요소 | 초안 시점 |
|---|---|---|---|---|
| F1 ★ | 전체 흐름도 | G코드 → 기준 / 센서 → 측정 → 정합 → 오차 (청사진 0.2 흐름) | K5 | W13 |
| F2 ★ | 측정 시스템 사진 + 배치 도식 | θ, WD, 레이저 평면, 스캔 방향 | B2, C1 | W8 |
| F3 | 좌표계 다이어그램 | {C} → {S} → {M} → {G} | C4 | W8 |
| F4 ★ | 캘리브레이션 결과 | 재투영 오차 분포, 레이저 평면 잔차 | D1, D2 | W8 |
| F5 ★ | 게이지 블록 검증 | 명목 단차 vs 측정 단차 + 오차 막대 | D5 | W10 |
| F6 ★ | 기준 모델 예시 | G코드 경로 → 층 마스크 → 기준 높이맵 | G1~G3 | W6 |
| F7 | 평가 마스크 | `M_ref`, `M_valid`, `M_edge`, `M_eval` 겹친 그림 | G4 | W12 |
| F8 ★ | 합성 데이터 복원 | 정답 vs 복원값 (이동·회전·배율·높이) | J3 | W12 |
| F9 ★ | 편차 히트맵 | `RdBu_r`, 0 = 흰색, 대칭 고정 범위 (예: ±0.2 mm), 단위 | H5, J4 | W14 |
| F10 ★ | 마스크 오버레이 | 기준만 파랑, 측정만 빨강, 겹침 회색 + IoU·HD95 | H6, J4 | W14 |
| F11 | 단면 프로파일 | 기준(점선) vs 측정(실선), 선폭 | H7 | W14 |
| F12 ★ | 위치 오차 화살표 지도 | 핀 격자 ΔX, ΔY (확대 배율 명시) | H7 | W21 |
| F13 ★ | Gage R&R 결과 | 분산 성분 막대 + %GRR | I2 | W17 |
| F14 ★ | Bland–Altman | 두 장비 평균 차이, ±1.96 SD | I3 | W21 |
| F15 ★ | 조건 비교 | 시편 단위 RMS 상자그림/점그림 | H8 | W21 |
| T1 ★ | 목표 사양 vs 달성 사양 | Z 반복성, XY 간격, FOV, 측정 깊이 | A2, B1 | W10 |
| T2 ★ | 불확도 예산표 | 요인, 평가 방법, A/B형, u_i, u_c, U | I1 | W17 |
| T3 ★ | 결과 요약표 | 형상별 mean, std, RMS, P95, IoU, 치수 오차 ± U | H5~H7 | W21 |
| T4 | 실험 조건표 | 재료, 노즐, 층 높이, 반복 수, 측정 순서 | E3, H8 | W14 |

모든 그림은 스크립트로 생성(`scripts/make_figures.py`)하고 **300 dpi 이상, 축 라벨에 단위**를 붙입니다 (J4 규칙). 시편끼리 비교하는 히트맵은 색 범위를 모두 같게 합니다.

### 4.4 작성 일정

| 주 | 기간 | 할 일 | 산출 |
|---|---|---|---|
| W8 | 11-24 ~ 11-30 | 2절 메모 (배치, 캘리브레이션 수치) | F2~F4 초안 |
| W10 | 12-08 ~ 12-14 | D5 검증 결과 정리 | F5, T1 |
| W12 | 12-22 ~ 12-28 | 3·4절 메모, 합성 테스트 결과 | F6~F8 |
| W14 | 01-05 ~ 01-11 | M4 결과로 그림 스크립트 완성 | F9~F11, T4 |
| W17 | 01-26 ~ 02-01 | 5절 메모 | F13, T2 |
| W21 | 02-23 ~ 03-01 | 본 실험 결과 그림 | F12, F14, F15, T3 |
| **W22** | 03-02 ~ 03-08 | **초고**: 2~6절 메모를 문장으로, 1·7·8절 작성 | 초고 v0.1 |
| **W23** | 03-09 ~ 03-15 | 지도교수 검토(3일) → 수정, 공개 점검 스크립트 실행, 데이터·코드 정리 | v0.2, 점검 결과 |
| **W24** | 03-16 ~ 03-22 | 최종 교정, 초록, 저장소 태그 `v1.0`, 체크섬, 백업 | **최종본 (M6)** |

## 5. 수행 절차

1. **산출물 매니페스트 작성 (W13)**
   - [ ] 6절 `release_manifest.yaml` 을 연구실 폴더 구조에 맞게 수정
   - [ ] 각 산출물의 수용 기준을 담당자와 확인
2. **그림 먼저 (W8~W21)**
   - [ ] 4.3 표의 초안 시점에 그림 스크립트 커밋
   - [ ] 그림마다 캡션 초안(무엇을, 어떤 조건에서, 무엇을 보여 주는지) 2~3문장
3. **방법 절 메모 (요소 완료 시마다)**
   - [ ] 요소가 끝나면 "무엇을 / 어떤 설정으로 / 결과 수치" 3줄 메모를 `paper/notes/` 에
4. **초고 (W22)**
   - [ ] 2~6절: 메모 → 문장. 수치는 결과 파일에서 복사 (손으로 다시 타이핑하지 않기)
   - [ ] 1절 서론, 7절 고찰(한계 포함), 8절 결론
5. **검토와 수정 (W23)**
   - [ ] 지도교수 검토 요청 (최소 3일 확보)
   - [ ] 5.1 공개 체크리스트 수행 + 6절 점검 스크립트
6. **최종 (W24, M6)**
   - [ ] 모든 수치가 `results/summary.csv` 와 일치하는지 대조
   - [ ] 저장소 태그, 체크섬, 백업 3곳
   - [ ] M6 판정 회의: 4.1 수용 기준 전부 확인

### 5.1 데이터·코드 공개 체크리스트

**코드**
- [ ] README: 설치 → 실행 → 기대 출력, 폴더 구조 설명
- [ ] `requirements.txt` 버전 고정, Python 버전 명시
- [ ] `pytest` 전부 통과
- [ ] 개인 경로(`C:\Users\...`), 비밀번호, API 키 제거
- [ ] LICENSE 파일
- [ ] 릴리스 태그와 논문에 적은 커밋 해시 일치

**데이터**
- [ ] `data/raw` 원본은 수정되지 않음 (체크섬으로 확인)
- [ ] 모든 스캔에 메타데이터 JSON (CAL-ID, G코드 SHA-256, 온도, 노출 등 F3 항목)
- [ ] G코드 + 슬라이서 프로파일 + 시편 CAD 포함
- [ ] 데이터 설명 파일 (`data/README.md`): 파일 형식, 단위(mm), 좌표계({G}), 부호 규칙
- [ ] 개인정보 없음 (측정자 이름은 `student_A` 처럼 익명화)
- [ ] 라이선스 (예: CC BY 4.0)

**논문**
- [ ] 모든 오차에 불확도(k=2) 또는 95 % 신뢰구간
- [ ] 평가 영역 비율(%) 보고 (G4)
- [ ] 정합 방법별(마커 기준 / 최적맞춤) 결과 분리 (H4)
- [ ] 통계는 시편 단위 (유사반복 없음, H8)
- [ ] 레이저 삼각측량 방식과 한계(2.5D, 표면 의존성, 가림) 명시

## 6. Python 구현

산출물 매니페스트를 읽어 ① 필요한 파일이 모두 있는지 ② 논문 그림이 300 dpi 이상인지 ③ 원본 데이터 체크섬 목록을 만듭니다.

**`release_manifest.yaml`**

```yaml
# 산출물 점검 목록: 각 항목의 파일 패턴(glob)이 1개 이상 있어야 통과
deliverables:
  - id: D1-system
    name: 측정 시스템 도면·사진
    patterns: ["docs/hardware/*.pdf", "docs/hardware/photos/*.jpg"]
  - id: D2-calibration
    name: 캘리브레이션 절차서 + 결과
    patterns: ["docs/calibration_procedure.md", "config/calibration/CAL-*.yaml"]
  - id: D3-software
    name: 분석 소프트웨어
    patterns: ["README.md", "requirements.txt", "src/cvlab/*.py", "tests/test_*.py"]
  - id: D4-msa
    name: 불확도 예산 + MSA 보고서
    patterns: ["results/msa/uncertainty_budget.csv", "results/msa/gage_rr.csv"]
  - id: D5-dataset
    name: 실험 데이터셋
    patterns: ["data/experiments.csv", "data/raw/*/*.json"]
  - id: D6-paper
    name: 결과 보고서 / 논문
    patterns: ["paper/main.*", "paper/figures/*.png"]
figures:
  dir: paper/figures
  min_dpi: 300
```

**`scripts/release_check.py`**

```python
"""K5 산출물 점검: 매니페스트(YAML)의 파일이 모두 있는지, 논문 그림이 300 dpi 이상인지,
데이터 파일 체크섬(SHA-256) 목록을 만든다.

사용법 (저장소 루트에서):
    python k5_release_check.py release_manifest.yaml --root . --checksums results/SHA256SUMS.txt
"""
import argparse
import hashlib
from pathlib import Path

import yaml
from PIL import Image


def check_deliverables(root, items):
    ok_all = True
    for d in items:
        missing = [p for p in d["patterns"] if not list(root.glob(p))]
        ok = not missing
        ok_all &= ok
        mark = "통과" if ok else "누락: " + ", ".join(missing)
        print(f"[{'O' if ok else 'X'}] {d['id']:15s} {d['name']} - {mark}")
    return ok_all


def check_figures(root, cfg):
    bad = []
    for png in sorted((root / cfg["dir"]).glob("*.png")):
        dpi = Image.open(png).info.get("dpi", (0, 0))[0]   # PNG에 저장된 dpi 정보
        if round(dpi) < cfg["min_dpi"]:
            bad.append(f"{png.name}({round(dpi)} dpi)")
    print("그림 해상도:", "모두 통과" if not bad else "기준 미달 " + ", ".join(bad))
    return not bad


def write_checksums(root, out):
    """data/raw 아래 모든 파일의 SHA-256 → 공개 후 파일이 바뀌지 않았음을 증명"""
    lines = []
    for f in sorted((root / "data" / "raw").rglob("*")):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            lines.append(f"{h}  {f.relative_to(root).as_posix()}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"체크섬 {len(lines)}개 저장: {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--root", default=".")
    ap.add_argument("--checksums", default="results/SHA256SUMS.txt")
    a = ap.parse_args()
    root = Path(a.root)
    cfg = yaml.safe_load(open(a.manifest, encoding="utf-8"))
    ok1 = check_deliverables(root, cfg["deliverables"])
    ok2 = check_figures(root, cfg["figures"])
    write_checksums(root, root / a.checksums)
    print("최종:", "공개 준비 완료" if ok1 and ok2 else "미완료 항목 있음")


if __name__ == "__main__":
    main()
```

**연습용 가짜 저장소 만들기** (점검 스크립트가 문제를 잡는지 확인. 일부러 Gage R&R 파일을 빼고, 그림 하나를 100 dpi로 저장)

```python
"""K5 점검 스크립트 연습용 가짜 저장소 만들기 (일부러 2가지 문제를 넣음)"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path("demo_repo")
files = ["docs/hardware/assembly.pdf", "docs/hardware/photos/front.jpg",
         "docs/calibration_procedure.md", "config/calibration/CAL-2026-11-30-A.yaml",
         "README.md", "requirements.txt", "src/cvlab/metrics.py", "tests/test_metrics.py",
         "results/msa/uncertainty_budget.csv",           # gage_rr.csv 는 일부러 빠뜨림
         "data/experiments.csv", "data/raw/S01_r01/S01_r01.json", "paper/main.tex"]
for f in files:
    p = root / f
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("demo\n")
(root / "paper/figures").mkdir(parents=True, exist_ok=True)
fig, ax = plt.subplots()
ax.plot([0, 1], [0, 1])
fig.savefig(root / "paper/figures/fig01_system.png", dpi=300)
fig.savefig(root / "paper/figures/fig02_heatmap.png", dpi=100)   # 일부러 저해상도
print("가짜 저장소 생성:", root)
```

**실행 예시**

```bash
python make_demo_tree.py
python scripts/release_check.py release_manifest.yaml --root demo_repo
```

**기대 출력** (체크섬 값은 파일 내용이 같으면 동일)

```text
가짜 저장소 생성: demo_repo
[O] D1-system       측정 시스템 도면·사진 - 통과
[O] D2-calibration  캘리브레이션 절차서 + 결과 - 통과
[O] D3-software     분석 소프트웨어 - 통과
[X] D4-msa          불확도 예산 + MSA 보고서 - 누락: results/msa/gage_rr.csv
[O] D5-dataset      실험 데이터셋 - 통과
[O] D6-paper        결과 보고서 / 논문 - 통과
그림 해상도: 기준 미달 fig02_heatmap.png(100 dpi)
체크섬 1개 저장: demo_repo/results/SHA256SUMS.txt
최종: 미완료 항목 있음
```

실제 저장소에서는 `--root .` 로 실행합니다. 파일 존재만 확인하므로 **내용이 맞는지는 4.1 수용 기준으로 사람이 확인**합니다. 공개 후 누군가 데이터를 받으면 `sha256sum -c results/SHA256SUMS.txt` (Linux/macOS) 로 파일이 바뀌지 않았음을 확인할 수 있습니다.

## 7. 검증 방법과 완료 기준

| 검증 | 방법 | 기준 |
|---|---|---|
| 산출물 존재 | 6절 스크립트 | "공개 준비 완료" |
| 수용 기준 | 4.1 표를 M6 회의에서 하나씩 확인 | 6종 × 모든 조건 충족 |
| 재현성 | 작성자가 아닌 연구실원이 새 PC에서 README대로 실행 | 요약표 숫자 일치 (소수점 표시 자리까지) |
| 수치 일치 | 논문 속 수치 ↔ `results/summary.csv` 대조 | 불일치 0 |
| 그림 품질 | dpi 검사 + 눈으로 단위·컬러바 확인 | 300 dpi 이상, 단위 표기 |
| 검토 | 지도교수 검토 | 승인 기록 |

**K5 완료 기준 (M6, 2027-03-22)**: 6종 산출물이 수용 기준을 충족하고, 최종 보고서와 태그된 저장소·체크섬·백업이 존재함.

## 8. 흔한 실수와 대응

| 실수 | 결과 | 대응 |
|---|---|---|
| 마지막 3주에 처음 쓰기 시작 | 그림 품질 저하, 검토 시간 없음 | 4.4 일정대로 W8부터 그림·메모 |
| 그림을 손으로 편집 | 데이터가 바뀌면 다시 못 만듦 | 스크립트로만 생성 |
| 수치를 손으로 옮겨 적음 | 오타, 버전 불일치 | 결과 파일에서 복사, 최종 대조 |
| 평균 오차 하나만 보고 | +/− 상쇄로 오차가 숨음 (A1) | mean + std/RMS + P95/최댓값 |
| ICP 결과만으로 위치 오차 보고 | 위치 오차가 0으로 사라짐 (H4) | 마커 기준 / 최적맞춤 분리 |
| 불확도 없이 오차 보고 | 장비 오차와 구분 불가 | "± U (k=2)" 표기, \|오차\| < U 해석 |
| 한계 절 생략 | 심사에서 지적 | 2.5D, 표면, 가림, 열 상태 명시 |
| 히트맵 색 범위가 그림마다 다름 | 시편끼리 비교 불가 | 대칭 고정 범위 |
| 데이터만 공개하고 메타데이터 누락 | 재사용 불가 | 5.1 체크리스트 |

## 9. 위험 요소

- **작성 시간 부족** (K4 R21): 트리거 "W20까지 그림 목록 미확정" → 확장 실험을 "향후 과제"로 돌리고 범위 축소.
- **본 실험 지연으로 결과가 늦게 나옴**: 그림 스크립트를 M4(W14) 데이터로 미리 완성해 두면 데이터만 바꿔 재실행.
- **공개 제한** (기관·공동연구 규정): W13에 지도교수와 공개 범위 합의.
- **대용량 데이터**: 원본 이미지 전체 공개는 비현실적 → 높이맵·메타데이터 중심, 원본은 요청 시 제공.

## 10. 기록 양식

**산출물 수용 판정표 (M6)**

| # | 산출물 | 기준 | 확인 방법 | 결과 (O/X) | 확인자 | 날짜 |
|---|---|---|---|---|---|---|
| D2 | 캘리브레이션 | 재투영 RMS < 0.2 px | CAL 결과 YAML | | | |
| D3 | 소프트웨어 | 새 PC 재현 | 다른 연구실원 실행 | | | |

**그림 진행표**

| # | 파일명 | 생성 스크립트 | 데이터 버전 (커밋) | 캡션 초안 | 300 dpi | 단위 | 상태 |
|---|---|---|---|---|---|---|---|
| F9 | fig09_heatmap.png | make_figures.py | | ☐ | ☐ | ☐ | 초안 |

## 11. 참고 자료

- JCGM 100:2008 *Evaluation of measurement data — Guide to the expression of uncertainty in measurement (GUM)* — 불확도 표기
- AIAG *Measurement Systems Analysis (MSA) Reference Manual* — Gage R&R 보고
- Wilkinson et al., "The FAIR Guiding Principles for scientific data management and stewardship", *Scientific Data* (2016) — 데이터 공개 원칙
- Zenodo (데이터·코드 DOI 발급 저장소), Creative Commons 라이선스 안내
- Python 공식 문서 `hashlib`, PyYAML 문서, Pillow 문서
- 상위 문서: [BLUEPRINT.md K5](../../BLUEPRINT.md#k5-산출물--논문-구성)
