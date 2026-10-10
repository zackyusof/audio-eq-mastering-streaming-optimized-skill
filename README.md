# Audio EQ Mastering — Streaming Optimized

Balance any stereo mix with FFT spectrum diagnostics, then master it to streaming loudness
standards (−14 LUFS / −1.0 dBTP) through a full modern mastering chain — corrective/linear-phase
EQ, dynamic EQ, de-ess, harshness taming, M/S, glue compression, clipper, limiter, dither, QC —
all from the command line, all reproducible, all verified by re-measurement.

Originally an [OpenCode](https://opencode.ai) skill (`SKILL.md` included) — the Python scripts
stand alone anywhere Python runs. **27 scripts**, one entry point (`master.py`).

> This tool **cannot hear.** It outputs numbers and renders; taste calls stay with you.

## What it does

| Group | Modules |
|---|---|
| **Analysis** | `analyze_audio.py` (probe / 9-band spectrum / timeline), `stem_space.py` (aligned-stem overlap and chosen EQ/pan), `perceived.py` (Fletcher‑Munson / ISO 226 ear-weighted), `anti_alias.py` (aliasing / oversampling diagnostic) |
| **Tonal** | `eq_demo.py` (minimum-phase corrective EQ), `linear_phase_eq.py` (zero-phase / linear-phase EQ), `dynamic_eq.py` (whole-song dynamic EQ), `ref_match.py` (reference tonal match), `vintage_color.py` (Pultec/tape/tube/transformer colour) |
| **Dynamics** | `deesser.py`, `harshness.py` (dynamic 2–8 kHz resonance tamer), `glue_comp.py` (bus glue), `multiband.py` (4-band glue), `transient.py` (attack/sustain punch) |
| **Spatial** | `mid_side.py` (true M/S EQ + width + mono-below), `stereo_tool.py` (mono lows / side-HPF + width + mono check), `translate.py` (low-end translation) |
| **Level & output** | `limiter.py` (lookahead brickwall), `lufs_meter.py` (BS.1770), `dither.py` (TPDF, CD only), `export_mp3.py` (320k VBR + Xing + ID3v2.3), `xing_header.py` (repair VBR headers) |
| **QC & repair** | `qc_report.py` (delivery QC + streaming forecast), `codec_check.py` (AAC/MP3 lossy gate), `dehum.py` (DC + mains-hum notch), `spectral_repair.py` (short clicks/pops and bounded peak smoothing) |

## Requirements

- Python 3.11+ with `python3 -m pip install -r requirements.txt` (numpy and scipy for mastering; `lameenc` and `mutagen` for MP3 export). `pyloudnorm` is optional; the bundled loudness meter is the fallback.
- WAV input (PCM 16/24/32 or Float32). For MP3/M4A, convert first:
  - macOS: `afconvert -f WAVE -d LEI24 in.mp3 tmp.wav`
  - Linux/Windows: `ffmpeg -i in.mp3 -c:a pcm_s24le tmp.wav`

## Use it with your own songs

Clone this repository and run the commands from its root (the directory containing `scripts/`). Keep each album or project in a **main directory beside the clone**. Put the source stereo WAV mixes directly in that main directory; put the finished WAVs in `mastered/` and the MP3 copies in `mp3/`. These output directories must exist before running the scripts.

```text
work/
|-- audio-eq-mastering-streaming-optimized-skill/  <- run commands here
|   |-- README.md
|   `-- scripts/
`-- My Album/                                 <- main directory: source material
    |-- Track 01.wav                              <- original stereo mix
    |-- Track 02.wav
    |-- mastered/                                <- finished WAVs
    |   |-- Track 01.wav
    |   `-- Track 02.wav
    `-- mp3/                                     <- MP3 copies of finished WAVs
        |-- Track 01.mp3
        `-- Track 02.mp3
```

The `mastered/` and `mp3/` files in the picture are **results**, not files to create by hand. Start by creating the two empty directories and placing your source WAVs in `My Album/`. The scripts do not automatically discover an album or create its output directories.

From the repository root, install dependencies and process one track:

```bash
python3 -m pip install -r requirements.txt
python3 -c "from pathlib import Path; p = Path('../My Album'); (p / 'mastered').mkdir(parents=True, exist_ok=True); (p / 'mp3').mkdir(exist_ok=True)"

# Inspect the source mix.
python3 scripts/analyze_audio.py probe "../My Album/Track 01.wav"

# Master it. The first path is the source; the second is the finished WAV.
python3 scripts/master.py "../My Album/Track 01.wav" "../My Album/mastered/Track 01.wav" \
  --lufs -14 --tp -1.0 --eq --deess --harsh --dyneq --translate \
  --clip 1.0 --comp --mono 200 --qc

# Export an MP3 from the finished WAV, with your own release tags.
python3 scripts/export_mp3.py "../My Album/mastered/Track 01.wav" "../My Album/mp3/Track 01.mp3" \
  --artist "Your Artist" --album "My Album" --year 2026
```

Replace the example names and tags with yours, then repeat the last three commands for each source WAV. The MP3 title defaults to the output filename, and Composer defaults to `--artist`; add `--title` or `--composer` if either should differ. Keep the source mixes untouched so you can change the mastering settings and render again. `--eq` and the other processing switches are an example chain; listen and measure before choosing them for a release. To check a finished WAV separately, run `python3 scripts/qc_report.py "../My Album/mastered/Track 01.wav" --target -14 --tp -1.0`.

## More commands

```bash
# 1. Diagnose a mix
python3 scripts/analyze_audio.py probe mix.wav
python3 scripts/analyze_audio.py spectrum mix.wav [skip_seconds]
python3 scripts/analyze_audio.py timeline mix.wav

# 2. Full mastering chain, one command  (EQ → clip → comp → mono → limit → QC)
python3 scripts/master.py rawmix.wav final.wav --lufs -14 --tp -1.0 \
  --eq --deess --harsh --dyneq --translate --clip 1.0 --comp --mono 200 --qc

# 3. Master with linear-phase EQ + M/S + transient shaping + de-hum
python3 scripts/master.py mix.wav out.wav --lufs -14 --tp -1.0 \
  --dehum 50 --lpeq --transient 2 --mono 120 --qc

# 4. Delivery QC report (LRA, PSR, correlation, streaming forecast, PASS/FAIL)
python3 scripts/qc_report.py out.wav --target -14 --tp -1.0

# 5. Lossy-codec gate (true-peak rise + overs after AAC/MP3)
python3 scripts/codec_check.py out.wav --aac 256 --mp3 320

# 6. House MP3 + metering
python3 scripts/export_mp3.py out.wav out.mp3 --album "My Album"
python3 scripts/lufs_meter.py *.wav
```

## Choose optional processing before rendering

For a new song or batch, choose any additional stages **before** changing audio. An agent using
`SKILL.md` asks once about repair, tone, dynamics/color, space, and delivery. If you choose no
extras, it runs the existing preset: `--lufs -14 --tp -1.0 --eq --deess --harsh --dyneq
--translate --clip 1.0 --comp --mono 200` with QC. The new stages below stay off by default.

| If you need... | Explicit option | Important limit |
|---|---|---|
| Short clicks or pops | `master.py --declick` | Isolated defects up to 2 ms; inspect before/after. Longer crackle or clipping needs a different repair. |
| Gentler narrow spectral peaks | `master.py --spectral-smooth 1.5` | Attenuation only, above 500 Hz, capped at 3 dB. It can dull useful harmonics. |
| More overall stereo width | `master.py --width 1.1` | Affects the whole mix, not individual instruments; check mono compatibility. |
| Room between instruments | `stem_space.py analyze` then `render` | Needs aligned original stems. Choose the lower-priority stem and EQ/pan move; verify in the full mix. |
| Source extraction from a finished mix | External model such as [Demucs](https://github.com/facebookresearch/demucs) | Optional separate install/download; estimated stems can bleed and are not the original multitrack. |

Examples (run from the repository root; create the destination directories first):

```bash
# Repair and smooth a source mix before mastering it, or use the same flags on master.py.
python3 scripts/spectral_repair.py "../My Album/Track 01.wav" "../My Album/Track 01 repaired.wav" \
  --declick --smooth-db 1.5
python3 scripts/master.py "../My Album/Track 01.wav" "../My Album/mastered/Track 01.wav" \
  --lufs -14 --tp -1.0 --eq --deess --harsh --dyneq --translate --clip 1.0 \
  --comp --mono 200 --declick --spectral-smooth 1.5 --qc

# With original aligned stems, find collision bands; then render one chosen stem move.
python3 scripts/stem_space.py analyze "../My Album/stems/Vocal.wav" "../My Album/stems/Guitar.wav"
python3 scripts/stem_space.py render "../My Album/stems/Guitar.wav" "../My Album/stems/Guitar space.wav" \
  --cut-hz 2500 --cut-db 1.5 --q 0.9
```

Recombine the processed stem with the other stems in your DAW. `stem_space.py` reports possible
masking from simultaneous band energy; its score is not a listening verdict or a neural
source-separation metric. See [the research notes](references/spectral-space-research.md) for
the GitHub projects and method limits.

## The mastering chain (`master.py`)

Order (doctrine: repair first, clipper before limiter, dither last):

```
[dehum] → [deess → harshness] → [corrective EQ | linear-phase EQ] → [dyneq] → [translate]
        → [ref-match] → [multiband]/[glue] → [color] → [transient] → mono-lows/width
        → clipper → limiter → verify → [dither16] → [MP3] → [QC]
```

```bash
python3 scripts/master.py <in.wav> <out.wav> --lufs -14 --tp -1.0 \
  [--dehum 50] [--eq | --lpeq] [--deess] [--harsh] [--dyneq] [--translate] \
  [--ref REF.wav --refamt 0.6] [--multiband] [--comp] \
  [--color pultec|tape15|tube|transformer] [--transient 3] \
  [--mono 200 --width 1.1 | --sidehpf 90] [--clip N] [--dither16] [--qc]
```

Key defaults:

| Stage | Default |
|---|---|
| Corrective EQ | HPF 28, +0.8 @90 / −1.5 @150 / −3.5 @270 / +2 @3.2k / +2.5 shelf @10.5k |
| Linear-phase EQ | same curve, zero-phase (constant group delay), for low-end correction |
| Clipper | soft-clip shave 0.5–2 dB (requested == measured), before makeup |
| Glue comp | 2.5:1, 30 ms / 250 ms, target ~1.5 dB GR |
| Multiband | 4-band 1.6/1.5/1.2/1.1, ~1 dB/band |
| Mono lows | LR4 highpass on the side < 200 Hz (or `--sidehpf 90` for a gentler slope) |
| Limiter | lookahead brickwall, ceiling −1.0 dBTP, true-peak auto-margin loop, 1 residual LUFS pass |

## Delivery QC (`qc_report.py`, `codec_check.py`)

`qc_report.py` is the end-of-chain check (Insight‑2 class): integrated LUFS, **LRA** (EBU R128,
relative-gated), short-term profile, **PSR**, true peak, PLR/crest, stereo correlation
min/avg/max, mono-compatibility loss, M/S balance, DC offset, noise floor, a **per-platform
streaming-normalization forecast** (Spotify/YouTube/Tidal/Amazon/Deezer/Apple — the gain each
applies and whether it is peak-limited), and PASS/FAIL against a target (`--json` for machines).

`codec_check.py` is the "lossy check": encode AAC/MP3, decode, re-measure — loud/clipped masters
rise most after encoding, so it **fails on any sample overs**.

## Anti-aliasing (measured)

Oversampling is mandatory only for the **ADC/SRC anti-alias filter** (physics). For DSP it is
conditional, and the discriminator is **waveshaper vs time-varying gain** — not "nonlinear vs
linear". Measured on the bundled chain (6.2 kHz sine, +6 dB, 44.1 kHz): a tanh clipper goes
**1× −28.2 → 2× −66.6 → 4× −87.6 dB** (plateau at 4×); a hard clipper keeps paying to 16×; the
dynamics stages do **not** alias (glue comp out-of-band −154.8 dB, identical at every ratio).
So oversample the clipper / saturation / low-band tube when they work on bright material — skip
it on every dynamics/EQ stage. Measure any stage with `anti_alias.py`.

## Real session results

A 4-album, 43-track batch through the skill-default chain, RMS-matched throughout:

- All masters landed **−14.0…−14.5 LUFS-I, TP ≤ −1.07 dBTP**, limiter GR ≤ 3.3 dB (transparent).
- Corrective EQ: mud 150–400 Hz typically 16–32 % → 9–20 %, centroid lifted toward 400–800 Hz.
- `diagnose → render → re-measure` on every file; true-peak auto-margin converged on all.

## How it works

- **Spectrum:** Hanning-windowed 32k rFFT, power averaged over the track (~every 4th window),
  integrated into 9 musical bands. ~1 min per 5-minute song.
- **EQ:** minimum-phase biquads (RBJ cookbook) by default; `linear_phase_eq.py` applies the same
  curve as an **exact zero-phase magnitude** (padded FFT) when phase matters.
- **Dynamic EQ:** whole-song 2 s ticks vs the song's own median — corrects per-section, not
  per-average (cuts-only, smoothed, no pumping).
- **Loudness:** `pyloudnorm` (validated BS.1770) is the standard meter; bundled `lufs_meter.py`
  (exact K-weighting @48 kHz) is the fallback and powers LRA/PSR.
- **Limiter:** peak detection with 5 ms lookahead, release-only gain smoothing at control rate,
  tanh safety above 0.95; true peak measured 4× oversampled with an auto-widening ceiling margin.

## Doctrine (the short version)

- Files are **full mixes by default** — never analyze as stems unless told.
- **Low cuts are guilty until proven innocent**: slice sub-bass into 10 Hz bands before any HPF.
- **Cut before boosting, mirror don't stack** (kick *or* bass owns each low band, never both).
- **Reference matching:** ~60% of measured band deltas, caps ±2.5 dB; tonal balance only, never loudness.
- **Physics wall:** under a brickwall, +1 dB makeup returns ~+0.3 LUFS while GR climbs ~+2 dB.
  Report shortfalls plainly — never promise distortion-free loud.
- **Back up before any re-render; prove a fix with a before/after measurement, never "looks right."**

## Limitations (honest)

- This tool cannot hear — it outputs numbers and renders; taste calls stay with you.
- True-peak meter is 4×-approximate, not a certified meter; keep 0.2–0.3 dB extra margin.
- No stem separation / source rebalancing; no neural (IRC-style) limiter algorithms.
- Validated on rock/metal full mixes. Other genres: same workflow, different target numbers.

## As an OpenCode skill

Drop this repo (or symlink it) at `~/.config/opencode/skills/audio-analysis/` — `SKILL.md`
contains the full agent operating contract (regime, workflow, troubleshooting). Rebuild the
skill index after adding: `python3 ~/.config/opencode/scripts/build_toc.py`.

## License

MIT — use it for your own masters, commercial or otherwise. No warranty; check your renders on
monitors, headphones, a phone, and a car before release.
