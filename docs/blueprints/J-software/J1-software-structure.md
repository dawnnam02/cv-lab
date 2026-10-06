# J1. 소프트웨어 구조

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: J. 소프트웨어

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-19 (W1-2) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | 없음 (프로젝트 첫 주에 시작) · 학습은 [K6 학습 로드맵](../K-management/K6-learning-roadmap.md)과 병행 |
| 후행 요소 | [J2 설정·재현성](J2-config-reproducibility.md), [J3 테스트](J3-synthetic-tests.md), [J4 시각화·리포트](J4-visualization-report.md), [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md), [F3 저장 형식](../F-acquisition/F3-data-storage.md) |
| 관련 마일스톤 | M4 (시편 1개 전체 파이프라인 완주) — 이 요소의 뼈대 위에서 M4가 달성됨. 첫 점검은 M0(W2 말) |

## 1. 목적

- 6개월 동안 여러 사람이 코드를 고쳐도 **어디에 무엇이 있는지 바로 알 수 있는 폴더·모듈 구조**를 W1–W2에 확정합니다.
- 측정(F) → 기준 모델(G) → 처리·분석(H) → 리포트(J4)를 **단계(stage)별로 나누고, 단계마다 결과를 파일로 저장**하는 실행 방식을 만듭니다. 그러면 뒤 단계 하나만 고칠 때 앞 단계(예: 2500장 이미지 처리)를 다시 돌릴 필요가 없습니다.
- Python 완전 초보도 **같은 환경(가상환경 + 고정 버전 라이브러리)** 에서 같은 명령으로 같은 결과를 얻도록 개발 환경 설치 절차를 표준화합니다.
- 이 요소가 끝나면: `python scripts/run_pipeline.py --scan-id S01_r01` 한 줄로 (지금은 합성 데이터로) 기준 → 측정 → 편차 → 지표 4단계가 돌아가고, 결과가 `data/processed/S01_r01/` 에 쌓여야 합니다.

## 2. 배경 지식 (초보자용)

**터미널(명령 창)**: 마우스 대신 글자로 컴퓨터에 명령하는 창입니다. Windows는 "PowerShell", macOS는 "터미널", Linux는 "Terminal"을 씁니다. VS Code 안의 터미널(메뉴 *Terminal → New Terminal*)을 쓰면 편합니다. 이 문서에서 `$` 로 시작하는 줄은 터미널에 입력하는 명령이고, `$` 자체는 입력하지 않습니다.

**Python 인터프리터**: `.py` 파일을 읽어 실행하는 프로그램입니다. 한 컴퓨터에 여러 버전이 깔려 있을 수 있으므로 **어떤 python을 쓰고 있는지** 항상 확인해야 합니다.

**모듈과 패키지**
- 모듈 = `.py` 파일 하나 (예: `metrics.py`). 다른 파일에서 `from cvlab.metrics import iou_dice` 처럼 가져다 씁니다.
- 패키지 = 모듈을 모은 폴더 (예: `src/cvlab/`). 폴더 안에 `__init__.py` 가 있으면 패키지로 인식됩니다.
- 라이브러리 = 남이 만든 패키지 (numpy, opencv 등). `pip` 로 설치합니다.

**가상환경(venv)**: 프로젝트마다 따로 쓰는 "라이브러리 보관함"입니다. 연구실 PC에 다른 과제용 numpy 1.x가 깔려 있어도, 이 과제의 `.venv` 안에는 정해진 버전만 들어갑니다. **가상환경 없이 시작하면 "내 컴퓨터에서는 되는데"가 반드시 생깁니다.**

**requirements.txt**: 필요한 라이브러리와 **정확한 버전**을 적은 목록입니다. `pip install -r requirements.txt` 한 줄로 누구나 같은 환경을 만듭니다.

**src 레이아웃**: 코드(`src/cvlab/`), 실행 스크립트(`scripts/`), 테스트(`tests/`), 데이터(`data/`), 결과(`results/`)를 폴더로 분리하는 방식입니다. 코드와 데이터가 섞이지 않아서 Git 관리와 백업이 쉬워집니다.

**단계(stage) 파이프라인**: 전체 처리를 "입력 파일 → 함수 → 출력 파일" 단위로 자릅니다.

```
[reference] G코드 → ref_height.npy
[measure]   원본 프로파일 → meas_height.npy          (실측에서는 F1·D2·H1)
[deviation] meas − ref → deviation.npy               (부호: + = 재료 과다)
[metrics]   deviation → metrics.csv                  (H5~H7)
```
출력 파일이 입력 파일보다 최신이면 그 단계는 건너뜁니다(빌드 도구 `make` 와 같은 원리). 이것이 청사진 J1의 원칙 **"단계마다 결과를 파일로 저장"** 을 코드로 구현한 것입니다.

**argparse**: `python run_pipeline.py --scan-id S03_r02 --force` 처럼 명령줄 옵션을 받는 표준 라이브러리입니다. 옵션을 쓰면 코드 안의 숫자를 고치지 않고도 다른 시편을 처리할 수 있습니다.

