# J2. 설정 · 재현성

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: J. 소프트웨어

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-06 ~ 2026-10-19 (W1-2) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [J1 소프트웨어 구조](J1-software-structure.md) (같은 기간에 병행, J1의 venv·폴더가 먼저) |
| 후행 요소 | [J3 테스트](J3-synthetic-tests.md), [J4 시각화·리포트](J4-visualization-report.md), [F3 저장 형식·메타데이터](../F-acquisition/F3-data-storage.md), [D5 캘리브레이션 검증·이력](../D-calibration/D5-calibration-verification.md), [H2 이상치](../H-analysis/H2-outliers.md), [H8 통계](../H-analysis/H8-statistics.md) |
| 관련 마일스톤 | M4 (시편 1개 전체 파이프라인 완주 — 결과 폴더마다 manifest 필수) |

## 1. 목적

- 처리에 쓰는 **모든 숫자(격자 0.02 mm, 선폭 0.42 mm, 경계 띠 0.25 mm, 공차 0.1 mm, 시드 42 …)를 코드 밖 YAML 파일 한 곳**에 모읍니다. 코드 안에 숫자가 흩어져 있으면 "이 그림은 어떤 값으로 만들었나"를 아무도 답할 수 없습니다.
- 설정 파일을 읽을 때 **기본값 채우기 + 오타·범위·관계 검증**을 자동으로 해서, 잘못된 값으로 몇 시간짜리 처리를 돌리는 일을 막습니다.
- 실행할 때마다 결과 폴더에 **설정 복사본 + git 커밋 해시 + 캘리브레이션 ID + 라이브러리 버전 + 시각 + 입력 파일 해시**(= manifest)를 자동 저장합니다. 6개월 뒤 논문 심사에서 "그림 5를 다시 만들어 보라"는 요청에 답할 수 있어야 합니다.
- 무작위성이 있는 처리(RANSAC 바닥 평면 H3, 합성 데이터 J3, 부트스트랩 H8)는 **시드를 고정**해서 같은 입력 → 같은 출력이 되게 합니다.

## 2. 배경 지식 (초보자용)

**재현성(reproducibility)**: 같은 데이터 + 같은 코드 + 같은 설정 → 같은 결과. 측정 연구에서는 "측정값이 맞다"는 증명만큼 "처리 과정을 다시 할 수 있다"는 증명이 중요합니다. 재현이 안 되는 원인은 대부분 다음 다섯 가지입니다.

| 원인 | 예 | 이 요소의 대응 |
|---|---|---|
| 설정값이 바뀜 | 누군가 `edge_band` 를 0.25 → 0.3 으로 고침 | 결과 폴더에 `config_resolved.yaml` 복사 |
| 코드가 바뀜 | 파서 버그 수정 후 숫자가 달라짐 | git 커밋 해시 + `dirty`(커밋 안 된 수정 있음) 기록 |
| 라이브러리 버전이 바뀜 | shapely 1.x → 2.x 에서 buffer 결과 미세 변화 | `requirements.txt` 고정 + manifest에 실제 버전 기록 |
| 캘리브레이션이 바뀜 | 렌즈를 건드려 재교정 | `calibration_id` 기록 (D5) |
| 난수 | RANSAC 이 매번 다른 점을 고름 | 시드 고정 |

**YAML**: 사람이 읽기 쉬운 설정 파일 형식입니다. 들여쓰기(공백 2칸)로 계층을 표현하고, `#` 뒤는 주석입니다. **탭 문자는 쓰면 안 됩니다.**
```yaml
grid:
  resolution_mm: 0.02    # grid 아래의 resolution_mm
gcode:
  exclude_types: [SKIRT, SUPPORT]   # 리스트
```
Python에서는 `yaml.safe_load` 로 읽으면 딕셔너리 `{"grid": {"resolution_mm": 0.02}, ...}` 가 됩니다. `yaml.load`(safe 아님)는 파일 안의 코드를 실행할 수 있어 위험하므로 쓰지 않습니다.

**기본값 + 덮어쓰기(deep merge)**: 코드에 전체 기본값을 두고, 실험별 YAML에는 **바꾸는 값만** 적습니다. 실험 파일이 짧아져서 "무엇을 바꿨는지"가 한눈에 보입니다. 명령줄 `--set metrics.tolerance_mm=0.05` 는 그 위에 한 번 더 덮어씁니다. 우선순위: **명령줄 > 실험 YAML > 코드 기본값**.

**검증(validation)**: 읽은 값이 말이 되는지 확인하는 단계입니다. 이 문서에서는 세 가지를 봅니다.
1. **오타**: 기본값에 없는 키(`resoluton_mm`)는 오타로 간주 → 에러. 오타를 그냥 두면 기본값이 조용히 쓰여서 가장 찾기 어려운 버그가 됩니다.
2. **자료형·범위**: `tolerance_mm: -1` 이나 `width_model: Nominal`(대문자) 거부.
3. **값 사이 관계**: 층 높이 < 선폭 (G2 비드 모델 가정), 격자 ≤ 선폭/5 (A2 "최소 형상에 5~10점" 규칙).

