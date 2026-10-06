"""simulate.py — 실험 3: 측정 시뮬레이션 (청사진 0_방법탐색 4.3절).

단위는 모두 µm (높이 포함). 부호: 오차 = 측정 − 설계, + = 재료 과다(A1).

합성 시편은 20 × 40 mm 전체를 2 µm 격자로 만들면 메모리가 너무 커서, 지표마다 필요한
작은 패치로 나눈다. 패치는 같은 시편의 일부이므로 '전체 위치 오차'(+200, −100) µm 가
모든 패치에 똑같이 들어가고, 샘플링 격자의 위상도 한 번의 측정(MC 1회) 안에서 공유한다.

  패치          정답(넣은 오차)                         지표 추출 (측정 데이터 + 설계값만 사용)
  단차 패치     윗면 400 → 아랫면 220 (설계 단차 200, −20) 경계 띠를 뺀 두 면 중앙값 차
  선 패치       단일 선 FWHM 400 → 440 (+40), 높이 200     행 평균 단면의 반높이 폭(FWHM)
  구멍 패치     판 두께 1000 위 Ø4000 → Ø3900 (−100)        경계점 Kåsa 원 맞춤
  핀 패치 ×9    Ø2000·높이 1000 핀 3×3 (간격 6 mm)          경계점 Kåsa 원 중심의 평균 이동

모델 가정 (보고서 '모델 가정 목록'과 같은 내용)
  A1. 가로 흐림: 광학 = 가우시안 σ = xy_blur/2.355 (xy_blur 를 PSF FWHM 으로 해석).
      접촉식 = 반경 r = xy_blur 구 프로브의 형태학적 '닫힘(closing)'.
      ※ 지시서는 '열림(opening)'이라 했지만, 위에서 내려오는 구가 기록하는 면은
        (f ⊕ b) ⊖ b = 닫힘이다(좁은 골·오목 모서리가 메워짐). 열림은 아래에서 올라오는
        구에 해당한다. CONTACT_MORPH 상수로 바꿀 수 있다.
  A2. 샘플링: 간격 xy_step, 위상 오프셋 U[0, step) 를 x·y 각각 MC 1회마다 새로 뽑는다.
      정답 격자(2 µm)보다 촘촘한 간격은 2 µm 로 처리한다(약간 보수적).
  A3. Z 잡음: 샘플마다 독립 가우시안 N(0, z_sigma). 공간 상관 잡음·드리프트·보정 오차는 없음
      → 면 전체를 평균하는 단차·선폭은 실제보다 낙관적일 수 있다(한계로 기록).
  A4. 결측: 흐린 면의 경사 > max_slope 인 곳 + 실제(흐리기 전) 벽에서 양쪽 edge_loss/2
      (합계 edge_loss 폭) 띠를 NaN 으로 둔다. 벽 = 정답 면 경사 > WALL_DEG.
      가림은 실제로는 한쪽에만 생기지만 여기서는 대칭으로 둔다.
  A5. measures_z = 0 (2D): 높이 없이 재료 실루엣의 이진 마스크만 준다. 실루엣에 가우시안
      흐림 후 0.5 문턱 → 샘플 점에서 판정(서브픽셀 없음). 그래서 경계 위치 잡음은 z_sigma 가
      아니라 '양자화' 오차, 즉 한 샘플 간격 안의 균등분포 → 표준편차 xy_step/√12 수준이다.
      위상이 한 영상 안에서 공유되므로 곧은 경계에서는 이 오차가 서로 상관(평균해도 안 줄어듦),
      곡선 경계(구멍·핀)에서는 점마다 달라져 원 맞춤에서 줄어든다. 2D 접촉식은 광학처럼 다룬다.
  A6. 선 단면: 반타원 z = h·√(1 − (x/a)²), a = w/√3 → 반높이 폭 = w (선폭 정의 = FWHM).
      2D 방식은 바닥 폭 2a 만 보므로 설계 비드 모델의 비율 FWHM/바닥폭 = √3/2 로 환산한다.
  A7. 선 패치는 단면이 y 방향으로 일정하고 결측도 열 단위이므로, 행 평균 단면 =
      단면 + N(0, z_sigma/√행수) 로 바로 만든다 (독립 잡음에서 nanmean 과 분포가 같음).
  A8. 이어 붙이기(시야 < 시편) 오차, 정합 오차, 표면 산란·다중 반사는 모델에 없다.
  A9. 측정 깊이: 패치의 높이 범위(단차 400, 선 200, 구멍 판 1000, 핀 1000 µm)가 depth_mm 를
      넘으면 그 패치의 지표는 '측정 불가'. 점이 모자라 지표를 못 뽑으면(점 측정 후보 등)
      오류 대신 NaN → 유효 회차가 80 % 미만이면 '측정 불가'.
  A10. 지표 추출은 측정 데이터와 설계값(G코드 위치·치수)만 쓴다. 넣은 오차(정답)는 쓰지 않는다.
       판정량 Q = |bias| + 2σ (위치는 |평균 오차 벡터| + 2·max(σx, σy)).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# ---------------------------------------------------------------- 상수 (µm)
TRUTH_GRID = 2.0                 # 정답 격자 2 µm
POS_ERR = (200.0, -100.0)        # 전체 위치 오차
STEP_UPPER, STEP_NOM, STEP_ERR = 400.0, 200.0, -20.0
FACE_W, FACE_L = 2500.0, 3000.0  # 단차 면 하나의 폭(x)·길이(y)
LINE_W_NOM, LINE_ERR, LINE_H = 400.0, 40.0, 200.0
LINE_LEN = 9000.0                # 선 3줄 × 3 mm
FWHM_PER_BASE = np.sqrt(3) / 2   # 반타원 단면: FWHM / 바닥폭
HOLE_D_NOM, HOLE_ERR, PLATE_T = 4000.0, -100.0, 1000.0
PIN_D, PIN_H, PIN_PITCH = 2000.0, 1000.0, 6000.0
EDGE_BAND = 250.0                # 단차 면 경계 띠 (H5 edge_band 0.25 mm)
WALL_DEG = 60.0                  # edge_loss 를 적용할 '벽' 경사 문턱
ROI_PAD = 150.0                  # 원 ROI 의 여유 (위치 오차 224 µm 에 더함)
VALID_FRAC_MIN = 0.8             # 유효 MC 비율이 이보다 낮으면 '측정 불가'
MIN_BOUNDARY_PTS = 12
DEFAULT_SLOPE_OPTICAL, DEFAULT_SLOPE_CONTACT = 60.0, 90.0
CONTACT_MORPH = "closing"        # 'closing'(물리적으로 맞음) 또는 'opening'(지시서 원문)

# 오차 종류: (이름, 그룹, 정답, 4:1 한계, 10:1 한계)   — 청사진 2.1절
ERROR_TYPES = [
    ("단차", "높이", STEP_ERR, 5.0, 2.0),
    ("선폭", "윤곽", LINE_ERR, 10.0, 4.0),
    ("구멍지름", "치수", HOLE_ERR, 25.0, 10.0),
    ("경계", "윤곽(참고)", -HOLE_ERR / 2, 25.0, 10.0),   # 구멍 경계의 반경 방향 이동, + = 재료 과다
    ("위치", "위치", float(np.hypot(*POS_ERR)), 50.0, 20.0),
]
TYPE_NAMES = [t[0] for t in ERROR_TYPES]
GRADES = ["10:1 통과", "4:1 통과", "불합격", "측정 불가"]
GRADE_RANK = {"10:1 통과": 3, "4:1 통과": 2, "불합격": 1, "측정 불가": 0}


@dataclass
class Model:
    z_sigma: float = 0.0
    xy_step: float = TRUTH_GRID
    xy_blur: float = 0.0
    edge_loss: float = 0.0
    max_slope: float = 90.0
    measures_z: bool = True
    contact: bool = False
    depth: float = np.inf               # 측정 깊이 [µm] (depth_mm × 1000)

    @property
    def step(self):
        return max(float(self.xy_step), TRUTH_GRID)

    @property
    def sigma(self):                       # 광학 가우시안 σ
        return 0.0 if self.contact else self.xy_blur / 2.355

    @property
    def probe_r(self):
        return self.xy_blur if (self.contact and self.measures_z) else 0.0

    @property
    def sigma_2d(self):                    # 2D 실루엣 흐림 (접촉식이어도 가우시안)
        return self.xy_blur / 2.355

    @property
    def margin(self):                      # 흐림·결측이 퍼지는 거리
        s = self.sigma if self.measures_z else self.sigma_2d
        return 4 * s + 1.2 * self.probe_r + self.edge_loss


def model_from_row(row) -> tuple[Model | None, list[str]]:
    """사양 행 → Model. 시뮬레이션 불가면 (None, 사유). 결측값 대체는 notes 에 적는다."""
    notes = []
    step = row.get("xy_step_um", np.nan)
    if not np.isfinite(step) or step <= 0:
        return None, ["xy_step 없음 → 측정 불가"]
    mz = row.get("measures_z", np.nan)
    zs = row.get("z_sigma_um", np.nan)
    if not np.isfinite(mz):
        mz = 1.0 if np.isfinite(zs) else 0.0
        notes.append(f"measures_z 없음 → {int(mz)} 가정")
    mz = bool(mz >= 0.5)
    if mz and not np.isfinite(zs):
        return None, ["measures_z=1 인데 z_sigma 없음 → 측정 불가"]
    contact = bool(row.get("contact", False))
    blur = row.get("xy_blur_um", np.nan)
    if not np.isfinite(blur):
        blur = step
        notes.append("xy_blur 없음 → xy_step 가정")
    el = row.get("edge_loss_um", np.nan)
    if not np.isfinite(el):
        el = 0.0
        notes.append("edge_loss 없음 → 0 가정")
    ms = row.get("max_slope_deg", np.nan)
    if not np.isfinite(ms):
        ms = DEFAULT_SLOPE_CONTACT if contact else DEFAULT_SLOPE_OPTICAL
        if mz:
            notes.append(f"max_slope 없음 → {ms:.0f}° 가정")
    if step < TRUTH_GRID:
        notes.append(f"xy_step {step:g} < 2 µm → 2 µm 로 처리")
    dep = row.get("depth_mm", np.nan)
    dep = float(dep) * 1000 if np.isfinite(dep) and dep > 0 else np.inf
    return Model(z_sigma=float(zs) if mz else 0.0, xy_step=float(step), xy_blur=max(float(blur), 0.0),
                 edge_loss=max(float(el), 0.0), max_slope=float(ms), measures_z=mz,
                 contact=contact, depth=dep), notes


# ---------------------------------------------------------------- 흐림 연산
def _ball(res, r, ndim):
    k = int(np.ceil(r / res))
    ax = np.arange(-k, k + 1) * res
    if ndim == 1:
        d2 = ax ** 2
    else:
        d2 = ax[:, None] ** 2 + ax[None, :] ** 2
    fp = d2 <= r * r
    s = np.where(fp, np.sqrt(np.clip(r * r - d2, 0, None)) - r, 0.0)
    return s, fp


def _morph(z, res, r):
    if r < res:
        return z
    s, fp = _ball(res, r, z.ndim)
    f = ndimage.grey_closing if CONTACT_MORPH == "closing" else ndimage.grey_opening
    return f(z, footprint=fp, structure=s, mode="nearest")


def _gauss2d_fft(z, sig_px):
    if sig_px < 0.3:
        return z
    F = np.fft.rfft2(z)
    F = ndimage.fourier_gaussian(F, sigma=sig_px, n=z.shape[1])
    return np.fft.irfft2(F, s=z.shape).astype(z.dtype)


def _nan_mask(zb, ztrue, res, m: Model):
    """경사 결측 + 벽 주변 edge_loss 띠 (가정 A4)."""
    grads = np.gradient(zb, res)
    if zb.ndim == 1:
        grads = [grads]
    slope = np.degrees(np.arctan(np.sqrt(sum(g * g for g in grads))))
    nanm = slope > m.max_slope
    if m.edge_loss > 0:
        gt = np.gradient(ztrue, res)
        if ztrue.ndim == 1:
            gt = [gt]
        wall = np.degrees(np.arctan(np.sqrt(sum(g * g for g in gt)))) > WALL_DEG
        if wall.any():
            dist = ndimage.distance_transform_edt(~wall) * res
            nanm |= dist <= m.edge_loss / 2
    return nanm


# ---------------------------------------------------------------- 1D 패치 (단차·선)
class Profile1D:
    """y 방향으로 일정한 형상의 단면. x0 = 격자 첫 점, res = 격자 간격."""

    def __init__(self, z, ztrue, x0, res, m: Model, silhouette=None):
        self.x0, self.res = x0, res
        if m.measures_z:
            if m.contact:
                zb = _morph(z, res, m.probe_r)
            else:
                sp = m.sigma / res
                zb = ndimage.gaussian_filter1d(z, sp, mode="nearest") if sp >= 0.3 else z
            self.z = zb
            self.nan = _nan_mask(zb, ztrue, res, m)
        else:
            sp = m.sigma_2d / res
            sb = ndimage.gaussian_filter1d(silhouette, sp, mode="nearest") if sp >= 0.3 else silhouette
            # 회색값을 그대로 두고 샘플 점에서 보간한 뒤 0.5 문턱 (격자 양자화가 끼지 않게)
            self.z = sb.astype(float)
            self.nan = np.zeros(z.shape, bool)

    def sample(self, xs):
        g = (xs - self.x0) / self.res
        z = np.interp(g, np.arange(self.z.size), self.z)
        nan = self.nan[np.clip(np.rint(g).astype(int), 0, self.nan.size - 1)]
        return z, nan


def _res1d(m: Model):
    s = m.sigma if m.measures_z else m.sigma_2d
    res = min(m.step, max(s, 1.0)) / 4
    if m.probe_r > 0:
        res = max(res, m.probe_r / 300)
    return float(np.clip(res, 0.5, 25.0))


def build_step(m: Model):
    res = _res1d(m)
    L = FACE_W + m.margin + 4 * res
    x = np.arange(-L, L + res / 2, res)
    xe = POS_ERR[0]                                   # 실제 경계 (설계 0 + 위치 오차)
    lower = STEP_UPPER - (STEP_NOM + STEP_ERR)
    frac = np.clip(0.5 - (x - xe) / res, 0, 1)        # 경계를 1칸 폭으로 부드럽게(정답 양자화 방지)
    z = lower + (STEP_UPPER - lower) * frac
    return Profile1D(z, z, x[0], res, m, silhouette=np.ones_like(z))


def _line_halfwidth_max():
    return (LINE_W_NOM + LINE_ERR) / np.sqrt(3)


def build_line(m: Model):
    res = _res1d(m)
    L = _line_halfwidth_max() + abs(POS_ERR[0]) + 400 + 2 * m.xy_blur + m.margin + 4 * res
    x = np.arange(-L, L + res / 2, res)
    a = (LINE_W_NOM + LINE_ERR) / np.sqrt(3)
    t = (x - POS_ERR[0]) / a
    z = LINE_H * np.sqrt(np.clip(1 - t * t, 0, None))
    sil = np.clip(0.5 - (np.abs(x - POS_ERR[0]) - a) / res, 0, 1)
    return Profile1D(z, z, x[0], res, m, silhouette=sil)


def _phase_axis(lo, hi, phase, step):
    k0 = int(np.ceil((lo - phase) / step))
    k1 = int(np.floor((hi - phase) / step))
    return phase + np.arange(k0, k1 + 1) * step


def measure_step(p: Profile1D, m: Model, rng, phase):
    if not m.measures_z:
        return np.nan
    xs = _phase_axis(-FACE_W, FACE_W, phase[0], m.step)
    ny = max(int(FACE_L // m.step), 1)
    z, nan = p.sample(xs)
    Z = np.broadcast_to(z.astype(np.float32), (ny, xs.size))
    if m.z_sigma > 0:
        Z = Z + np.float32(m.z_sigma) * rng.standard_normal((ny, xs.size), dtype=np.float32)
    Z = np.array(Z, dtype=np.float32)
    Z[:, nan] = np.nan
    if not (~nan).any():
        return np.nan
    col = np.nanmedian(Z[:min(ny, 200)], axis=0)       # 경계 찾기용 열 중앙값 (앞 200행)
    # 1차 면 추정: 설계 경계(0)에서 충분히 먼 바깥쪽 절반 (위치 오차 0.2 mm ≪ 1.25 mm)
    up0 = np.nanmedian(Z[:, xs < -FACE_W / 2]) if (xs < -FACE_W / 2).any() else np.nan
    lo0 = np.nanmedian(Z[:, xs > FACE_W / 2]) if (xs > FACE_W / 2).any() else np.nan
    if not (np.isfinite(up0) and np.isfinite(lo0)):
        return np.nan
    thr = (up0 + lo0) / 2
    ok = np.isfinite(col)
    xv, cv = xs[ok], col[ok]
    above = cv > thr
    idx = np.nonzero(above[:-1] != above[1:])[0]
    if idx.size == 0:
        return np.nan
    i = idx[np.argmin(np.abs(xv[idx]))]               # 설계 경계에 가장 가까운 교차
    x_e = xv[i] + (thr - cv[i]) * (xv[i + 1] - xv[i]) / (cv[i + 1] - cv[i])
    band = max(EDGE_BAND, 2 * m.xy_blur, m.edge_loss)
    up = Z[:, xs < x_e - band]
    lo = Z[:, xs > x_e + band]
    if np.isfinite(up).sum() < 3 or np.isfinite(lo).sum() < 3:
        return np.nan
    return float(np.nanmedian(up) - np.nanmedian(lo)) - STEP_NOM


def fwhm(xs, prof):
    """단면의 반높이 폭. 바닥 = 양 끝 15 % 중앙값, 꼭대기 = 최고점 근처 포물선 꼭짓점."""
    ok = np.isfinite(prof)
    x, v = xs[ok], prof[ok]
    if x.size < 7:
        return np.nan
    n15 = max(int(0.15 * xs.size), 1)
    edge = np.concatenate([prof[:n15], prof[-n15:]])
    base = np.nanmedian(edge)
    if not np.isfinite(base):
        return np.nan
    ip = int(np.argmax(v))
    vmax = v[ip]
    if vmax - base <= 0:
        return np.nan
    sel = np.nonzero(v >= base + 0.95 * (vmax - base))[0]
    sel = sel[np.abs(sel - ip) <= max(np.abs(sel - ip).min() + sel.size, 1)]
    if sel.size < 3:
        sel = np.arange(max(ip - 1, 0), min(ip + 2, v.size))
    top = vmax
    if sel.size >= 3:
        c = np.polyfit(x[sel] - x[ip], v[sel], 2)
        if c[0] < 0:
            xv = -c[1] / (2 * c[0])
            if abs(xv) <= (x[sel].max() - x[sel].min()):
                top = c[2] - c[1] ** 2 / (4 * c[0])
    half = base + (top - base) / 2
    # 왼쪽
    j = ip
    while j > 0 and v[j] >= half:
        j -= 1
    if v[j] >= half:
        return np.nan
    xl = x[j] + (half - v[j]) * (x[j + 1] - x[j]) / (v[j + 1] - v[j])
    k = ip
    while k < v.size - 1 and v[k] >= half:
        k += 1
    if v[k] >= half:
        return np.nan
    xr = x[k - 1] + (half - v[k - 1]) * (x[k] - x[k - 1]) / (v[k] - v[k - 1])
    return float(xr - xl)


def measure_line(p: Profile1D, m: Model, rng, phase):
    L = _line_halfwidth_max() + abs(POS_ERR[0]) + 400 + 2 * m.xy_blur + m.edge_loss
    xs = _phase_axis(-L, L, phase[0], m.step)
    z, nan = p.sample(xs)
    if not m.measures_z:
        # 2D: 열마다 같은 판정 → 마스크 폭 = 재료 칸 수 × 간격 (가정 A5·A6)
        base_w = float((z > 0.5).sum()) * m.step
        if base_w <= 0:
            return np.nan
        return base_w * FWHM_PER_BASE - LINE_W_NOM
    ny = max(int(LINE_LEN // m.step), 1)
    prof = z + (rng.normal(0, m.z_sigma / np.sqrt(ny), xs.size) if m.z_sigma > 0 else 0)  # 가정 A7
    prof = np.where(nan, np.nan, prof)
    w = fwhm(xs, prof)
    return w - LINE_W_NOM if np.isfinite(w) else np.nan


# ---------------------------------------------------------------- 2D 패치 (구멍·핀)
def _res2d(m: Model):
    if m.measures_z and m.contact:
        r = m.probe_r
        res = max(min(m.step / 2, max(TRUTH_GRID, r / 12)), r / 30)
    else:
        s = m.sigma if m.measures_z else m.sigma_2d
        res = min(m.step, max(s, 1.0)) / 2
    # 큰 프로브(예: 볼 반경 1–3 mm)에서도 구조요소가 61×61 칸을 넘지 않게 상한을 r/30 까지 올린다
    return float(np.clip(res, TRUTH_GRID, max(100.0, m.probe_r / 30)))


class Patch2D:
    """원형 형상(구멍·핀) 패치. 격자 원점 = 실제 형상 중심. kind='hole' 또는 'pin'."""

    def __init__(self, kind, m: Model):
        self.kind = kind
        R = (HOLE_D_NOM + HOLE_ERR) / 2 if kind == "hole" else PIN_D / 2
        Rd = HOLE_D_NOM / 2 if kind == "hole" else PIN_D / 2
        self.R_design = Rd
        self.w = roi_halfwidth(m)
        res = _res2d(m)
        half = Rd + self.w + float(np.hypot(*POS_ERR)) + m.margin + 4 * res
        n = int(np.ceil(2 * half / res)) + 1
        ax = (np.arange(n) - (n - 1) / 2) * res
        r = np.hypot(ax[:, None], ax[None, :]).astype(np.float32)
        if kind == "hole":
            ind = np.clip((r - R) / res + 0.5, 0, 1)
            h = PLATE_T
        else:
            ind = np.clip((R - r) / res + 0.5, 0, 1)
            h = PIN_H
        del r
        self.res, self.n = res, n
        if m.measures_z:
            z = (h * ind).astype(np.float32)
            if m.contact:
                zb = _morph(z.astype(float), res, m.probe_r).astype(np.float32)
            else:
                zb = _gauss2d_fft(z, m.sigma / res)
            self.z = zb
            self.nan = _nan_mask(zb, z, res, m)
        else:
            sb = _gauss2d_fft(ind.astype(np.float32), m.sigma_2d / res)
            self.z = sb.astype(np.float32)        # 샘플 점에서 보간 후 0.5 문턱
            self.nan = np.zeros(self.z.shape, bool)

    def sample(self, X, Y):
        """실제 중심 기준 좌표 (X, Y) 에서 표본 (쌍선형) + 결측 (최근접)."""
        c = (self.n - 1) / 2
        gi = Y / self.res + c
        gj = X / self.res + c
        z = ndimage.map_coordinates(self.z, [gi, gj], order=1, mode="nearest")
        if not self.has_nan:
            return z, np.zeros(z.shape, bool)
        ii = np.clip(np.rint(gi).astype(np.int64), 0, self.n - 1)
        jj = np.clip(np.rint(gj).astype(np.int64), 0, self.n - 1)
        return z, self.nan[ii, jj]

    @property
    def has_nan(self):
        if not hasattr(self, "_has_nan"):
            self._has_nan = bool(self.nan.any())
        return self._has_nan


def roi_halfwidth(m: Model):
    return float(np.hypot(*POS_ERR)) + ROI_PAD + 3 * (m.sigma if m.measures_z else m.sigma_2d) \
        + m.edge_loss + 1.2 * m.probe_r + 2 * m.step


def kasa(x, y):
    """대수적(Kåsa) 원 맞춤 → (cx, cy, r)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x * x + y * y)
    (D, E, F), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -D / 2, -E / 2
    r2 = cx * cx + cy * cy - F
    return cx, cy, (np.sqrt(r2) if r2 > 0 else np.nan)


