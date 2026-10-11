#!/usr/bin/env python3
"""Tilt EQ — ONE see-saw control that pivots the whole tonal balance around a frequency.

Lineage: Baxandall tone controls (1950s) -> the "slope/tilt" control; canonical digital
form is the musicdsp.org "Niveau filter" / Ivanov 2009 "Simple Tilt Equaliser":
split the signal with a one-pole low-pass, then apply opposing gains to the low and high
halves. Removing the sub-<200 Hz phase wrecking of stacked shelves is why it reads as
"phase-friendly" and natural (fewer overlapping bands than a multi-band EQ).

Two entry points:
  process: tilt.py <in.wav> <out.wav> --tilt DB [--pivot HZ] [--skew G]
  measure: tilt.py --measure <in.wav> [--pivot HZ] [--target-slope DB_OCT]

--tilt T is the TOTAL spread: extremes differ by T dB (low end -T/2, high end +T/2).
RMS-matched render (fair A/B), minimum-phase only, ceiling-only soft-clip (skill doctrine).
"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = __import__("os").path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load, avg_power


def apply_tilt(y, sr, tilt_db, pivot_hz=800.0, skew=1.0):
    """Symmetric tilt: low end -T/2 dB, high end +T/2*skew dB about pivot_hz. Per channel.
    Complementary first-order split (low + high == x), so the DC/HF gains are exact."""
    if tilt_db == 0.0:
        return y
    low_db = -tilt_db / 2.0
    high_db = +tilt_db / 2.0 * skew
    gL = 10 ** (low_db / 20.0) - 1.0
    gH = 10 ** (high_db / 20.0) - 1.0
    sos = signal.butter(1, min(pivot_hz, sr * 0.45), btype="lowpass", fs=sr, output="sos")
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        lp = signal.sosfilt(sos, y[:, c])
        out[:, c] = y[:, c] + gL * lp + gH * (y[:, c] - lp)
    return out


def measure_slope(mono, sr):
    """Least-squares dB-level slope vs log2(f) over octave centres 125 Hz..8 kHz, in dB/oct."""
    P, fr = avg_power(mono, sr)
    centres = [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]
    x, db = [], []
    for c in centres:
        m = (fr >= c / np.sqrt(2)) & (fr < c * np.sqrt(2))
        x.append(np.log2(c))
        db.append(10 * np.log10(max(P[m].sum(), 1e-18)))
    x, db = np.array(x), np.array(db)
    slope = float(np.polyfit(x, db, 1)[0])
    # balance either side of the pivot (energy ratio, dB)
    return slope, x, db


def curvature_db(mono, sr):
    """Mid-vs-edge residual from the tilt line, in dB.
    < 0 = mid scoop ('smiley face' / V)   > 0 = mid hump ('frown' / bell).
    Orthogonal to the slope: a tilt cannot produce curvature."""
    slope, x, db = measure_slope(mono, sr)
    res = db - np.polyval(np.polyfit(x, db, 1), x)
    return float(res[[1, 2, 3]].mean() - res[[0, 5, 6]].mean())


def tilt_for_target(cur_slope, target_slope, lo=125.0, hi=8000.0, clamp=3.0):
    """Tilt dB needed to move a slope (dB/oct) from cur to target; clamped to +/- clamp."""
    span = float(np.log2(hi / lo))
    return float(np.clip((target_slope - cur_slope) * span, -clamp, clamp))


def balance_db(mono, sr, pivot_hz):
    P, fr = avg_power(mono, sr)
    lo = P[(fr >= 60) & (fr < pivot_hz)].sum()
    hi = P[(fr >= pivot_hz) & (fr < 12000)].sum()
    return 10 * np.log10(max(hi, 1e-18) / max(lo, 1e-18))


def cmd_measure(path, pivot, target_slope):
    y, sr = load(path)
    mono = y.mean(axis=1)
    slope, x, db = measure_slope(mono, sr)
    bal = balance_db(mono, sr, pivot)
    curv = curvature_db(mono, sr)
    shape = "mid scoop (smiley/V)" if curv < -0.3 else ("mid hump (frown)" if curv > 0.3 else "balanced (neither)")
    print(f"slope {slope:+.2f} dB/oct (125 Hz-8 kHz)   balance(> / < {pivot:.0f} Hz) {bal:+.2f} dB")
    print(f"curvature {curv:+.2f} dB  -> {shape}")
    print("  octave levels (dB, relative to mean):")
    rel = db - db.mean()
    for c, r in zip([125, 250, 500, 1000, 2000, 4000, 8000], rel):
        print(f"    {c:>5d} Hz  {r:+5.2f}")
    if target_slope is not None:
        span = np.log2(8000.0 / 125.0)  # ~6 octaves
        needed = (target_slope - slope) * span
        print(f"  to reach {target_slope:+.2f} dB/oct, tilt (positive = brighter) ~ {needed:+.2f} dB "
              f"@ pivot {pivot:.0f} Hz  ->  --tilt {needed:+.1f}")


def main():
    a = sys.argv
    if len(a) < 2 or a[1] in ("-h", "--help"):
        print(__doc__)
        return
    if "--measure" in a:
        i = a.index("--measure")
        path = a[i + 1]
        pivot = float(a[a.index("--pivot") + 1]) if "--pivot" in a else 800.0
        tgt = float(a[a.index("--target-slope") + 1]) if "--target-slope" in a else None
        cmd_measure(path, pivot, tgt)
        return
    if len(a) < 3:
        sys.exit("usage: tilt.py <in.wav> <out.wav> --tilt DB [--pivot HZ] [--skew G]  |  tilt.py --measure <in.wav>")
    src, dst = a[1], a[2]
    tilt_db = float(a[a.index("--tilt") + 1]) if "--tilt" in a else 0.0
    pivot = float(a[a.index("--pivot") + 1]) if "--pivot" in a else 800.0
    skew = float(a[a.index("--skew") + 1]) if "--skew" in a else 1.0
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    out = apply_tilt(y, sr, tilt_db, pivot, skew)
    out *= orig_rms / max(float(np.sqrt((out ** 2).mean())), 1e-12)  # RMS-match (fair A/B)
    peak = float(np.abs(out).max())
    if peak >= 0.999:
        th = 0.95
        m = np.abs(out) > th
        out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
        if float(np.abs(out).max()) > 0.99:
            out = out * 0.99 / float(np.abs(out).max())
    wavfile.write(dst, sr, out.astype(np.float32))
    print(f"tilt {tilt_db:+.2f} dB @ {pivot:.0f} Hz (skew {skew:.2f}) -> {dst} "
          f"rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")


if __name__ == "__main__":
    main()
