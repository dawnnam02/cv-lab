"""환경 점검: Python 판과 requirements.txt의 라이브러리 판을 대조한다 (세부청사진 T6 SV3).

    python scripts/check_env.py [--requirements requirements.txt]

라이브러리 판이 하나라도 다르거나 없으면 종료 코드 1. Python은 pyproject의 requires-python (>=3.11)을 보고,
J1 권장 (3.11 · 3.12)과 다르면 알림만 남긴다 (설치는 하지 않음).
"""

from __future__ import annotations

import argparse
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
J1_RECOMMENDED = ("3.11", "3.12")


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-+]+)$", line)
        if not m:
            raise ValueError(f"== 고정이 아닌 줄: {line}")
        out.append((m.group(1), m.group(2)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Python·라이브러리 판 대조")
    ap.add_argument("--requirements", default=str(ROOT / "requirements.txt"))
    a = ap.parse_args(argv)
    py = sys.version.split()[0]
    major_minor = ".".join(py.split(".")[:2])
    ok = True
    if tuple(map(int, py.split(".")[:2])) < (3, 11):
        print(f"Python {py}: requires-python >=3.11 아님  [다름]")
        ok = False
    else:
        note = "" if major_minor in J1_RECOMMENDED else f" (J1 권장 {'·'.join(J1_RECOMMENDED)}과 다름, 기록만)"
        print(f"Python {py}: requires-python >=3.11  [같음]{note}")
    try:
        reqs = parse_requirements(Path(a.requirements))
    except (OSError, ValueError) as e:
        print(f"requirements 읽기 실패: {e}")
        return 1
    for name, want in reqs:
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            have = "없음"
        same = have == want
        ok &= same
        print(f"{name:<11} 요구 {want:<9} 설치 {have:<9} [{'같음' if same else '다름'}]")
    print("결과:", "통과" if ok else "불일치")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
