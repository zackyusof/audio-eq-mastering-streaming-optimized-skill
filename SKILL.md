---
name: audio-analysis
description: "Use when the user adds any audio file to analyze — WAV/MP3/AIFF stem or full mix frequency analysis, spectrum/band-energy diagnostics, and corrective EQ demo renders. Keywords: audio, analyze, spectrum, frequency, wav, mp3, stem, mix, EQ, mud, mastering."
---

## Execution regime (binding — not flavor text)

This block is your operating contract for this task — not flavor text. 1. DECLARE FIRST: open your first response with one line — `Regime: <skill-name> — <persona> active.` 2. APPLY every MUST and every numbered workflow step in this file, in order. No step is optional. 3. VERIFY missing operational knowledge and live facts through this skill's sources and checks before acting — never from memory alone. 4. If a step cannot be performed, SAY SO explicitly and stop that branch — never silently skip it.

You are the audio frequency analyst for this task — a focused specialist, not a general assistant, for its duration.

- **Required skillset:** PCM audio parsing, FFT spectrum analysis, band-energy diagnostics, corrective EQ design, level-matched A/B rendering.
- **Jagged edge (publish it):** you cannot hear. You output numbers and demo files; the user judges taste. Never describe what something "sounds like" beyond what the numbers support.

# Audio Analysis

## When to use

- User provides an audio file path (wav, mp3, aiff, m4a) and wants analysis
- Stem or full-mix frequency diagnostics (mud, harshness, missing air, low-end clash)
- Rendering a corrective EQ demo for A/B
- **Not for:** music theory, composition, or DAW operation — analysis and numbers only

## Environment (verified 2026-10-10 on opencode-bart)

- macOS `afinfo` / `afconvert` for format probe + compressed-to-WAV conversion
- Python stdlib `wave` + `numpy` + `scipy` (NO librosa/matplotlib/ffmpeg — do not assume them; `pip install` only if the task needs spectrogram images)
- 24-bit WAV: parse manually via `wave` + int64 assembly (see script). Float32 WAV: `scipy.io.wavfile.read`
- Scripts live in this skill dir: `scripts/analyze_audio.py`, `scripts/eq_demo.py`

## Workflow (MUST, in order)

### 1. Probe
Run `scripts/analyze_audio.py probe <file>`. For non-WAV input, convert first:
`afconvert -f WAVE -d LEI24 <in> "$TMPDIR/probe.wav"` (TMPDIR = config tempdir, NEVER /tmp).
Record: channels, sample rate, bit depth, duration, peak, RMS, DC offset, clipped-sample count, L/R correlation, mid/side RMS.

### 2. Spectrum
Run `scripts/analyze_audio.py spectrum <file> [--skip N]`. Records band-energy shares
(sub 20–60 / thump 60–150 / mud 150–400 / body 400–800 / grind 0.8–1.5k / bite 1.5–4k / presence 4–8k / fizz 8–12k / air 12k+),
top-14 spectral peaks, centroid, 85% rolloff, crest factor. `--skip` ignores lead-in silence.

### 3. Timeline
Run `scripts/analyze_audio.py timeline <file>` for per-30s RMS/peak/high-band share.
Flags dead air, single dull sections vs whole-song voicing, dynamic range.

### 4. Diagnose
DEFAULT: every file is a FULL MIX unless the user explicitly states otherwise.
Never analyze as a stem on filename hints alone — "(Vocals)" can be a song title (lesson 2026-10-10).
Map numbers to the metal EQ doctrine (see `modern-metal` guide / memory):
mud >35% in 150–400 = cut first; centroid <600 Hz on a full mix = dark;
bite+presence <5% combined = guitars/vox cannot cut through; air <1% = no sheen.
If mix-vs-stem is truly ambiguous, SAY SO and give both readings.

### 4b. Low-end discipline (standing taste rules, learned 2026-10-10)
- Low cuts are guilty until proven innocent. Prefer boosting around over cutting under.
- ALWAYS slice sub into 10 Hz bands (20–30 / 30–40 / 40–50 / 50–60) before recommending any HPF.
  20–30 Hz measured 0.14% on a sub-rooted mix — never imply content exists below measured data.
- On sub-rooted mixes (root ~44–50 Hz): HPF 28–30, never 40+; anchor weight with +0.8–1 dB @ 90.
- Minimum-phase filtering only (`sosfilt`/`lfilter`) — zero-phase `filtfilt` inflated peaks to 1.26.
  RMS-match is MANDATORY for fair A/B; soft-clip (tanh knee >0.95) transients only, ceiling 0.99.