**노트북 vs 스크립트**: Jupyter 노트북(`.ipynb`)은 셀 단위로 실행하며 그림을 바로 보는 **탐색용**입니다. 셀 실행 순서에 따라 결과가 달라질 수 있어 재현성이 약하므로, **최종 처리는 반드시 `scripts/` 의 `.py` 로** 실행합니다(청사진 J1 원칙).

**Git**: 코드의 "저장 시점(커밋)"을 기록하는 도구입니다. 언제든 과거 버전으로 돌아갈 수 있고, 결과 폴더에 커밋 해시를 남기면(J2) "이 그림은 어느 코드로 만들었는가"를 증명할 수 있습니다. **데이터는 Git에 넣지 않습니다**(스캔 1회 ≈ 3.9 GB, F3).

## 3. 입력과 산출물

| 구분 | 이름 | 형식 / 위치 | 설명 |
|---|---|---|---|
| 입력 | 청사진 J1 폴더 구조 | `docs/BLUEPRINT.md` | 폴더·모듈 이름의 기준 |
| 입력 | 학습 계획 | [K6](../K-management/K6-learning-roadmap.md) | W1–2 Python 기초와 병행 |
| 산출물 | 개발 환경 | `.venv/` (Git 제외) | Python 3.11 또는 3.12 가상환경 |
| 산출물 | 의존성 목록 | `requirements.txt` | 모든 라이브러리 `==` 버전 고정 |
| 산출물 | 패키지 설정 | `pyproject.toml` | `pip install -e .` 로 `import cvlab` 가능하게 |
| 산출물 | Git 제외 목록 | `.gitignore` | `.venv`, `data/raw/*`, `data/processed/*`, `results/*` 제외 |
| 산출물 | 폴더 뼈대 + 빈 모듈 13개 | `src/cvlab/*.py`, `tests/`, `scripts/` … | `scripts/make_skeleton.py` 로 생성 |
| 산출물 | 환경 점검 스크립트 | `scripts/check_env.py` | 버전·설치 여부 출력, 실패 시 종료코드 1 |
| 산출물 | 파이프라인 실행기 | `scripts/run_pipeline.py` | argparse, 4단계, 최신 여부 판단, `--from/--only/--force` |
| 산출물 | 단계별 결과(데모) | `data/processed/<scan_id>/ref_height.npy`, `meas_height.npy`, `deviation.npy`, `metrics.csv` | 700×700 float64 배열(0.02 mm 격자), CSV 1행 |
| 산출물 | 환경 기록 | `docs/env_setup_log.md` (10절 양식) | 사람별 OS·Python·설치 결과 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| Python 버전 | 3.10 / 3.11 / 3.12 / 최신 | **3.11 또는 3.12** 중 하나로 연구실 통일 | 과학 라이브러리 바이너리(휠)가 가장 안정적으로 제공됨. 최신 버전은 카메라 SDK 지원이 늦을 수 있음 (B4 SDK 확인) |
| 환경 관리 | venv+pip / conda / 시스템 Python | **venv + pip** | 표준 라이브러리만으로 동작, 초보에게 개념이 단순. 카메라 SDK가 conda를 요구하면 그때만 conda |
| 코드 배치 | 평평한 폴더 / **src 레이아웃** | **src 레이아웃** (`src/cvlab/`) | 테스트가 설치된 패키지를 쓰게 되어 "경로 때문에 우연히 되는" 문제 방지 |
| 모듈 분할 | 영역별 / 기능별 | **청사진 J1 표 그대로** (영역 F·D·G·H·J 대응) | 문서 요소 번호와 파일이 1:1로 대응 → 찾기 쉬움 |
| 단계 산출물 형식 | pickle / **npy·npz·csv·json** | 배열 = `.npy`(하나)·`.npz`(여러 개), 표 = `.csv`, 메타 = `.json` | pickle은 Python 버전이 바뀌면 못 읽을 수 있고 보안 위험. F3 형식 규칙과 일치 |
| 파이프라인 도구 | 직접 만든 argparse 실행기 / Make / Snakemake | **argparse 실행기 (이 문서 6절)** | 의존성 0, 초보가 전부 읽을 수 있는 140줄. 본 실험(W18–21)에서 시편 수십 개 일괄 처리 시 확장 |
| 단계 재실행 판단 | 항상 전부 / 파일 수정시각 비교 / 해시 비교 | **수정시각 비교 + `--force`** | 단순하고 충분. 앞 단계를 다시 만들면 뒤 단계도 자동 재실행 |
| 데이터 위치 | Git 안 / **Git 밖** | `data/` 는 Git 제외, 연구실 NAS·외장 디스크에 3-2-1 백업 | 스캔당 ≈ 3.9 GB (F3) |
| 편집기 | VS Code / PyCharm / 메모장 | **VS Code** + Python·Jupyter 확장 | 무료, 터미널·노트북·Git 통합 |
| 노트북 위치 | 아무 데나 / `notebooks/` | `notebooks/날짜_이름_주제.ipynb` | 최종 처리는 `scripts/` 로만 |
| Git 브랜치 | main만 / main + 작업 브랜치 | 2명 이상이면 **작업 브랜치 → main 병합** | 동시에 같은 파일을 고칠 때 충돌 감소 |
| 이름 규칙 | 자유 / 규칙 | 파일·함수 `snake_case`, 단위는 이름 끝에 (`_mm`, `_deg`, `_um`) | C4 "모든 단위 mm" 규칙을 코드에서 눈으로 확인 |

