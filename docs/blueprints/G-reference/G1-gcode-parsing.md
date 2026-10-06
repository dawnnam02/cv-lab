# G1. G코드 파싱

> 상위 문서: [전체 청사진](../../BLUEPRINT.md) · 영역: G. G코드 기준 모델 (마스킹)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-10-20 ~ 2026-11-02 (W3-4) |
| 우선순위 | 높음 |
| 트랙 | 소프트웨어 |
| 선행 요소 | [A3 가공 공정 확정](../A-goals/A3-process.md) · [J1 소프트웨어 구조](../J-software/J1-software-structure.md) · [J2 설정·재현성](../J-software/J2-config-reproducibility.md) · [K6 학습 로드맵](../K-management/K6-learning-roadmap.md) |
| 후행 요소 | [G2 비드 모델](G2-bead-model.md) · [G3 마스크·높이맵](G3-mask-heightmap.md) · [G4 평가 마스크](G4-evaluation-masks.md) · [E3 시편 설계](../E-specimen/E3-test-artifact.md) · [J3 합성 테스트](../J-software/J3-synthetic-tests.md) · [H7 치수 지표](../H-analysis/H7-dimensional-metrics.md) |
| 관련 마일스톤 | **M3** (합성 데이터에서 변형 복원 — 파서가 그 출발점). K1 W3–4 소프트웨어 목표: "슬라이서 미리보기와 일치, 압출량 ±1 %" |

---

## 1. 목적

G코드 파일(텍스트)을 읽어서 **"노즐이 어디서 어디로, 몇 번째 층에서, 어떤 종류의 경로로, 재료를 얼마나 내보내며 움직였는가"** 를 담은 **선분 표(segment table)** 로 바꿉니다.
이 표가 기준 모델(G2~G4)의 유일한 입력이므로, 여기서 생긴 실수(단위, 상대좌표, 원호 방향)는 이후 모든 오차 값에 그대로 섞여 들어갑니다. 측정 오차와 구분할 방법도 없습니다.

이 요소가 끝나면 다음을 할 수 있어야 합니다.
- 연구실에서 쓰는 슬라이서(Cura 또는 PrusaSlicer 계열)의 G코드를 **경고 없이** 읽는다.
- 층별·경로 종류별로 선분을 그려서 **슬라이서 미리보기와 같은 그림**을 얻는다.
- 전체 압출량 ΣΔE가 슬라이서 보고값과 **±1 % 이내**로 맞는다.

## 2. 배경 지식 (초보자용)

**G코드란?** 3D프린터·CNC가 실행하는 명령 목록입니다. 한 줄에 명령 하나가 있습니다.
```gcode
G1 X20.5 Y10 E0.3135 F1800   ; X=20.5, Y=10 으로 직선 이동하며 필라멘트 0.3135 mm를 밀어냄
```
- 첫 단어(`G1`)가 **명령**, 나머지(`X20.5` 등)가 **인자**입니다. `;` 뒤는 주석입니다.
- **모달(modal) 상태**: `G90`(절대좌표)이나 `M83`(E 상대)은 "이후 모든 줄"에 영향을 줍니다. 그래서 파서는 한 줄씩 읽으면서 **현재 상태(위치, 모드, 단위, 층, 경로 종류)를 기억하는 변수**를 계속 갱신해야 합니다. 이것이 파서의 핵심입니다.

**E축(압출축)**: 필라멘트를 몇 mm 밀었는지입니다. 이동하면서 E가 늘면 압출, 이동 없이 E가 줄면 리트랙션(필라멘트를 살짝 빼서 흘림 방지)입니다.

**원호 G2/G3**: G2는 시계방향, G3는 반시계방향 원호입니다(위에서 내려다볼 때). 중심을 주는 방법이 두 가지입니다.
- `I, J` : **시작점 기준** 중심까지의 오프셋 (G90 절대모드여도 I, J는 항상 상대값)
- `R` : 반지름. R > 0 이면 180° 이하의 짧은 원호, R < 0 이면 긴 원호

원호는 비교에 쓰기 위해 **짧은 직선(현)** 여러 개로 나눕니다. 길이 s인 현이 원호에서 벗어나는 최대 거리(현 처짐, sagitta)는 `s²/(8r)` 입니다. s = 0.1 mm, r = 2 mm이면 0.6 µm로, 측정 정밀도(A2: Z 5 µm, XY 0.02 mm)에 비해 무시할 수 있습니다.

**줄 번호와 체크섬**: 프린터와 PC가 직렬 통신할 때 `N12 G1 X5*87` 처럼 줄 번호(`N12`)와 체크섬(`*87`)을 붙입니다. 체크섬은 `*` 앞의 모든 글자 코드를 XOR한 값입니다. 파일로 저장된 G코드에는 보통 없지만, 출력 로그나 호스트 프로그램이 남긴 파일에는 있을 수 있습니다.

**슬라이서 주석**: 슬라이서는 기계가 무시하는 주석으로 정보를 남깁니다.

| 슬라이서 | 층 표시 | 경로 종류 표시 예 | 필라멘트 사용량 |
|---|---|---|---|
| Cura | `;LAYER:0` | `;TYPE:WALL-OUTER`, `;TYPE:FILL`, `;TYPE:SKIRT` | `;Filament used: 1.2345m` (파일 앞부분) |
| PrusaSlicer 계열 | `;LAYER_CHANGE` + `;Z:0.2` | `;TYPE:External perimeter`, `;TYPE:Solid infill` | `; filament used [mm] = 1234.5` (파일 끝부분) |

이 이름들을 **표준 이름**(WALL-OUTER, WALL-INNER, FILL, SKIN, SKIRT, BRIM, SUPPORT …)으로 통일해 두면 G4의 경로 종류 마스크(`M_type`)를 슬라이서와 상관없이 만들 수 있습니다.

## 3. 입력과 산출물

