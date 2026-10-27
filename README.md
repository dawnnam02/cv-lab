# cv-lab

레이저 삼각측량 센서로 측정한 형상을 G코드(마스킹된 기준 형상)와 비교해 오차를 정량적으로 측정하는 연구 프로젝트.

- 과제 청사진: [docs/BLUEPRINT.md](docs/BLUEPRINT.md)

## 설치·실행

- Python 3.11 이상 (지금 쓰는 판 3.14.4). 라이브러리는 `requirements.txt`의 7개를 `==`로 고정합니다.
- 코드는 `src/cvlab/` (src 레이아웃)입니다. 설치하지 않고 `PYTHONPATH=src`로 읽습니다 (pytest는 `pyproject.toml`의 `pythonpath`가 대신함).

```bash
pip install -r requirements.txt                     # 새 PC에서만. 판 확인: python scripts/check_env.py
PYTHONPATH=src python scripts/extract_spec_schema.py # 명세 → config/spec/ 스키마·규칙표
PYTHONPATH=src python scripts/validate_dataset.py data/raw/<campaign_id> --report out.json   # 명세 검증
PYTHONPATH=src python scripts/validate_dataset.py --selftest                                # 검증기 자체 시험
python -m pytest tests/infra -q                      # 시험 (폴더 하나씩. 인자 없이 돌리면 V2 시험까지 4–5분)
```

- 명세 검증기 설명: [docs/명세-검증기.md](docs/명세-검증기.md). 설정 파일: [config/README.md](config/README.md)
- `data/raw/`·`data/_truth/`·`results/`는 Git에 올리지 않습니다 (`.gitignore`).