## 5. 수행 절차

**1단계 (W1, 1일차) — Python 설치 확인**
- [ ] Windows: PowerShell에서 `py --version` → `Python 3.12.x` 처럼 나오면 됨. 없으면 python.org 설치 파일로 설치하면서 **"Add python.exe to PATH" 체크**.
- [ ] macOS/Linux: 터미널에서 `python3 --version`. macOS에 없으면 python.org 설치 파일 사용.
- [ ] 결과를 10절 환경 기록표에 적기 (사람마다 1행).

**2단계 (W1, 1일차) — Git 설치와 사용자 설정**
- [ ] `git --version` 확인 (Windows는 "Git for Windows" 설치).
- [ ] `git config --global user.name "홍길동"` / `git config --global user.email "학교메일"`
- [ ] 연구실 원격 저장소(학교 GitLab 또는 GitHub 비공개 저장소) 주소 받기 → `git clone <주소> cv-lab`

**3단계 (W1, 1–2일차) — 가상환경 만들기**
- [ ] 프로젝트 폴더(`cv-lab/`)로 이동한 뒤 아래 명령 실행.

```text
# Windows (PowerShell)
PS> cd C:\work\cv-lab
PS> py -3.12 -m venv .venv
PS> .\.venv\Scripts\Activate.ps1
# "스크립트 실행이 비활성화" 오류가 나면 한 번만:
PS> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# macOS / Linux
$ cd ~/work/cv-lab
$ python3 -m venv .venv
$ source .venv/bin/activate
```
- [ ] 활성화되면 프롬프트 앞에 `(.venv)` 가 붙음. `python -c "import sys; print(sys.prefix)"` 결과가 `…/cv-lab/.venv` 이어야 함.
- [ ] **매번 새 터미널을 열면 다시 activate** 해야 함 (VS Code는 4단계 설정 후 자동).

**4단계 (W1, 2일차) — 라이브러리 설치**
- [ ] `python -m pip install --upgrade pip`
- [ ] 6.3절 `requirements.txt` 를 저장소 루트에 두고 `pip install -r requirements.txt` (약 5–10분, 300–500 MB).
- [ ] `pip install -e .` (6.3절 `pyproject.toml` 필요) → 어느 폴더에서든 `import cvlab` 가능.
- [ ] `python scripts/check_env.py` → 마지막 줄 `환경 점검 통과`.
- [ ] 설치 직후 `pip freeze > requirements-lock.txt` 로 실제 설치된 전체 버전을 기록(커밋).

**5단계 (W1, 3일차) — VS Code + Jupyter**
- [ ] VS Code 설치 → 확장(Extensions)에서 **Python**, **Jupyter** 설치 (둘 다 Microsoft 제공).
- [ ] `Ctrl+Shift+P`(macOS `Cmd+Shift+P`) → "Python: Select Interpreter" → `.venv` 안의 python 선택.
- [ ] 노트북 커널용: `pip install ipykernel` → 새 `.ipynb` 에서 커널을 `.venv` 로 선택.
- [ ] 노트북 첫 셀에서 `import numpy, cvlab; print(numpy.__version__)` 실행 확인.

**6단계 (W1, 3–4일차) — 폴더 뼈대 만들기**
- [ ] 6.2절 `make_skeleton.py` 를 `scripts/` 에 저장하고 `python scripts/make_skeleton.py` 실행 → "새 모듈 13개 생성".
- [ ] 다시 실행해서 "새 모듈 0개 생성" (기존 파일을 덮어쓰지 않음) 확인.
- [ ] `config/calibration/` 에는 D1·D2 결과 YAML이 CAL-ID별로 들어갈 예정임을 README에 적기.

**7단계 (W1, 4일차) — `.gitignore` 와 첫 커밋**
- [ ] 6.3절 `.gitignore` 저장.
- [ ] `git status` 로 `.venv/`, `data/raw/` 안의 파일이 목록에 **안 나오는지** 확인.
- [ ] `git add .` → `git commit -m "J1: 폴더 뼈대와 환경 설정"` → `git push`.

**8단계 (W2, 1–3일차) — 파이프라인 실행기**
- [ ] 6.4절 `run_pipeline.py` 를 `scripts/` 에 저장.
- [ ] `python scripts/run_pipeline.py --list` → 4개 단계 출력.
- [ ] 전체 실행 → 4개 파일 생성, `metrics.csv` 의 `mean_mm` = 0.03 (합성 데이터에 넣은 +0.03 mm 과다가 그대로 복원) 확인.
- [ ] 같은 명령 재실행 → 4단계 모두 "건너뜀".
- [ ] `--from deviation --force` → 2개 단계만 실행.
- [ ] 입력이 없는 상태에서 `--only metrics` → "입력 파일 없음" 오류와 종료코드 1.

