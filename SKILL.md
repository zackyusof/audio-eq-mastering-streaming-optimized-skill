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
- Scripts live in this skill dir: `scripts/analyze_audio.py`, `scripts/eq_demo.py`, `scripts/anti_alias.py` (alias diagnostic), `scripts/linear_phase_eq.py`, `scripts/mid_side.py`, `scripts/qc_report.py`, `scripts/codec_check.py`, `scripts/dehum.py`, `scripts/transient.py`

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
- `scripts/master.py <in> <out> --lufs <t> --tp <t> [flags]` — full chain: deess+harsh → eq → dyneq → translate → ref → multiband/comp → color → mono → clip → makeup → limit → verify → dither.
  `--eq` skill-default EQ (raw mixes only); `--clip N` soft-clip pre-makeup; `--deess` split-shelf 7kHz/2.5dB first-insert;
  `--harsh` dynamic resonance tamer (2-8kHz, top-3 peaks prom≥8dB, range 2dB/peak total cap 4dB, skips clean material);
  `--dyneq` whole-song dynamic EQ (2s ticks vs song-median target, cuts-only cap 2dB, 3-tick smoothing, filter-bank gains — fixes sections, never the average; sub/thump excluded); `--translate` low-end translation (three zones: sub felt / body 60-200 heard-everywhere / 200-500 harmonics;
  sub>12% -> broad trim cap 2dB @45Hz + always lite parallel tube ghost 60-250Hz mix 0.25 for psychoacoustic bass;
  balanced tracks pass through; per-channel, RMS-match); `--clip N` pre-limiter transient shave (~1dB limGR per 0.5 clip);
  escalation: limGR >4 after clip 1.0 → clip 1.5 → max 2.0; if still >4.5, physics wall — ship + report shortfall
  plainly, offer a −15 LUFS breathing variant (a dense track: 5.7→5.1→4.7 across clip 1.0/1.5/2.0); `--ref REF.wav --refamt 0.6` tonal deltas ~60% cap ±2.5dB (sub-cap -1dB, MP3-top-octave + mud~=ref skips; tonal only, RMS kept);
  `--multiband` 4-band glue (1.6/1.5/1.2/1.1, ~1dB/band); `--comp` bus glue 2.5:1/30ms/250ms target 1.5dB;
  `--color pultec|tape15|tube|transformer` vintage box drive 0.5 mix 0.5 parallel; `--mono F` + `--width` (1.0 = off);
  `--sidehpf 90` gentler alternative to `--mono` (HPFs side channel only, keeps 90–200 Hz width);
  `--dither16` TPDF 2LSB int16, LAST, CD only.
  Standalone `dynamic_eq.py` (--tick 2.0 --cap 2.0 --csv ticks.csv; validated gated synth: mud/bite cuts track sections, verse +0.2dB, RMS identical).
  Standalone `translate.py` (validated: 23.5%sub->18.7% trim -1.72dB RMS-identical; balanced 6.7%->6.7% pass-through).
  Standalones: `deesser.py`, `glue_comp.py` (warns >3dB), `stereo_tool.py` (mono-LR4 or side-HPF mode, warns corr<0.3), `dither.py`,
  `vintage_color.py` (--flavor --drive 0-1 --mix), `multiband.py`, `ref_match.py` (--amount 0.6 --maxdb 2.5), `harshness.py` (--zone --peaks 3 --range 2.0 --prom 8),
  `export_mp3.py` — house MP3: 48kHz / 320k-ceiling VBR (q0, avg ~250k reported) / 16-bit stereo
  (`pip install lameenc`; afconvert MPG3 encode unavailable on macOS 27 — AAC path works, MP3 does not).
  **lameenc writes NO Xing/Info VBR header** (verified every setting) → players/parsers assume CBR from the
  first frame bitrate and show bogus durations (a 4:47 track as 39 min). `export_mp3.py` now injects a
  standard Xing frame (frames|bytes|TOC) losslessly after encode; `xing_header.py <file.mp3> [...]` repairs
  already-delivered files in place (no re-encode, `.bak` kept). ALWAYS verify duration after export.
  House ID3v2.3 defaults on every export (mutagen, UTF-8): Title = filename minus extension,
  Artist = the configured artist, Album = source dir name (`--album` overrides; skips generic `mp3/mastered/out` dirs),
  Year = current year verified live at runtime, AlbumArtist + Composer = the configured artist.
  Missing-field rule: empty title/album with no override = exit non-zero naming the field — ask the user,
  never ship untagged. Retag mode: `export_mp3.py <existing.mp3>` (no re-encode).
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
- Glue/stereo/dither (built 2026-10-10, validated synthetic): `glue_comp.py` 1.64dB on 1.5 target;
  `stereo_tool.py` mono<200 LR4 + width 1.15, monoloss +0.00dB, corr warn <0.3; `dither.py` TPDF int16 out.
  Full-chain synth: LUFS -14.0 TP -7.06 GR -0.0dB; CD dither path int16 verified.