| 구분 | 이름 | 형식 | 설명 |
|---|---|---|---|
| 입력 | `data/gcode/<시편ID>_v<버전>.gcode` | 텍스트 | 슬라이서 출력 원본 (수정 금지) |
| 입력 | `data/gcode/<시편ID>_v<버전>.3mf` 또는 `.ini` | 슬라이서 프로파일 | 선폭·층높이·필라멘트 지름 확인용 (E3 관리 규칙) |
| 입력 | `config/default.yaml` → `gcode:` 절 | YAML | `arc_seg_mm`, 선폭, 층높이 (J2) |
| 산출물 | `src/cvlab/gcode_parser.py` | Python 모듈 | 이 문서 6절의 코드 |
| 산출물 | `data/processed/<시편ID>/segments.parquet` (또는 `.csv`) | 표 | 선분 표: `line_no, layer, type, kind, arc, x0, y0, z0, x1, y1, z1, de, length, f` |
| 산출물 | `data/processed/<시편ID>/parse_summary.json` | JSON | 층 수, 압출 길이, ΣΔE, 슬라이서 보고값과의 차이 %, 경고 목록, G코드 SHA-256 |
| 산출물 | `results/<시편ID>/g1_paths.png` | PNG 120 dpi 이상 | 층별 경로 그림 (슬라이서 미리보기와 비교) |
| 산출물 | `tests/test_gcode_parser.py` | pytest | 단위 테스트 8개 이상 |

> `.parquet` 저장에는 `pyarrow` 가 필요합니다. 설치가 어려우면 `.csv` 로 저장해도 됩니다(용량만 큼).

## 4. 결정 사항

| 결정 항목 | 선택지 | 권장 | 근거 |
|---|---|---|---|
| 기준 슬라이서 | Cura / PrusaSlicer / Orca 등 | **한 가지로 고정**, 버전까지 기록 | 주석 형식·경로 생성 규칙이 다름. 바꾸면 기준이 바뀜 |
| E 모드 | 절대(M82) / 상대(M83) | 파서는 둘 다 지원, 슬라이서는 **M83(상대) 권장** | 상대 E는 G92 리셋 실수가 적고 선분별 ΔE가 바로 보임 |
| 원호 출력 | 슬라이서 "Arc fitting" 켬 / 끔 | **끔** (직선만) | 원호를 끄면 파서 단순화. 단 파서는 원호도 처리 가능하게 유지 |
| 원호 분할 길이 `arc_seg_mm` | 0.05 / 0.1 / 0.2 mm | **0.1 mm** | 현 처짐 r = 1 mm에서도 1.25 µm < 측정 정밀도. 선분 수 과다 방지 |
| G90/G91이 E에도 적용? | 적용(Marlin) / 미적용 | **적용** (`g9x_sets_e=True`) 후 M82/M83이 덮어씀 | Marlin 펌웨어 동작. 다른 펌웨어면 문서 확인 후 변경 |
| 체크섬 틀린 줄 | 무시 / 경고 후 사용 | **무시 + 경고 기록** | 깨진 줄을 쓰면 위치가 어긋남. 개수가 0이 아니면 원인 조사 |
| 층 번호 기준 | 주석 / Z 값 | **주석 우선**, 없으면 압출 선분의 Z 값 | 주석이 가장 정확(Z hop 영향 없음) |
| 저장 형식 | CSV / parquet | parquet (없으면 CSV) | 수십만 줄이면 CSV는 느리고 큼 |

## 5. 수행 절차

1. **환경 준비 (W3 첫날, 1시간)**
   - [ ] `src/cvlab/gcode_parser.py`, `tests/test_gcode_parser.py` 빈 파일 생성 (J1 구조)
   - [ ] `pip install numpy pandas matplotlib pytest` 후 `python -c "import pandas"` 로 확인
2. **손으로 쓴 G코드로 시작 (W3, 1일)**
   - [ ] 6절의 `TEST_GCODE` (10 mm 정사각형 + 원호 2개 + 상대좌표 + inch + 체크섬)를 그대로 실행
   - [ ] 출력의 둘레 40.0000 mm, 원호 길이 15.708 mm(오차 < 0.001 mm), 원호 끝점 (35, 25) 확인
3. **단위 테스트 작성 (W3, 1일)**
   - [ ] 6.3절 pytest 8개 통과 (`pytest -q` → `8 passed`)
   - [ ] 새 기능(예: 다른 슬라이서 주석)을 넣을 때마다 테스트 1개 이상 추가
4. **실제 슬라이서 G코드 읽기 (W3–4, 2일)**
   - [ ] E3 후보 시편 중 단순한 것(20×20×2 mm 블록)을 연구실 슬라이서로 슬라이싱 → `data/gcode/` 저장
   - [ ] `summarize()` 결과의 `types` 목록에 모르는 이름이 있으면 `TYPE_ALIASES` 에 추가
   - [ ] `warnings` 가 0개가 될 때까지 원인 확인 (명령어 없는 줄, R 원호 오류 등)
5. **슬라이서 미리보기와 비교 (W4, 1일)**
   - [ ] 첫 층, 중간 층, 마지막 층 3장을 `g1_paths.png` 형식으로 그리고 슬라이서 화면 캡처와 나란히 비교
   - [ ] 비교 항목: 외곽 위치(눈금 1 mm 단위로 일치), 경로 종류 색, 채움 방향, 층 수
6. **압출량 검증 (W4, 반나절)**
   - [ ] `summarize()["filament_diff_pct"]` 의 절댓값 ≤ 1 % 확인
   - [ ] 슬라이서가 "필라멘트 무게(g)"만 보고하면: 길이 = 무게 / (밀도 × π(d_f/2)²). PLA 밀도 1.24 g/cm³
7. **결과 저장과 기록 (W4 마지막 날)**
   - [ ] `segments.parquet`, `parse_summary.json`(G코드 SHA-256 포함) 저장
   - [ ] 10절 기록 양식 작성, `config/default.yaml` 의 `gcode:` 절에 `arc_seg_mm: 0.1` 추가
8. **(CNC 공정일 때만)** 압출 대신 절삭 판정 추가
   - [ ] `kind` 판정을 "G1 이면서 Z < 소재 윗면" 으로 바꾸고, `T` 공구 번호와 `G41/G42/G40` 상태를 기억하는 변수 추가 (공구 형상은 G2에서 처리)