def measure_circle(patch: Patch2D, m: Model, rng, phase, design_c, true_c):
    """설계 중심 design_c 둘레 고리 ROI 에서 경계점을 찾아 원 맞춤.
    반환 (cx, cy, r): 설계 좌표계. 재료 쪽 경계와 빈 쪽 경계를 따로 맞춰 평균한다
    (결측 띠나 반 칸 치우침이 양쪽에 대칭으로 상쇄됨)."""
    # 1차(거친) 단계: 간격을 k 배로 솎아 설계 고리 ROI 전체에서 문턱과 대략의 원을 구한다.
    # 2차(세밀) 단계: 1차 원 둘레의 얇은 고리만 원래 간격으로 다시 봐서 맞춘다 (계산량 절감).
    # 두 단계 모두 측정 데이터와 설계값만 쓴다.
    Rd, w, st = patch.R_design, patch.w, m.step
    k = max(1, int(np.ceil(COARSE_STEP / st)))
    if k > 1:
        fit0, thr = _circle_pass(patch, m, rng, phase, st * k, design_c, max(Rd - w, 0), Rd + w, true_c)
        if fit0 is None or not np.isfinite(fit0[2]):
            return np.nan, np.nan, np.nan
        c0 = (design_c[0] + fit0[0], design_c[1] + fit0[1])
        wf = 3 * (m.sigma if m.measures_z else m.sigma_2d) + m.edge_loss / 2 + 1.2 * m.probe_r \
            + 1.5 * st * k + 24
        fit, _ = _circle_pass(patch, m, rng, phase, st, c0, max(fit0[2] - wf, 0), fit0[2] + wf,
                              true_c, thr=thr)
        if fit is None:
            return np.nan, np.nan, np.nan
        return c0[0] + fit[0], c0[1] + fit[1], fit[2]
    fit, _ = _circle_pass(patch, m, rng, phase, st, design_c, max(Rd - w, 0), Rd + w, true_c)
    if fit is None:
        return np.nan, np.nan, np.nan
    return design_c[0] + fit[0], design_c[1] + fit[1], fit[2]