**git 커밋 해시**: 커밋마다 붙는 40자리 고유 번호(예: `28dde58f…`)입니다. 결과 폴더에 이 값이 있으면 `git checkout 28dde58` 으로 그때 코드로 돌아갈 수 있습니다. 커밋하지 않은 수정이 있으면(`dirty: true`) 그 결과는 **정확히 재현할 수 없다는 경고**입니다. 본 실험(W18–21) 결과는 반드시 `dirty: false` 상태에서 만듭니다.

**시드(seed)**: 컴퓨터의 난수는 "시드"라는 출발값에서 계산되는 가짜 난수입니다. 시드가 같으면 같은 순서의 난수가 나옵니다. numpy는 `rng = np.random.default_rng(42)` 로 만든 `rng` 를 함수에 인자로 넘겨 쓰는 방식을 권장합니다.

**해시(SHA-256)**: 파일 내용으로 계산한 64자리 지문입니다. 한 글자만 바뀌어도 완전히 달라집니다. G코드 파일의 해시를 기록하면 "같은 이름의 다른 G코드"를 구별할 수 있습니다(F3 메타데이터의 `gcode_sha256` 과 같은 방식).

## 3. 입력과 산출물

| 구분 | 이름 | 형식 / 위치 | 설명 |
|---|---|---|---|
| 입력 | 처리 파라미터 기본값 | `config/default.yaml` | 청사진 J2 예시 + `calibration_id` |
| 입력 | 실험별 설정 | `config/exp_<이름>.yaml` | 바꾸는 값만 기록 (예: 공차 0.05) |
| 입력 | 캘리브레이션 결과 | `config/calibration/CAL-2026-10-06-A/*.yaml` | D1·D2·D3 결과, ID 폴더별 |
| 산출물 | 설정 모듈 | `src/cvlab/config.py` | `load_config`, `validate`, `set_seed`, `git_info`, `start_run` |
| 산출물 | 실행 스크립트 연결 예 | `scripts/run_analysis.py` | `--config`, `--set key=value`, `--name` |
| 산출물 | 결과 폴더 (실행 1회마다) | `results/<YYYYMMDD-HHMMSS>_<scan_id>/` | 같은 초에 또 실행하면 `_2`, `_3` 접미사 |
| 산출물 | ├ 원본 설정 복사 | `config_original.yaml` | 사람이 쓴 그대로 |
| 산출물 | ├ 실제 사용 설정 | `config_resolved.yaml` | 기본값 + YAML + 명령줄을 합친 최종값 |
| 산출물 | └ 실행 기록 | `manifest.json` | run_name, timestamp(시간대 포함), git{commit, dirty}, calibration_id, random_seed, command, platform, libraries{…}, inputs{경로: sha256} |
| 산출물 | 테스트 | `tests/test_config.py` | pytest 7개 |
| 산출물 | 버전 잠금 | `requirements-lock.txt` | `pip freeze` 전체 결과 (J1) |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 설정 형식 | YAML / JSON / TOML / .py 상수 | **YAML** | 주석 가능, 청사진 J2 예시와 같음. JSON은 주석 불가, .py는 코드와 섞임 |
| 읽기 함수 | `yaml.load` / **`yaml.safe_load`** | `safe_load` | 임의 코드 실행 방지 |
| 기본값 위치 | YAML만 / **코드 DEFAULTS + YAML** | 코드에 전체 기본값, YAML엔 변경분 | 키 누락이 원천적으로 없어짐 |
| 검증 방식 | 없음 / 직접 규칙표 / pydantic 등 외부 라이브러리 | **직접 규칙표 (RULES 딕셔너리)** | 의존성 추가 없이 초보가 읽을 수 있음. 키가 50개를 넘으면 외부 라이브러리 검토 |
| 모르는 키 | 무시 / 경고 / **에러** | 에러 | 오타가 조용히 기본값으로 대체되는 것 방지 |
| 결과 폴더 이름 | 시편 ID만 / **시각_시편ID** | `20261006-141500_S03_r02` | 덮어쓰기 방지, 정렬하면 시간순 |
| 커밋 안 된 수정 | 무시 / 기록 / 실행 거부 | 개발 중 **기록**, 본 실험 단계(W18~)는 **`dirty: true` 이면 실행 거부** 옵션 추가 | 개발 속도와 재현성의 균형 |
| git 없는 PC | 에러 / **`"unknown"` 으로 계속** | unknown | 실험실 측정 PC에 git이 없을 수 있음. 대신 manifest에 경고가 남음 |
| 시드 | 고정 안 함 / 실행마다 다름(기록) / **고정 42** | 기본 42, 바꾸면 manifest에 기록 | 청사진 J2 `random_seed: 42` |
| 난수 API | `np.random.seed` / **`np.random.default_rng`** | Generator 객체를 함수 인자로 전달 | 전역 상태 공유로 인한 순서 의존 제거 |
| 캘리브레이션 ID | 선택 / **실측 분석 시 필수** | `require_calibration=True` | D5 "모든 측정에 CAL-ID" 규칙 |
| 데이터 버전 관리 | Git LFS / DVC / **해시만 기록** | 입력 파일 SHA-256 기록 | 소규모 연구실에 추가 도구 부담 최소화. 원본은 F3 3-2-1 백업 |