## 6. Python 구현

### 6.1 파서 모듈 — `src/cvlab/gcode_parser.py`

```python
"""
gcode_parser.py  —  G1. G코드 파싱 (FDM 기준)

G코드 텍스트를 읽어서 "선분(segment) 표"로 바꿉니다.
한 줄 = 노즐이 직선으로 움직인 한 구간.

처리하는 것
- G0/G1 직선, G2/G3 원호(I,J 중심 또는 R 반지름) → 짧은 직선으로 분할
- G90/G91 (XYZ 절대/상대), M82/M83 (E 절대/상대), G92 (위치 재설정)
- G20/G21 (inch/mm), G28 (원점 복귀), G10/G11 (펌웨어 리트랙션)
- 줄 번호 N…, 체크섬 *xx (검사 후 제거), 주석 ; … 와 ( … )
- 슬라이서 주석 ;LAYER:n / ;LAYER_CHANGE / ;TYPE:…  (Cura, PrusaSlicer 계열)
- 선분 종류 판정: extrude(압출) / travel(공이동) / retract / unretract
"""
import math
import re
from dataclasses import dataclass, field

import pandas as pd

# 슬라이서마다 다른 경로 종류 이름을 하나의 표준 이름으로 통일
TYPE_ALIASES = {
    # Cura
    "WALL-OUTER": "WALL-OUTER", "WALL-INNER": "WALL-INNER", "SKIN": "SKIN",
    "FILL": "FILL", "SKIRT": "SKIRT", "SUPPORT": "SUPPORT",
    "SUPPORT-INTERFACE": "SUPPORT", "PRIME-TOWER": "PRIME-TOWER",
    # PrusaSlicer / SuperSlicer / OrcaSlicer
    "EXTERNAL PERIMETER": "WALL-OUTER", "OUTER WALL": "WALL-OUTER",
    "PERIMETER": "WALL-INNER", "INNER WALL": "WALL-INNER",
    "OVERHANG PERIMETER": "WALL-OUTER",
    "SOLID INFILL": "SKIN", "TOP SOLID INFILL": "SKIN", "BOTTOM SURFACE": "SKIN",
    "TOP SURFACE": "SKIN", "INTERNAL SOLID INFILL": "SKIN",
    "INTERNAL INFILL": "FILL", "SPARSE INFILL": "FILL",
    "SKIRT/BRIM": "SKIRT", "BRIM": "BRIM",
    "SUPPORT MATERIAL": "SUPPORT", "SUPPORT MATERIAL INTERFACE": "SUPPORT",
    "WIPE TOWER": "PRIME-TOWER", "GAP FILL": "FILL", "BRIDGE INFILL": "SKIN",
}

WORD_RE = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def normalize_type(raw):
    key = raw.strip().upper()
    return TYPE_ALIASES.get(key, key)          # 모르는 이름은 대문자 그대로 둠


def checksum_ok(line):
    """'N12 G1 X1*85' 형식의 체크섬 검사. *가 없으면 None 반환."""
    if "*" not in line:
        return None
    body, _, cs = line.partition("*")
    try:
        expected = int(cs.strip())
    except ValueError:
        return False
    calc = 0
    for ch in body:                            # '*' 앞의 모든 글자를 XOR
        calc ^= ord(ch)
    return calc == expected


@dataclass
class ParseResult:
    segments: pd.DataFrame                     # 선분 표
    warnings: list = field(default_factory=list)
    slicer_filament_mm: float | None = None    # 슬라이서가 보고한 필라멘트 길이
    n_lines: int = 0
    n_checksum_bad: int = 0


def parse_gcode_text(text, arc_seg_mm=0.1, g9x_sets_e=True):
    """
    text       : G코드 전체 문자열
    arc_seg_mm : 원호를 나눌 최대 선분 길이 [mm] (0.1 mm 권장)
    g9x_sets_e : True면 Marlin처럼 G90/G91이 E 모드도 함께 바꿈 (그 뒤 M82/M83이 다시 덮어씀)
    """
    pos = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
    abs_xyz, abs_e = True, True
    unit = 1.0                                 # G21(mm)=1.0, G20(inch)=25.4
    feed = 0.0                                 # 마지막 F 값 [mm/min]
    layer, ftype = -1, None
    saw_layer_comment = False
    rows, warns = [], []
    slicer_fil = None
    n_bad = 0

    def add(kind, p0, p1, de, line_no, arc=False):
        length = math.hypot(p1["X"] - p0["X"], p1["Y"] - p0["Y"])
        rows.append(dict(
            line_no=line_no, layer=layer, type=ftype, kind=kind, arc=arc,
            x0=p0["X"], y0=p0["Y"], z0=p0["Z"], x1=p1["X"], y1=p1["Y"], z1=p1["Z"],
            de=de, length=length, f=feed))

    def classify(p0, p1, de):
        moved = math.hypot(p1["X"] - p0["X"], p1["Y"] - p0["Y"]) > 1e-9
        if moved and de > 1e-9:
            return "extrude"
        if moved:
            return "travel"                    # E 감소 + 이동(=wipe)도 여기서는 travel로 봄
        if de < -1e-9:
            return "retract"
        if de > 1e-9:
            return "unretract"
        return "travel"                        # Z만 움직임 등

    for line_no, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        # ---------- 1) 슬라이서 주석 읽기 ----------
        if s.startswith(";"):
            c = s[1:].strip()
            cu = c.upper()
            if cu.startswith("LAYER:") or cu.startswith("LAYER_CHANGE"):
                layer += 1
                saw_layer_comment = True
            elif cu.startswith("TYPE:"):
                ftype = normalize_type(c[5:])
            elif cu.startswith("FILAMENT USED:"):            # Cura: ";Filament used: 1.23456m"
                m = re.search(r"([\d.]+)\s*m", c[14:])
                if m:
                    slicer_fil = float(m.group(1)) * 1000.0
            elif cu.startswith("FILAMENT USED [MM]"):        # PrusaSlicer
                m = re.search(r"=\s*([\d.]+)", c)
                if m:
                    slicer_fil = float(m.group(1))
            continue
        # ---------- 2) 체크섬 검사 후 제거 ----------
        code = s.split(";")[0]
        ok = checksum_ok(code)
        if ok is False:
            n_bad += 1
            warns.append(f"line {line_no}: checksum mismatch -> 줄 무시")
            continue
        code = code.split("*")[0]
        code = re.sub(r"\(.*?\)", "", code).upper().strip()  # ( ) 주석 제거
        if not code:
            continue
        words = WORD_RE.findall(code)
        if not words:
            continue
        if words[0][0] == "N":                 # 줄 번호 제거
            words = words[1:]
        if not words:
            continue
        letter, num = words[0]
        if letter not in "GMT":
            # 명령 없이 좌표만 있는 줄(모달 G1)은 드물어서 경고만 남김
            warns.append(f"line {line_no}: 명령어 없음 '{code}' -> 무시")
            continue
        cmd = f"{letter}{int(float(num))}"
        args = {k: float(v) for k, v in words[1:]}

        if "F" in args:
            feed = args["F"] * unit

        # ---------- 3) 모드 명령 ----------
        if cmd == "G90":
            abs_xyz = True
            if g9x_sets_e:
                abs_e = True
        elif cmd == "G91":
            abs_xyz = False
            if g9x_sets_e:
                abs_e = False
        elif cmd == "M82":
            abs_e = True
        elif cmd == "M83":
            abs_e = False
        elif cmd == "G20":
            unit = 25.4
        elif cmd == "G21":
            unit = 1.0
        elif cmd == "G92":
            if not any(k in args for k in "XYZE"):       # 인자 없으면 전부 0 (RepRap wiki)
                for k in pos:
                    pos[k] = 0.0
            for k in "XYZE":
                if k in args:
                    pos[k] = args[k] * unit             # 이동 없이 '현재값'만 바꿈
        elif cmd == "G28":
            axes = [k for k in "XYZ" if k in args] or ["X", "Y", "Z"]
            for k in axes:
                pos[k] = 0.0                            # 원점=0 가정 (프린터마다 확인)
        elif cmd in ("G10", "G11"):
            # 펌웨어 리트랙션: E 좌표는 바뀌지 않음. 표시만 남김
            p = dict(pos)
            add("retract" if cmd == "G10" else "unretract", p, p, 0.0, line_no)
        # ---------- 4) 직선 이동 ----------
        elif cmd in ("G0", "G1"):
            new = dict(pos)
            for k in "XYZ":
                if k in args:
                    v = args[k] * unit
                    new[k] = v if abs_xyz else pos[k] + v
            if "E" in args:
                v = args["E"] * unit
                new["E"] = v if abs_e else pos["E"] + v
            de = new["E"] - pos["E"]
            add(classify(pos, new, de), pos, new, de, line_no)
            pos = new
        # ---------- 5) 원호 이동 ----------
        elif cmd in ("G2", "G3"):
            new = dict(pos)
            for k in "XYZ":
                if k in args:
                    v = args[k] * unit
                    new[k] = v if abs_xyz else pos[k] + v
            if "E" in args:
                v = args["E"] * unit
                new["E"] = v if abs_e else pos["E"] + v
            cw = cmd == "G2"
            x0, y0, x1, y1 = pos["X"], pos["Y"], new["X"], new["Y"]
            if "R" in args:                    # 반지름 방식 → 중심 계산
                r = args["R"] * unit
                dx, dy = x1 - x0, y1 - y0
                d = math.hypot(dx, dy)
                if d < 1e-12 or abs(r) < d / 2:
                    warns.append(f"line {line_no}: R 원호 계산 불가 -> 직선 처리")
                    de = new["E"] - pos["E"]
                    add(classify(pos, new, de), pos, new, de, line_no)
                    pos = new
                    continue
                hgt = math.sqrt(r * r - (d / 2) ** 2)
                # R>0 이면 짧은 원호, R<0 이면 긴 원호 (RepRap/Marlin 규칙)
                sgn = (-1 if cw else 1) * (1 if r > 0 else -1)
                cx = x0 + dx / 2 - sgn * hgt * dy / d
                cy = y0 + dy / 2 + sgn * hgt * dx / d
            else:                              # I, J = 시작점 기준 중심 오프셋 (항상 상대값)
                cx = x0 + args.get("I", 0.0) * unit
                cy = y0 + args.get("J", 0.0) * unit
            r = math.hypot(x0 - cx, y0 - cy)
            a0 = math.atan2(y0 - cy, x0 - cx)
            a1 = math.atan2(y1 - cy, x1 - cx)
            sweep = a1 - a0
            if cw and sweep >= -1e-12:
                sweep -= 2 * math.pi           # 시계방향은 음의 각도
            if (not cw) and sweep <= 1e-12:
                sweep += 2 * math.pi           # 반시계방향은 양의 각도
            arc_len = abs(sweep) * r
            n = max(1, math.ceil(arc_len / arc_seg_mm))
            total_de = new["E"] - pos["E"]
            prev = dict(pos)
            for i in range(1, n + 1):
                t = i / n
                a = a0 + sweep * t
                p = {"X": cx + r * math.cos(a), "Y": cy + r * math.sin(a),
                     "Z": pos["Z"] + (new["Z"] - pos["Z"]) * t,
                     "E": pos["E"] + total_de * t}
                if i == n:                     # 끝점은 G코드 값 그대로 (누적 오차 방지)
                    p["X"], p["Y"] = x1, y1
                de = p["E"] - prev["E"]
                add(classify(prev, p, de), prev, p, de, line_no, arc=True)
                prev = p
            pos = new
        # 그 외 명령 (M104 온도, M106 팬 등)은 형상과 무관 → 무시

    df = pd.DataFrame(rows, columns=[
        "line_no", "layer", "type", "kind", "arc", "x0", "y0", "z0",
        "x1", "y1", "z1", "de", "length", "f"])
    if not saw_layer_comment and len(df):
        # 층 주석이 없는 G코드: 압출 선분의 Z 값으로 층 번호를 매김
        zs = sorted(df.loc[df.kind == "extrude", "z1"].round(4).unique())
        zmap = {z: i for i, z in enumerate(zs)}
        df["layer"] = df["z1"].round(4).map(zmap).fillna(-1).astype(int)
        warns.append("층 주석 없음 -> Z 값으로 층 번호 생성")
    return ParseResult(df, warns, slicer_fil, line_no if text else 0, n_bad)


def parse_gcode(path, **kw):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return parse_gcode_text(f.read(), **kw)


def summarize(res):
    """층 수, 압출 길이, ΣΔE, 리트랙션 횟수 등 요약 딕셔너리"""
    df = res.segments
    ex = df[df.kind == "extrude"]
    out = {
        "n_segments": len(df),
        "n_extrude": len(ex),
        "n_layers": int(ex.layer.nunique()),
        "extrude_len_mm": round(float(ex.length.sum()), 4),
        "sum_de_mm": round(float(ex.de.sum()), 5),
        "n_retract": int((df.kind == "retract").sum()),
        "types": sorted(ex.type.dropna().unique().tolist()),
        "n_checksum_bad": res.n_checksum_bad,
    }
    if res.slicer_filament_mm:
        # 슬라이서 보고값은 리트랙션 후 재압출(unretract)까지 포함하는 경우가 많음 → 확인 필요
        net_e = float(df.de.sum())                    # 모든 선분의 ΔE 합 = 순 사용량
        out["slicer_filament_mm"] = round(res.slicer_filament_mm, 3)
        out["net_e_mm"] = round(net_e, 5)
        out["filament_diff_pct"] = round(100 * (net_e - res.slicer_filament_mm)
                                         / res.slicer_filament_mm, 3)
    return out
```