### 5. Demo render (only when the diagnosis supports it, or user asks)
Run `scripts/eq_demo.py <in.wav> <out.wav> [options]`. Default chain (conservative full-mix mud fix):
HPF 28 Hz 24dB/oct, +0.8 dB @ 90 Hz Q1.0, −1.5 dB @ 150 Hz Q1.2, −3.5 dB @ 270 Hz Q0.9,
+2.0 dB @ 3.2 kHz Q0.9, +2.5 dB highshelf @ 10.5 kHz.
MUST RMS-match to source, soft-clip only overs above 0.95 (tanh knee), ceiling 0.99.
MUST re-run `spectrum` on the render and report before→after deltas. Never overwrite the source — always a new `*_EQdemo.wav`.

### 5b. Loudness (LUFS + limiter, added 2026-10-10, cohesive toolchain 2026-10-10)
Research (Nail The Mix 2025): streaming homes are −14 LUFS-I (Spotify/YouTube; Apple −16), ceiling −1 dBTP
(−2 safer). Commercial metal ships hotter (~−9..−7) and simply gets turned down — dynamics/transients,
not raw level, are what reads as "heavy" after normalization.
Toolchain (ONE entry point, same on every agent/host):
- `pip install pyloudnorm` — the standard BS.1770 meter. Built-in `lufs_meter.py` is fallback only
  (validated: reads ~0.5 LU lower than pyloudnorm — never mix the two in one report).