**9단계 (W2, 4–5일차) — 연결 계획과 문서화**
- [ ] 각 단계 함수(`stage_reference` 등)가 나중에 어느 요소의 진짜 함수로 바뀔지 10절 "단계 정의표"에 기록: reference → G3 `reference_heightmap`, measure → F1 + D2 + H1, deviation/metrics → H5–H7.
- [ ] `README.md` 에 "설치 4줄 + 실행 1줄" 사용법 적기.
- [ ] 팀원 1명이 **다른 PC에서** README만 보고 1~8단계를 30분 안에 재현 (7절 기준).

**Git 기초 명령 (매일 쓰는 것만)**

| 하고 싶은 일 | 명령 |
|---|---|
| 변경된 파일 보기 | `git status` |
| 변경 내용 보기 | `git diff` |
| 저장 준비 | `git add 파일명` (전부: `git add .`) |
| 저장(커밋) | `git commit -m "G1: G92 처리 추가"` (메시지 앞에 요소 번호) |
| 서버로 올리기 / 받기 | `git push` / `git pull` |
| 작업 브랜치 만들기 | `git switch -c feature/g1-parser` |
| 기록 보기 | `git log --oneline -10` |
| 파일을 마지막 커밋 상태로 되돌리기 | `git restore 파일명` |

## 6. Python 구현

### 6.1 환경 점검 스크립트 — `scripts/check_env.py`

```python
"""check_env.py — 개발 환경 점검 (J1). 실행: python scripts/check_env.py"""
import importlib
import sys

REQUIRED = {           # import 이름: 설치(pip) 이름
    "numpy": "numpy", "scipy": "scipy", "shapely": "shapely", "cv2": "opencv-python",
    "matplotlib": "matplotlib", "pandas": "pandas", "yaml": "PyYAML", "pytest": "pytest",
}

ok = True
print(f"Python {sys.version.split()[0]}  ({sys.executable})")
if sys.version_info < (3, 10):
    print("  [X] Python 3.10 이상이 필요합니다"); ok = False
if sys.prefix == sys.base_prefix:
    print("  [!] 가상환경(venv)이 활성화되지 않았습니다 → activate 먼저")
for mod, pipname in REQUIRED.items():
    try:
        m = importlib.import_module(mod)
        print(f"  [OK] {pipname:15s} {getattr(m, '__version__', '?')}")
    except ImportError:
        print(f"  [X] {pipname:15s} 없음 → pip install {pipname}"); ok = False
print("환경 점검 통과" if ok else "환경 점검 실패: 위 [X] 항목을 해결하세요")
sys.exit(0 if ok else 1)
```

실행 예시 (가상환경을 켜지 않은 경우):
```text
$ python scripts/check_env.py
Python 3.13.16  (/usr/bin/python3)
  [!] 가상환경(venv)이 활성화되지 않았습니다 → activate 먼저
  [OK] numpy           2.5.3
  [OK] scipy           1.18.1
  [OK] shapely         2.1.2
  [OK] opencv-python   5.0.0
  [OK] matplotlib      3.11.2
  [OK] pandas          3.0.5
  [OK] PyYAML          6.0.1
  [OK] pytest          9.1.1
환경 점검 통과
```
(버전 숫자는 설치 시점에 따라 다릅니다. `.venv` 를 켜면 `[!]` 줄이 사라집니다.)

### 6.2 폴더 뼈대 생성 — `scripts/make_skeleton.py`