COARSE_STEP = 16.0   # 1차 단계 간격 하한 [µm]


def _circle_pass(patch, m, rng, phase, st, ctr, r_in, r_out, true_c, thr=None):
    """중심 ctr, 반경 [r_in, r_out] 고리 안 샘플 → (ctr 기준 원 맞춤, 문턱).
    재료 쪽 경계와 빈 쪽 경계를 따로 맞춰 평균한다 (결측 띠·반 칸 치우침이 대칭으로 상쇄)."""
    xs = _phase_axis(ctr[0] - r_out, ctr[0] + r_out, phase[0], st).astype(np.float32)
    ys = _phase_axis(ctr[1] - r_out, ctr[1] + r_out, phase[1], st).astype(np.float32)
    dx = xs - np.float32(ctr[0])
    dy = ys - np.float32(ctr[1])
    if xs.size < 3 or ys.size < 3:
        return None, thr
    iy, ix = _annulus_points(dx.astype(float), dy.astype(float), st, r_in, r_out)
    if iy.size < 20:
        return None, thr
    shape = (ys.size, xs.size)
    zz, nn = patch.sample(xs[ix] - np.float32(true_c[0]), ys[iy] - np.float32(true_c[1]))
    if m.measures_z and m.z_sigma > 0:
        zz = zz + rng.normal(0, m.z_sigma, zz.size).astype(np.float32)
    lab = np.full((shape[0] + 2, shape[1] + 2), -2, np.int8)   # -2 ROI 밖, -1 결측, 0 빈 쪽, 1 재료 쪽
    iy, ix = iy + 1, ix + 1                                     # 테두리 1칸 덧댐
    if m.measures_z:
        if thr is None:
            v = zz[~nn]
            if v.size < 20:
                return None, thr
            mid = (np.percentile(v, 5) + np.percentile(v, 95)) / 2
            hi, lo = v[v > mid], v[v <= mid]
            if hi.size < 5 or lo.size < 5:
                return None, thr
            thr = (np.median(hi) + np.median(lo)) / 2
        lab[iy, ix] = np.where(nn, -1, (zz > thr).astype(np.int8))
    else:
        lab[iy, ix] = (zz > 0.5).astype(np.int8)
    me = lab[iy, ix]
    nb = [lab[iy - 1, ix], lab[iy + 1, ix], lab[iy, ix - 1], lab[iy, ix + 1]]
    b_hi = (me == 1) & np.logical_or.reduce([(q == 0) | (q == -1) for q in nb])
    b_lo = (me == 0) & np.logical_or.reduce([(q == 1) | (q == -1) for q in nb])
    fits = []
    for b in (b_hi, b_lo):
        if b.sum() >= MIN_BOUNDARY_PTS:
            fits.append(kasa(dx[ix[b] - 1].astype(float), dy[iy[b] - 1].astype(float)))
    if not fits:
        return None, thr
    return tuple(np.nanmean(np.array(fits), axis=0)), thr