- Vintage color + multiband + ref (built 2026-10-10: MusicRadar vintage survey, Unison ref doctrine, MusicGuy 4-band glue):
  `vintage_color.py` 4 flavors (pultec low-trick boost+cut 60Hz + air / tape15 18k damp + sat / tube asymmetric 2nd-harmonic / transformer iron),
  all RMS-matched peak 0.99; `multiband.py` ~1dB/band on music synth; `ref_match.py` caps enforced (±2.5, sub -1, skips verified).
  Full 8-stage chain synth: LUFS -15.6 TP -1.15 GR 8.7 (stacked-synth sausage, honestly reported).
  Lesson: never reuse `want` as a loop var in master.py — it shadows target LUFS (bug 2026-10-10, fixed → `delta`).
- Harshness (built 2026-10-10: BabyAudio/Soothe, MousePlugins/Harshmallow, CryoMix 2-5kHz doctrine — harshness≠sibilance):
  gated-resonance synth: 3100+4300Hz found exact, ON-windows cut -1.4dB / OFF untouched ±0.2dB, RMS bit-identical, score halved;
  white-noise control stays busy by design (noise IS resonances — Soothe behaves the same).
- Ceiling discipline (bug 2026-10-10, caught by harshness validation): every script normalized output UP to 0.99
  (`out * 0.99/peak`), silently breaking RMS-match whenever source peaked below 0.99. Fixed all 8 scripts to
  ceiling-only (`if peak > 0.99`). Delivered 9 masters UNAFFECTED (master.py chain was always ceiling-correct).
- Deliverables: 24-bit WAV, −14 LUFS-I / −1 dBTP (covers Spotify/YouTube/Tidal/Amazon; Apple −16 needs no
  separate file). File convention (house rule 2026-10-10): ORIGINAL filenames kept, subdir disambiguates —
  `<project>/mastered/<name>.wav` + `<project>/mp3/<name>.mp3` (house MP3 via `export_mp3.py`), never a
  `_master` suffix. Dither ONLY when reducing to 16-bit CD. Always A/B against a LEVEL-MATCHED reference.
- Five classic failures: limiter-only loudness (6 dB+ GR), no reference, over-widening (mono collapse),
  boosting instead of cutting, untreated room before plugin shopping.

