"""설정 읽기 (세부청사진 T6 SV10, J2).

`config/*.yaml`을 최상위 키로 합친다. 같은 최상위 키가 두 파일에 있으면 오류.
T6가 소유한 절 (run · grid · paths · validate)만 여기서 검사한다. judge · gcode 절은 그 패키지가 검사한다
(병렬 작업 중 서로 import하지 않으려고). 검증기 CLI는 `load_owned()`로 default.yaml만 읽어 같은 검사를 한다.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

# T6 소유 절의 키와 자료형
SCHEMA = {
    "run": {"random_seed": int, "spec_version": str},
    "grid": {"res_mm": float, "frame": str},
    "paths": {"data_raw": str, "data_processed": str, "results": str},
    # enable_rules: 상태 '비활성' 규칙 켜기 (v1.0에서 0개). disable_rules: 기본 켬 규칙 끄기 (D-21 채택 X4 · X7만 허용)
    "validate": {"enable_rules": list, "disable_rules": list},
}
DEFAULT_YAML = CONFIG_DIR / "default.yaml"


class ConfigError(ValueError):
    pass


def _check_owned(cfg: dict, sources: dict[str, str]) -> None:
    for sec, keys in SCHEMA.items():
        if sec not in cfg:
            raise ConfigError(f"절 '{sec}'이 없음")
        val = cfg[sec]
        if not isinstance(val, dict):
            raise ConfigError(f"절 '{sec}'은 사전이어야 함 ({sources.get(sec)})")
        unknown = sorted(set(val) - set(keys))
        if unknown:
            raise ConfigError(f"절 '{sec}'에 모르는 키 {unknown} ({sources.get(sec)})")
        missing = sorted(set(keys) - set(val))
        if missing:
            raise ConfigError(f"절 '{sec}'에 키가 빠짐 {missing} ({sources.get(sec)})")
        for k, typ in keys.items():
            v = val[k]
            ok = isinstance(v, typ) and not isinstance(v, bool)
            if typ is float:
                ok = isinstance(v, (int, float)) and not isinstance(v, bool)
            if not ok:
                raise ConfigError(f"{sec}.{k} 자료형이 {typ.__name__}가 아님: {v!r}")
    if cfg["grid"]["res_mm"] <= 0:
        raise ConfigError("grid.res_mm > 0 이어야 함")
    if cfg["run"]["random_seed"] < 0:
        raise ConfigError("run.random_seed ≥ 0 이어야 함")
    for k in ("enable_rules", "disable_rules"):
        if not all(isinstance(x, str) for x in cfg["validate"][k]):
            raise ConfigError(f"validate.{k}는 규칙 ID 글자 목록이어야 함")


def load_owned(path: str | Path = DEFAULT_YAML) -> dict:
    """T6 소유 `config/default.yaml` 하나만 읽어 T6 절 (run · grid · paths · validate)을 검사한다 (팀장검증 5차 S-4).

    다른 담당의 yaml은 읽지 않는다 (그 파일이 바뀌어도 검증기 CLI가 멈추지 않게). 그 대신 T6 절은 `load_config()`와
    같은 검사를 받는다: 모르는 키 (오타 `enable_rule` 등) · 빠진 키 · 목록 아님 → ConfigError.
    """
    p = Path(path)
    try:
        with open(p, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except OSError as e:
        raise ConfigError(f"설정 파일을 못 읽음: {p} ({e})") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"{p.name}: YAML 문법 오류 ({e})") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{p.name}: 최상위가 사전이 아님")
    _check_owned(data, {k: p.name for k in data})
    return data


def load_config(config_dir: str | Path = CONFIG_DIR) -> dict:
    """config/*.yaml을 합친 사전. 파일 이름 순으로 읽는다."""
    d = Path(config_dir)
    files = sorted(d.glob("*.yaml"))
    if not files:
        raise ConfigError(f"설정 파일 없음: {d}")
    cfg: dict = {}
    sources: dict[str, str] = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if data is None:
            continue
        if not isinstance(data, dict):
            raise ConfigError(f"{f.name}: 최상위가 사전이 아님")
        for k, v in data.items():
            if k in cfg:
                raise ConfigError(f"최상위 키 '{k}'가 {sources[k]}와 {f.name}에 둘 다 있음")
            cfg[k] = v
            sources[k] = f.name
    _check_owned(cfg, sources)
    return cfg
