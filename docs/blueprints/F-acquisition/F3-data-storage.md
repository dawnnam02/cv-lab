# F3. 데이터 저장 형식 · 메타데이터

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: F. 데이터 획득

| 항목 | 내용 |
|---|---|
| 기간 | 2026-12-01 ~ 2026-12-14 (W9-10) |
| 우선순위 | 보통 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [F1 레이저 라인 중심 추출](F1-line-extraction.md) · [F2 획득 파라미터](F2-acquisition-params.md) · [J1 소프트웨어 구조](../J-software/J1-software-structure.md) · [J2 설정·재현성](../J-software/J2-config-reproducibility.md) · [D5 캘리브레이션 검증·이력](../D-calibration/D5-calibration-verification.md) · [G1 G코드 파싱](../G-reference/G1-gcode-parsing.md) |
| 후행 요소 | [H1 점→격자 변환](../H-analysis/H1-gridding.md) · [H8 통계 분석](../H-analysis/H8-statistics.md) · [I2 MSA](../I-reliability/I2-msa.md) · [J4 시각화·리포트](../J-software/J4-visualization-report.md) · [K5 산출물·논문](../K-management/K5-deliverables-paper.md) |
| 관련 마일스톤 | M2 (D5 검증 측정부터 이 형식으로 저장) |

---

## 1. 목적

스캔 한 번의 결과를 **나중에 누가 보더라도 "무엇을, 언제, 어떤 장비 상태로, 어떤 G코드와 비교하려고" 측정했는지 알 수 있게** 저장하는 규칙과 코드를 만듭니다.

- 측정 데이터는 다시 만들 수 없습니다. 형식이 엉망이면 24주 후 논문을 쓸 때 "이 스캔이 어느 캘리브레이션이었지?"에 답할 수 없습니다.
- 이 요소가 끝나면: ① 폴더·파일 이름 규칙, ② 메타데이터 필수 항목과 자동 검증, ③ `.npz` + `.json` 저장/불러오기 함수(지문 검증 포함), ④ `experiments.csv` 총괄표, ⑤ 백업 절차가 정해지고 동작해야 합니다.
- **M2 의 게이지 블록 측정(D5)부터** 이 형식을 씁니다. 그 전 데이터는 `data/raw/_legacy/` 에 따로 둡니다.

## 2. 배경 지식 (초보자용)

**`.npz` 파일**: numpy 배열 여러 개를 이름을 붙여 한 파일에 담는 형식입니다. `np.savez_compressed("a.npz", v=v, peak=peak)` 로 저장하고 `np.load("a.npz")["v"]` 로 꺼냅니다. NaN 도 그대로 보존됩니다. 압축(`_compressed`)하면 용량이 줄고 읽을 때 자동으로 풀립니다.

**`.json` 파일**: 사람이 메모장으로 읽을 수 있는 "이름: 값" 텍스트입니다. Python 의 딕셔너리와 거의 같습니다. 메타데이터(측정 조건)는 json 에 둡니다. 한글을 쓰려면 `ensure_ascii=False`, 파일은 `encoding="utf-8"` 로 저장합니다.

**메타데이터**: "데이터에 대한 데이터". 측정값 자체가 아니라 측정 조건(날짜, 측정자, 온도, 노출, 캘리브레이션 ID 등)입니다.

**SHA-256 지문(해시)**: 파일 내용을 64자리 16진수로 요약한 값입니다. **1바이트만 달라도 완전히 다른 값**이 나옵니다. 두 가지에 씁니다.
1. **G코드 지문** (`gcode_sha256`): 파일 이름이 같아도 내용이 다른 G코드(슬라이서 설정을 바꿔 다시 저장한 경우)를 구별합니다. 비교 기준(G 영역)이 정확히 어떤 파일이었는지 증명합니다.
2. **데이터 파일 지문** (`files`): 저장 후 `.npz` 가 바뀌거나 손상되었는지 불러올 때 검사합니다.

**ID 체계** (이 프로젝트의 모든 문서에서 같은 형식)

| ID | 형식 | 예 | 정하는 곳 |
|---|---|---|---|
| 시편 ID | `S` + 2자리 | `S03` | E3 |
| 스캔 ID | `시편ID_r반복2자리` (층별이면 `_L층3자리`) | `S03_r02`, `S03_r02_L015` | F3 (BLUEPRINT 규칙) |
| 캘리브레이션 ID | `CAL-YYYY-MM-DD-문자` | `CAL-2026-11-30-A` | D5 |
| 획득 프로파일 ID | `ACQ-YYYY-MM-DD-문자` | `ACQ-2026-12-10-A` | F2 |

**원본 수정 금지**: `data/raw` 의 파일은 **절대 고치지 않습니다**. 잘못 찍었으면 새 반복번호(`r03`)로 다시 찍고, 잘못된 스캔은 `experiments.csv` 의 `notes` 에 "무효: 이유"를 적습니다. 처리 결과는 `data/processed` 에 따로 저장합니다.

**용량 계산** (B1·F2 예시 장비 기준)