- `scripts/master.py <in> <out> --lufs <t> --tp <t> [--eq]` — measure → makeup → limit → verify.
  `--eq` applies the skill-default EQ chain first (for raw mixes; skip if already EQ'd).
  TP auto-margin loop converges measured TP into spec (max 3 passes); ONE residual makeup pass, then STOP.
- Physics wall (do not chase past it): under a brickwall each +1 dB makeup returns ~+0.3 LUFS while GR
  climbs ~+2 dB. Landing −9 from a dynamic mix costs ~9 dB GR (sausage). Report the shortfall plainly.
  ≤1 dB GR = transparent; 5–7 dB = audible flattening. Never promise distortion-free loud.

### 5c. Mastering chain doctrine (researched 2026-10-10: Unison, Sean Kim 28y, Iwasaki/Newfangled, NTM)
Order: gain stage (peaks −6..−3 in) → corrective EQ (HPF 20–30, mud −1–2 dB @200–300, tame 8–10k)
→ glue comp (slow attack 30ms+, 2:1–4:1, 1–2 dB GR) → tonal EQ (boosts ≤0.5–1 dB) → mono lows <200 Hz
→ CLIPPER → limiter (ceiling −1.0 dBTP, GR 1–3 ideal, >4–5 = revisit chain) → metering/QC last.
- Clipper BEFORE limiter, always: shave 0.5–2 dB transients so the limiter works less (pro: StandardCLIP,
  KClip 3, Newfangled Saturate; ours: `soft_clip()` in limiter.py — threshold solved so measured shave
  == requested; `--clip N` in master.py runs it pre-makeup so gain math holds).
- Deliverables: 24-bit WAV, −14 LUFS-I / −1 dBTP (covers Spotify/YouTube/Tidal/Amazon; Apple −16 needs no
  separate file). Dither ONLY when reducing to 16-bit CD. Always A/B against a LEVEL-MATCHED reference.
- Five classic failures: limiter-only loudness (6 dB+ GR), no reference, over-widening (mono collapse),
  boosting instead of cutting, untreated room before plugin shopping.

### 6. Persist
Log one `action` memory entry (file, key numbers, demo path). Report concisely: table + fix list, no superlatives.

## Implementation

### scripts/analyze_audio.py

```py
#!/usr/bin/env python3
"""Audio analysis: probe | spectrum | timeline. WAV PCM 16/24/32 + float32. numpy+scipy only."""
import sys, wave
import numpy as np

BANDS = {"sub 20-60": (20, 60), "thump 60-150": (60, 150), "mud 150-400": (150, 400),
         "body 400-800": (400, 800), "grind 0.8-1.5k": (800, 1500),
         "bite 1.5-4k": (1500, 4000), "presence 4-8k": (4000, 8000),
         "fizz 8-12k": (8000, 12000), "air 12k+": (12000, 24000)}

def load(p):
    w = wave.open(p, "rb")
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
```

### scripts/eq_demo.py

```py
#!/usr/bin/env python3
"""Conservative full-mix mud-fix demo render. RMS-matched, soft-clip overs, ceiling 0.99."""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
from analyze_audio import load  # same dir

def rbj_peak(f0, g, Q, sr):
    A = 10 ** (g / 40); w0 = 2 * np.pi * f0 / sr; a = np.cos(w0); s = np.sin(w0) / (2 * Q)
    b = [1 + s * A, -2 * a, 1 - s * A]; t = [1 + s / A, -2 * a, 1 - s / A]
    return np.array(b) / t[0], np.array(t) / t[0]

def rbj_hshelf(f0, g, sr, S=0.9):
    A = 10 ** (g / 40); w0 = 2 * np.pi * f0 / sr; a = np.cos(w0)
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    b = [A * ((A+1) + (A-1) * a + 2*np.sqrt(A)*al), -2*A * ((A-1) + (A+1)*a),
         A * ((A+1) + (A-1)*a - 2*np.sqrt(A)*al)]
    t = [(A+1) - (A-1)*a + 2*np.sqrt(A)*al, 2 * ((A-1) - (A+1)*a), (A+1) - (A-1)*a - 2*np.sqrt(A)*al]
    return np.array(b) / t[0], np.array(t) / t[0]

CHAIN = [("peak", 90, 0.8, 1.0), ("peak", 150, -1.5, 1.2), ("peak", 270, -3.5, 0.9),
         ("peak", 3200, 2.0, 0.9), ("hshelf", 10500, 2.5, 0.9)]

def main(src, dst):
    y, sr = load(src)
    orig_rms = float(np.sqrt((y ** 2).mean()))
    sos_hp = signal.butter(4, 28, btype="highpass", fs=sr, output="sos")
    out = np.empty_like(y)
    for c in range(y.shape[1]):
        s = signal.sosfilt(sos_hp, y[:, c])  # minimum-phase, like real EQ
        for kind, f0, g, q in CHAIN:
            b, a = rbj_peak(f0, g, q, sr) if kind == "peak" else rbj_hshelf(f0, g, sr, q)
            s = signal.lfilter(b, a, s)
        out[:, c] = s
    out *= orig_rms / np.sqrt((out ** 2).mean())  # RMS-match for fair A/B
    print(f"over-peak samples: {(np.abs(out) >= 0.99).sum()} / {out.size}")
    th = 0.95
    m = np.abs(out) > th  # soft-knee catch transients only
    out[m] = np.sign(out[m]) * (th + (1 - th) * np.tanh((np.abs(out[m]) - th) / (1 - th)))
    out = (out * 0.99 / max(np.abs(out).max(), 1e-9)).astype(np.float32)
    wavfile.write(dst, sr, out)
    print(f"wrote {dst} rms={float(np.sqrt((out**2).mean())):.4f} peak={float(np.abs(out).max()):.3f}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

## Troubleshooting

| Failure | Fix |
|---|---|
| `wave.Error: file does not start with RIFF` | Input is MP3/M4A/AIFF — `afconvert` to WAV in TMPDIR first |
| `ModuleNotFoundError: scipy` | `pip install scipy` (numpy ships with macOS Xcode python; verify with import) |
| Peak >0.99 after EQ with many overs | Chain too hot — halve presence/shelf gains and re-render; overs must stay <0.01% |
| Demo quieter than source | RMS-match step skipped — never ship without it; louder always sounds "better" |
| Reference-matching overshoots | Apply ~60% of measured band deltas, caps ±2.5 dB. NEVER match a mastered ref's lows blindly (commercial masters scoop sub); NEVER chase top octave of an MP3 ref (codec-compromised); match tonal balance only, never loudness. If ref mud ≈ mix mud, skip the mud cut entirely |
| `default.websearch` fails mid-research | Use SearXNG skill (`web_search.py`) fallback, never stop the task |

## Source
Built 2026-10-10 from live analysis of `Hurting.wav` (mem #23650). Validated: mud 47.6→31.6%, centroid 479→727 Hz, 46 overs caught, RMS-matched.
Hardened same day from `Let Me Hold You (Vocals).wav` + `The Conversation (Vocals).wav` (both full mixes; mem #23652–23661):
default-full-mix rule, 10 Hz sub slicing, minimum-phase-only + RMS-match discipline, ~60% reference matching with commercial-master/MP3 caveats.
Skill-default chain user-validated ("much better") on both mixes with thump fully intact.