```python
"""make_skeleton.py — 청사진 J1의 폴더 구조와 빈 모듈을 한 번에 만든다.

사용법:  python make_skeleton.py  [만들 위치(기본: 현재 폴더)]
이미 있는 파일은 절대 덮어쓰지 않는다(안전).
"""
import sys
from pathlib import Path

# 만들 폴더 목록 (청사진 J1 구조 그대로)
DIRS = [
    "config/calibration",
    "data/gcode", "data/raw", "data/processed",
    "src/cvlab/acquisition", "src/cvlab/calibration",
    "scripts", "tests", "notebooks", "results",
]

# 만들 모듈: 파일 경로 → 첫 줄 설명(docstring)
MODULES = {
    "src/cvlab/__init__.py": "cvlab: 레이저 삼각측량 기반 G코드 대비 형상 오차 측정 패키지",
    "src/cvlab/acquisition/__init__.py": "카메라·스테이지 제어, 촬영 (F)",
    "src/cvlab/calibration/__init__.py": "카메라·레이저평면·스캔축 캘리브레이션 (D)",
    "src/cvlab/triangulation.py": "레이저 라인 중심 추출과 픽셀→3D 변환 (F1, D2)",
    "src/cvlab/gcode_parser.py": "G코드 파싱 (G1)",
    "src/cvlab/reference_model.py": "비드 모델·기준 높이맵 (G2, G3)",
    "src/cvlab/masks.py": "평가 마스크 M_ref, M_valid, M_eval (G4)",
    "src/cvlab/preprocess.py": "점→격자, 이상치, 바닥 평면 (H1~H3)",
    "src/cvlab/registration.py": "정합: 기준마커 / 최적맞춤 (H4)",
    "src/cvlab/metrics.py": "높이·윤곽·치수 지표 (H5~H7)",
    "src/cvlab/stats.py": "통계·불확도 (H8, I)",
    "src/cvlab/report.py": "시각화·리포트 (J4)",
    "tests/__init__.py": "pytest 테스트 모음 (J3)",
}


def main(root: Path) -> None:
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)      # 이미 있어도 에러 없음
    created = 0
    for rel, doc in MODULES.items():
        p = root / rel
        if p.exists():                                     # 덮어쓰기 금지
            continue
        p.write_text(f'"""{doc}"""\n', encoding="utf-8")
        created += 1
    # data/raw 는 git에 올리지 않지만 폴더는 유지되도록 빈 표시 파일을 둔다
    for d in ["data/raw", "data/processed", "results"]:
        keep = root / d / ".gitkeep"
        keep.touch(exist_ok=True)
    print(f"폴더 {len(DIRS)}개 확인, 새 모듈 {created}개 생성 → {root.resolve()}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
```

실행 예시:
```text
$ python scripts/make_skeleton.py
폴더 10개 확인, 새 모듈 13개 생성 → /home/me/work/cv-lab
$ python scripts/make_skeleton.py
폴더 10개 확인, 새 모듈 0개 생성 → /home/me/work/cv-lab
```

### 6.3 설정 파일 3종

`requirements.txt`
```text
# cvlab 의존 라이브러리 — 버전은 반드시 == 로 고정 (J2 재현성)
# 아래 숫자는 예시입니다. 실제로는 설치 후 `pip freeze` 로 확인한 값을 적습니다.
numpy==2.5.3
scipy==1.18.1
shapely==2.1.2
opencv-python==5.0.0.93
matplotlib==3.11.2
pandas==3.0.5
PyYAML==6.0.1
statsmodels==0.15.0
pytest==9.1.1
```

`pyproject.toml` (설치 후 `import cvlab` 가 어디서든 되게 하고, pytest 설정도 함께 둠)
```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "cvlab"
version = "0.1.0"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`.gitignore`
```text
# 가상환경·캐시
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ipynb_checkpoints/
*.egg-info/