| 데이터 | 계산 | 스캔 1회(50 mm, 2501 프레임) |
|---|---|---|
| 원본 이미지 전체 센서 8-bit | 1440 × 1080 × 1 B × 2501 | ≈ 3.9 GB (BLUEPRINT 값) |
| 원본 이미지 ROI 584 행, 12-bit(16-bit 저장) | 1440 × 584 × 2 B × 2501 | ≈ 4.2 GB (PNG 압축 전) |
| 프로파일 묶음 (v float32 + peak uint16 + width float32) | 1440 × 10 B × 2501 | ≈ 36 MB (압축 전) |
| 메타데이터 json | – | ≈ 2 KB |

본 실험(조건 수 × 시편 3 × 스캔 3, H8)이 수십 스캔이면 원본 이미지 전체 저장은 수백 GB 가 됩니다. 그래서 BLUEPRINT 전략대로 **개발 초기에는 전부, 안정화 후에는 프로파일 + 샘플 이미지 몇 장**만 저장합니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 · 파일 | 설명 |
|---|---|---|---|
| 입력 | 프레임별 추출 결과 | F1 출력 `v`, `peak`, `width` (N × W) | NaN = 검출 실패 |
| 입력 | 스테이지 위치·시각 | `stage_y_mm`, `t_s` (N,) | C1 엔코더 / 트리거 기록 |
| 입력 | 획득 프로파일 | `config/acquisition/ACQ-….yaml` | F2 |
| 입력 | 캘리브레이션 ID | `config/calibration/CAL-…/` | D5 |
| 입력 | G코드 파일 | `data/gcode/<이름>.gcode` | G1 |
| 산출물 | 메타데이터 | `data/raw/<scan_id>/<scan_id>.json` | 6.1 스키마 (schema_version 1) |
| 산출물 | 프로파일 묶음 | `data/raw/<scan_id>/<scan_id>_profiles.npz` | 키: `v`, `peak`, `width`, `stage_y_mm`, `t_s` |
| 산출물 | 원본 프레임(선택) | `data/raw/<scan_id>/frames/000000.png …` | 16-bit 무손실 PNG |
| 산출물 | 실험 총괄표 | `data/experiments.csv` | 스캔 1회 = 1줄, 열 순서 고정 |
| 산출물 | 저장 모듈 | `src/cvlab/acquisition/storage.py` | `save_scan_bundle`, `load_scan_bundle`, `append_experiment`, `validate_meta` |
| 산출물 | 단위 테스트 | `tests/test_storage.py` | pytest 9개 통과 |
| 산출물 | 백업 기록 | `data/backup_log.csv` | 날짜, 대상, 매체, 확인자 |

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 프로파일 형식 | `.npz` / HDF5 / `.csv` | **`.npz` (압축)** | numpy 만으로 읽고 씀, 초보에게 쉬움. csv 는 10배 크고 느림 |
| 메타데이터 형식 | `.json` / `.yaml` / 파일 이름에 넣기 | **`.json` (스캔마다 1개)** | BLUEPRINT F3. 이름에는 ID 만, 조건은 메타데이터에 |
| 원본 이미지 형식 | PNG / TIFF / JPEG | **16-bit PNG (무손실)** | JPEG 는 손실 압축 → 중심 위치가 바뀜. 금지 |
| 원본 이미지 보존 | 전체 / 샘플 | 개발 초기(~M3): **전체**, 안정화 후(M4~): **250장마다 1장 + 첫·끝** | 재처리 가능성 vs 용량 |
| 폴더 구조 | 날짜별 / 스캔별 | **스캔 ID 별 폴더 1개** | 한 스캔의 모든 파일이 한곳에 |
| 스캔 ID 규칙 | 자유 / 정규식 강제 | **`^S\d{2}_r\d{2}(_L\d{3})?$` 강제** | 정렬·검색·자동 처리 가능 |
| 시각 표기 | 지역시각 / ISO 8601 + 시간대 | **ISO 8601 + `+09:00`** | 모호함 제거 |
| 덮어쓰기 | 허용 / 금지 | **금지 (폴더가 있으면 오류) + 읽기 전용 권한** | 원본 보호 |
| 메타데이터 값 출처 | 손으로 입력 / 자동 | 노출·게인 등 장비값은 **카메라에서 읽어 자동**, 온도·메모는 입력 | 오타·누락 방지 |
| 총괄표 | 엑셀 / CSV | **`experiments.csv` (UTF-8)** + pandas 로 읽기 | Git 으로 변경 이력 확인 가능 |
| 백업 | 없음 / 3-2-1 | **3-2-1** (연구실 PC + 외장 HDD + 학교 클라우드/NAS 중 1곳 외부) | BLUEPRINT F3 |
| 스키마 변경 | 그냥 바꿈 / 버전 | **`schema_version` 올리고 변경 기록** | 옛 파일을 읽는 코드가 구별 가능 |

## 5. 수행 절차

1. **규칙 확정 (W9 월, 0.5일)**
   - [ ] 2절 ID 체계와 4절 결정 사항을 팀이 확인 (K2 역할: 실험·품질 담당이 관리자)
   - [ ] 필수 메타데이터 항목 목록 확정 (6.1 의 `REQUIRED_META`, BLUEPRINT 예시 + `acq_id`, `roi_rows`, `frame_avg_n`)