def _annulus_points(dx, dy, st, r_in, r_out):
    """균등 격자(dx: 열 좌표, dy: 행 좌표, 간격 st) 중 r_in ≤ r ≤ r_out 인 칸의 (행, 열) 번호.
    행마다 두 구간을 해석적으로 구해 전체 사각형을 만들지 않는다."""
    xo = np.sqrt(np.clip(r_out ** 2 - dy ** 2, 0, None))
    xi = np.sqrt(np.clip(r_in ** 2 - dy ** 2, 0, None))
    x0 = dx[0]
    nx = dx.size

    def jr(lo, hi):
        a = np.clip(np.ceil((lo - x0) / st - 1e-9), 0, nx).astype(np.int64)
        b = np.clip(np.floor((hi - x0) / st + 1e-9) + 1, 0, nx).astype(np.int64)
        return a, np.maximum(b, a)

    inside = np.abs(dy) <= r_out
    hole = (xi > 0) & inside
    a1, b1 = jr(-xo, np.where(hole, -xi, xo))
    a2, b2 = jr(xi, xo)
    b2 = np.where(hole, b2, a2)                 # 안쪽 원이 행에 안 걸리면 구간 하나
    a1, b1 = np.where(inside, a1, 0), np.where(inside, b1, 0)
    b2 = np.where(inside, b2, a2)
    rows, cols = [], []
    for a, b in ((a1, b1), (a2, b2)):
        n = b - a
        tot = int(n.sum())
        if tot == 0:
            continue
        r = np.repeat(np.arange(dy.size), n)
        start = np.repeat(a - np.concatenate([[0], np.cumsum(n)[:-1]]), n)
        rows.append(r)
        cols.append(np.arange(tot) + start)
    if not rows:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    return np.concatenate(rows), np.concatenate(cols)


