#!/usr/bin/env python3
"""Audio analysis: probe | spectrum | timeline. WAV PCM 16/24/32 + float32. numpy+scipy only."""
import sys, wave
import numpy as np

BANDS = {"sub 20-60": (20, 60), "thump 60-150": (60, 150), "mud 150-400": (150, 400),
         "body 400-800": (400, 800), "grind 0.8-1.5k": (800, 1500),
         "bite 1.5-4k": (1500, 4000), "presence 4-8k": (4000, 8000),
         "fizz 8-12k": (8000, 12000), "air 12k+": (12000, 24000)}

def load(p):
    try:
        w = wave.open(p, "rb")
    except wave.Error:
        # non-PCM WAV (e.g. Float32 demo renders) -> scipy fallback
        from scipy.io import wavfile
        sr, d = wavfile.read(p)
        y = np.atleast_2d(d.astype(np.float64).T).T
        if np.issubdtype(d.dtype, np.integer):
            y = y / float(2 ** (8 * d.dtype.itemsize - 1))
        return y, sr
    nch, sw, sr, nfr = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(nfr); w.close()
    if sw == 3:  # 24-bit LE manual assembly
        x = np.frombuffer(raw, dtype=np.uint8).reshape(-1, nch, 3)
        v = (x[:, :, 0].astype(np.int64) | (x[:, :, 1].astype(np.int64) << 8) | (x[:, :, 2].astype(np.int64) << 16))
        v = np.where(v >= 0x800000, v - 0x1000000, v)
        y = v.astype(np.float64) / 0x800000
    else:
        dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
        y = np.frombuffer(raw, dtype=dt).reshape(-1, nch).astype(np.float64) / float(2 ** (8 * sw - 1))
    return y, sr

def avg_power(mono, sr, N=32768, stride=4):
    P = np.zeros(N // 2 + 1); han = np.hanning(N); n = 0
    for s in range(0, len(mono) - N, N * stride):
        P += np.abs(np.fft.rfft(mono[s:s + N] * han)) ** 2; n += 1
    return P / max(n, 1), np.fft.rfftfreq(N, 1 / sr)

def cmd_probe(p):
    y, sr = load(p)
    L, R = y[:, 0], y[:, -1] if y.shape[1] > 1 else (y[:, 0], y[:, 0])
    mid, side = (L + R) / 2, (L - R) / 2
    print(f"ch={y.shape[1]} sr={sr} dur={len(y)/sr:.1f}s")
    print(f"peak={np.abs(y).max():.3f} rms={np.sqrt((y**2).mean()):.4f} "
          f"crest={20*np.log10(np.abs(y).max()/np.sqrt((y**2).mean())):.1f}dB")
    print(f"dc={y.mean(axis=0)} clip>=0.999: {(np.abs(y) >= 0.999).sum()}")
    print(f"rms L/R/M/S={[float(np.sqrt((c**2).mean())) for c in (L, R, mid, side)]}")
    if y.shape[1] > 1:
        print(f"corr L-R={float(np.corrcoef(L[::97], R[::97])[0, 1]):.3f}")

def cmd_spectrum(p, skip=0):
    y, sr = load(p)
    mono = y.mean(axis=1)[int(skip * sr):]
    P, fr = avg_power(mono, sr)
    tot = P.sum()
    for k, (a, b) in BANDS.items():
        m = (fr >= a) & (fr < b)
        print(f"{k:16s} {P[m].sum()/tot*100:5.2f}%")
    sm = np.convolve(10 * np.log10(P + 1e-18), np.ones(25) / 25, mode="same")
    cands = sorted(((sm[i], fr[i]) for i in range(2, len(sm) - 2)
                    if sm[i] > sm[i-1] and sm[i] >= sm[i+1] and fr[i] > 30), reverse=True)
    import math
    picked = []
    for _, f in cands:
        if all(abs(math.log(f / q, 2)) > 0.12 for q in picked):
            picked.append(f)
        if len(picked) >= 14:
            break
    print("peaks Hz:", [round(f) for f in sorted(picked)])
    print("centroid:", round(float((fr * P).sum() / tot)),
          "rolloff85:", round(float(fr[np.searchsorted(np.cumsum(P) / tot, 0.85)])))

def cmd_timeline(p, step=30):
    y, sr = load(p)
    mono = y.mean(axis=1); N = 32768
    print("sec  rms_db  peak  hi%>2k")
    for t in range(0, int(len(mono) / sr), step):
        s = mono[t*sr:(t+1)*sr][:step*sr]
        if len(s) < N:
            break
        P, fr = avg_power(s, sr, stride=2)
        hi = P[fr >= 2000].sum() / P.sum() * 100
        print(f"{t:3d}  {20*np.log10(np.sqrt((s**2).mean())+1e-12):6.1f}  {np.abs(s).max():.2f}  {hi:5.2f}")

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "probe": cmd_probe(sys.argv[2])
    elif c == "spectrum": cmd_spectrum(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0)
    elif c == "timeline": cmd_timeline(sys.argv[2])
    else: sys.exit("usage: analyze_audio.py {probe|spectrum [skip]|timeline} <file.wav>")