**읽는 요령 (초보자용)**
- `pos` 딕셔너리가 "지금 노즐 위치"입니다. 이동 명령을 만날 때마다 `new` 를 계산해서 선분을 저장하고 `pos = new` 로 갱신합니다.
- `abs_xyz`, `abs_e`, `unit`, `layer`, `ftype` 은 **모달 상태 변수**입니다. 줄을 읽을 때마다 바뀔 수 있습니다.
- 원호는 시작각 `a0` 에서 `sweep` 만큼 돌면서 `n` 조각으로 나눕니다. G2(시계)는 `sweep < 0`, G3(반시계)는 `sweep > 0` 이 되도록 2π를 더하거나 뺍니다. 시작점과 끝점이 같으면 한 바퀴(2π) 원으로 처리됩니다.

### 6.2 손으로 쓴 G코드 시험 + 경로 그림 — `notebooks/g1_example.py`

```python
"""
g1_example.py — 손으로 쓴 짧은 G코드로 파서를 검사하고, 층별 경로 그림을 저장
실행: python g1_example.py
"""
import math

import matplotlib
matplotlib.use("Agg")                     # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt

from gcode_parser import parse_gcode_text, summarize


def with_checksum(n, cmd):
    """'N{n} {cmd}*{체크섬}' 형식의 줄을 만듦 (프린터 직렬통신 형식)"""
    body = f"N{n} {cmd}"
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"{body}*{cs}"


TEST_GCODE = "\n".join([
    ";FLAVOR:Marlin",
    "G21 ; mm 단위",
    "G90",
    "M83 ; E 상대",
    "G28",
    ";LAYER:0",
    "G0 Z0.2 F600",
    ";TYPE:WALL-OUTER",
    "G0 X10 Y10",
    "G1 X20 Y10 E0.3135",                 # 10 mm 정사각형 4변 (각 E 0.3135)
    "G1 X20 Y20 E0.3135",
    "G1 X10 Y20 E0.3135",
    "G1 X10 Y10 E0.3135",
    "G1 E-0.8 F2100 ; 리트랙션",
    "G0 X25 Y15",
    "G1 E0.8 ; 재압출",
    ";TYPE:FILL",
    "G2 X30 Y20 I5 J0 E0.2463",          # 시계 원호 (I,J 방식): 중심(30,15), 반지름 5, 90°
    "G3 X35 Y25 R5 E0.2463",              # 반시계 원호 (R 방식): 중심(30,25), 90°
    ";LAYER:1",
    with_checksum(10, "G0 Z0.4"),
    with_checksum(11, "G91"),             # 상대 좌표 (Marlin: E도 상대)
    with_checksum(12, "G1 X-5 Y0 E0.1568"),
    "N13 G1 X-5 Y0 E0.1568*99",           # 일부러 틀린 체크섬 → 무시되어야 함
    with_checksum(14, "G90"),
    "M83",
    "G20 ; inch 단위로 전환",
    "G1 X1 Y1 E0.01",                     # 1 inch = 25.4 mm 지점으로 이동
    "G21",
    "G92 E0",
]) + "\n"

res = parse_gcode_text(TEST_GCODE, arc_seg_mm=0.1)
df = res.segments
print(summarize(res))
for w in res.warnings:
    print("WARN:", w)

ex = df[df.kind == "extrude"]
sq = ex[(ex.layer == 0) & (ex.type == "WALL-OUTER")]
arc = ex[(ex.layer == 0) & (ex.type == "FILL")]
print(f"정사각형 둘레 = {sq.length.sum():.4f} mm (정답 40)")
print(f"원호 길이 합  = {arc.length.sum():.4f} mm (정답 {math.pi * 5:.4f}), 분할 수 {len(arc)}")
print(f"원호 끝점     = ({arc.x1.iloc[-1]:.3f}, {arc.y1.iloc[-1]:.3f}) (정답 35, 25)")
l1 = ex[ex.layer == 1]
print("1층 선분:", l1[["x0", "y0", "x1", "y1", "z1"]].round(3).values.tolist())

# 층별 경로 그림: 압출=종류별 색, 공이동=회색 점선
# LineCollection = 선분 수천 개를 한 번에 그리는 빠른 방법
from matplotlib.collections import LineCollection

colors = {"WALL-OUTER": "tab:red", "WALL-INNER": "tab:orange",
          "FILL": "tab:blue", "SKIN": "tab:cyan", "SKIRT": "tab:gray"}
layers = sorted(ex.layer.unique())
fig, axes = plt.subplots(1, len(layers), figsize=(5 * len(layers), 5),
                         sharex=True, sharey=True, squeeze=False)
for ax, L in zip(axes[0], layers):
    d = df[df.layer == L]
    tr = d[d.kind == "travel"]
    ax.add_collection(LineCollection(tr[["x0", "y0", "x1", "y1"]].values.reshape(-1, 2, 2),
                                     colors="0.7", linewidths=0.8, linestyles="--"))
    e = d[d.kind == "extrude"]
    ax.add_collection(LineCollection(e[["x0", "y0", "x1", "y1"]].values.reshape(-1, 2, 2),
                                     colors=[colors.get(t, "k") for t in e.type], linewidths=2))
    ax.autoscale()
    ax.set_title(f"layer {L}")
    ax.set_aspect("equal")                 # X, Y 축척을 같게 (안 하면 원이 타원으로 보임)
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]")
fig.savefig("g1_paths.png", dpi=120, bbox_inches="tight")
print("saved g1_paths.png")
```