### 5d. Fletcher-Munson / equal loudness (added 2026-10-10: Fletcher-Munson 1933 -> Robinson-Dadson 1956 -> ISO 226:2003, ed. 2023 equivalent; iZotope + Tonalux doctrine)
The ear is not a flat mic: ~3-4kHz ear-canal resonance = peak sensitivity (exactly our harshness zone);
lows/highs need far more SPL when quiet; contours flatten with level (85dB SPL studio ref, 83 film).
- `scripts/perceived.py <file>` — ANALYSIS ONLY: raw shares vs A-weighted (~40-phon/quiet ear, IEC exact)
  vs C-weighted (~100-phon/loud ear, exact). A-vs-C delta per band = translation forecast (big delta =
  balance moves with the listener's volume knob). Validated: Conversation master thump 49% raw -> 2% quiet-ear.
- Discipline: calibrated monitoring level; low-volume check 50-60dB (bass really there?); reference at
  70/80/90dB SPL. NEVER build inverse-EQ curves from contours (averaged lab data, not your ears — iZotope).
  K-weighting (LUFS/pyloudnorm) already covers broadcast-level loudness; A/C covers the quiet/loud ends.

### 5e. Tests + requirements (added 2026-10-10, external review feedback)
`tests/test_lufs_meter.py` (5 tests: gain-tracking, silence, 4x TP ±0.5 dB, stereo +3 dB, <40 Hz HPF) +
`tests/test_limiter_true_peak.py` (5 tests: 4x-measured ceiling, transparency, GR, soft-clip shave + 0.99 cap).
Run: `python3 tests/test_*.py` (stdlib unittest, no pytest). `requirements.txt`: numpy/scipy (+lameenc for MP3 only).

### 5f. Multi-album batches (learned 2026-10-10, 33-track parallel run: mix 9 + BOD 11 + Vol.1 11 + Vol.2 11)
- One background agent per album, identical flags, per-album LOG; agent must do the work DIRECTLY —
  forbid nested backgrounding (2/3 agents ducked out into inner runners and "completed" with nothing done).
- Watcher fallback: own-session shell loop every 2 min on `mastered/*.wav + mp3/*.mp3` counts == source counts,
  90-min timeout with partial-state report; its exit is the completion ping. Then verify per-track table from
  logs (LUFS/TP/limGR/compGR/harsh/translate/mp3avg, zero nonzero-rc) + tag readback + **duration check
  (mp3 == src, see 5g)** + freshness mtimes.
- Typical yields: harsh fires ~20% of tracks (real +8dB outliers only), translate trims only sub>12% tracks,
  limGR ≤3.8 except dense-wall tracks (see clip escalation). Album tags: Title=file, Album=src dir, Year=live.

### 5g. Duration integrity — MANDATORY gate (added 2026-10-10, from 43 MP3s shipped with wrong lengths)
Never ship an MP3 whose *reported* length is wrong. lameenc emits **no Xing/Info VBR header**, so players
and parsers assume CBR from the first frame's bitrate and show garbage durations (e.g. 4:48 track as ~39 min)
— the audio is fine, only the length metadata is wrong. Rules:
- `export_mp3.py` injects a Xing frame after encode **and hard-gates**: it re-reads the tagged MP3 and
  `sys.exit`s (deleting the file) if `|MP3 reported duration − source duration| > 0.5 s`. NEVER bypass.
- Repair already-delivered files **losslessly, no re-encode**: `python3 scripts/xing_header.py <file.mp3> [...]`
  (keeps a `.bak`). Idempotent — skips files that already have a header.
- VERIFY every export: `mutagen` `MP3(dst).info.length` must equal the source WAV length. Ground truth for an
  MP3's true length is a **frame scan** (`frames × 1152 / sr` for MPEG-1 Layer III @48k) — `afinfo`
  mis-estimates VBR and must not be trusted for duration.
- Album gate: `src wav count == mastered count == mp3 count` AND every `mp3 duration == src duration`.

### 5h. Anti-aliasing / oversampling — is it mandatory? (researched 2026-10-10: Tonalux, Gazillion, Wojcik-measured, Julius O. Smith)
Two different things share the name — do not conflate them:
- **ADC / SRC anti-alias filter (AAF):** MANDATORY, physics. Every converter and rate-change lowpasses below
  Nyquist; a signal above fs/2 that isn't filtered folds back as an inharmonic alias. Not optional, ever.
- **Oversampling a nonlinear DSP stage:** CONDITIONAL, *not* mandatory. It only helps where a nonlinearity
  generates harmonics above Nyquist that fold. Linear processes fold nothing and gain zero from it.

The split is **waveshapers vs time-varying gain** — not "nonlinear vs linear". A time-varying gain (any dynamics
process) is technically nonlinear, but its gain envelope only changes at Hz–tens-of-Hz rates, so it only creates
intermodulation sidebands that *hug each partial* — they never reach Nyquist and never fold. Only a *waveshaper*
(harmonics at integer multiples, racing past Nyquist) aliases.

| our stage | aliases? | oversample? |
|---|---|---|
| **waveshapers:** `soft_clip` / master `--clip N`, `vintage_color` (`--color`, tube/tape/transformer), `translate` low-band tube sat | YES | yes when doing real work on bright material |
| **time-varying gain (all dynamics):** `glue_comp` / `--comp`, `multiband`, `dynamic_eq`, `deesser`, `harshness` | NO | skip — pure CPU waste |
| **linear:** `eq_demo` EQ, `stereo_tool`, `dither`, `ref_match` gain, `limit()` brickwall | NO | skip |

`glue_comp` is a pure feedforward RMS→soft-knee gain, no internal saturation → no alias. It only becomes an alias
concern if a compressor carries an analog-modeled *gain cell* / internal saturation (SSL-style, tube/opto bus
comps) — ours does not.

Measured on OUR chain (`anti_alias.py`, 6.2 kHz sine +6 dB, 44.1 kHz, non-harmonic rel. total):
- tanh clipper thr=1.0: **1× −28.2 → 2× −66.6 → 4× −87.6 → 8× −87.8 dB** (+60 dB; ceiling reached at 4×)
- hard clipper (`clip`): 1× −25.5 → 8× −63.0 dB (still improving — hard corners keep paying to 16×)
- our gentle `soft_clip` @2 dB shave: 1× −48.0 → 2× −103.7 → 4× −105.5 dB (already −48 at 1× = mild by design)
- 110 Hz source: no measurable alias at any ratio → "kick safe, hi-hat not". Crossover ≈1–3 kHz source.
- `glue_comp` out-of-band (15–22 kHz energy, 1–14 kHz chirp, 6 dB GR): **slow 30/250 ms −154.8 dB, fast 1/10 ms
  −98.7 dB** — vs a tanh clipper on the same chirp at **−16.5 dB**. Confirms dynamics do not fold.

Rules: **4× default**, 8× when a hard clipper does real work, 16× only for hard corners. Enable on bright
material / full mix / master bus; skip on bass or kick alone. Drive is the real alias control — a lower `--clip`
shave means less fold. Offline rendering has no monitoring-latency downside, so OS costs only CPU (~2–4×) —
worth it. **Brighten AFTER clipping, never before** (a pre-clipper high shelf feeds the clipper its worst material).
Two nonlinear stages in series each fold the previous one's output.
GAP (open, waveshapers only): the three waveshaper stages run at native rate (no internal OS); the dynamics
stages do not need it. `anti_alias.py` verifies any stage empirically; wrap a waveshaper core in
`resample_poly(x,4,1) → process → resample_poly(...,1,4)` when it does real work on bright content. Not
mandatory at our gentle 0.5–2 dB shaves (measured −48 dB already).

`scripts/anti_alias.py [--stage clipper|hardclip|softclip] [--f0 6200] [--drive 6] [--shave 2.0] [--ratios 1,2,4,8]`
— the industry "sine test": reports folded-energy dB per oversampling ratio so "is AA needed here?" is a number, not a vibe.

### 5i. Modern-chain coverage — modules added 2026-10-10 (gap audit vs Ozone 12 + the 2026 mastering checklist)
Audited the chain against Ozone 12's module set (EQ / Dynamic EQ / Dynamics / Maximizer / Imager / Low End
Focus / Stabilizer / Clarity / Master Rebalance / Vintage suite) and the SessionFlow 2026 mastering checklist.
Already covered: EQ, dynamic EQ, de-ess, harshness (Clarity), multiband, glue comp, clipper, limiter, Imager-lite,
Vintage colour, ref-match, translate (Low-End-Focus-lite), dither, MP3 export. Built the missing stages:
- `linear_phase_eq.py` — zero-phase (linear-phase) EQ via padded FFT: EXACT magnitude (verified +5.95 dB on a
  +6 target), constant group delay, no phase smear — the standard mastering EQ mode for low-end correction
  (Ozone "Linear Phase"). Minimum-phase `eq_demo` stays the colouration default.