## 5. 수행 절차

**1단계 (W1, 3일차) — 기본 설정 파일 만들기**
- [ ] 6.1절 `config/default.yaml` 을 저장 (청사진 J2 값 + `calibration_id`).
- [ ] 각 값 옆에 **단위와 근거 요소 번호**를 주석으로 적기 (예: `# 경계 제외 띠 (E2, G4)`).
- [ ] 아직 캘리브레이션 전이므로 `calibration_id: null` 로 두고, D5 완료 후 채움.

**2단계 (W1, 4–5일차) — 설정 모듈 작성**
- [ ] 6.2절 `config.py` 를 `src/cvlab/config.py` 로 저장.
- [ ] `python -m cvlab.config` 로 데모 실행 → 6.2절 기대 출력과 비교.
- [ ] 연구실에서 쓰는 파라미터가 늘어나면 `DEFAULTS` 와 `RULES` 에 **함께** 추가 (한쪽만 추가하면 테스트에서 걸림).

**3단계 (W2, 1일차) — 검증 규칙 정하기**
- [ ] 6.2절 RULES 표의 범위가 우리 장비에 맞는지 검토: 예) `resolution_mm` 0.005–0.2, `edge_band_mm` 0–2.0.
- [ ] 관계 규칙 2개(층높이 < 선폭, 격자 ≤ 선폭/5) 외에 필요한 규칙 추가 여부 결정 (예: `edge_band_mm ≥ line_width_mm/2`, E2 권장 "선폭의 절반 + 2·δx").

**4단계 (W2, 2일차) — 실행 스크립트에 연결**
- [ ] 6.3절 `run_analysis.py` 패턴을 J1의 `run_pipeline.py` 에 이식: `--config` 인자 추가, 각 단계 함수가 `ctx["cfg"]` 에서 값을 읽도록 변경.
- [ ] 같은 설정으로 2회 실행 → `result.json` 해시 동일 확인.
- [ ] `--set random_seed=7` 로 실행 → 결과가 달라지고 manifest의 `random_seed` 가 7인지 확인.

**5단계 (W2, 3일차) — 테스트**
- [ ] 6.4절 `tests/test_config.py` 저장 후 `python -m pytest tests/test_config.py -q` → `7 passed`.

**6단계 (W2, 4일차) — git 해시 기록 확인**
- [ ] 저장소 안에서 실행 → `manifest.json` 의 `git.commit` 이 `git rev-parse HEAD` 와 같은지 비교.
- [ ] 파일 하나를 고치고(커밋 안 함) 실행 → `dirty: true` 확인.
- [ ] git이 없는 폴더(예: USB)에서 실행 → `commit: "unknown"` 으로 멈추지 않고 진행 확인.

**7단계 (W2, 5일차) — 재현성 체크리스트 운영 규칙 확정**
- [ ] 청사진 J2 체크리스트 5개 항목에 담당자 지정 (10절 표).
- [ ] 결과 폴더를 지울 때 규칙: **논문·보고서에 쓴 결과 폴더는 삭제 금지**, `results/README.md` 에 "어느 그림 ← 어느 폴더" 대응표 유지.
- [ ] 측정 쪽 메타데이터(F3 `S03_r02.json`)와 분석 쪽 manifest가 `scan_id`, `calibration_id`, `gcode_sha256` 3개 키로 연결되는지 확인.

**8단계 (W11 이후, 반복) — 본 실험 전 잠금**
- [ ] 본 실험(W18–21) 시작 전 `default.yaml` 을 `config/exp_main_v1.yaml` 로 복사해 고정하고, 이후 변경은 새 파일(`v2`)로만.
- [ ] `start_run` 에 `dirty: true` 이면 중단하는 옵션 적용.

## 6. Python 구현

> 아래 코드는 테스트를 위해 같은 폴더에 둔 `config.py` 를 `from config import ...` 로 가져옵니다. 실제 저장소에서는 `src/cvlab/config.py` 에 두고 `from cvlab.config import ...` 로 바꿔 씁니다 (J1에서 `pip install -e .` 를 했다면 어디서든 동작).

### 6.1 `config/default.yaml`

```yaml
# config/default.yaml — 처리 파라미터 (청사진 J2). 단위는 키 이름 끝에 표시.
grid:
  resolution_mm: 0.02          # 격자 간격 = 측정 X 간격 (A2, G3)
gcode:
  line_width_mm: 0.42          # 명목 선폭 (G2)
  layer_height_mm: 0.2
  exclude_types: [SKIRT, SUPPORT]
  width_model: nominal         # nominal | extrusion
masks:
  edge_band_mm: 0.25           # 경계 제외 띠 (E2, G4)
preprocess:
  spike_mad_k: 5               # 스파이크 판정 k·MAD (H2)
  median_filter: false
registration:
  fiducial_radius_mm: 4.0      # 기준 구 반지름 (C3, H4)
metrics:
  tolerance_mm: 0.1            # 공차 (H5 공차 만족률)
calibration_id: CAL-2026-10-06-A
random_seed: 42
```

