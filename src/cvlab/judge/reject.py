"""판정 거부 X1–X7 (T2 docs/측정-실패사례.md 5.2절, D-21). 규칙 문서: docs/판정-규칙.md §16

- 하나라도 걸리면 판정은 측정 불충분 (insufficient). 큰 U (불리 시나리오)로 덮어 판정하지 않는다.
- X6은 D-20 R2 (유효 칸 < 판정 영역의 90 %)와 같은 것이라 verdict.decide가 정하고, 여기서는 이름만 둔다.
- 메타데이터 입력은 얇게: {"scans": [스캔 행, ...], "refs": [기준 행, ...]}. 행은 명세 필드 이름을 키로 하는 dict.
  필드 이름은 META_FIELDS 하나에만 둔다. 파일을 열지 않으며 (메시 파일이 실제로 있는지는 T6 검증기 몫),
  값 형식 (정규식) 검사도 T6 몫이다.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

# 명세 필드 이름 (docs/하드웨어-데이터-명세.md). 코드에서는 이 키로만 꺼낸다.
META_FIELDS = {
    # 스캔 행 (판정에 넣은 층 스캔마다 1행, 줄 나눔 스캔이면 줄마다 1행)
    "scan_id": "meta.scan_id",
    "session_id": "meta.session_id",
    "scan_pass_idx": "meta.scan_pass_idx",  # 스캔 줄 번호 (J-4, 명세 v1.0). 없으면 줄 하나 (0)로 봄
    "timing": "meta.timing",  # layer · post. post (식힌 재측정)는 X5 · X7에서 뺌 (J-4). 없으면 layer
    "layer_idx": "meta.layer_idx",
    "layer_count": "meta.layer_count",
    "layer_macro_version": "meta.layer_macro_version",
    "layer_end_t_ns": "meta.layer_end_t_ns",
    "thermal_state": "meta.thermal_state",
    "bed_ref_id": "meta.bed_ref_id",
    "zero_ref_method": "meta.zero_ref_method",
    "mesh_enabled": "meta.mesh_enabled",
    "bed_mesh_file": "meta.bed_mesh_file",
    "calibration_id": "meta.calibration_id",
    # 기준 행 (reference). 세션은 기준 폴더 sessions/<session_id>/ 에서 읽어 X1 표의 이름 rep.session_id로 넣는다
    "ref_id": "ref.ref_id",
    "ref_kind": "ref.kind",
    "ref_calibration_id": "ref.calibration_id",
    "ref_t_start_ns": "ref.t_start_ns",
    "ref_scan_pass_idx": "ref.scan_pass_idx",  # bed_bare를 잰 줄 번호 (J-4). 없으면 0으로 봄
    "ref_session_id": "rep.session_id",
}

# 사유 코드 (T2 5.2절 표). 순서대로 결과에 적는다.
REJECT_CODES = {
    "X1": "베드 기준 스캔 없음 · 같은 세션 출력 전 bed_bare 아님",
    "X2": "0점을 프린터 Z만으로 이어 감 (z_only) 또는 값 없음",
    "X3": "베드 메시를 켰는데 메시 표 원본 없음",
    "X4": "층 스캔과 베드 기준 스캔의 교정 ID가 다름 (D-21)",
    "X5": "판정에 넣은 스캔의 열 상태가 없거나 in_process가 아님",
    "X6": "유효 칸 < 판정 영역의 90 % (D-20 R2와 같음)",
    "X7": "스캔한 층 수 < G코드 층 수 (D-18, D-21)",
}

ZERO_REF_OK = ("step_gauge", "bed_marker", "ref_tower")  # z_only · 빈 값 · 그 밖은 X2
META_KEYS = ("scans", "refs")

NOTE_REJECT = ("판정 거부: 대책이 빠진 측정은 큰 U로 덮어 판정하지 않고 측정 불충분으로 냅니다 "
               "(T2 5.2절, 참고로 불리 시나리오 U는 GUM 92.4 µm라 보류 띠가 T의 92 %). "
               "reference_verdict는 거부 조건을 보지 않고 넣은 U로 낸 참고 판정이며 판정이 아닙니다.")

F = META_FIELDS


def _empty(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _rows(meta: Mapping, key: str) -> list:
    rows = meta.get(key, [])
    if rows is None:
        rows = []
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Sequence):
        raise ValueError(f"meta[{key!r}]: 행 목록 (list of dict)이 아님")
    for r in rows:
        if not isinstance(r, Mapping):
            raise ValueError(f"meta[{key!r}]: dict가 아닌 행 {r!r}")
    return list(rows)


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _pass_idx(row: Mapping, key: str) -> Any:
    """줄 번호. 빈 값이면 0 (줄 하나, 명세 "줄이 하나면 0"). 0 이상 정수가 아니면 그 값을 그대로 돌려 X1로 거른다."""
    v = row.get(F[key])
    return 0 if _empty(v) else v


def _is_post(s: Mapping) -> bool:
    return s.get(F["timing"]) == "post"


def _label(s: Mapping) -> str:
    sid = s.get(F["scan_id"])
    return str(sid) if not _empty(sid) else f"층 {s.get(F['layer_idx'])}"


def check_meta(layer_states: Mapping[int, Any], meta: Mapping | None) -> tuple[dict, bool]:
    """X1–X5 · X7 검사. X6은 판정 칸 수로 verdict가 정한다.

    layer_states: 판정에 넣은 층 {layer_idx: LayerInput.thermal_state}.
    반환: ({코드: [이유 문장, ...]}, 메타를 검사했는지).
    meta가 None이면 LayerInput 열 상태 (X5)만 보고 나머지는 '검사 안 함'으로 둔다.
    """
    hits: dict[str, list[str]] = {}

    def hit(code: str, msg: str) -> None:
        hits.setdefault(code, []).append(msg)

    # X5 (입력 층): cooled는 verdict에서 오류 (M14). 그 밖에 in_process가 아니면 거부
    for k, st in sorted(layer_states.items()):
        if st != "in_process":
            hit("X5", f"층 {k}: LayerInput thermal_state = {st!r}")

    if meta is None:
        return hits, False
    if not isinstance(meta, Mapping):
        raise ValueError("meta: dict가 아님 ({'scans': [...], 'refs': [...]})")
    extra = set(meta) - set(META_KEYS)
    if extra:
        raise ValueError(f"meta: 모르는 키 {sorted(extra)} (받는 키 {META_KEYS})")
    scans = _rows(meta, "scans")
    refs = {r.get(F["ref_id"]): r for r in _rows(meta, "refs") if not _empty(r.get(F["ref_id"]))}

    # post (timing = post, 식힌 재측정)는 층 판정 대상이 아님: X5 · X7에서 빼고 X1–X4는 그대로 봄 (J-4)
    layer_scans = [s for s in scans if not _is_post(s)]

    by_layer: dict[int, list] = {}
    for s in layer_scans:
        li = s.get(F["layer_idx"])
        if isinstance(li, bool) or not isinstance(li, int):
            hit("X7", f"{_label(s)}: {F['layer_idx']} 없음 · 정수 아님 ({li!r})")
            continue
        by_layer.setdefault(li, []).append(s)

    # X5 (메타): 판정에 넣은 층마다 스캔 행이 있고 열 상태가 in_process
    for k in sorted(layer_states):
        if k not in by_layer:
            hit("X5", f"층 {k}: 스캔 메타 행 없음 (열 상태 모름)")
    for s in layer_scans:
        st = s.get(F["thermal_state"])
        if st != "in_process":
            hit("X5", f"{_label(s)}: {F['thermal_state']} = {st!r}")

    # X1 · X4: 베드 기준 스캔. 줄마다 bed_bare (명세 v1.0 meta.bed_ref_id, LM-T14-3):
    # 같은 scan_pass_idx끼리 같은 bed_ref_id, 가리킨 bed_bare의 ref.scan_pass_idx = 스캔 줄 번호
    first_end = [s.get(F["layer_end_t_ns"]) for s in layer_scans]
    first_end = min((t for t in first_end if _is_int(t)), default=None)
    ids_by_pass: dict[int, set] = {}
    for s in scans:
        p, bid = _pass_idx(s, "scan_pass_idx"), s.get(F["bed_ref_id"])
        if _is_int(p) and p >= 0 and not _empty(bid):
            ids_by_pass.setdefault(p, set()).add(bid)
    for p, ids in sorted(ids_by_pass.items()):
        if len(ids) > 1:
            hit("X1", f"줄 {p} ({F['scan_pass_idx']}) 안 {F['bed_ref_id']}가 여러 개 {sorted(map(str, ids))}")
    for s in scans:
        lab = _label(s)
        bid = s.get(F["bed_ref_id"])
        sp = _pass_idx(s, "scan_pass_idx")
        if not (_is_int(sp) and sp >= 0):
            hit("X1", f"{lab}: {F['scan_pass_idx']} = {sp!r} (0 이상 정수 아님, 줄마다 기준을 맞출 수 없음)")
        ref = None
        if _empty(bid):
            hit("X1", f"{lab}: {F['bed_ref_id']} 없음")
        elif bid not in refs:
            hit("X1", f"{lab}: {F['bed_ref_id']} {bid!r}에 해당하는 기준 행 없음")
        else:
            ref = refs[bid]
            if ref.get(F["ref_kind"]) != "bed_bare":
                hit("X1", f"{lab}: 기준 {bid} {F['ref_kind']} = {ref.get(F['ref_kind'])!r} (bed_bare 아님)")
            rp = _pass_idx(ref, "ref_scan_pass_idx")
            if _is_int(sp) and sp >= 0 and rp != sp:
                hit("X1", f"{lab}: 줄 {sp}인데 기준 {bid} {F['ref_scan_pass_idx']} = {rp!r} (같은 줄 bed_bare 아님)")
            rs, ss = ref.get(F["ref_session_id"]), s.get(F["session_id"])
            if _empty(rs) or _empty(ss) or rs != ss:
                hit("X1", f"{lab}: 기준 세션 {rs!r} ≠ 스캔 세션 {ss!r} (같은 세션이어야 함)")
            t0 = ref.get(F["ref_t_start_ns"])
            if _is_int(t0) and first_end is not None and t0 >= first_end:
                hit("X1", f"{lab}: 기준 {bid} {F['ref_t_start_ns']} {t0} ≥ 첫 층 끝 {first_end} (출력 전이 아님)")
        cal = s.get(F["calibration_id"])
        if _empty(cal):
            hit("X4", f"{lab}: {F['calibration_id']} 없음")
        elif ref is not None:
            rc = ref.get(F["ref_calibration_id"])
            if _empty(rc) or rc != cal:
                hit("X4", f"{lab}: 교정 ID {cal!r} ≠ 베드 기준 {bid} {F['ref_calibration_id']} {rc!r}")

        # X2: 0점 이어 가기
        z = s.get(F["zero_ref_method"])
        if z not in ZERO_REF_OK:
            hit("X2", f"{lab}: {F['zero_ref_method']} = {z!r}")
        # X3: 메시 (mesh_enabled가 False로 적힌 때만 메시 표 없이 통과)
        if s.get(F["mesh_enabled"]) is not False and _empty(s.get(F["bed_mesh_file"])):
            hit("X3", f"{lab}: {F['mesh_enabled']} = {s.get(F['mesh_enabled'])!r}인데 {F['bed_mesh_file']} 없음")

    # X7: 0부터 layer_count − 1까지 모든 층이 판정에 들어왔는지 (D-18). post 행은 층 수에 안 셈 (J-4)
    counts = {s.get(F["layer_count"]) for s in layer_scans}
    good = {c for c in counts if _is_int(c) and c >= 1}
    macro = sorted({str(s.get(F["layer_macro_version"])) for s in layer_scans})
    if not layer_scans:
        hit("X7", "스캔 메타 행 없음 (G코드 층 수 모름)")
    elif len(good) != 1 or len(counts) != 1:
        hit("X7", f"{F['layer_count']} 없음 · 여러 값 {sorted(map(str, counts))}")
    else:
        n = good.pop()
        judged = set(layer_states)
        scanned = judged & set(by_layer)
        missing = sorted(set(range(n)) - scanned)
        over = sorted(k for k in judged | set(by_layer) if k >= n)
        if missing:
            shown = missing if len(missing) <= 10 else missing[:10] + ["…"]
            hit("X7", f"스캔한 층 {len(set(range(n)) & scanned)} < G코드 층 {n}, 빠진 층 {shown} "
                      f"({F['layer_macro_version']} {macro})")
        if over:
            hit("X7", f"층 번호 {over} ≥ {F['layer_count']} {n}")
    return hits, True


MAX_REASONS = 10  # 코드마다 결과에 적는 이유 문장 수 (전체 건수는 n_reasons)


def _cap(msgs: list) -> list:
    msgs = list(msgs)
    return msgs if len(msgs) <= MAX_REASONS else msgs[:MAX_REASONS] + [f"… 외 {len(msgs) - MAX_REASONS}건"]


def reject_block(hits: Mapping[str, list], checked: bool, reference_verdict: str, U_mm: float,
                 U_source: str | None) -> dict:
    """결과 JSON의 reject 묶음."""
    codes = [c for c in REJECT_CODES if c in hits]
    return {
        "rejected": bool(codes),
        "codes": codes,
        "names": {c: REJECT_CODES[c] for c in codes},
        "reasons": {c: _cap(hits[c]) for c in codes},
        "n_reasons": {c: len(hits[c]) for c in codes},
        "meta_checked": checked,
        "not_checked": [] if checked else ["X1", "X2", "X3", "X4", "X7"],
        "reference_verdict": reference_verdict,
        "reference_U": {"U_um": U_mm * 1000.0, "U_source": U_source},
        "note": NOTE_REJECT if codes else None,
    }
