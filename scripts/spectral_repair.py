#!/usr/bin/env python3
"""Optional short-click repair and gentle spectral peak smoothing for WAV audio.

Neither stage runs in the default mastering chain. Click repair targets isolated
sample-scale defects, not clipping, scratches, or long dropouts. Smoothing only
attenuates narrow spectral peaks; it is not source separation or denoising.
"""

import argparse
from pathlib import Path

import numpy as np
from scipy import ndimage, signal
from scipy.io import wavfile

from analyze_audio import load


def _repair_channel(x, sr, sensitivity, max_ms):
    baseline = ndimage.median_filter(x, size=5, mode="reflect")
    residual = np.abs(x - baseline)
    win = max(101, int(sr * 0.02) | 1)
    local = np.sqrt(ndimage.uniform_filter1d(residual ** 2, size=win, mode="reflect"))
    candidates = np.flatnonzero(residual > np.maximum(0.025, sensitivity * local))
    max_samples = max(2, int(sr * max_ms / 1000))
    intervals = []
    if len(candidates):
        cuts = np.flatnonzero(np.diff(candidates) > max_samples)
        starts = np.r_[0, cuts + 1]
        ends = np.r_[cuts, len(candidates) - 1]
        intervals.extend((int(candidates[first]), int(candidates[last]))
                         for first, last in zip(starts, ends))
    # A flat pop can have no median-filter residual: its two abrupt edges are
    # individually plausible samples. Pair opposite jumps with a returning
    # baseline inside the maximum repair span.
    delta = np.diff(x)
    delta_local = np.sqrt(ndimage.uniform_filter1d(delta ** 2, size=win, mode="reflect"))
    edges = np.flatnonzero(np.abs(delta) > np.maximum(0.08, sensitivity * delta_local))
    for pos, first in enumerate(edges):
        for second in edges[pos + 1 :]:
            if second - first > max_samples:
                break
            if delta[first] * delta[second] >= 0:
                continue
            ratio = abs(delta[first] / delta[second])
            if 0.5 <= ratio <= 2 and abs(x[first] - x[second + 1]) <= 0.3 * abs(delta[first]):
                intervals.append((int(first + 1), int(second)))
                break
    if not intervals:
        return x.copy(), 0
    intervals.sort()
    merged = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    out = x.copy()
    repaired = 0
    for lo, hi in merged:
        if hi - lo + 1 > max_samples or lo < 2 or hi + 2 >= len(x):
            continue
        left, right = lo - 1, hi + 1
        # Hermite interpolation uses intact slopes on both sides, preserving a
        # curved tone better than a straight line across a millisecond pop.
        span = right - left
        u = (np.arange(lo, hi + 1) - left) / span
        m0 = (x[left] - x[left - 1]) * span
        m1 = (x[right + 1] - x[right]) * span
        out[lo : hi + 1] = ((2 * u**3 - 3 * u**2 + 1) * x[left]
                              + (u**3 - 2 * u**2 + u) * m0
                              + (-2 * u**3 + 3 * u**2) * x[right]
                              + (u**3 - u**2) * m1)
        repaired += 1
    return out, repaired


def declick_array(y, sr, sensitivity=8.0, max_ms=2.0):
    """Interpolate isolated defects of at most max_ms; return audio and count."""
    if not 4 <= sensitivity <= 20 or not 0.1 <= max_ms <= 5:
        raise ValueError("sensitivity must be 4..20 and max_ms 0.1..5")
    x = np.asarray(y, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    out = x.copy()
    total = 0
    block = max(sr, sr * 8)
    guard = max(int(sr * 0.03), int(sr * max_ms / 1000) * 2)
    for ch in range(x.shape[1]):
        for start in range(0, len(x), block):
            stop = min(start + block, len(x))
            lo, hi = max(0, start - guard), min(len(x), stop + guard)
            fixed, _ = _repair_channel(x[lo:hi, ch], sr, sensitivity, max_ms)
            a, b = start - lo, stop - lo
            out[start:stop, ch] = fixed[a:b]
            total += int(np.count_nonzero(np.abs(fixed[a:b] - x[start:stop, ch]) > 1e-12))
    return out, total


def _smooth_channel(x, sr, max_db, min_hz):
    nfft = 2048
    if len(x) < nfft:
        return x.copy()
    _, _, z = signal.stft(x, fs=sr, nperseg=nfft, noverlap=1536, boundary="zeros")
    mag_db = 20 * np.log10(np.maximum(np.abs(z), 1e-8))
    local_db = ndimage.median_filter(mag_db, size=(5, 1), mode="nearest")
    excess = np.maximum(mag_db - local_db - 1.0, 0.0)
    reduction = np.minimum(excess, max_db)
    reduction[: int(min_hz * nfft / sr), :] = 0.0
    reduction = ndimage.gaussian_filter1d(reduction, sigma=1.0, axis=1)
    gain = 10 ** (-reduction / 20)
    _, rebuilt = signal.istft(z * gain, fs=sr, nperseg=nfft, noverlap=1536, boundary=True)
    return rebuilt[: len(x)]


def smooth_array(y, sr, max_db=1.5, min_hz=500.0):
    """Bounded, attenuation-only smoothing of narrow spectral peaks."""
    if not 0 < max_db <= 3 or not 100 <= min_hz < sr / 2:
        raise ValueError("max_db must be 0..3 and min_hz 100..Nyquist")
    x = np.asarray(y, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    out = np.empty_like(x)
    block = max(sr, sr * 6)
    guard = 4096
    for ch in range(x.shape[1]):
        for start in range(0, len(x), block):
            stop = min(start + block, len(x))
            lo, hi = max(0, start - guard), min(len(x), stop + guard)
            fixed = _smooth_channel(x[lo:hi, ch], sr, max_db, min_hz)
            out[start:stop, ch] = fixed[start - lo : stop - lo]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--declick", action="store_true", help="repair isolated clicks and short pops")
    p.add_argument("--smooth-db", type=float, default=0.0, help="maximum narrow-peak attenuation, 0..3 dB")
    p.add_argument("--sensitivity", type=float, default=8.0, help="click threshold multiple, 4..20")
    p.add_argument("--max-ms", type=float, default=2.0, help="maximum repair duration, 0.1..5 ms")
    p.add_argument("--min-hz", type=float, default=500.0, help="lowest frequency to smooth")
    p.add_argument("--report-only", action="store_true", help="analyze without writing audio")
    a = p.parse_args()
    if not a.declick and a.smooth_db <= 0:
        p.error("choose --declick and/or --smooth-db")
    if a.source.resolve() == a.output.resolve():
        p.error("output must differ from source")
    y, sr = load(str(a.source))
    repaired = 0
    if a.declick:
        y, repaired = declick_array(y, sr, a.sensitivity, a.max_ms)
        print(f"declick: repaired {repaired} samples (isolated events <= {a.max_ms:g} ms)")
    if a.smooth_db > 0:
        y = smooth_array(y, sr, a.smooth_db, a.min_hz)
        print(f"spectral smooth: attenuated narrow peaks by at most {a.smooth_db:g} dB above {a.min_hz:g} Hz")
    if not a.report_only:
        if not a.output.parent.exists():
            p.error("output directory does not exist")
        wavfile.write(a.output, sr, y.astype(np.float32))
        print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