### 6.2 설정 모듈 — `src/cvlab/config.py`

```python
"""config.py — 설정(YAML) 읽기·검증 + 실행 기록(manifest) 저장 + 시드 고정 (J2).

src/cvlab/config.py 로 두고 다른 스크립트에서
    from cvlab.config import load_config, start_run
처럼 가져다 쓴다. 이 파일만 단독 실행하면 데모가 돈다:
    python config.py
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import platform
import random
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
import yaml

# ---------------------------------------------------------------- 1. 기본값
# 청사진 J2 의 config/default.yaml 과 같은 값. YAML에 빠진 항목은 이 값으로 채운다.
DEFAULTS = {
    "grid": {"resolution_mm": 0.02},
    "gcode": {
        "line_width_mm": 0.42,
        "layer_height_mm": 0.2,
        "exclude_types": ["SKIRT", "SUPPORT"],
        "width_model": "nominal",          # nominal | extrusion
    },
    "masks": {"edge_band_mm": 0.25},
    "preprocess": {"spike_mad_k": 5, "median_filter": False},
    "registration": {"fiducial_radius_mm": 4.0},
    "metrics": {"tolerance_mm": 0.1},
    "calibration_id": None,                # 예: CAL-2026-10-06-A (측정 분석 시 필수)
    "random_seed": 42,
}

# ---------------------------------------------------------------- 2. 검증 규칙
# 경로: (자료형, 최솟값, 최댓값) 또는 (자료형, 허용값 목록)
RULES = {
    "grid.resolution_mm": (float, 0.005, 0.2),
    "gcode.line_width_mm": (float, 0.1, 2.0),
    "gcode.layer_height_mm": (float, 0.04, 1.0),
    "gcode.width_model": (str, ["nominal", "extrusion"]),
    "gcode.exclude_types": (list, None),
    "masks.edge_band_mm": (float, 0.0, 2.0),
    "preprocess.spike_mad_k": (float, 2.0, 20.0),
    "preprocess.median_filter": (bool, None),
    "registration.fiducial_radius_mm": (float, 1.0, 10.0),
    "metrics.tolerance_mm": (float, 0.001, 1.0),
    "random_seed": (int, 0, 2**32 - 1),
}


class ConfigError(ValueError):
    """설정 파일에 문제가 있을 때 발생시키는 에러."""


def deep_merge(base: dict, override: dict) -> dict:
    """base 위에 override 를 덮어쓴 새 딕셔너리 (중첩 딕셔너리도 재귀적으로)."""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def _flat_keys(d: dict, prefix=""):
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            yield from _flat_keys(v, key + ".")
        else:
            yield key


def validate(cfg: dict, require_calibration: bool = False) -> None:
    errors = []
    # (a) 오타 잡기: 기본값에 없는 키는 거의 항상 오타다 (예: resoluton_mm)
    known = set(_flat_keys(DEFAULTS))
    for key in _flat_keys(cfg):
        if key not in known:
            errors.append(f"알 수 없는 키 '{key}' (오타인지 확인)")
    # (b) 자료형과 범위
    for key, rule in RULES.items():
        try:
            val = _get(cfg, key)
        except (KeyError, TypeError):
            errors.append(f"'{key}' 없음")
            continue
        typ = rule[0]
        if typ is float and isinstance(val, int) and not isinstance(val, bool):
            val = float(val)                      # YAML의 5 를 5.0 으로 인정
        if not isinstance(val, typ) or (typ is int and isinstance(val, bool)):
            errors.append(f"'{key}' 자료형 오류: {val!r} (필요: {typ.__name__})")
            continue
        if len(rule) == 3 and not (rule[1] <= val <= rule[2]):
            errors.append(f"'{key}'={val} 범위 밖 [{rule[1]}, {rule[2]}]")
        if len(rule) == 2 and isinstance(rule[1], list) and val not in rule[1]:
            errors.append(f"'{key}'={val!r} 허용값 아님 {rule[1]}")
    # (c) 값끼리의 관계
    try:
        if cfg["gcode"]["layer_height_mm"] >= cfg["gcode"]["line_width_mm"]:
            errors.append("layer_height_mm 는 line_width_mm 보다 작아야 함 (G2 비드 모델 가정)")
        if cfg["grid"]["resolution_mm"] > cfg["gcode"]["line_width_mm"] / 5:
            errors.append("격자가 너무 거침: 선폭에 최소 5칸이 들어가야 함 (A2 샘플링 규칙)")
    except (KeyError, TypeError):
        pass
    if require_calibration and not cfg.get("calibration_id"):
        errors.append("calibration_id 가 비어 있음 (실측 분석에는 필수, D5)")
    if errors:
        raise ConfigError("설정 오류 %d건:\n  - " % len(errors) + "\n  - ".join(errors))


def load_config(path: str | Path | None, overrides: dict | None = None,
                require_calibration: bool = False) -> dict:
    """YAML 읽기 → 기본값과 합치기 → (명령줄 등의) overrides 적용 → 검증."""
    user = {}
    if path is not None:
        with open(path, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}          # safe_load: 임의 코드 실행 방지
    cfg = deep_merge(DEFAULTS, user)
    cfg = deep_merge(cfg, overrides or {})
    validate(cfg, require_calibration)
    return cfg


# ---------------------------------------------------------------- 3. 재현성 도구
def set_seed(seed: int) -> np.random.Generator:
    """파이썬·numpy 난수 시드를 고정하고, 앞으로 쓸 Generator 를 돌려준다."""
    random.seed(seed)
    np.random.seed(seed)                 # 옛 방식 함수(np.random.rand 등)용
    return np.random.default_rng(seed)   # 새 코드는 이 rng 를 함수 인자로 넘겨 쓴다


def git_info(repo_dir: Path = Path(".")) -> dict:
    """git 커밋 해시와 '커밋 안 된 변경 있음' 여부. git 이 없거나 저장소가 아니면 unknown."""
    def _run(*args):
        return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True,
                              text=True, timeout=10, check=True).stdout.strip()
    try:
        commit = _run("rev-parse", "HEAD")
        dirty = bool(_run("status", "--porcelain", "--untracked-files=no"))
        return {"commit": commit, "dirty": dirty}
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {"commit": "unknown", "dirty": None}


def lib_versions(names=("numpy", "scipy", "shapely",
                        ("opencv-python", "opencv-python-headless", "opencv-contrib-python"),
                        "matplotlib", "pandas", "PyYAML")) -> dict:
    """설치된 라이브러리 버전. 튜플은 '이름이 여러 개인 같은 라이브러리'(예: OpenCV 배포판)."""
    out = {"python": platform.python_version()}
    for n in names:
        candidates = n if isinstance(n, tuple) else (n,)
        out[candidates[0]] = "not installed"
        for c in candidates:
            try:
                out[candidates[0]] = f"{metadata.version(c)} ({c})" if c != candidates[0] else metadata.version(c)
                break
            except metadata.PackageNotFoundError:
                continue
    return out


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def start_run(cfg: dict, config_path: Path | None, results_root: Path, run_name: str,
              input_files: list[Path] = ()) -> Path:
    """결과 폴더를 만들고 config 복사본 + manifest.json 을 저장한다. 결과 폴더 경로를 반환."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(results_root) / f"{stamp}_{run_name}"
    k = 2
    while run_dir.exists():                              # 같은 초에 두 번 실행해도 덮어쓰지 않음
        run_dir = Path(results_root) / f"{stamp}_{run_name}_{k}"
        k += 1
    run_dir.mkdir(parents=True)
    if config_path is not None:
        shutil.copy2(config_path, run_dir / "config_original.yaml")   # 사람이 쓴 원본
    with open(run_dir / "config_resolved.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)    # 기본값까지 합친 실제 사용값
    manifest = {
        "run_name": run_name,
        "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git": git_info(),
        "calibration_id": cfg.get("calibration_id"),
        "random_seed": cfg["random_seed"],
        "command": " ".join(sys.argv),
        "platform": platform.platform(),
        "libraries": lib_versions(),
        "inputs": {str(p): sha256_of(Path(p)) for p in input_files},
    }
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return run_dir


# ---------------------------------------------------------------- 4. 데모
if __name__ == "__main__":
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    good = tmp / "exp01.yaml"
    good.write_text("grid:\n  resolution_mm: 0.02\nmetrics:\n  tolerance_mm: 0.05\n"
                    "calibration_id: CAL-2026-10-06-A\nrandom_seed: 7\n", encoding="utf-8")
    cfg = load_config(good, require_calibration=True)
    print("tolerance_mm =", cfg["metrics"]["tolerance_mm"], "(YAML 값)")
    print("line_width_mm =", cfg["gcode"]["line_width_mm"], "(기본값으로 채워짐)")

    rng = set_seed(cfg["random_seed"])
    print("시드 7 첫 난수:", np.round(rng.normal(size=3), 4))
    rng = set_seed(cfg["random_seed"])
    print("다시 시드 7  :", np.round(rng.normal(size=3), 4), "← 같아야 함")

    gfile = tmp / "square.gcode"
    gfile.write_text("G21\nG90\nG1 X10 Y0 E1\n", encoding="utf-8")
    run_dir = start_run(cfg, good, tmp / "results", "S01_r01", [gfile])
    print("결과 폴더 파일:", sorted(p.name for p in run_dir.iterdir()))
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    print("manifest 키:", list(man))

    bad = tmp / "bad.yaml"
    bad.write_text("grid:\n  resoluton_mm: 0.02\nmetrics:\n  tolerance_mm: -1\n"
                   "gcode:\n  width_model: Nominal\n", encoding="utf-8")
    try:
        load_config(bad)
    except ConfigError as e:
        print(e)
```