- `mid_side.py` — true M/S EQ: independent mid (centre: vocal/kick) and side (image) biquad chains + width +
  mono-below. Ozone's EQ/Dynamics/Imager all offer M/S; this is the routing.
- `qc_report.py` — Insight-2-class delivery QC: integrated LUFS, LRA (EBU R128, relative-gated), short-term
  profile, PSR, true peak, PLR/crest, correlation min/avg/max, mono-compat loss, M/S balance, DC, noise floor,
  per-platform streaming-normalization forecast, PASS/FAIL vs a target (`--json` for machines).
- `codec_check.py` — lossy gate: AAC (afconvert) / MP3 (lameenc) round-trip → TP rise + sample overs. Loud/clipped
  masters rise most after encoding; gate on overs.
- `dehum.py` — repair: DC removal + 50/60 Hz mains-hum notch chain (Q ~10-20 = 50/Q Hz bandwidth; higher Q too narrow).
- `transient.py` — transient shaper (attack/sustain) = the punch control Ozone splits into Low End Focus; run before the limiter.
Wired into `master.py`: `--dehum 50`, `--lpeq` (linear-phase default EQ), `--transient A`, `--qc` (end-of-chain report).
Two latent bugs found during the audit and fixed (both real, both silent):
- `multiband.py` gain ride `wet / Σbands` spiked when a band sum ≈0 in quiet gaps, then RMS-match crushed the whole
  track (peak +46 dB pre-limit before the fix). Fixed: absolute floor + ±6 dB ride cap (mirrored in master.py).
- `stereo_tool.py` / `mid_side.py` mono-below used `side − lowpass(side)`; a minimum-phase lowpass has phase lag,
  so the subtraction BOOSTED the transition ~+3 dB instead of removing lows (measured +2.5 dB @ 80 Hz). Fixed:
  apply an LR4 **highpass** to the side directly.