2. **폴더 만들기 (W9 월, 0.5일)**
   - [ ] `data/raw`, `data/processed`, `data/gcode`, `config/acquisition`, `config/calibration` 생성 (J1)
   - [ ] `.gitignore` 에 `data/raw/`, `data/processed/` 추가 (데이터는 Git 밖), `data/experiments.csv` 는 Git 에 포함
3. **저장 모듈 구현 (W9 화~목, 2.5일)**
   - [ ] 6.1 코드를 `src/cvlab/acquisition/storage.py` 로 저장, 실행 → 6.2 와 같은 출력 확인
   - [ ] 6.4 pytest 9개 통과
   - [ ] 6.3 프레임 저장 함수 추가, 16-bit 무손실 확인
4. **촬영 스크립트와 연결 (W10 월~화, 1.5일)**
   - [ ] `scripts/run_scan.py` 의 마지막 단계에서 `save_scan_bundle` → `append_experiment` 순서로 호출
   - [ ] 카메라에서 다시 읽은 노출·게인값(F2 6.4)과 엔코더 위치를 자동으로 메타데이터·npz 에 넣기
   - [ ] 스캔 시작 전에 `validate_meta` 를 먼저 실행해서, 메타데이터가 틀리면 **촬영을 시작하지 않게** 함 (25초 촬영 후 저장 실패 방지)
5. **실제 시험 저장 (W10 수, 1일)**
   - [ ] 평판을 `S00_r01`~`S00_r03` 으로 3회 스캔·저장 → 불러와서 높이 프로파일 1줄을 그려 확인
   - [ ] 용량 실측 → 2절 표와 비교해서 기록
6. **백업 체계 (W10 목, 0.5일)**
   - [ ] 외장 HDD 로 복사 (`rsync -a` 또는 파일 복사) → 복사본에서 `load_scan_bundle(verify=True)` 로 지문 검사
   - [ ] 외부 사본(학교 클라우드/NAS) 1곳 지정, 주 1회 동기화 일정 등록
   - [ ] `data/backup_log.csv` 첫 줄 기록
7. **문서화 (W10 금, 0.5일)**
   - [ ] `data/README.md`(1쪽): 폴더 구조, ID 규칙, 메타데이터 항목 의미·단위, 무효 스캔 처리 방법

## 6. Python 구현

### 6.1 저장 · 불러오기 · 총괄표 모듈 (`storage.py`)

