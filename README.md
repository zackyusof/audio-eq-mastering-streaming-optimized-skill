# Audio EQ Mastering — Streaming Optimized

Balance any stereo mix with FFT spectrum diagnostics and a validated corrective EQ chain,
then master it to streaming loudness standards (−14 LUFS / −1.0 dBTP) with a calibrated
soft-clipper and lookahead brickwall limiter — all from the command line, all reproducible,
all verified by re-measurement.

Built from a real session: 9 full mixes analyzed, EQ'd, and mastered to −14 LUFS / −1.0 dBTP.
Originally an [OpenCode](https://opencode.ai) skill (`SKILL.md` included) — the Python scripts
stand alone anywhere Python runs.

## What it does

| Stage | What happens |
|---|---|
| **Analyze** | Averaged-FFT spectrum → energy per band (sub / thump / mud / body / grind / bite / presence / fizz / air), top spectral peaks, centroid, 85% rolloff, crest factor, stereo correlation, mid/side levels, per-section timeline |
| **EQ balance** | Conservative corrective chain: HPF 28 Hz, +0.8 dB @ 90 Hz, −1.5 dB @ 150 Hz, −3.5 dB @ 270 Hz, +2 dB @ 3.2 kHz, +2.5 dB shelf @ 10.5 kHz — RMS-matched, overs soft-caught, source never touched |
| **Clip** | Calibrated soft-clipper (0.5–2 dB) shaves transient tops so the limiter idles — requested shave == measured shave |
| **Limit / master** | Lookahead brickwall limiter with LUFS makeup gain, true-peak auto-margin loop, one residual pass, full before/after report |

## Requirements

- Python 3.11+ with `pip install -r requirements.txt` (numpy, scipy, pyloudnorm)
- WAV input (PCM 16/24/32 or Float32). For MP3/M4A, convert first:
  - macOS: `afconvert -f WAVE -d LEI24 in.mp3 tmp.wav`
  - Linux/Windows: `ffmpeg -i in.mp3 -c:a pcm_s24le tmp.wav`

## Quickstart

```bash
# 1. Diagnose a mix
python3 scripts/analyze_audio.py probe mix.wav
python3 scripts/analyze_audio.py spectrum mix.wav [skip_seconds]
python3 scripts/analyze_audio.py timeline mix.wav

# 2. Render a corrective EQ demo (RMS-matched, new file, source untouched)
python3 scripts/eq_demo.py mix.wav mix_EQdemo.wav

# 3. Master to streaming spec (-14 LUFS-I, -1.0 dBTP ceiling)
python3 scripts/master.py mix.wav mix_Master14.wav --lufs -14 --tp -1.0

# 4. Full chain in one go: EQ + soft-clip + master
python3 scripts/master.py rawmix.wav final.wav --eq --clip 1.0 --lufs -14 --tp -1.0

# 5. Meter anything
python3 scripts/lufs_meter.py *.wav
```

## Real session results

9 mixes, skill-default chain, RMS-matched throughout:

| Mix | Mud 150–400 Hz | Thump 60–150 Hz | Centroid |
|---|---|---|---|
| Mix A | 16.6 → 9.5% | intact | 447 → 591 Hz |
| Mix B | 28.5 → 17.0% | intact | 395 → 534 Hz |
| Mix C | 32.2 → 19.9% | intact | 466 → 681 Hz |

Mastering to −14/−1.0: limiter gain reduction 0–2.4 dB on 8 of 9 (transparent);
true-peak auto-margin converged on every file.

## How it works

- **Spectrum:** Hanning-windowed 32k rFFT, power averaged over the track (~every 4th window),
  integrated into 9 musical bands. Fast: ~1 min per 5-minute song.
- **EQ:** minimum-phase biquads (RBJ cookbook) + Butterworth HPF — like real analog EQ.
  Zero-phase filtering was tried and rejected (inflated peaks to 1.26).
- **Loudness:** `pyloudnorm` (validated BS.1770) is the standard meter; the bundled
  `lufs_meter.py` (exact K-weighting @48 kHz) is the fallback.
- **Limiter:** peak detection with 5 ms lookahead (`maximum_filter1d`), release-only gain
  smoothing at control rate, tanh safety above 0.95, hard ceiling 0.99.
- **True peak:** measured 4× oversampled; the limiter auto-widens its ceiling margin until
  measured TP is in spec (max 3 passes), then one residual LUFS pass, then it stops.

## Doctrine (the short version)

- Files are **full mixes by default** — never analyze as stems unless told.
- **Low cuts are guilty until proven innocent:** slice sub-bass into 10 Hz bands before
  recommending any high-pass; never imply content exists below measured data.
- **Cut before boosting, mirror don't stack** (kick *or* bass owns each low band, never both).
- **Reference matching:** apply ~60% of measured band deltas, caps ±2.5 dB; never chase a
  mastered reference's lows or an MP3's top octave; tonal balance only, never loudness.
- **Physics wall:** under a brickwall, +1 dB makeup returns ~+0.3 LUFS while GR climbs ~+2 dB.
  Report shortfalls plainly — never promise distortion-free loud.

## Limitations (honest)

- This tool **cannot hear**. It outputs numbers and renders; taste calls stay with you.
- True-peak meter is 4×-approximate, not a certified meter; keep 0.2–0.3 dB extra margin for picky distributors.
- Minimum-phase EQ only; no linear-phase, multiband, glue compression, or stereo imaging stages.
- Validated on rock/metal full mixes. Other genres: same workflow, different target numbers.

## As an OpenCode skill

Drop this repo (or symlink it) at `~/.config/opencode/skills/audio-analysis/` — `SKILL.md`
contains the full agent operating contract (regime, 6-step workflow, troubleshooting).
Rebuild the skill index after adding: `python3 ~/.config/opencode/scripts/build_toc.py`.

## License

MIT — use it for your own masters, commercial or otherwise. No warranty; check your renders on
monitors, headphones, a phone, and a car before release.