실행 예시 (`python config.py`, 저장소 밖 임시 폴더에서 동작):
```text
tolerance_mm = 0.05 (YAML 값)
line_width_mm = 0.42 (기본값으로 채워짐)
시드 7 첫 난수: [ 0.0012  0.2987 -0.2741]
다시 시드 7  : [ 0.0012  0.2987 -0.2741] ← 같아야 함
결과 폴더 파일: ['config_original.yaml', 'config_resolved.yaml', 'manifest.json']
manifest 키: ['run_name', 'timestamp', 'git', 'calibration_id', 'random_seed', 'command', 'platform', 'libraries', 'inputs']
설정 오류 3건:
  - 알 수 없는 키 'grid.resoluton_mm' (오타인지 확인)
  - 'gcode.width_model'='Nominal' 허용값 아님 ['nominal', 'extrusion']
  - 'metrics.tolerance_mm'=-1.0 범위 밖 [0.001, 1.0]
```

### 6.3 실행 스크립트에 붙이기 — `scripts/run_analysis.py`

```python
"""run_analysis.py — 설정 + manifest + 시드를 실제 실행 스크립트에 붙이는 예 (J2).

사용 예:
  python run_analysis.py --config config/default.yaml --name S01_r01
  python run_analysis.py --config config/default.yaml --name S01_r01 --set metrics.tolerance_mm=0.05
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from config import ConfigError, load_config, set_seed, start_run


def parse_set(items):
    """['a.b=1', 'c=[X, Y]'] → {'a': {'b': 1}, 'c': ['X', 'Y']}  (값은 YAML 문법으로 해석)."""
    out = {}
    for item in items or []:
        key, _, raw = item.partition("=")
        cur = out
        parts = key.strip().split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = yaml.safe_load(raw)
    return out


def fake_ransac_like(rng, n=1000):
    """무작위성이 있는 처리의 대역(예: RANSAC 평면 맞춤). 시드가 같으면 결과도 같아야 한다."""
    idx = rng.choice(n, size=50, replace=False)
    return float(np.sort(idx)[:10].sum())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--name", required=True, help="실행 이름 (보통 scan_id)")
    ap.add_argument("--set", action="append", help="설정 덮어쓰기: key.sub=value (여러 번 가능)")
    ap.add_argument("--results", type=Path, default=Path("results"))
    a = ap.parse_args(argv)
    try:
        cfg = load_config(a.config, overrides=parse_set(a.set))
    except ConfigError as e:
        print(e)
        return 2
    rng = set_seed(cfg["random_seed"])
    run_dir = start_run(cfg, a.config, a.results, a.name)
    result = {"tolerance_mm": cfg["metrics"]["tolerance_mm"], "ransac_like": fake_ransac_like(rng)}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    digest = hashlib.sha256((run_dir / "result.json").read_bytes()).hexdigest()[:12]
    print(f"결과 폴더: {run_dir}")
    print(f"result = {result}   sha256[:12] = {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

실행 예시:
```text
$ python run_analysis.py --config config/default.yaml --name S01_r01
결과 폴더: results/20261006-111212_S01_r01
result = {'tolerance_mm': 0.1, 'ransac_like': 1265.0}   sha256[:12] = b3061fa8f82e
$ python run_analysis.py --config config/default.yaml --name S01_r01
결과 폴더: results/20261006-111212_S01_r01_2
result = {'tolerance_mm': 0.1, 'ransac_like': 1265.0}   sha256[:12] = b3061fa8f82e      ← 해시 동일 = 재현됨
$ python run_analysis.py --config config/default.yaml --name S01_r01 --set metrics.tolerance_mm=0.05 --set random_seed=7
결과 폴더: results/20261006-111212_S01_r01_3
result = {'tolerance_mm': 0.05, 'ransac_like': 1079.0}   sha256[:12] = 9dc01894734b
$ python run_analysis.py --config config/default.yaml --name bad --set grid.resolution_mm=0.1
설정 오류 1건:
  - 격자가 너무 거침: 선폭에 최소 5칸이 들어가야 함 (A2 샘플링 규칙)