```python
"""
storage.py — 스캔 데이터 저장 · 불러오기 · 실험 총괄표 (F3)
최종 위치(권장): src/cvlab/acquisition/storage.py

폴더 구조 (스캔 1회 = 폴더 1개)
data/raw/S03_r02/
    S03_r02.json            ← 메타데이터 (사람이 읽는 파일)
    S03_r02_profiles.npz    ← 프로파일 묶음 (v, peak, width, stage_y_mm, t_s)
    frames/                 ← (개발 초기만) 원본 이미지 000000.png ...
data/experiments.csv        ← 모든 스캔의 한 줄 요약
"""
import csv
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np

SCHEMA_VERSION = 1
SCAN_ID_RE = re.compile(r"^S\d{2}_r\d{2}(_L\d{3})?$")      # S03_r02, 층별이면 S03_r02_L015
SPECIMEN_RE = re.compile(r"^S\d{2}$")
CAL_ID_RE = re.compile(r"^CAL-\d{4}-\d{2}-\d{2}-[A-Z]$")    # CAL-2026-10-06-A (D5)
ACQ_ID_RE = re.compile(r"^ACQ-\d{4}-\d{2}-\d{2}-[A-Z]$")    # ACQ-2026-12-10-A (F2)

# 메타데이터 필수 항목: 이름 → 허용 타입
REQUIRED_META = {
    "scan_id": str, "specimen_id": str, "repeat": int, "datetime": str,
    "operator": str, "gcode_file": str, "gcode_sha256": str,
    "calibration_id": str, "acq_id": str, "room_temp_C": (int, float), "bed_temp_C": (int, float),
    "exposure_us": (int, float), "gain_db": (int, float), "laser_power_pct": (int, float),
    "roi_rows": list, "frame_avg_n": int,
    "scan_pitch_mm": (int, float), "scan_speed_mm_s": (int, float), "notes": str,
}
# experiments.csv 열 순서 (고정 — 바꾸면 SCHEMA_VERSION 을 올린다)
CSV_COLUMNS = ["scan_id", "specimen_id", "repeat", "datetime", "operator",
               "gcode_file", "gcode_sha256", "calibration_id", "acq_id", "room_temp_C",
               "bed_temp_C", "exposure_us", "gain_db", "laser_power_pct",
               "frame_avg_n", "scan_pitch_mm", "scan_speed_mm_s", "n_frames",
               "valid_pct", "notes"]
PROFILE_KEYS = {"v": 2, "peak": 2, "width": 2, "stage_y_mm": 1, "t_s": 1}  # 이름: 차원 수


def sha256_file(path, chunk=1 << 20):
    """파일 내용의 지문(SHA-256). 1바이트만 달라도 완전히 다른 값이 나온다"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def git_commit():
    """현재 코드의 git 커밋 해시 (J2 재현성). git 이 없으면 'unknown'"""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True, timeout=5).stdout.strip()
    except Exception:
        return "unknown"


def validate_scan_id(scan_id):
    return bool(SCAN_ID_RE.match(scan_id))


def validate_meta(meta):
    """문제 목록(문자열 리스트)을 반환. 빈 리스트면 통과"""
    errs = []
    for k, typ in REQUIRED_META.items():
        if k not in meta:
            errs.append(f"필수 항목 없음: {k}")
        elif not isinstance(meta[k], typ) or isinstance(meta[k], bool):
            errs.append(f"타입 오류: {k}={meta[k]!r}")
    if errs:
        return errs
    if not validate_scan_id(meta["scan_id"]):
        errs.append(f"scan_id 형식 오류: {meta['scan_id']} (예: S03_r02)")
    if not SPECIMEN_RE.match(meta["specimen_id"]):
        errs.append(f"specimen_id 형식 오류: {meta['specimen_id']}")
    elif not meta["scan_id"].startswith(f"{meta['specimen_id']}_r{meta['repeat']:02d}"):
        errs.append("scan_id 와 specimen_id/repeat 불일치")
    if not CAL_ID_RE.match(meta["calibration_id"]):
        errs.append(f"calibration_id 형식 오류: {meta['calibration_id']}")
    if not ACQ_ID_RE.match(meta["acq_id"]):
        errs.append(f"acq_id 형식 오류: {meta['acq_id']}")
    if not re.fullmatch(r"[0-9a-f]{64}", meta["gcode_sha256"]):
        errs.append("gcode_sha256 은 64자리 16진수여야 함")
    try:
        datetime.fromisoformat(meta["datetime"])
    except ValueError:
        errs.append(f"datetime 형식 오류(ISO 8601): {meta['datetime']}")
    if not (0 < meta["exposure_us"] < 1e6):
        errs.append("exposure_us 범위 오류")
    if not (0 <= meta["laser_power_pct"] <= 100):
        errs.append("laser_power_pct 는 0~100")
    return errs


def save_scan_bundle(raw_root, meta, profiles, readonly=True):
    """
    raw_root : data/raw 폴더
    meta     : 메타데이터 dict (REQUIRED_META 항목 포함)
    profiles : {"v": (N,W) float32, "peak": (N,W), "width": (N,W),
                "stage_y_mm": (N,), "t_s": (N,)}
    반환     : 스캔 폴더 경로
    """
    errs = validate_meta(meta)
    if errs:
        raise ValueError("메타데이터 오류:\n  " + "\n  ".join(errs))
    for k, nd in PROFILE_KEYS.items():
        if k not in profiles or np.ndim(profiles[k]) != nd:
            raise ValueError(f"profiles['{k}'] 없음 또는 차원 오류 (필요 {nd}차원)")
    N, W = profiles["v"].shape
    if profiles["stage_y_mm"].shape != (N,):
        raise ValueError("stage_y_mm 길이 ≠ 프레임 수")

    sid = meta["scan_id"]
    d = Path(raw_root) / sid
    if d.exists():
        raise FileExistsError(f"{d} 가 이미 있음 — 원본은 덮어쓰지 않는다 (반복번호를 올릴 것)")
    d.mkdir(parents=True)

    npz_path = d / f"{sid}_profiles.npz"
    np.savez_compressed(
        npz_path,
        v=profiles["v"].astype(np.float32),
        peak=profiles["peak"].astype(np.uint16),
        width=profiles["width"].astype(np.float32),
        stage_y_mm=profiles["stage_y_mm"].astype(np.float64),
        t_s=profiles["t_s"].astype(np.float64),
    )
    full = dict(meta)
    full.update({
        "schema_version": SCHEMA_VERSION,
        "n_frames": int(N), "n_cols": int(W),
        "valid_pct": round(float(100 * np.isfinite(profiles["v"]).mean()), 2),
        "files": {npz_path.name: sha256_file(npz_path)},
        "software": {"git_commit": git_commit(), "python": platform.python_version(),
                     "numpy": np.__version__},
    })
    json_path = d / f"{sid}.json"
    json_path.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    if readonly:                                     # 원본 보호: 읽기 전용
        for p in (npz_path, json_path):
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return d


def load_scan_bundle(raw_root, scan_id, verify=True):
    """메타데이터와 프로파일을 읽는다. verify=True 면 파일 지문을 다시 계산해 비교"""
    d = Path(raw_root) / scan_id
    meta = json.loads((d / f"{scan_id}.json").read_text(encoding="utf-8"))
    npz_path = d / f"{scan_id}_profiles.npz"
    if verify:
        expect = meta["files"][npz_path.name]
        if sha256_file(npz_path) != expect:
            raise IOError(f"{npz_path.name} 지문 불일치 — 파일이 바뀌었거나 손상됨")
    with np.load(npz_path) as z:
        profiles = {k: z[k] for k in z.files}
    return meta, profiles


def append_experiment(csv_path, meta):
    """experiments.csv 에 한 줄 추가. 같은 scan_id 가 이미 있으면 거부"""
    csv_path = Path(csv_path)
    exists = csv_path.exists()
    if exists:
        with open(csv_path, newline="", encoding="utf-8") as f:
            if any(r["scan_id"] == meta["scan_id"] for r in csv.DictReader(f)):
                raise ValueError(f"{meta['scan_id']} 는 이미 experiments.csv 에 있음")
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow({k: meta.get(k, "") for k in CSV_COLUMNS})


# ---------------------------------------------------------------------------
# 실행 예: 합성 데이터로 저장 → 불러오기 → 검증
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile
    import pandas as pd

    root = Path(tempfile.mkdtemp())
    raw = root / "data" / "raw"
    gcode = root / "data" / "gcode" / "step_pyramid_v2.gcode"
    gcode.parent.mkdir(parents=True)
    gcode.write_text("G21\nG90\nM82\nG1 X10 Y0 E1.0 F1200\n", encoding="utf-8")

    rng = np.random.default_rng(0)
    N, W = 250, 1440                                   # 5 mm 스캔 (0.02 mm 간격)
    v = (540 + rng.normal(0, 0.07, (N, W))).astype(np.float32)
    v[:, :30] = np.nan                                 # 레이저가 안 보인 열
    profiles = {
        "v": v,
        "peak": rng.integers(150, 200, (N, W)),
        "width": np.full((N, W), 4.5),
        "stage_y_mm": np.arange(N) * 0.02,
        "t_s": np.arange(N) * 0.01,
    }
    meta = {
        "scan_id": "S03_r02", "specimen_id": "S03", "repeat": 2,
        "datetime": "2026-12-03T14:20:00+09:00", "operator": "student_A",
        "gcode_file": gcode.name, "gcode_sha256": sha256_file(gcode),
        "calibration_id": "CAL-2026-11-30-A", "acq_id": "ACQ-2026-12-10-A", "room_temp_C": 22.4, "bed_temp_C": 23.0,
        "exposure_us": 800, "gain_db": 0, "laser_power_pct": 60,
        "roi_rows": [250, 834], "frame_avg_n": 1,
        "scan_pitch_mm": 0.02, "scan_speed_mm_s": 2.0, "notes": "matte spray 없음",
    }

    d = save_scan_bundle(raw, meta, profiles)
    for p in sorted(d.iterdir()):
        print(f"저장: {p.name:<22} {p.stat().st_size / 1e6:6.2f} MB")
    meta2, prof2 = load_scan_bundle(raw, "S03_r02")
    print("불러오기 OK:", prof2["v"].shape, "유효 %:", meta2["valid_pct"],
          "G코드 지문 앞 12자리:", meta2["gcode_sha256"][:12])
    print("NaN 보존:", bool(np.isnan(prof2["v"][:, :30]).all()))

    append_experiment(root / "data" / "experiments.csv",
                      {**meta2})
    print(pd.read_csv(root / "data" / "experiments.csv")[
        ["scan_id", "calibration_id", "acq_id", "n_frames", "valid_pct"]])

    # 실수 사례 1: 같은 scan_id 로 다시 저장
    try:
        save_scan_bundle(raw, meta, profiles)
    except FileExistsError as e:
        print("거부됨:", type(e).__name__)
    # 실수 사례 2: 잘못된 이름·캘리브레이션 ID
    bad = {**meta, "scan_id": "S3-run2", "calibration_id": "cal_1130"}
    print("검증 오류:", validate_meta(bad))
    # 실수 사례 3: 저장 후 npz 가 바뀜 → 지문 불일치
    npz = d / "S03_r02_profiles.npz"
    os.chmod(npz, stat.S_IRUSR | stat.S_IWUSR)
    with open(npz, "ab") as f:
        f.write(b"\x00")
    try:
        load_scan_bundle(raw, "S03_r02")
    except IOError as e:
        print("거부됨:", e)
```