Intentionally NOT covered (say so, never fake): Master Rebalance (stem separation), Stabilizer, neural/IRC-style
limiter algorithms — out of scope for an offline numpy/scipy chain.
Blast radius + re-render (2026-10-10, same day): the mono-below phase bug had SHIPPED in every master of a
4-album, 43-track batch — the buggy filter made bass ~7–10 dB too WIDE
(side <300 Hz measured). All 43 re-rendered with the fixed LR4 highpass (canonical chain `--eq --deess --harsh
--dyneq --translate --clip 1.0 --comp --mono 200`), MP3s re-exported with exact per-album tags preserved;
verified 43/43 in spec (−14.0..−14.5 LUFS, TP ≤ −1.07 dBTP, MP3 durations ok). Pre-fix backup kept at
`<project>/.pre-mono-fix-backup-20261010`. Re-render discipline: recover the batch flags from the opencode log
("spawning process"), BACK UP FIRST, and prove the fix with a before/after band measurement — never trust "looks right".

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
| MP3 Album tag ≠ siblings after a project-folder rename | `export_mp3.py` derives Album from the source's parent dir; if the project dir was renamed mid-project (e.g. a project dir renamed mid-project), READ a sibling tag first and pass `--album "<exact sibling value>"` — never trust the current folder name |
| Album reported N/N but source has MORE tracks | Before declaring an album done assert `src wav count == mastered wav count == mp3 count`; a track added after the batch is silently missed (BOD logged 11/11 with a 12th source present). Recover the batch's exact flags from `~/.local/share/opencode/log/opencode.log` ("spawning process") and reuse them verbatim for a consistent sibling |
| Metallic/gritty ring over bright hats, cymbals, sibilance or a full mix after clipping/saturation | alias fold (see 5h) — measure with `anti_alias.py --stage <clipper\|hardclip\|softclip>`; lower the drive (`--clip` shave) and/or oversample the nonlinear core ×4; if brightening, do it AFTER the clipper |
| Full master blows up (huge TP, RMS collapsed) after `--multiband` on material with quiet gaps | multiband gain ride spiked on a near-zero band sum — fixed 2026-10-10 (floor + ±6 dB cap). If it recurs, lower the multiband target GR |
| "Mono below F" sounds boomy/wide instead of tight | old bug: `side − lowpass(side)` boosts lows (~+3 dB, phase lag). Fixed 2026-10-10 to an LR4 highpass on the side |
| MP3 duration shown wrong (e.g. 4:47 track reads 39 min) | lameenc emits NO Xing/Info VBR header → parsers assume CBR from the first frame bitrate. Fix: `xing_header.py <file.mp3> [...]` injects a standard Xing frame losslessly (no re-encode); `export_mp3.py` now does this automatically. Confirm with `mutagen` (`MP3(p).info.length`) — it equals the source WAV when correct. `afinfo` mis-estimates VBR too, so scan frames (frames × 1152/sr) as the ground truth |

## Source
Built 2026-10-10 from live analysis of `Hurting.wav` (mem #23650). Validated: mud 47.6→31.6%, centroid 479→727 Hz, 46 overs caught, RMS-matched.
Hardened same day from two full-mix vocal files (mem #23652–23661):
default-full-mix rule, 10 Hz sub slicing, minimum-phase-only + RMS-match discipline, ~60% reference matching with commercial-master/MP3 caveats.
Skill-default chain user-validated ("much better") on both mixes with thump fully intact.
Hardened 2026-10-10 (post-delivery audit): 5g duration-integrity gate + `xing_header.py` — lameenc emits no
VBR header, so all 43 delivered MP3s reported wrong lengths; repaired losslessly, export now self-verifies (mem #23709/#23710).
Extended 2026-10-10 (chain gap audit vs Ozone 12 + 2026 checklist): 6 new modules — `linear_phase_eq.py`,
`mid_side.py`, `qc_report.py`, `codec_check.py`, `dehum.py`, `transient.py` — wired into master.py
(`--dehum/--lpeq/--transient/--qc`) + 5i section; two latent bugs fixed (multiband gain spike, mono-below
phase trick). mem #23717–#23719.
Extended 2026-10-10: 5h anti-aliasing/oversampling research + `anti_alias.py` diagnostic — the "is AA mandatory?"
question is conditional, measured on our own chain (mem #23712). Corrected same day: the discriminator is
**waveshapers vs time-varying gain**, not "nonlinear vs linear" — dynamics (`glue_comp`/`multiband`/`dynamic_eq`/
`deesser`/`harshness`) do NOT alias (glue_comp measured −154.8 dB out-of-band); only `soft_clip`, `vintage_color`
and the `translate` low-band tube sat do (mem #23716).