(종료코드 2)
```

생성된 `manifest.json` 예 (git 저장소 밖에서 실행한 경우라 commit 이 unknown):
```json
{
  "run_name": "S01_r01",
  "timestamp": "2026-10-06T11:12:12+00:00",
  "git": {"commit": "unknown", "dirty": null},
  "calibration_id": "CAL-2026-10-06-A",
  "random_seed": 7,
  "command": "run_analysis.py --config config/default.yaml --name S01_r01 --set metrics.tolerance_mm=0.05 --set random_seed=7",
  "platform": "Linux-6.18.44-fc-v70-x86_64-with-glibc2.39",
  "libraries": {"python": "3.13.16", "numpy": "2.5.3", "scipy": "1.18.1", "shapely": "2.1.2",
                "opencv-python": "5.0.0.93 (opencv-python-headless)", "matplotlib": "3.11.2",
                "pandas": "3.0.5", "PyYAML": "6.0.1"},
  "inputs": {}
}
```
저장소 안에서 실행하면 `"git": {"commit": "28dde58fe4b7e8d555e7fc575fd872ffb7ef59d2", "dirty": false}` 처럼 기록됩니다. 실측 분석에서는 `start_run(..., input_files=[gcode_path, raw_npz_path])` 로 입력 파일 해시도 남깁니다.

### 6.4 테스트 — `tests/test_config.py`

```python
"""J2 설정·재현성 테스트."""
import json