PIN_CENTERS = [(i * PIN_PITCH, j * PIN_PITCH) for j in (-1, 0, 1) for i in (-1, 0, 1)]


# ---------------------------------------------------------------- MC 실행
# 패치별 높이 범위 [µm]: 측정 깊이(depth_mm)보다 크면 그 패치는 '측정 불가' (2D 방식은 무관)
PATCH_RELIEF = {"step": STEP_UPPER, "line": LINE_H, "hole": PLATE_T, "pin": PIN_H}


def _safe(f, *a, n=1):
    """점이 모자라거나(점 측정 후보 등) 맞춤이 퇴화하면 오류 대신 NaN."""
    try:
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return f(*a)
    except (ValueError, IndexError, ZeroDivisionError, np.linalg.LinAlgError, FloatingPointError):
        return np.nan if n == 1 else (np.nan,) * n


def depth_ok(m: Model, key):
    return (not m.measures_z) or PATCH_RELIEF[key] <= m.depth


def run_once(parts, m: Model, rng):
    """MC 1회 → {오차종류: 추정 오차 (위치는 (dx, dy))}."""
    phase = rng.uniform(0, m.step, 2)
    out = {"단차": _safe(measure_step, parts["step"], m, rng, phase) if depth_ok(m, "step") else np.nan,
           "선폭": _safe(measure_line, parts["line"], m, rng, phase) if depth_ok(m, "line") else np.nan}
    r = np.nan
    if depth_ok(m, "hole"):
        cx, cy, r = _safe(measure_circle, parts["hole"], m, rng, phase, (0.0, 0.0), POS_ERR, n=3)
    out["구멍지름"] = 2 * r - HOLE_D_NOM if np.isfinite(r) else np.nan
    out["경계"] = -(2 * r - HOLE_D_NOM) / 2 if np.isfinite(r) else np.nan
    d = []
    if depth_ok(m, "pin"):
        for c in PIN_CENTERS:
            tc = (c[0] + POS_ERR[0], c[1] + POS_ERR[1])
            px, py, pr = _safe(measure_circle, parts["pin"], m, rng, phase, c, tc, n=3)
            if np.isfinite(px) and np.isfinite(py):
                d.append((px - c[0], py - c[1]))
    out["위치"] = tuple(np.mean(d, axis=0)) if len(d) >= 5 else (np.nan, np.nan)
    return out


