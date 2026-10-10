#!/usr/bin/env python3
"""Mastering QC / delivery report (the "Insight 2 + checklist" pass). numpy+scipy only.

Reports the full verification set a master passes before release:
  integrated LUFS, LRA (EBU R128, relative-gated), short-term profile, PSR,
  true peak (4x) + sample peak, PLR/crest, stereo correlation (min/avg/max),
  mono-compatibility loss, M/S balance, DC offset, approx noise floor,
  streaming-normalization forecast per platform, and PASS/FAIL vs a target.

Usage: qc_report.py <file.wav> [<file2.wav> ...] [--target -14] [--tp -1.0] [--json]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from analyze_audio import load
from lufs_meter import k_weight, block_loudness

# platform: (playback LUFS target, true-peak ceiling dBTP, boosts-quiet?)
PLATFORMS = {
    "Spotify": (-14.0, -1.0, True),
    "YouTube": (-14.0, -1.0, False),
    "Tidal": (-14.0, -1.0, False),
    "Amazon Music": (-14.0, -2.0, False),
    "Deezer": (-15.0, -1.0, False),
    "Apple Music": (-16.0, -1.0, True),
}


def integrated(y, sr):
    yw, srw = k_weight(y, sr)
    b = block_loudness(yw, srw, 0.400, 0.100)
    b = b[b > -70]
    if len(b) == 0:
        return -120.0
    return float(b[b > b.mean() - 10].mean())


def lra(y, sr):
    """EBU R128 / Tech 3342 loudness range: 3s ST, 1s step, relative gate -20 LU."""
    yw, srw = k_weight(y, sr)
    st = block_loudness(yw, srw, 3.0, 1.0)
    st = st[st > -70]
    if len(st) < 2:
        return 0.0, st
    integ = integrated(y, sr)
    gated = st[st > integ - 20.0]
    if len(gated) < 2:
        gated = st
    return float(np.percentile(gated, 95) - np.percentile(gated, 10)), st


def true_peak(y, sr):
    from scipy import signal
    up = signal.resample_poly(y, 4, 1, axis=0)
    return float(np.abs(up).max())


def corr_stats(y, sr):
    if y.shape[1] < 2:
        return 1.0, 1.0, 1.0
    L, R = y[:, 0], y[:, 1]
    win, hop = int(1.0 * sr), int(0.5 * sr)
    vals = []
    for s in range(0, len(L) - win + 1, hop):
        a, b = L[s:s + win][::13], R[s:s + win][::13]
        if a.std() < 1e-6 or b.std() < 1e-6:
            vals.append(1.0)
            continue
        vals.append(np.corrcoef(a, b)[0, 1])
    if not vals:
        return 1.0, 1.0, 1.0
    v = np.array(vals)
    return float(v.min()), float(v.mean()), float(v.max())


def noise_floor_db(y):
    n = int(0.1 * 48000)
    hop = max(1, n // 2)
    rms = []
    for s in range(0, max(1, len(y) - n), hop):
        rms.append(np.sqrt((y[s:s + n] ** 2).mean()))
    rms = np.array(rms)
    if len(rms) < 5:
        return -120.0
    q = np.percentile(rms, 3)  # quietest 3% -> ~ noise floor
    return float(20 * np.log10(q + 1e-12))


def analyze(path, target, tp_ceiling):
    y, sr = load(path)
    peak = float(np.abs(y).max())
    integ = integrated(y, sr)
    lrv, st = lra(y, sr)
    tpv = true_peak(y, sr)
    tp_db = 20 * np.log10(tpv + 1e-12)
    cmin, cavg, cmax = corr_stats(y, sr)
    dc = [float(c) for c in y.mean(axis=0)]

    # mono compatibility loss: mono-sum level vs mean channel level (stereo only)
    if y.shape[1] >= 2:
        m = y.mean(axis=1)
        mono_loss = 20 * np.log10((np.sqrt((m ** 2).mean()) + 1e-12) /
                                  max(np.sqrt((y ** 2).mean()), 1e-12))
        M = (y[:, 0] + y[:, 1]) / 2
        S = (y[:, 0] - y[:, 1]) / 2
        ms_bal = 20 * np.log10((np.sqrt((S ** 2).mean()) + 1e-12) / (np.sqrt((M ** 2).mean()) + 1e-12))
    else:
        mono_loss, ms_bal = 0.0, -120.0

    plr = 20 * np.log10(peak + 1e-12) - integ
    crest = 20 * np.log10(peak + 1e-12) - 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-12)
    psr = tp_db - (float(st.max()) if len(st) else integ)

    forecast = {}
    for name, (tgt, ceil, boosts) in PLATFORMS.items():
        headroom = ceil - tp_db  # dB available before hitting the platform ceiling
        want = tgt - integ
        if want > 0 and not boosts:
            applied = 0.0  # this platform never boosts a quiet master
        elif want > 0 and boosts:
            applied = min(want, max(0.0, headroom))
        else:
            applied = want  # turn down louder masters (applied < 0)
        forecast[name] = {"applied_db": round(applied, 2), "playback_lufs": round(integ + applied, 1),
                          "limited_by_peak": bool(want > 0 and boosts and headroom < want)}

    checks = {
        "tp <= ceiling": tp_db <= tp_ceiling + 1e-6,
        "integrated within ±0.5 LU of target": abs(integ - target) <= 0.5,
        "LRA >= 3 LU (dynamics present)": lrv >= 3.0,
        "corr min > 0.3 (mono-safe)": cmin > 0.3,
        "DC |offset| < 0.001": all(abs(d) < 0.001 for d in dc),
    }
    return {
        "file": path, "sr": sr, "ch": int(y.shape[1]),
        "integrated_lufs": round(integ, 1), "lra": round(lrv, 1),
        "st_min": round(float(st.min()), 1) if len(st) else None,
        "st_max": round(float(st.max()), 1) if len(st) else None,
        "psr": round(psr, 1), "plr": round(plr, 1), "crest": round(crest, 1),
        "true_peak_dbtp": round(tp_db, 2), "sample_peak_dbfs": round(20 * np.log10(peak + 1e-12), 2),
        "corr_min": round(cmin, 3), "corr_avg": round(cavg, 3), "corr_max": round(cmax, 3),
        "mono_loss_db": round(mono_loss, 2), "ms_balance_db": round(ms_bal, 1),
        "dc": [round(d, 5) for d in dc], "noise_floor_dbfs": round(noise_floor_db(y), 1),
        "streaming": forecast, "checks": checks,
        "pass": all(checks.values()),
    }


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        sys.exit("usage: qc_report.py <file.wav> [...] [--target -14] [--tp -1.0] [--json]")
    files = [x for x in a if not x.startswith("-")]
    target = float(a[a.index("--target") + 1]) if "--target" in a else -14.0
    tp_ceiling = float(a[a.index("--tp") + 1]) if "--tp" in a else -1.0
    as_json = "--json" in a
    reports = [analyze(f, target, tp_ceiling) for f in files]
    if as_json:
        print(json.dumps(reports, indent=2))
        return
    for r in reports:
        print(f"=== QC {os.path.basename(r['file'])}  ({r['sr']}Hz {'stereo' if r['ch'] == 2 else 'mono'}) ===")
        print(f"  loudness : I {r['integrated_lufs']:>6} LUFS   LRA {r['lra']:>4} LU   "
              f"ST {r['st_min']}..{r['st_max']}   PSR {r['psr']:>4} dB")
        print(f"  level    : TP {r['true_peak_dbtp']:>6} dBTP   peak {r['sample_peak_dbfs']:>5} dBFS   "
              f"PLR {r['plr']:>4} dB   crest {r['crest']:>4} dB")
        print(f"  stereo   : corr {r['corr_min']}/{r['corr_avg']}/{r['corr_max']} (min/avg/max)   "
              f"mono-loss {r['mono_loss_db']:+.2f} dB   M/S {r['ms_balance_db']:+.1f} dB")
        print(f"  hygiene  : DC {r['dc']}   noise-floor {r['noise_floor_dbfs']} dBFS")
        print("  streaming playback (after normalization):")
        for name, f in r["streaming"].items():
            note = " (peak-limited)" if f["limited_by_peak"] else ""
            print(f"    {name:13s} {f['applied_db']:+6.2f} dB -> {f['playback_lufs']:>6} LUFS{note}")
        print(f"  checks   : " + ("  ".join(f"{'PASS' if v else 'FAIL'} {k}" for k, v in r["checks"].items())))
        print(f"  VERDICT  : {'PASS' if r['pass'] else 'REVIEW'}")
        print()


if __name__ == "__main__":
    main()