### 6.2 실행 예시와 기대 출력

```bash
python storage.py
```

```text
저장: S03_r02.json             0.00 MB
저장: S03_r02_profiles.npz     1.09 MB
불러오기 OK: (250, 1440) 유효 %: 97.92 G코드 지문 앞 12자리: e22539cab74d
NaN 보존: True
   scan_id    calibration_id            acq_id  n_frames  valid_pct
0  S03_r02  CAL-2026-11-30-A  ACQ-2026-12-10-A       250      97.92
거부됨: FileExistsError
검증 오류: ['scan_id 형식 오류: S3-run2 (예: S03_r02)', 'scan_id 와 specimen_id/repeat 불일치', 'calibration_id 형식 오류: cal_1130']
거부됨: S03_r02_profiles.npz 지문 불일치 — 파일이 바뀌었거나 손상됨
```

**결과 읽는 법**
- 250 프레임 합성 데이터의 `.npz` 가 약 1.1 MB 입니다 (합성 v 가 무작위 값이라 압축이 잘 안 된 경우). 실제 2501 프레임이면 압축 전 약 36 MB 입니다.
- 불러온 뒤 NaN 위치가 그대로 보존됩니다 (검출 실패 = NaN 원칙, E2·H1).
- 같은 `scan_id` 재저장은 `FileExistsError` 로, 형식이 틀린 ID 는 검증 오류 목록으로, 저장 후 바뀐 파일은 지문 불일치로 **모두 거부**됩니다.