실행: `python g1_example.py` → 기대 출력 (같은 코드를 실제로 실행한 결과)
```text
{'n_segments': 170, 'n_extrude': 164, 'n_layers': 2, 'extrude_len_mm': 65.3251, 'sum_de_mm': 2.1574, 'n_retract': 1, 'types': ['FILL', 'WALL-OUTER'], 'n_checksum_bad': 1}
WARN: line 24: checksum mismatch -> 줄 무시
정사각형 둘레 = 40.0000 mm (정답 40)
원호 길이 합  = 15.7077 mm (정답 15.7080), 분할 수 158
원호 끝점     = (35.000, 25.000) (정답 35, 25)
1층 선분: [[35.0, 25.0, 30.0, 25.0, 0.4], [30.0, 25.0, 25.4, 25.4, 0.4]]
saved g1_paths.png
```
- 원호 길이 15.7077 mm는 정답 15.7080 mm보다 0.3 µm 짧습니다. 0.1 mm 현으로 나눈 결과이며 2절의 sagitta 계산과 맞습니다.
- `N13` 줄은 체크섬이 틀려서 무시되었습니다. 그래서 1층 선분은 2개입니다(첫 선분 35→30, 둘째는 inch 이동 30→25.4).
- 저장된 `g1_paths.png`: 0층은 빨간 정사각형 + 파란 S자 원호 + 회색 점선 공이동이 보여야 합니다.

