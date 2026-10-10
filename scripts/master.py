#!/usr/bin/env python3
"""One entry point for mastering: [EQ] -> makeup gain -> limit -> verify (TP auto-margin loop).
Usage: master.py <in.wav> <out.wav> --lufs -14 --tp -1.0 [--eq]
Standard meter: pyloudnorm (fallback: built-in lufs_meter, reads ~0.5 LU lower)."""
import os
import sys
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load
from limiter import limit

try:
    import pyloudnorm as pyln
    HAVE_PYLN = True
except ImportError:
    HAVE_PYLN = False


def lufs_integrated(y, sr):
    if HAVE_PYLN:
        return float(pyln.Meter(sr).integrated_loudness(y))
    from lufs_meter import measure_array
    return float(measure_array(y, sr)["lufs"])


def full_measure(y, sr):
    from lufs_meter import measure_array
    return measure_array(y, sr)


def limit_tp(base, sr, tp_t, margin0=1.0):
    """Limit with auto-margin loop until measured TP is in spec (max 3 passes)."""
    margin = margin0
    for _ in range(3):
        out, gr = limit(base, sr, ceil_db=tp_t - margin)
        m = full_measure(out, sr)
        print(f"  margin {margin:.1f} -> LUFS-I {m['lufs']} TP {m['tp']}dBTP (GR {gr}dB)")
        if m["tp"] <= tp_t:
            return out, gr, m, margin
        margin += (m["tp"] - tp_t) + 0.3
    return out, gr, m, margin


def main():
    a = sys.argv
    src, dst = a[1], a[2]
    want = float(a[a.index("--lufs") + 1]) if "--lufs" in a else -14.0
    tp_t = float(a[a.index("--tp") + 1]) if "--tp" in a else -1.0
    do_eq = "--eq" in a
    clip_db = float(a[a.index("--clip") + 1]) if "--clip" in a else 0.0
    from scipy.io import wavfile
    y, sr = load(src)
    if do_eq:
        from scipy import signal
        from eq_demo import CHAIN, rbj_peak, rbj_hshelf
        sos_hp = signal.butter(4, 28, btype="highpass", fs=sr, output="sos")
        for c in range(y.shape[1]):
            y[:, c] = signal.sosfilt(sos_hp, y[:, c])
            for kind, f0, g, q in CHAIN:
                b, bb = rbj_peak(f0, g, q, sr) if kind == "peak" else rbj_hshelf(f0, g, sr, q)
                y[:, c] = signal.lfilter(b, bb, y[:, c])
        print("eq: skill-default chain applied")
    if clip_db > 0:  # clip FIRST: makeup is measured after shaving, like a real chain
        from limiter import soft_clip
        y, shaved = soft_clip(y, clip_db)
        print(f"clip: soft-clip shaved {shaved} dB before limiting")
    m0 = full_measure(y, sr)
    print(f"before: LUFS-I {m0['lufs']} TP {m0['tp']}dBTP crest {m0['crest']}dB")
    step = max(min(want - (lufs_integrated(y, sr)), 12.0), -12.0)
    print(f"makeup {step:+.1f} dB -> LUFS {want} TP {tp_t}dBTP")
    base = y * 10 ** (step / 20)
    out, gr, m, margin = limit_tp(base, sr, tp_t)
    if (want - m["lufs"]) > 0.5:  # brickwall ate makeup -> residual compensation pass
        add = want - m["lufs"]
        print(f"residual {add:+.1f} dB -> re-run with margin {margin:.1f}")
        base = y * 10 ** ((step + add) / 20)
        out, gr, m, margin = limit_tp(base, sr, tp_t, margin0=margin)
    wavfile.write(dst, sr, out.astype(np.float32))
    print(f"wrote {dst} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")


if __name__ == "__main__":
    main()