생성되는 메타데이터 json 의 모양 (BLUEPRINT 예시에 `acq_id`, `roi_rows`, `frame_avg_n`, `schema_version`, `n_frames`, `n_cols`, `valid_pct`, `files`, `software` 가 추가됨):

```json
{
  "scan_id": "S03_r02",
  "specimen_id": "S03",
  "repeat": 2,
  "datetime": "2026-12-03T14:20:00+09:00",
  "operator": "student_A",
  "gcode_file": "step_pyramid_v2.gcode",
  "gcode_sha256": "e22539cab74d…(64자리)",
  "calibration_id": "CAL-2026-11-30-A",
  "acq_id": "ACQ-2026-12-10-A",
  "room_temp_C": 22.4,
  "bed_temp_C": 23.0,
  "exposure_us": 800,
  "gain_db": 0,
  "laser_power_pct": 60,
  "roi_rows": [250, 834],
  "frame_avg_n": 1,
  "scan_pitch_mm": 0.02,
  "scan_speed_mm_s": 2.0,
  "notes": "matte spray 없음",
  "schema_version": 1,
  "n_frames": 250,
  "n_cols": 1440,
  "valid_pct": 97.92,
  "files": {"S03_r02_profiles.npz": "…(64자리)"},
  "software": {"git_commit": "…", "python": "3.x.x", "numpy": "2.x.x"}
}
```

### 6.3 원본 프레임 무손실 저장 (`frames/`)

```python
"""원본 프레임을 무손실 PNG 로 저장 (개발 초기 전체 / 안정화 후 샘플만)"""
import tempfile
from pathlib import Path
import cv2
import numpy as np


def save_frames(frame_dir, frames, keep="all", every=250):
    """
    frames : 이미지 반복자 (uint8 또는 uint16, Mono12 는 uint16 으로 받음)
    keep   : "all" = 전부, "sample" = every 장마다 1장 + 첫·마지막 장
    파일명 : 000000.png (프레임 번호 6자리) — 정렬 순서 = 촬영 순서
    """
    frame_dir = Path(frame_dir)
    frame_dir.mkdir(parents=True, exist_ok=False)          # 이미 있으면 오류 (덮어쓰기 금지)
    frames = list(frames)
    n = len(frames)
    idx = range(n) if keep == "all" else sorted({0, n - 1, *range(0, n, every)})
    for i in idx:
        ok = cv2.imwrite(str(frame_dir / f"{i:06d}.png"), frames[i])   # PNG = 무손실
        if not ok:
            raise IOError(f"저장 실패: {i}")
    return list(idx)


d = Path(tempfile.mkdtemp()) / "S03_r02" / "frames"
rng = np.random.default_rng(0)
frames = [rng.integers(0, 4096, (584, 1440), dtype=np.uint16) for _ in range(1001)]  # 12-bit
kept = save_frames(d, frames, keep="sample", every=250)
print("저장한 프레임 번호:", kept)
back = cv2.imread(str(d / "000250.png"), cv2.IMREAD_UNCHANGED)       # 원래 비트 그대로 읽기
print("무손실 확인:", back.dtype, bool(np.array_equal(back, frames[250])))
size_mb = sum(p.stat().st_size for p in d.iterdir()) / 1e6
print(f"샘플 {len(kept)}장 용량: {size_mb:.1f} MB")
```

```text
저장한 프레임 번호: [0, 250, 500, 750, 1000]
무손실 확인: uint16 True
샘플 5장 용량: 7.5 MB
```

합성 프레임은 무작위 잡음이라 압축이 거의 안 되어 장당 1.5 MB 입니다. 실제 레이저 이미지는 대부분 어두워서 PNG 압축이 훨씬 잘 됩니다 — 5절 5단계에서 실측 용량을 기록합니다. `cv2.imread` 에 `cv2.IMREAD_UNCHANGED` 를 빼면 8-bit 로 바뀌어 정보가 사라지므로 주의합니다.

### 6.4 단위 테스트 (`tests/test_storage.py`)