import numpy as np
import pytest

from config import ConfigError, git_info, load_config, set_seed, start_run


def write(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_defaults_fill_missing(tmp_path):
    cfg = load_config(write(tmp_path, "metrics:\n  tolerance_mm: 0.05\n"))
    assert cfg["metrics"]["tolerance_mm"] == 0.05          # YAML 값
    assert cfg["grid"]["resolution_mm"] == 0.02            # 기본값


def test_typo_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="resoluton_mm"):
        load_config(write(tmp_path, "grid:\n  resoluton_mm: 0.02\n"))


def test_range_and_choice(tmp_path):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, "metrics:\n  tolerance_mm: -1\n"))
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, "gcode:\n  width_model: Nominal\n"))


def test_calibration_required(tmp_path):
    with pytest.raises(ConfigError, match="calibration_id"):
        load_config(write(tmp_path, ""), require_calibration=True)


def test_seed_reproducible():
    a = set_seed(42).normal(size=5)
    b = set_seed(42).normal(size=5)
    assert np.array_equal(a, b)


def test_manifest_written(tmp_path):
    cfg = load_config(None, overrides={"calibration_id": "CAL-2026-10-06-A"})
    d1 = start_run(cfg, None, tmp_path, "S01_r01")
    d2 = start_run(cfg, None, tmp_path, "S01_r01")         # 같은 초에 다시 → 다른 폴더
    assert d1 != d2
    man = json.loads((d1 / "manifest.json").read_text(encoding="utf-8"))
    for key in ("timestamp", "git", "calibration_id", "random_seed", "libraries"):
        assert key in man
    assert man["calibration_id"] == "CAL-2026-10-06-A"
    assert (d1 / "config_resolved.yaml").exists()


def test_git_info_outside_repo(tmp_path):
    assert git_info(tmp_path)["commit"] == "unknown"       # git 저장소 아님 → 멈추지 않고 unknown