### 6.3 단위 테스트 — `tests/test_gcode_parser.py`

```python
"""tests/test_gcode_parser.py — pytest 단위 테스트 (실행: pytest -q tests/test_gcode_parser.py)"""
import math

import pytest

from gcode_parser import parse_gcode_text, checksum_ok

SQUARE = """G21
G90
M82
G92 E0
;LAYER:0
;TYPE:WALL-OUTER
G0 X0 Y0 Z0.2
G1 X10 Y0 E1
G1 X10 Y10 E2
G1 X0 Y10 E3
G1 X0 Y0 E4
"""


def extr(text, **kw):
    df = parse_gcode_text(text, **kw).segments
    return df[df.kind == "extrude"]


def test_square_four_segments_40mm():
    ex = extr(SQUARE)
    assert len(ex) == 4
    assert ex.length.sum() == pytest.approx(40.0)
    assert ex.de.sum() == pytest.approx(4.0)


def test_relative_xyz_and_e():
    g = "G91\nM83\nG1 X5 E0.5\nG1 X5 E0.5\n"
    ex = extr(g)
    assert ex.x1.tolist() == [5.0, 10.0]
    assert ex.de.tolist() == [0.5, 0.5]


def test_g92_reset_does_not_create_extrusion():
    g = "M82\nG1 X1 E5\nG92 E0\nG1 X2 E0.1\n"
    ex = extr(g)
    assert ex.de.tolist() == pytest.approx([5.0, 0.1])


def test_inch_units():
    ex = extr("G20\nG1 X1 Y0 E0.01\n")
    assert ex.x1.iloc[0] == pytest.approx(25.4)


def test_arc_quarter_ij_and_r():
    g = "G0 X5 Y0\nG3 X0 Y5 I-5 J0 E1\n"          # 반시계 90°, r=5
    ex = extr(g, arc_seg_mm=0.05)
    assert ex.length.sum() == pytest.approx(math.pi * 5 / 2, rel=1e-4)
    assert ex.de.sum() == pytest.approx(1.0)
    g2 = "G0 X5 Y0\nG3 X0 Y5 R5 E1\n"
    ex2 = extr(g2, arc_seg_mm=0.05)
    assert ex2.length.sum() == pytest.approx(ex.length.sum())


def test_retraction_kinds():
    df = parse_gcode_text("M83\nG1 E-0.8\nG0 X5\nG1 E0.8\n").segments
    assert df.kind.tolist() == ["retract", "travel", "unretract"]


def test_checksum():
    assert checksum_ok("N1 G28*18") is True
    assert checksum_ok("N1 G28*19") is False
    assert checksum_ok("G28") is None


def test_layer_from_z_when_no_comment():
    g = "G1 Z0.2\nG1 X1 E1\nG1 Z0.4\nG1 X2 E2\n"
    ex = extr(g)
    assert ex.layer.tolist() == [0, 1]
```
실행: `pytest -q tests/test_gcode_parser.py` → `........                                                                 [100%]
8 passed in 0.31s`

### 6.4 합성 시편 G코드 생성기 — `tests/synthetic_gcode.py`

G2~G4와 J3에서 공통으로 쓰는 **정답을 아는 G코드**입니다. E 값을 G2의 비드 단면적 공식으로 만들기 때문에, 역산하면 선폭 0.42 mm가 나와야 합니다.