def build_parts(m: Model):
    return {"step": build_step(m), "line": build_line(m),
            "hole": Patch2D("hole", m), "pin": Patch2D("pin", m)}


def grade(q, lim4, lim10):
    if not np.isfinite(q):
        return "측정 불가"
    if q <= lim10:
        return "10:1 통과"
    if q <= lim4:
        return "4:1 통과"
    return "불합격"


def simulate(m: Model, n_mc=50, seed=0):
    """→ (요약 dict {종류: {...}}, 원시 리스트). 판정량 Q = |bias| + 2σ."""
    rng = np.random.default_rng(seed)
    parts = build_parts(m)
    runs = [run_once(parts, m, rng) for _ in range(n_mc)]
    summary = {}
    for name, group, truth, l4, l10 in ERROR_TYPES:
        if name == "위치":
            e = np.array([r["위치"] for r in runs], float) - np.array(POS_ERR)
            ok = np.all(np.isfinite(e), axis=1)
            e = e[ok]
            if ok.mean() < VALID_FRAC_MIN or len(e) < 2:
                bias = sd = q = np.nan
            else:
                bias = float(np.hypot(*e.mean(axis=0)))
                sd = float(np.max(e.std(axis=0, ddof=1)))
                q = bias + 2 * sd
            extra = {"bias_x_um": float(e[:, 0].mean()) if len(e) else np.nan,
                     "bias_y_um": float(e[:, 1].mean()) if len(e) else np.nan}
        else:
            v = np.array([r[name] for r in runs], float)
            ok = np.isfinite(v)
            e = v[ok] - truth
            if ok.mean() < VALID_FRAC_MIN or len(e) < 2:
                bias = sd = q = np.nan
            else:
                bias, sd = float(e.mean()), float(e.std(ddof=1))
                q = abs(bias) + 2 * sd
            extra = {}
        summary[name] = dict(group=group, truth_um=truth, bias_um=bias, sd2_um=2 * sd if np.isfinite(sd) else np.nan,
                             Q_um=q, lim4_um=l4, lim10_um=l10, grade=grade(q, l4, l10),
                             valid_frac=float(ok.mean()), **extra)
    return summary, runs


def unmeasurable_summary(reason=""):
    return {name: dict(group=g, truth_um=t, bias_um=np.nan, sd2_um=np.nan, Q_um=np.nan, lim4_um=l4,
                       lim10_um=l10, grade="측정 불가", valid_frac=0.0)
            for name, g, t, l4, l10 in ERROR_TYPES}