```

실행 예시:
```text
$ python -m pytest tests/test_config.py -q
.......                                                                  [100%]
7 passed in 0.17s
```

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 기본값 채움 | 키 1개만 있는 YAML 로드 | 나머지 키 전부 DEFAULTS 값 (테스트 통과) |
| 오타 검출 | 키 철자 1자 틀린 YAML | `ConfigError`, 메시지에 틀린 키 이름 포함 |
| 범위·허용값 | 범위 밖 값 3종 | 3건 모두 한 번에 보고 (첫 오류에서 멈추지 않음) |
| 관계 규칙 | `resolution_mm=0.1`, 선폭 0.42 | 오류 1건 (0.1 > 0.42/5 = 0.084) |
| 재현성 | 같은 설정·시드로 2회 실행 | `result.json` SHA-256 동일 (2/2) |
| 시드 민감도 | 시드만 바꿔 실행 | 결과가 달라지고 manifest에 새 시드 기록 |
| manifest 완전성 | 결과 폴더 검사 | 9개 키 모두 존재, `config_resolved.yaml` 존재 |
| git 기록 | 저장소 안 / 밖 실행 | 안: 40자리 해시 = `git rev-parse HEAD`, 밖: `"unknown"` 으로 정상 종료 |
| dirty 감지 | 커밋 안 한 수정 후 실행 | `dirty: true` |
| 덮어쓰기 방지 | 1초 안에 2회 실행 | 서로 다른 폴더 2개 |
| 자동 테스트 | `pytest tests/test_config.py` | 7 passed, 0 failed |
| 코드 내 하드코딩 | `grep -rn "0\.02\|0\.42\|0\.25" src/cvlab` | 설정 모듈(DEFAULTS) 외 0건 (W14 M4 시점) |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| YAML 들여쓰기에 탭 사용 | `yaml.scanner.ScannerError` | VS Code 오른쪽 아래 "Spaces: 2" 설정 |
| 지수 표기 `2e-2` 사용 | PyYAML(YAML 1.1 규칙)이 숫자가 아닌 **문자열** `'2e-2'` 로 읽음 | `0.02` 또는 소수점 있는 `2.0e-2` 사용. 검증기가 자료형 오류로 잡음 |
| `exclude_types: SKIRT, SUPPORT` (괄호 없음) | 리스트가 아니라 문자열 하나 | `[SKIRT, SUPPORT]` 또는 `- SKIRT` 줄 형식 |
| `yes`/`no`/`on`/`off` 를 문자열로 의도 | YAML 1.1 규칙으로 True/False 로 읽힘 | 문자열은 따옴표: `"on"` |
| 코드 안에서 설정값 수정 (`cfg["grid"]["resolution_mm"] = 0.01`) | manifest와 실제 사용값 불일치 | 설정 변경은 YAML 또는 `--set` 으로만. 로드 후 읽기 전용으로 취급 |
| 결과 폴더를 시편 ID로만 생성 | 재실행 시 이전 결과 덮어씀 | 시각_ID 폴더 + `_2` 접미사 (6.2) |
| 커밋 안 하고 본 실험 처리 | `dirty: true`, 그 코드 상태를 되살릴 수 없음 | 처리 전 `git status` 깨끗하게, 본 실험부터 dirty 거부 |
| `np.random.rand()` 를 여러 함수에서 호출 | 함수 호출 순서가 바뀌면 결과가 바뀜 | `rng` 객체를 인자로 전달 |
| 시드를 고정했는데 결과가 다름 | 멀티스레드 처리, 집합(set) 순회 순서, 라이브러리 버전 차이 | 정렬 후 처리, 라이브러리 버전 고정, 차이가 1e-12 수준인지 확인 |
| 캘리브레이션 ID 를 손으로 입력 | 오타로 존재하지 않는 ID 기록 | `config/calibration/<ID>/` 폴더 존재 여부를 검증 규칙에 추가 |
| manifest를 나중에 손으로 작성 | 누락·불일치 | `start_run` 이 자동 생성. 손으로 쓰지 않음 |

## 9. 위험 요소

- **설정 키 증가**: H·I 영역이 진행되며 파라미터가 30–50개로 늘어납니다. DEFAULTS·RULES·default.yaml 세 곳을 동시에 고쳐야 하므로, 키를 추가할 때 `test_defaults_fill_missing` 류 테스트를 같이 추가합니다.
- **라이브러리 업데이트로 인한 결과 변화**: 같은 코드라도 numpy·shapely·OpenCV 메이저 버전이 바뀌면 경계 픽셀이 달라질 수 있습니다. 본 실험 기간(W18–21)에는 `pip install --upgrade` 금지, 업그레이드는 J3 합성 테스트를 전부 다시 통과한 뒤에만 합니다.
- **git 해시만으로는 데이터 재현 불가**: 코드는 되살려도 원본 데이터가 없으면 재현이 안 됩니다. 입력 SHA-256 기록 + F3 3-2-1 백업을 함께 운영합니다.
- **측정 PC와 분석 PC 분리**: 촬영 PC의 메타데이터(F3)와 분석 PC의 manifest가 따로 놀 수 있습니다. 두 파일을 잇는 키(`scan_id`, `calibration_id`, `gcode_sha256`)를 반드시 양쪽에 둡니다.
- **시간대 혼동**: 여러 PC의 시계가 다르면 시간순 정렬이 틀어집니다. manifest는 시간대(+09:00 등)를 포함한 ISO 형식으로 기록하고, PC 시계는 인터넷 시간 동기화를 켭니다.

## 10. 기록 양식

**실험 설정 변경 이력** (`config/CHANGELOG.md`)

| 날짜 | 파일 | 키 | 이전 값 | 새 값 | 이유 (근거 요소) | 영향받는 결과 폴더 | 작성자 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

**재현성 체크리스트 담당표** (청사진 J2 체크리스트)

| 항목 | 담당 | 확인 주기 | 마지막 확인일 | 상태 |
|---|---|---|---|---|
| `requirements.txt` 버전 고정 | | 라이브러리 추가 시 | | |
| 가상환경 사용 | | 신규 인원 합류 시 | | |
| 결과 폴더에 설정·해시·CAL-ID 자동 저장 | | 매 실행 (자동) | | |
| 무작위 알고리즘 시드 고정 | | 코드 리뷰 시 | | |
| Git 관리 (데이터는 Git 밖, 경로만 기록) | | 주 1회 | | |

**결과 폴더 ↔ 보고서 대응표** (`results/README.md`)
```csv
figure_or_table,run_dir,scan_ids,git_commit,dirty,calibration_id,config_file,note
Fig5_heatmap,results/20270115-101500_S03_r02,S03_r02,28dde58,false,CAL-2026-12-14-A,config/exp_main_v1.yaml,
```

**실험 설정 YAML 템플릿** (`config/exp_<이름>.yaml`, 바꾸는 값만)
```yaml
# 실험: <이름>   작성: <이름>   날짜: <YYYY-MM-DD>
# 목적: <무엇을 바꿔서 무엇을 보려는가>
calibration_id: CAL-YYYY-MM-DD-X
metrics:
  tolerance_mm: 0.1
random_seed: 42
```

## 11. 참고 자료

- PyYAML 문서 — "PyYAML Documentation" (`yaml.safe_load`, `yaml.safe_dump`)
- YAML 1.2 사양 (yaml.org) — 자료형 해석 규칙
- Python 공식 문서 — `subprocess`, `importlib.metadata`, `hashlib`, `json`, `datetime`, `argparse`
- NumPy 문서 — "Random Generator" (`numpy.random.default_rng`) 및 "Random sampling" 의 시드 관련 권장 사항
- Git 문서 — `git rev-parse`, `git status --porcelain`
- pip 문서 — "pip freeze", "Requirements File Format"
- Wilson, G. 외, "Good enough practices in scientific computing", PLOS Computational Biology (2017)