```python
"""
synthetic_gcode.py — 정답을 아는 합성 G코드 생성기 (G1~G4, J3 테스트용)

시편: 10 x 10 mm 블록 (X 10~20, Y 10~20), 층높이 0.2 mm, 6층
  - 0~3층: 전체 10x10  → 윗면 Z = 0.8 mm
  - 4~5층: 왼쪽 절반(X 10~15)만 → 윗면 Z = 1.2 mm (0.4 mm 단차)
  - 0층에만 스커트 (윤곽에서 3 mm 바깥)
  - 벽 2줄(외벽/내벽) + 100 % 직선 채움(층마다 X/Y 방향 교대, 벽과 25 % 겹침)
E 값은 G2의 비드 단면적 공식으로 계산하므로, 역산하면 선폭 0.42 mm가 나와야 함.
"""
import math

W, H, DF = 0.42, 0.2, 1.75          # 선폭, 층높이, 필라멘트 지름 [mm]
A_BEAD = (W - H) * H + math.pi * (H / 2) ** 2
A_FIL = math.pi * (DF / 2) ** 2


def rect_path(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def make_block_gcode(n_layers=6, step_from=4, flow=1.0, retract=0.8):
    out, net_e = [], 0.0
    pos = [0.0, 0.0]

    def travel(x, y):
        nonlocal net_e
        out.append(f"G1 E{-retract:.4f} F2100")          # 리트랙션
        out.append(f"G0 X{x:.3f} Y{y:.3f} F6000")
        out.append(f"G1 E{retract:.4f} F2100")           # 재압출
        pos[:] = [x, y]

    def extrude_path(pts):
        nonlocal net_e
        travel(*pts[0])
        for x, y in pts[1:]:
            L = math.hypot(x - pos[0], y - pos[1])
            e = flow * A_BEAD * L / A_FIL
            net_e += e
            out.append(f"G1 X{x:.3f} Y{y:.3f} E{e:.5f} F1800")
            pos[:] = [x, y]

    for k in range(n_layers):
        z = round(H * (k + 1), 3)
        xr = 15.0 if k >= step_from else 20.0           # 위층은 왼쪽 절반만
        out.append(f";LAYER:{k}")
        out.append(f"G0 Z{z:.3f} F600")
        if k == 0:
            out.append(";TYPE:SKIRT")
            extrude_path(rect_path(7.0, 7.0, 23.0, 23.0))
        out.append(";TYPE:WALL-OUTER")
        extrude_path(rect_path(10 + W / 2, 10 + W / 2, xr - W / 2, 20 - W / 2))
        out.append(";TYPE:WALL-INNER")
        extrude_path(rect_path(10 + 1.5 * W, 10 + 1.5 * W, xr - 1.5 * W, 20 - 1.5 * W))
        out.append(";TYPE:FILL")
        # 채움 선 중심 범위: 내벽 안쪽 경계(2W)에서 W/2 들어가되, 벽과 25 % 겹치게(-0.25W)
        lo_x, hi_x = 10 + 2.25 * W, xr - 2.25 * W
        lo_y, hi_y = 10 + 2.25 * W, 20 - 2.25 * W
        if k % 2 == 0:                                  # X 방향 선
            n = math.ceil((hi_y - lo_y) / W) + 1          # 간격 ≤ W (틈 방지)
            ys = [lo_y + i * (hi_y - lo_y) / (n - 1) for i in range(n)]
            pts = []
            for i, y in enumerate(ys):
                a, b = (lo_x, hi_x) if i % 2 == 0 else (hi_x, lo_x)
                pts += [(a, y), (b, y)]
        else:                                           # Y 방향 선
            n = math.ceil((hi_x - lo_x) / W) + 1
            xs = [lo_x + i * (hi_x - lo_x) / (n - 1) for i in range(n)]
            pts = []
            for i, x in enumerate(xs):
                a, b = (lo_y, hi_y) if i % 2 == 0 else (hi_y, lo_y)
                pts += [(x, a), (x, b)]
        extrude_path(pts)
    header = [";FLAVOR:Marlin", f";Filament used: {net_e / 1000:.5f}m",
              f";Layer height: {H}", "G21", "G90", "M83", "G28", "G92 E0"]
    return "\n".join(header + out + ["M107", "M84"]) + "\n"


if __name__ == "__main__":
    g = make_block_gcode()
    open("block_test.gcode", "w").write(g)
    print(len(g.splitlines()), "lines written to block_test.gcode")
```

파싱 확인:
```python
from gcode_parser import parse_gcode, summarize
res = parse_gcode("block_test.gcode")
print(summarize(res))
```
기대 출력 (`python synthetic_gcode.py` 로 파일을 만든 뒤):
```text
{'n_segments': 337, 'n_extrude': 274, 'n_layers': 6, 'extrude_len_mm': 1326.88, 'sum_de_mm': 41.60263, 'n_retract': 19, 'types': ['FILL', 'SKIRT', 'WALL-INNER', 'WALL-OUTER'], 'n_checksum_bad': 0, 'slicer_filament_mm': 41.6, 'net_e_mm': 41.60263, 'filament_diff_pct': 0.006}
```
`filament_diff_pct` 0.006 %는 헤더의 "Filament used" 값을 소수 5자리(m 단위)로 반올림했기 때문입니다. 합격 기준 1 %보다 훨씬 작습니다.

## 7. 검증 방법과 완료 기준

| 검증 항목 | 방법 | 합격 기준 |
|---|---|---|
| 단위 테스트 | `pytest -q tests/test_gcode_parser.py` | 8개 이상 전부 통과 |
| 정사각형 둘레 | 손 G코드 10 mm 정사각형 | 40.000 ± 0.001 mm |
| 원호 | I,J 방식과 R 방식 90° 원호 | 길이 오차 < 0.01 %, 끝점 오차 < 1 µm, 두 방식 결과 동일 |
| 압출량 | ΣΔE(순 사용량) vs 슬라이서 보고값 | **|차이| ≤ 1 %** (BLUEPRINT G1) |
| 경로 모양 | 첫·중간·마지막 층 그림 vs 슬라이서 미리보기 | 외곽 위치·층 수·경로 종류 색이 눈으로 구분 안 될 만큼 일치 |
| 층 수 | 압출 선분이 있는 층 수 vs 슬라이서 표시 층 수 | 정확히 일치 |
| 경고 | `res.warnings`, `n_checksum_bad` | 실제 시편 G코드에서 0개 (있으면 원인 기록) |
| 경로 종류 | `summarize()["types"]` | 모든 이름이 표준 이름(TYPE_ALIASES 값)으로 변환됨 |
| 속도 | 50만 줄 G코드 파싱 | 30 s 이내 (참고: 합성 8.5만 줄 ≈ 0.8 s 측정됨) |

