# 처리 담당 (T4b · T7–T12) 열람 금지 (세부청사진 T3 §5).
"""카메라 (세부청사진 §6.4, SM5). OV9281 1280 × 800 · 3 µm · 글로벌셔터 · 120 fps, ROI 1280 × 256 GRAY8.

빛 세기 (명목 선 꼭대기 ≈ 1) → 전자 수 (peak_fill × 포화 × 노출 비) × 화소 감도 고정 패턴 (PRNU)
→ + 암전류 (온도로 두 배) + 어두운 고정 패턴 (DSNU) → 산탄 (포아송) → + 읽기 잡음 → 포화에서 자름
→ 양자화 (8비트 기본, 10비트 선택). 고정 패턴은 카메라 갈래 시드로 한 번만 뽑아 캠페인 내내 같음.
시각: 펄스 k의 노출 시작 → 노출 · 읽기 · 호스트 지터 뒤 t_host. 빠진 프레임은 펄스는 있고 프레임만 없음.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Sensor:
    ccfg: dict
    width: int
    height: int
    prnu: np.ndarray
    dsnu: np.ndarray

    @classmethod
    def create(cls, ccfg: dict, width: int, height: int, rng) -> "Sensor":
        prnu = (1.0 + rng.normal(0.0, ccfg["prnu"], (height, width))).astype(np.float32)
        dsnu = rng.normal(0.0, ccfg["dsnu_e"], (height, width)).astype(np.float32)
        return cls(ccfg, width, height, prnu, dsnu)

    @property
    def max_dn(self) -> int:
        return 2 ** int(self.ccfg["bit_depth"]) - 1

    def e_per_dn(self) -> float:
        return self.ccfg["full_well_e"] / self.max_dn

    def expose(self, irr: np.ndarray, roi_y0: int, rng, exposure_us: float | None = None,
               temp_c: float | None = None, shutter_open: bool = True) -> tuple[np.ndarray, int]:
        """빛 세기 (roi_h, W) → (영상 uint8/uint16, 포화 화소 수). shutter_open=False면 암흑 (렌즈 가림)."""
        c = self.ccfg
        exp_us = c["exposure_us"] if exposure_us is None else exposure_us
        T = c["sensor_temp_c"] if temp_c is None else temp_c
        h = irr.shape[0]
        sl = slice(roi_y0, roi_y0 + h)
        gain = np.float32(c["peak_fill"] * c["full_well_e"] * (exp_us / c["exposure_us"]))
        dark = np.float32(c["dark_e_per_s_25c"] * 2.0 ** ((T - 25.0) / c["dark_double_c"]) * exp_us * 1e-6)
        if shutter_open:
            mean = np.asarray(irr, np.float32) * gain
            mean *= self.prnu[sl]
            mean += dark
            np.maximum(mean, 0.0, out=mean)
        else:
            mean = np.full(irr.shape, dark, np.float32)
        # 산탄 + 읽기 잡음 (T3-2, 속도): 평균 ≥ 20 e⁻ 화소는 두 가우스의 합을 한 번에 (분산 = 평균 + 읽기²),
        # 그 아래만 포아송 + 읽기 가우스 [모델 문서 §3.4]. 통계는 같고 난수 실현만 바뀜.
        rn2 = np.float32(c["read_noise_e"] ** 2)
        z = rng.standard_normal(mean.shape, dtype=np.float32)
        e = mean + np.sqrt(mean + rn2) * z
        low = mean < 20.0
        if low.any():
            n_low = int(low.sum())
            e[low] = rng.poisson(mean[low]).astype(np.float32) + \
                np.float32(c["read_noise_e"]) * rng.standard_normal(n_low, dtype=np.float32)
        e += self.dsnu[sl]
        e *= np.float32(1.0 / self.e_per_dn())
        e += np.float32(0.5)
        np.floor(e, out=e)
        np.clip(e, 0, self.max_dn, out=e)
        img = e.astype(np.uint8 if self.max_dn <= 255 else np.uint16)
        return img, int(np.count_nonzero(img == self.max_dn))

    @property
    def pixel_format(self) -> str:
        return {8: "GRAY8", 10: "GRAY10", 12: "GRAY12", 16: "GRAY16"}[int(self.ccfg["bit_depth"])]


def frame_times(t_pulse_ns: np.ndarray, ccfg: dict, rng, drop_prob: float = 0.0):
    """펄스 시각 → (남은 프레임의 펄스 번호, t_host_ns, dropped_before). 호스트 시각은 늘 증가."""
    n = len(t_pulse_ns)
    keep = np.ones(n, bool) if drop_prob <= 0 else rng.random(n) >= drop_prob
    idx = np.flatnonzero(keep)
    lat = (ccfg["exposure_us"] * 1e-6 + ccfg["readout_ms"] * 1e-3) * 1e9
    jit = rng.normal(0.0, ccfg["host_jitter_ms"] * 1e6, n)
    t = np.asarray(t_pulse_ns, np.int64)[idx] + np.int64(round(lat)) + np.rint(np.abs(jit[idx])).astype(np.int64)
    for i in range(1, len(t)):  # 같은 호스트에서 받은 순서 유지
        if t[i] <= t[i - 1]:
            t[i] = t[i - 1] + 1
    dropped = np.diff(np.concatenate([[-1], idx])) - 1
    return idx, t, dropped.astype(int)


def roi_bytes(width: int, roi_h: int, bit_depth: int = 8) -> int:
    return width * roi_h * (1 if bit_depth <= 8 else 2)


def saturation_fraction(img: np.ndarray, max_dn: int) -> float:
    return float((img == max_dn).mean())


def snr_peak(ccfg: dict) -> float:
    """명목 꼭대기 SNR (산탄 + 읽기) — 문서 · 시험용."""
    e = ccfg["peak_fill"] * ccfg["full_well_e"]
    return e / math.sqrt(e + ccfg["read_noise_e"] ** 2)
