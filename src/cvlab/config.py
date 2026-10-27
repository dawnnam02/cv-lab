"""설정 읽기 (세부청사진 T6 SV10, J2).

`config/*.yaml`을 최상위 키로 합친다. 같은 최상위 키가 두 파일에 있으면 오류.
T6가 소유한 절 (run · grid · paths · validate)만 여기서 검사한다. judge · gcode 절은 그 패키지가 검사한다
(병렬 작업 중 서로 import하지 않으려고).
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
    "validate": {"enable_rules": list},  # SV13: 기본 끔 규칙 (D-21 대기 X4 · X7) 켜기
}


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
    if not all(isinstance(x, str) for x in cfg["validate"]["enable_rules"]):
        raise ConfigError("validate.enable_rules는 규칙 ID 글자 목록이어야 함")


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