## 8. 흔한 실수와 대응

| 실수 | 증상 | 대응 |
|---|---|---|
| G91(상대좌표)을 무시 | 형상이 한 점에 뭉치거나 대각선으로 길게 늘어남 | 모달 변수 `abs_xyz` 확인, 테스트 `test_relative_xyz_and_e` |
| M83인데 절대 E로 계산 | ΣΔE가 음수이거나 수백 배 | `abs_e` 처리 확인, 압출량 검증 |
| `G92 E0` 를 이동으로 처리 | 큰 음수 ΔE 선분(가짜 리트랙션) 생김 | G92는 위치값만 덮어쓰고 선분을 만들지 않음 |
| G20(inch) 무시 | 형상이 1/25.4 크기 | `unit` 변수, `test_inch_units` |
| 원호 방향 반대 | 90° 원호가 270°로 그려짐 | G2 = 시계(sweep < 0). 그림으로 확인, `test_arc_quarter_ij_and_r` |
| I, J를 절대좌표로 해석 | 원호 중심이 원점 근처로 튐 | I, J는 항상 시작점 기준 상대값 |
| `;LAYER` 주석만 믿고 Z hop 무시 | 층 Z가 0.4 mm 높게 기록 | 층 Z는 압출 선분 Z의 중앙값으로 계산(G2, G3 코드가 그렇게 함) |
| 주석 안의 "E" 를 인자로 읽음 | 엉뚱한 E 값 | `;` 와 `( )` 주석을 먼저 제거 |
| 리트랙션 재압출을 "압출"로 셈 | 짧은 0길이 압출 선분 생김 | 이동 없는 E 증가는 `unretract` 로 분리 |
| 프린터 원점 ≠ 0 가정 | G28 후 위치가 틀림 | G28 직후 G코드가 바로 절대좌표로 이동하면 영향 없음. 아니면 프린터 원점 좌표 확인 |
| 줄 끝 `\r` (Windows) | 마지막 인자 읽기 실패 | `strip()` 사용 |

## 9. 위험 요소

- **슬라이서 업데이트**: 같은 슬라이서라도 버전이 바뀌면 주석 이름이나 채움 경로가 바뀝니다. 슬라이서 버전을 메타데이터(F3)에 적고, 본 실험 기간에는 업데이트하지 않습니다.
- **펌웨어 의존 동작**: G90/G91이 E에 영향을 주는지, G28 원점 좌표, 펌웨어 리트랙션(G10/G11)의 길이는 펌웨어 설정에 따릅니다. 연구실 프린터의 펌웨어 종류와 설정을 한 번 확인해서 10절 양식에 남깁니다.
- **압출량 ±1 %를 못 맞추는 경우**: 슬라이서 보고값이 "순 사용량"인지 "리트랙션 포함 총 밀어낸 길이"인지 다를 수 있습니다. 원인 확인 전에는 G2의 압출량 기반 선폭(w_eff)을 쓰지 않습니다.
- **원호 피팅(Arc Welder 등 후처리)**: 후처리 프로그램이 G2/G3를 넣으면 경로가 미세하게 바뀝니다. 기준 G코드는 **프린터에 실제로 보낸 파일**이어야 합니다.
- **대용량**: 수백 MB G코드는 메모리 부족이 날 수 있습니다. 이때는 층 단위로 나눠 저장하거나, 비교에 필요한 층만 남깁니다.

## 10. 기록 양식

`data/processed/<시편ID>/parse_summary.json` 템플릿:
```json
{
  "specimen_id": "S03",
  "gcode_file": "data/gcode/S03_v2.gcode",
  "gcode_sha256": "",
  "slicer": "Cura 5.x.x",
  "slicer_profile": "data/gcode/S03_v2.3mf",
  "firmware": "Marlin 2.x, g9x_sets_e=true",
  "parser_git_commit": "",
  "arc_seg_mm": 0.1,
  "n_lines": 0,
  "n_segments": 0,
  "n_layers": 0,
  "extrude_len_mm": 0.0,
  "net_e_mm": 0.0,
  "slicer_filament_mm": 0.0,
  "filament_diff_pct": 0.0,
  "n_checksum_bad": 0,
  "warnings": [],
  "preview_match_checked_by": "",
  "date": "2026-11-02"
}
```

슬라이서 미리보기 비교 기록표:

| 날짜 | 시편ID | 층 | 외곽 위치 일치 | 종류 색 일치 | 층 수 일치 | 압출량 차이 % | 확인자 | 비고 |
|---|---|---|---|---|---|---|---|---|
| | | 0 | ☐ | ☐ | ☐ | | | |
| | | 중간 | ☐ | ☐ | ☐ | | | |
| | | 마지막 | ☐ | ☐ | ☐ | | | |

## 11. 참고 자료

- Marlin Firmware G-code documentation (G0-G1, G2-G3, G90, G91, G92, M82, M83, G10/G11 항목)
- RepRap Wiki, "G-code" 페이지 (명령 목록, 체크섬과 줄 번호 규칙)
- LinuxCNC G-code reference (G2/G3 원호의 I, J, R 해석, G41/G42 공구 반경 보정)
- Ultimaker Cura 및 PrusaSlicer 공식 문서 (G코드 주석 형식, 필라멘트 사용량 보고 방식)
- pandas 공식 문서 "10 minutes to pandas"
- matplotlib 공식 문서 `LineCollection` 예제