# 데이터·결과는 Git 밖에서 관리 (용량 큼, F3 백업 규칙 따름)
data/raw/*
data/processed/*
results/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!results/.gitkeep

# 운영체제 부산물
.DS_Store
Thumbs.db
```

### 6.4 파이프라인 실행기 — `scripts/run_pipeline.py`

```python
"""run_pipeline.py — 단계(stage)별로 파일을 읽고 쓰는 최소 파이프라인 실행기 (J1).

각 단계는 "입력 파일 → 함수 → 출력 파일" 이다. 출력이 입력보다 최신이면 건너뛴다.
지금은 실제 장비 데이터 대신 합성 데이터로 동작하며, 나중에 각 단계 함수만
src/cvlab/ 의 진짜 함수로 바꾸면 된다.

사용 예:
  python run_pipeline.py --scan-id S01_r01                 # 전체 실행
  python run_pipeline.py --scan-id S01_r01                 # 다시 실행 → 모두 건너뜀
  python run_pipeline.py --scan-id S01_r01 --from deviation --force   # 뒤 단계만 강제 재실행
  python run_pipeline.py --list                            # 단계 목록 보기
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import numpy as np

log = logging.getLogger("pipeline")
RES_MM = 0.02  # 격자 간격 [mm] (청사진 G3: 0.02 mm)


# ---------------------------------------------------------------- 단계 함수들
def stage_reference(inp, out, ctx):
    """[G3 자리] 기준 높이맵: 10×10 mm 사각 블록, 높이 2.0 mm (바깥은 0 = 베드)."""
    n = int(round(14 / RES_MM))                     # 14 mm × 14 mm 격자 → 700×700
    xs = (np.arange(n) + 0.5) * RES_MM              # 격자 칸 중심 좌표 [mm]
    X, Y = np.meshgrid(xs, xs)
    H = np.zeros((n, n))
    H[(X > 2) & (X < 12) & (Y > 2) & (Y < 12)] = 2.0
    np.save(out["ref"], H)


def stage_measure(inp, out, ctx):
    """[H1 자리] 측정 높이맵: 기준 + 0.03 mm 과다 + 노이즈 σ=5 µm + 결측 2 %."""
    rng = np.random.default_rng(ctx["seed"])        # 시드 고정 → 매번 같은 결과
    H = np.load(inp["ref"]) + 0.03
    H += rng.normal(0, 0.005, H.shape)
    H[rng.random(H.shape) < 0.02] = np.nan          # 측정 안 된 칸은 NaN (보간 금지)
    np.save(out["meas"], H)


def stage_deviation(inp, out, ctx):
    """[H5 준비] 편차 = 측정값 − 기준값  (+ 는 재료 과다)."""
    dev = np.load(inp["meas"]) - np.load(inp["ref"])
    np.save(out["dev"], dev)


def stage_metrics(inp, out, ctx):
    """[H5 자리] 블록 윗면(기준 높이 > 0)에서 지표를 계산해 CSV 한 줄로 저장."""
    dev, ref = np.load(inp["dev"]), np.load(inp["ref"])
    e = dev[(ref > 0) & ~np.isnan(dev)]
    row = {
        "scan_id": ctx["scan_id"], "n": e.size,
        "mean_mm": round(float(e.mean()), 4),
        "std_mm": round(float(e.std(ddof=1)), 4),
        "rms_mm": round(float(np.sqrt((e ** 2).mean())), 4),
        "p95_abs_mm": round(float(np.percentile(np.abs(e), 95)), 4),
    }
    with open(out["metrics"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)
    log.info("  지표: %s", row)


# 단계 정의: (이름, 함수, 입력 키 목록, 출력 {키: 파일명})  ※ 순서가 곧 실행 순서
STAGES = [
    ("reference", stage_reference, [], {"ref": "ref_height.npy"}),
    ("measure", stage_measure, ["ref"], {"meas": "meas_height.npy"}),
    ("deviation", stage_deviation, ["meas", "ref"], {"dev": "deviation.npy"}),
    ("metrics", stage_metrics, ["dev", "ref"], {"metrics": "metrics.csv"}),
]


# ---------------------------------------------------------------- 실행기
def is_up_to_date(inputs, outputs):
    """출력이 모두 있고, 가장 오래된 출력이 가장 최신 입력보다 새것이면 True."""
    if not all(p.exists() for p in outputs):
        return False
    if not inputs:
        return True
    return min(p.stat().st_mtime for p in outputs) >= max(p.stat().st_mtime for p in inputs)


def run(scan_id, workdir, start=None, only=None, force=False, seed=42):
    workdir.mkdir(parents=True, exist_ok=True)
    files = {}                                         # 키 → 경로 (모든 단계 공유)
    for _, _, _, outs in STAGES:
        files.update({k: workdir / v for k, v in outs.items()})
    names = [s[0] for s in STAGES]
    first = names.index(start) if start else 0
    ctx = {"scan_id": scan_id, "seed": seed}
    for i, (name, func, in_keys, outs) in enumerate(STAGES):
        if i < first or (only and name != only):
            continue
        inp = {k: files[k] for k in in_keys}
        out = {k: files[k] for k in outs}
        missing = [str(p) for p in inp.values() if not p.exists()]
        if missing:
            raise FileNotFoundError(f"[{name}] 입력 파일 없음: {missing} → 앞 단계를 먼저 실행하세요")
        if not force and is_up_to_date(list(inp.values()), list(out.values())):
            log.info("[%s] 건너뜀 (출력이 최신)", name)
            continue
        t0 = time.perf_counter()
        func(inp, out, ctx)
        log.info("[%s] 완료 %.2f s → %s", name, time.perf_counter() - t0,
                 ", ".join(p.name for p in out.values()))
        force = True   # 한 단계를 다시 만들었으면 뒤 단계도 반드시 다시 만든다


def main(argv=None):
    ap = argparse.ArgumentParser(description="cvlab 분석 파이프라인 (J1 최소 버전)")
    ap.add_argument("--scan-id", default="S01_r01", help="스캔 ID (예: S03_r02)")
    ap.add_argument("--workdir", default="data/processed", help="결과 상위 폴더")
    ap.add_argument("--from", dest="start", choices=[s[0] for s in STAGES], help="이 단계부터 실행")
    ap.add_argument("--only", choices=[s[0] for s in STAGES], help="이 단계 하나만 실행")
    ap.add_argument("--force", action="store_true", help="최신이어도 다시 실행")
    ap.add_argument("--seed", type=int, default=42, help="난수 시드")
    ap.add_argument("--list", action="store_true", help="단계 목록만 출력")
    a = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    if a.list:
        for name, func, ins, outs in STAGES:
            print(f"{name:10s} 입력={ins or '-'}  출력={list(outs.values())}  # {func.__doc__.splitlines()[0]}")
        return 0
    run(a.scan_id, Path(a.workdir) / a.scan_id, a.start, a.only, a.force, a.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

실행 예시와 기대 출력:
```text
$ python scripts/run_pipeline.py --list
reference  입력=-  출력=['ref_height.npy']  # [G3 자리] 기준 높이맵: 10×10 mm 사각 블록, 높이 2.0 mm (바깥은 0 = 베드).
measure    입력=['ref']  출력=['meas_height.npy']  # [H1 자리] 측정 높이맵: 기준 + 0.03 mm 과다 + 노이즈 σ=5 µm + 결측 2 %.
deviation  입력=['meas', 'ref']  출력=['deviation.npy']  # [H5 준비] 편차 = 측정값 − 기준값  (+ 는 재료 과다).
metrics    입력=['dev', 'ref']  출력=['metrics.csv']  # [H5 자리] 블록 윗면(기준 높이 > 0)에서 지표를 계산해 CSV 한 줄로 저장.

$ python scripts/run_pipeline.py --scan-id S01_r01
[reference] 완료 0.01 s → ref_height.npy
[measure] 완료 0.03 s → meas_height.npy
[deviation] 완료 0.02 s → deviation.npy
  지표: {'scan_id': 'S01_r01', 'n': 245023, 'mean_mm': 0.03, 'std_mm': 0.005, 'rms_mm': 0.0304, 'p95_abs_mm': 0.0382}
[metrics] 완료 0.02 s → metrics.csv

$ python scripts/run_pipeline.py --scan-id S01_r01          # 두 번째 실행
[reference] 건너뜀 (출력이 최신)
[measure] 건너뜀 (출력이 최신)
[deviation] 건너뜀 (출력이 최신)
[metrics] 건너뜀 (출력이 최신)

$ python scripts/run_pipeline.py --scan-id S01_r01 --from deviation --force
[deviation] 완료 0.01 s → deviation.npy
  지표: {...같은 값...}
[metrics] 완료 0.02 s → metrics.csv

$ python scripts/run_pipeline.py --scan-id S99_r01 --only metrics
FileNotFoundError: [metrics] 입력 파일 없음: [...deviation.npy', ...ref_height.npy'] → 앞 단계를 먼저 실행하세요
```

**결과 읽는 법**: 합성 측정값에 +0.03 mm(재료 과다)와 σ = 5 µm 노이즈를 넣었으므로 `mean_mm = 0.03`, `std_mm = 0.005` 가 나와야 정상입니다. `rms_mm`(0.0304) ≈ √(0.03² + 0.005²) 로 청사진 H5의 `RMS² = 평균² + 표준편차²` 관계도 확인됩니다. n = 245 023 은 블록 윗면 250 000칸 중 결측 2 %를 뺀 값입니다.

**나중에 바꿀 곳**: `stage_reference` 안을 `from cvlab.reference_model import reference_heightmap` 호출로, `stage_measure` 를 실측 프로파일(`data/raw/<scan_id>/*.npz`) → 높이맵 변환으로 바꾸면 실행기 코드는 그대로 씁니다. 설정값(격자 0.02 mm 등)은 J2에서 YAML로 옮깁니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 환경 재현 | 팀원 전원이 각자 PC에서 5절 1–4단계 수행 | 전원 `check_env.py` 종료코드 0, 걸린 시간 ≤ 30분/인 |
| 버전 고정 | `requirements.txt` 검사 | 모든 줄이 `==` 로 고정 (`>=`, 버전 없음 0개) |
| Git 제외 | 1 GB 더미 파일을 `data/raw/` 에 두고 `git status` | 목록에 0개 표시 |
| 뼈대 멱등성 | `make_skeleton.py` 2회 실행 | 2회째 "새 모듈 0개" |
| 파이프라인 정답 | 전체 실행 후 `metrics.csv` | `mean_mm` = 0.030 ± 0.001, `std_mm` = 0.005 ± 0.0005 |
| 건너뛰기 | 재실행 | 4단계 모두 "건너뜀", 총 실행 < 1 s |
| 부분 재실행 | `--from deviation --force` | 정확히 2단계 실행 |
| 오류 처리 | 입력 없이 `--only metrics` | 종료코드 ≠ 0, 메시지에 누락 파일 경로 포함 |
| 문서 | README의 설치·실행 절차 | 처음 보는 사람이 질문 없이 따라 할 수 있음 (팀원 1명 확인 서명) |
| 마일스톤 연결 | W2 말 M0 점검 | 위 항목 전부 통과 시 J1 완료 |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 가상환경을 켜지 않고 설치 | `pip install` 은 됐는데 실행 시 `ModuleNotFoundError` | 프롬프트에 `(.venv)` 확인. `python -m pip ...` 형식으로 설치하면 지금 쓰는 python에 설치됨 |
| VS Code가 다른 인터프리터 사용 | 터미널에선 되는데 ▶ 버튼으론 에러 | "Python: Select Interpreter" 에서 `.venv` 선택 |
| `.venv` 를 Git에 커밋 | 저장소 용량 수백 MB, 다른 OS에서 동작 안 함 | `.gitignore` 에 `.venv/`. 이미 올렸으면 `git rm -r --cached .venv` |
| 데이터를 Git에 커밋 | push 실패, 저장소 GB 단위 | `data/*` 제외. 데이터는 경로만 기록 (J2 manifest) |
| 파일 이름을 `numpy.py`, `yaml.py` 로 저장 | `import numpy` 가 내 파일을 불러와 이상한 에러 | 라이브러리와 같은 이름 금지 |
| 경로를 `C:\Users\...` 로 하드코딩 | 다른 PC·macOS에서 실패 | `pathlib.Path` 와 상대 경로(저장소 루트 기준) 사용 |
| 노트북에서만 결과 생성 | 셀 순서에 따라 값이 바뀌어 재현 불가 | 확정된 코드는 `src/cvlab/` 로 옮기고 `scripts/` 로 실행 |
| 한 파일에 모든 코드 | 2000줄짜리 `main.py`, 고칠 때마다 다른 곳이 깨짐 | 청사진 J1 모듈 분할(요소별 1 파일) 유지 |
| 단계 결과를 덮어쓰고 원본까지 수정 | `data/raw` 손상, 재처리 불가 | 원본은 읽기만. 단계 출력은 `data/processed/<scan_id>/` 에만 씀 |
| 단위 없는 변수 이름 (`width = 0.42`) | mm·µm 혼동으로 1000배 오차 | `line_width_mm`, `sigma_um` 처럼 단위 접미사 |
| 앞 단계 수정 후 뒤 단계를 안 돌림 | 그림이 옛 결과 기반 | 실행기가 "앞 단계를 다시 만들면 뒤 단계 강제 재실행" 하도록 구현됨 (6.4) |

## 9. 위험 요소

- **카메라 SDK의 Python 버전 제한** (B4): 제조사 SDK가 특정 Python 버전(예: 3.11까지)만 지원할 수 있습니다. W2 안에 SDK 지원 버전을 확인하고 연구실 Python 버전을 그에 맞춥니다. 안 맞으면 촬영용(`acquisition/`)과 분석용 가상환경을 분리합니다.
- **Windows·macOS 혼용**: 경로 구분자, 줄바꿈(CRLF/LF), 한글 경로 문제. 저장소 경로에 한글·공백을 쓰지 않습니다(예: `C:\work\cv-lab`).
- **구조 과설계**: 초보 팀이 처음부터 클래스·플러그인 구조를 만들면 W3 G1 일정이 밀립니다. 함수 + 모듈 수준에서 멈춥니다.
- **실행기 수정시각 판단의 한계**: 코드(함수)를 고쳐도 파일 시각은 그대로라 "건너뜀"이 됩니다. 코드를 고친 뒤에는 `--force` 를 쓰는 습관을 들이고, J2의 manifest(커밋 해시)로 어떤 코드로 만든 결과인지 남깁니다.
- **디스크 용량**: 원본 이미지 저장 시 스캔당 ≈ 3.9 GB(F3). 분석 PC에 1 TB 이상 SSD 또는 NAS를 W2 안에 확보합니다(K3 예산).
- **담당자 1명 의존**: 환경 구성을 한 사람만 알면 그 사람이 빠질 때 멈춥니다. 7절 "다른 PC 재현"을 반드시 다른 사람이 수행합니다.

## 10. 기록 양식

**환경 설치 기록표** (`docs/env_setup_log.md`)

| 날짜 | 이름 | OS / 버전 | Python 버전 | `check_env.py` 결과 | 소요 시간 | 문제와 해결 |
|---|---|---|---|---|---|---|
| | | | | 통과 / 실패 | 분 | |
| | | | | | | |

**단계 정의표** (실행기 단계 ↔ 청사진 요소 연결)

| 단계 이름 | 입력 파일 | 출력 파일 | 현재 구현 | 최종 구현 함수 (요소) | 담당 | 완료일 |
|---|---|---|---|---|---|---|
| reference | G코드, config | `ref_height.npy` | 합성 | `reference_model.reference_heightmap` (G3) | | |
| measure | `data/raw/<id>/*.npz` | `meas_height.npy` | 합성 | `triangulation` + `preprocess` (F1, D2, H1–H3) | | |
| deviation | meas, ref | `deviation.npy` | 완료 | (정합 H4 후 계산) | | |
| metrics | deviation, masks | `metrics.csv` | 일부 | `metrics` (H5–H7) | | |

**주간 점검 YAML** (`docs/weekly/2026-W02.yaml`)
```yaml
week: 2026-W02
element: J1
done:
  - "venv + requirements 설치 (3명)"
todo_next_week: []
blocked_by: []        # 예: "카메라 SDK Python 버전 미확인"
check_env_pass: 0/3   # 통과 인원 / 전체 인원
pipeline_demo_pass: false
```

## 11. 참고 자료

- Python 공식 문서 — "venv — Creation of virtual environments" (docs.python.org)
- Python 공식 문서 — "argparse — Parser for command-line options", "pathlib", "logging"
- Python Packaging User Guide — "Installing packages using pip and virtual environments", "Writing your pyproject.toml" (packaging.python.org)
- pip 문서 — "Requirements File Format"
- Visual Studio Code 문서 — "Python in Visual Studio Code", "Jupyter Notebooks in VS Code"
- Pro Git (Scott Chacon, Ben Straub) — git-scm.com 에서 무료 공개, 1–3장
- 「점프 투 파이썬」 (청사진 K6 권장 입문서)