```python
"""tests/test_storage.py — F3 단위 테스트 (pytest 의 tmp_path = 테스트용 임시 폴더)"""
import numpy as np
import pytest
from storage import (save_scan_bundle, load_scan_bundle, append_experiment,
                     validate_scan_id, validate_meta, sha256_file)


def make_case(tmp_path):
    g = tmp_path / "a.gcode"
    g.write_text("G1 X1 E1\n")
    meta = {
        "scan_id": "S01_r01", "specimen_id": "S01", "repeat": 1,
        "datetime": "2026-12-01T10:00:00+09:00", "operator": "A",
        "gcode_file": g.name, "gcode_sha256": sha256_file(g),
        "calibration_id": "CAL-2026-11-30-A", "acq_id": "ACQ-2026-12-10-A", "room_temp_C": 22.0, "bed_temp_C": 22.5,
        "exposure_us": 800, "gain_db": 0, "laser_power_pct": 60,
        "roi_rows": [250, 834], "frame_avg_n": 1,
        "scan_pitch_mm": 0.02, "scan_speed_mm_s": 2.0, "notes": "",
    }
    v = np.random.default_rng(0).normal(500, 1, (10, 20)).astype(np.float32)
    v[0, 0] = np.nan
    prof = {"v": v, "peak": np.full((10, 20), 180), "width": np.full((10, 20), 4.0),
            "stage_y_mm": np.arange(10) * 0.02, "t_s": np.arange(10) * 0.01}
    return meta, prof


@pytest.mark.parametrize("sid,ok", [("S03_r02", True), ("S03_r02_L015", True),
                                    ("S3_r2", False), ("S03-r02", False), ("s03_r02", False)])
def test_scan_id(sid, ok):
    assert validate_scan_id(sid) is ok


def test_roundtrip(tmp_path):
    meta, prof = make_case(tmp_path)
    save_scan_bundle(tmp_path / "raw", meta, prof)
    m2, p2 = load_scan_bundle(tmp_path / "raw", "S01_r01")
    np.testing.assert_array_equal(p2["v"], prof["v"])      # NaN 위치까지 동일
    assert m2["calibration_id"] == "CAL-2026-11-30-A"
    assert m2["n_frames"] == 10


def test_no_overwrite(tmp_path):
    meta, prof = make_case(tmp_path)
    save_scan_bundle(tmp_path / "raw", meta, prof)
    with pytest.raises(FileExistsError):
        save_scan_bundle(tmp_path / "raw", meta, prof)


def test_missing_meta(tmp_path):
    meta, _ = make_case(tmp_path)
    del meta["calibration_id"]
    assert "필수 항목 없음: calibration_id" in validate_meta(meta)


def test_csv_duplicate(tmp_path):
    meta, _ = make_case(tmp_path)
    append_experiment(tmp_path / "e.csv", meta)
    with pytest.raises(ValueError):
        append_experiment(tmp_path / "e.csv", meta)
```

```bash
python -m pytest -q test_storage.py
```

```text
.........                                                                [100%]
9 passed in 0.12s
```

### 6.5 총괄표 활용 예 (pandas)

```python
import pandas as pd
import tempfile, pathlib

# 실제로는 df = pd.read_csv("data/experiments.csv")
p = pathlib.Path(tempfile.mkdtemp()) / "experiments.csv"
p.write_text(
    "scan_id,specimen_id,repeat,calibration_id,acq_id,valid_pct,notes\n"
    "S03_r01,S03,1,CAL-2026-11-30-A,ACQ-2026-12-10-A,97.5,\n"
    "S03_r02,S03,2,CAL-2026-11-30-A,ACQ-2026-12-10-A,97.9,\n"
    "S04_r01,S04,1,CAL-2026-12-14-B,ACQ-2026-12-10-A,95.1,\n"
    "S04_r02,S04,2,CAL-2026-12-14-B,ACQ-2026-12-10-A,61.0,무효: 레이저 가림\n",
    encoding="utf-8")
df = pd.read_csv(p)
valid = df[~df["notes"].fillna("").str.startswith("무효")]          # 무효 스캔 제외
print(valid.groupby("calibration_id")["scan_id"].count())            # 캘리브레이션별 스캔 수
print("유효율 90 % 미만:", df.loc[df["valid_pct"] < 90, "scan_id"].tolist())
```

```text
calibration_id
CAL-2026-11-30-A    2
CAL-2026-12-14-B    1
Name: scan_id, dtype: int64
유효율 90 % 미만: ['S04_r02']
```

## 7. 검증 방법과 완료 기준

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 왕복 무결성 | 저장 → 불러오기 (6.4 `test_roundtrip`) | 모든 배열 비트 단위 동일 (NaN 위치 포함) |
| 2 | 덮어쓰기 방지 | 같은 ID 재저장 | 100 % 거부 |
| 3 | 메타데이터 검증 | 필수 항목 누락·형식 오류 사례 5개 이상 | 모두 오류 메시지로 검출 |
| 4 | 손상 검출 | 저장 후 1바이트 변경 | 지문 불일치로 거부 |
| 5 | 이미지 무손실 | 16-bit PNG 저장·읽기 | `np.array_equal` = True |
| 6 | 실제 스캔 적용 | `S00_r01`~`r03` 저장·불러오기·그림 | 3개 모두 성공, `experiments.csv` 3줄 |
| 7 | 추적 가능성 | 임의 스캔 1개를 골라 G코드 파일·캘리브레이션 파일·획득 프로파일을 찾아감 | 5분 안에 3개 모두 찾고 G코드 지문 일치 |
| 8 | 백업 | 외장 HDD 사본에서 `load_scan_bundle(verify=True)` | 전체 통과, 백업 기록 1줄 |
| 9 | 테스트 | `pytest tests/test_storage.py` | 9개 통과 |

