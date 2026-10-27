# config/

| 파일 | 최상위 키 | 소유 | 검사하는 곳 |
|---|---|---|---|
| `default.yaml` | `run`, `grid`, `paths` | T6 | `cvlab.config.load_config()` |
| `judge.yaml` | `judge` | T15 | `cvlab.judge.params` |
| `gcode.yaml` | `gcode` | T4a | `cvlab.gcode.params` |
| `spec/fields_v1.0.csv` | - | T6 | 명세 필드표를 뽑은 표 (`scripts/extract_spec_schema.py`) |
| `spec/rules_v1.0.csv` | - | T6 | 검증 규칙표 |
| `spec/SOURCE.txt` | - | T6 | 뽑은 명세의 SHA-256과 뽑은 시각 |

- `load_config()`는 `config/*.yaml`을 최상위 키로 합칩니다. 같은 최상위 키가 두 파일에 있으면 오류입니다.
- 읽을 때는 `yaml.safe_load`만 씁니다.
- `spec/` 아래 파일은 손으로 고치지 않습니다. 명세가 바뀌면 `PYTHONPATH=src python scripts/extract_spec_schema.py`로 다시 뽑습니다.
