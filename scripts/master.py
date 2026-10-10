#!/usr/bin/env python3
"""One entry point for mastering: [deess+harsh] -> [EQ] -> [dyneq] -> [translate] -> [ref] -> [multiband/comp] -> [color] -> [mono] -> clip -> makeup -> limit -> verify -> [dither16].
Usage: master.py <in.wav> <out.wav> --lufs -14 --tp -1.0 [--dehum 50] [--eq | --lpeq] [--clip N] [--deess] [--harsh] [--dyneq] [--translate] [--ref REF.wav --refamt 0.6] [--multiband] [--comp] [--color pultec|tape15|tube|transformer] [--transient A] [--mono 200 --width 1.1 | --sidehpf 90] [--dither16] [--qc]
Chain order = doctrine (deess+harsh first, translation before dynamics, clipper before limiter, dither last, 16-bit only).
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
    do_deess = "--deess" in a
    do_harsh = "--harsh" in a
    do_translate = "--translate" in a
    do_dyneq = "--dyneq" in a
    do_comp = "--comp" in a
    mono_f = float(a[a.index("--mono") + 1]) if "--mono" in a else 0.0
    sidehpf = float(a[a.index("--sidehpf") + 1]) if "--sidehpf" in a else 0.0
    width = float(a[a.index("--width") + 1]) if "--width" in a else 1.0
    do_dither = "--dither16" in a
    do_mb = "--multiband" in a
    color = a[a.index("--color") + 1] if "--color" in a else ""
    ref_p = a[a.index("--ref") + 1] if "--ref" in a else ""
    refamt = float(a[a.index("--refamt") + 1]) if "--refamt" in a else 0.6
    dehum_f = float(a[a.index("--dehum") + 1]) if "--dehum" in a else 0.0
    do_lpeq = "--lpeq" in a
    transient_a = float(a[a.index("--transient") + 1]) if "--transient" in a else None
    do_qc = "--qc" in a
    from scipy.io import wavfile
    y, sr = load(src)
    if dehum_f > 0:  # repair first (DC + mains hum), before any tonal/dynamics work
        from scipy import signal as _sh
        y = y - y.mean(axis=0)
        for h in range(1, 5):
            f0 = dehum_f * h
            if f0 >= sr / 2 * 0.95:
                break
            b, aa = _sh.iirnotch(f0, 15.0, fs=sr)
            for c in range(y.shape[1]):
                y[:, c] = _sh.lfilter(b, aa, y[:, c])
        print(f"dehum: DC removed + {dehum_f:.0f}Hz x4 notch")
    if do_deess:
        from deesser import bandpass, detect_env, gr_from_env
        import numpy as _np
        F0, Q, RNG, RATIO = 7000.0, 1.8, 2.5, 3.0
        bands = _np.empty_like(y)
        for c in range(y.shape[1]):
            bands[:, c] = bandpass(y[:, c], sr, F0, Q)
        brms = float(_np.sqrt((bands ** 2).mean()))
        import numpy as _n2
        thresh = 20 * _n2.log10(max(brms, 1e-9)) + 12.0
        for c in range(y.shape[1]):
            env = detect_env(bands[:, c], sr)
            gr = gr_from_env(20 * _n2.log10(_n2.maximum(env, 1e-9)), thresh, RATIO, RNG)
            g = 10 ** (-gr / 20)
            from scipy import signal as _ss
            hip = _ss.sosfilt(_ss.butter(2, max(F0 * 0.8, 20.0), btype="highpass", fs=sr, output="sos"), y[:, c])
            y[:, c] = (y[:, c] - hip) + hip * g
        print(f"deess: split-shelf {F0:.0f}Hz range {RNG}dB applied (first insert)")
    if do_harsh:
        from harshness import find_resonances
        from deesser import bandpass as _bp, detect_env as _de, gr_from_env as _gr
        import numpy as _nh
        hpeaks, hscore, _ = find_resonances(src, 2000.0, 8000.0, 3, 8.0)
        if hpeaks:
            for _, hf0 in hpeaks:
                det = _nh.zeros(len(y))
                for c in range(y.shape[1]):
                    det += _bp(y[:, c], sr, hf0, 2.5) / y.shape[1]
                henv = _de(det, sr, attack=0.005, release=0.12)
                hdb = 20 * _nh.log10(_nh.maximum(henv, 1e-9))
                hth = float(hdb.max()) - 8.0
                hgr = _gr(hdb, hth, 3.0, 2.0)
                hg = 10 ** (-_nh.minimum(hgr, 4.0) / 20)
                for c in range(y.shape[1]):
                    hb = _bp(y[:, c], sr, hf0, 2.5)
                    y[:, c] = (y[:, c] - hb) + hb * hg
            print(f"harsh: {len(hpeaks)} peaks score {hscore} tamed (dynamic, post-deess)")
        else:
            print(f"harsh: no resonances >=8dB (score {hscore}) — skipped")
    if do_lpeq:  # linear-phase variant of the skill-default chain (standard mastering EQ mode)
        from linear_phase_eq import process_channel
        _bands = [(90, 0.8, 1.0), (150, -1.5, 1.2), (270, -3.5, 0.9), (3200, 2.0, 0.9)]
        _hs = [(10500, 2.5)]
        for c in range(y.shape[1]):
            y[:, c] = process_channel(y[:, c], sr, 28.0, _bands, [], _hs, 50.0)
        print("eq: skill-default chain applied (LINEAR phase)")
    elif do_eq:
        from scipy import signal
        from eq_demo import CHAIN, rbj_peak, rbj_hshelf
        sos_hp = signal.butter(4, 28, btype="highpass", fs=sr, output="sos")
        for c in range(y.shape[1]):
            y[:, c] = signal.sosfilt(sos_hp, y[:, c])
            for kind, f0, g, q in CHAIN:
                b, bb = rbj_peak(f0, g, q, sr) if kind == "peak" else rbj_hshelf(f0, g, sr, q)
                y[:, c] = signal.lfilter(b, bb, y[:, c])
        print("eq: skill-default chain applied (minimum phase)")
    if ref_p:
        from ref_match import shares, KEYS, CENTERS
        from eq_demo import rbj_peak as _rp, rbj_hshelf as _rhs
        from scipy import signal as _sg
        ms, _, _, _ = shares(src)
        rs, _, rroll, _ = shares(ref_p)
        _, _, mroll, _ = shares(src)
        for k, f0 in zip(KEYS, CENTERS):
            delta = 10 * __import__("numpy").log10(max(rs[k], 1e-9) / max(ms[k], 1e-9))
            app = delta * refamt
            if k == "sub 20-60" and app < -1.0:
                app = -1.0
            if k == "air 12k+" and rroll < 16000 and mroll > 18000:
                app = 0.0
            if k == "mud 150-400" and abs(delta) < 1.0:
                app = 0.0
            app = max(-2.5, min(2.5, app))
            if abs(app) < 0.05:
                continue
            for c in range(y.shape[1]):
                if k == "air 12k+":
                    b, bb = _rhs(12000, app, sr, 0.7)
                else:
                    b, bb = _rp(f0, app, 1.0, sr)
                y[:, c] = _sg.lfilter(b, bb, y[:, c])
        print(f"ref: tonal match vs {ref_p} @ {refamt} (tonal only, RMS kept)")
    if do_dyneq:
        from dynamic_eq import tick_shares, correction_curves, apply_dynamic, dyn_stats
        _ticks = tick_shares(y.mean(axis=1), sr)
        _curves, _ = correction_curves(_ticks)
        _rep, _ = dyn_stats(_ticks, _curves)
        y = apply_dynamic(y, sr, _curves)
        print(f"dyneq: {len(_ticks)} ticks whole-song dynamic ({_rep})")
    if do_translate:
        from translate import translate_array
        y, tsub0, tsub1, tbody, ttrim = translate_array(y, sr)
        print(f"translate: sub {tsub0:.1f}%->{tsub1:.1f}% body {tbody:+.2f}pp (ghost parallel)")
    if do_mb:
        from multiband import split_bands, comp_band
        import numpy as _nmb
        mono = y.mean(axis=1)
        parts = split_bands(mono, sr)
        from multiband import BANDS as _MB
        tot = []
        for (lo, hi, ratio, atk), b in zip(_MB, parts):
            o, g, th = comp_band(b, sr, ratio, atk)
            tot.append(o)
        wet = _nmb.sum(tot, axis=0)
        denom = _nmb.sum(parts, axis=0)
        g = _nmb.ones_like(wet)
        nz = _nmb.abs(denom) > 1e-4  # floor: avoid gain spike in quiet gaps
        g[nz] = wet[nz] / denom[nz]
        g = _nmb.clip(g, 10 ** (-6 / 20), 10 ** (6 / 20))  # +/-6dB ride cap
        y = y * g[:, None]
        print("multiband: 4-band glue applied")
    if clip_db > 0:  # clip FIRST: makeup is measured after shaving, like a real chain
        from limiter import soft_clip
        y, shaved = soft_clip(y, clip_db)
        print(f"clip: soft-clip shaved {shaved} dB before limiting")
    if do_comp:
        from glue_comp import compress
        y, maxgr, thresh = compress(y, sr)
        print(f"comp: glue ratio 2.5 attack 30ms release 250ms thresh {thresh:.1f}dB maxGR {maxgr:.2f}dB")
    if color:
        from vintage_color import tone, saturate
        import numpy as _nv
        toned = tone(y, sr, color, 0.5)
        sat = saturate(toned / max(float(_nv.abs(toned).max()), 1e-9) * 0.9, 0.5, color)
        sat *= float(_nv.sqrt((toned ** 2).mean())) / max(float(_nv.sqrt((sat ** 2).mean())), 1e-12)
        y = toned * 0.5 + sat * 0.5
        print(f"color: vintage {color} drive 0.5 mix 0.5 (parallel)")
    if transient_a is not None:  # punch shaping before the limiter (transient designer)
        from transient import shape
        for c in range(y.shape[1]):
            y[:, c] = shape(y[:, c], sr, transient_a, 0.0)
        print(f"transient: attack {transient_a:+.1f} dB")
    if (mono_f > 0 or sidehpf > 0) and y.shape[1] == 2:
        from stereo_tool import process
        y = process(y, sr, mono_f, width, sidehpf)
        print(f"stereo: {'sidehpf<%dHz' % sidehpf if sidehpf > 0 else 'mono<%dHz' % mono_f} width={width}")
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
    if do_dither:
        import numpy as _npd
        rng = _npd.random.default_rng(0)
        tpdf = rng.random(out.shape) - rng.random(out.shape)
        out = _npd.clip(_npd.round((out + tpdf / 32768.0) * 32768.0), -32768, 32767).astype(_npd.float32) / 32768.0
        print("dither: TPDF 2LSB to 16-bit grid (last, CD only)")
        wavfile.write(dst, sr, (out * 32768.0).astype("int16"))
    else:
        wavfile.write(dst, sr, out.astype("float32"))
    print(f"wrote {dst} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")
    if do_qc:
        from qc_report import analyze
        r = analyze(dst, want, tp_t)
        print(f"QC: I {r['integrated_lufs']} LUFS  LRA {r['lra']}  TP {r['true_peak_dbtp']} dBTP  "
              f"PSR {r['psr']}  corr(min) {r['corr_min']}  mono-loss {r['mono_loss_db']:+}dB  "
              f"verdict {'PASS' if r['pass'] else 'REVIEW'}")


if __name__ == "__main__":
    main()