**완료 판정**: 1~9 모두 합격하면 완료입니다. 이후 D5(M2) 검증 측정부터 모든 스캔이 이 경로로 저장되어야 합니다.

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| 파일 이름에 조건을 다 넣음 (`S03_노출800_1203_최종2.npz`) | 이름이 제각각, 자동 처리 불가 | 이름은 ID 만, 조건은 json |
| 원본을 직접 고침 (이상치 삭제 후 같은 이름 저장) | 원래 데이터 복구 불가, 재현 불가 | `data/raw` 읽기 전용, 처리 결과는 `data/processed` |
| 캘리브레이션 ID 를 안 적음 | 재교정 전후 데이터가 섞여 해석 불가 | `calibration_id` 필수 + 형식 검사 |
| G코드 파일을 같은 이름으로 다시 저장 | 기준 모델이 바뀌었는데 모름 | `gcode_sha256` 저장, 분석 시 지문 재확인 |
| JPEG 로 이미지 저장 | 손실 압축의 블록 무늬로 밝기 분포가 바뀌어 중심 위치가 달라짐 (크기는 압축률에 따라 다름) | PNG(무손실) 또는 TIFF |
| `cv2.imread` 기본 옵션으로 16-bit 읽기 | 8-bit 로 잘려 정밀도 손실 | `cv2.IMREAD_UNCHANGED` |
| 검출 실패를 0 또는 −1 로 저장 | 높이맵에 가짜 구멍 | NaN 사용, float 자료형 |
| 엑셀로 CSV 를 열었다 저장 | 인코딩·날짜 형식이 바뀌어 한글 깨짐 | 엑셀은 보기만, 수정은 코드로 (또는 "다른 이름으로 저장") |
| 무효 스캔 파일을 지움 | 반복 번호가 비어 이유를 모름 | 지우지 말고 notes 에 "무효: 이유" |
| 백업을 "나중에" | 디스크 고장으로 실험 수주 손실 | 측정 당일 외장 HDD 복사 + 주 1회 외부 동기화 |

## 9. 위험 요소

| 위험 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 디스크 용량 부족 (원본 이미지 전체 저장 시 스캔당 수 GB) | 높음 | 중 | M4 이후 샘플 저장 전환, 측정 전 남은 용량 확인(스캔당 5 GB 여유) |
| 데이터 유실 (디스크 고장, 실수 삭제) | 낮음 | 높음 | 3-2-1 백업, 읽기 전용 권한, 백업 기록 |
| 스키마 변경으로 옛 파일을 못 읽음 | 중 | 중 | `schema_version`, 읽기 함수에서 버전별 처리, 변경 기록 |
| 메타데이터 수동 입력 오류 (온도·시편 ID) | 중 | 중 | 형식 검증, 촬영 전 검증, 장비값 자동 기록 |
| 개인 PC 에 흩어진 데이터 | 중 | 중 | 공용 `data/` 위치 한 곳만 사용, 경로를 설정 파일(J2)로 관리 |

## 10. 기록 양식

**실험 총괄표 (`data/experiments.csv`) — 헤더 (열 순서 고정)**

```csv
scan_id,specimen_id,repeat,datetime,operator,gcode_file,gcode_sha256,calibration_id,acq_id,room_temp_C,bed_temp_C,exposure_us,gain_db,laser_power_pct,frame_avg_n,scan_pitch_mm,scan_speed_mm_s,n_frames,valid_pct,notes
```

**백업 기록 (`data/backup_log.csv`)**

```csv
date,scope,source,destination,media,n_scans,total_GB,verify_ok,checked_by,note
2026-12-11,S00_r01~S00_r03,lab-pc:data/raw,외장HDD-1,HDD,3,,,,
```

**스캔 전 확인표 (촬영할 때마다)**

| 항목 | 확인 |
|---|---|
| scan_id 가 규칙에 맞고 중복이 아님 | ☐ |
| 시편 ID·반복 번호가 실험 계획(H8 무작위 순서)과 일치 | ☐ |
| calibration_id 가 현재 유효한 것 (D5 이력) | ☐ |
| acq_id 와 실제 카메라 설정 일치 (F2) | ☐ |
| G코드 파일이 `data/gcode` 에 있고 지문 계산됨 | ☐ |
| 실내·베드 온도 기록 (C6) | ☐ |
| 디스크 남은 용량 ≥ 5 GB | ☐ |

## 11. 참고 자료

- NumPy 공식 문서: `numpy.savez_compressed`, `numpy.load` (NPZ 형식)
- Python 표준 라이브러리 문서: `json`, `hashlib`, `csv`, `pathlib`, `datetime.fromisoformat`
- ISO 8601 — 날짜·시각 표기 표준
- FIPS 180-4 (Secure Hash Standard) — SHA-256 정의
- FAIR 데이터 원칙 (Findable, Accessible, Interoperable, Reusable; Wilkinson 외, Scientific Data, 2016) — 연구 데이터 관리의 일반 원칙
- 3-2-1 백업 원칙 (일반 데이터 관리 지침)
- pandas 공식 문서: "10 minutes to pandas", `read_csv`
- 상위 문서 [BLUEPRINT.md](../../BLUEPRINT.md) F3 절, J1(폴더 구조), J2(재현성), D5(캘리브레이션 ID)
