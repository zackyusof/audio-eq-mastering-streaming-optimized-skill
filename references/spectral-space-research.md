# Spectral repair and instrument space: source review (2026-10-10)

These are research leads and design limits, not copied implementation code. The bundled scripts
use only the existing NumPy/SciPy stack and work on user-provided WAVs.

## Source extraction versus mix-space analysis

- [Demucs](https://github.com/facebookresearch/demucs) estimates vocals, drums, bass, and other
  from a finished mix using a hybrid waveform/spectrogram model. Its repository was archived in
  2025; model installation/download and current command must be verified if the user selects it.
  Estimated stems are not the original multitrack and may bleed or contain artifacts.
- [Open-Unmix](https://github.com/sigsep/open-unmix-pytorch) is a four-stem research baseline.
  [Spleeter](https://github.com/deezer/spleeter) also offers pretrained 2/4/5-stem models;
  its standard model family has a documented high-frequency limit. These are alternatives,
  not an automatic default or a warrant to process a user's full mix as separate instruments.
- [librosa HPSS](https://librosa.org/doc/latest/generated/librosa.decompose.hpss.html) uses
  spectrogram median filtering to distinguish horizontal harmonic structure from vertical
  percussive structure. HPSS does **not** label guitar, bass, vocal, or individual drums.
- [museval](https://github.com/sigsep/museval) provides source-separation evaluation metrics
  when reference stems exist. The new `stem_space.py` score is deliberately named *potential
  masking*: it is not SDR, SIR, or a perceptual quality score.

## Calculating possible collisions between provided stems

For aligned original stems, a useful first pass is time-frequency band energy, not a single
whole-song spectrum. `stem_space.py` computes short-time power in seven musical bands, then
reports each pair's coactivity, shared energy, and level balance. Its bounded score is
`overlap * coactivity * energy_share`, where overlap is twice the shared lesser energy divided
by total pair energy in active frames. This is an original screening heuristic, not a validated
auditory-masking model. It reduces false certainty by showing when two parts occupy the same
band at the same time, but cannot tell whether listeners actually lose one part. Compare the
stems, arrangement, panning, and full mix by ear. A deliberate unison can score high and be fine.

The [librosa spectral contrast implementation](https://github.com/librosa/librosa/blob/main/librosa/feature/spectral.py)
shows why peak-versus-valley structure is distinct from gross band level. [Essentia](https://github.com/MTG/essentia)
has a broader set of descriptors, but these features do not identify source ownership in a
finished mix. For space, prefer small, wide cuts in the lower-priority original stem, modest
mono-stem panning, and arrangement changes. Recombine and check in mono. A full mix can receive
global M/S width, but this cannot move its individual instruments.

## Click repair and spectral smoothing

- [Audacity Repair](https://manual.audacityteam.org/man/repair.html) is aimed at a tiny click
  or dropout with valid audio on both sides; it is unsuitable for long selections or faults at
  the boundary. The bundled declick stage follows that scope: detect short, high-contrast
  sample deviations, interpolate only bounded spans, and report how many samples changed.
- [Audacity's spectrogram click workflow](https://manual.audacityteam.org/man/click_removal_using_the_spectrogram_view.html)
  supports visual diagnosis of vertical broadband defects. The bundled detector works in the
  waveform because a short impulse is most local there; a spectrogram helps confirm the event.
- [noisereduce](https://github.com/timsainb/noisereduce) uses frequency and time-smoothed
  spectral masks for stationary and nonstationary noise. The bundled smoother is narrower:
  attenuation-only on local frequency peaks above 500 Hz, maximum 3 dB, with the original
  phase. It is not a noise-removal implementation and cannot restore missing harmonics.
- [Spotify Pedalboard](https://github.com/spotify/pedalboard) exposes EQ, reverb, delay, and
  other spatial effects. Reverb/delay can create depth but also smear a master; per-instrument
  depth is best added to stems in the mix. This skill does not auto-add reverb to a full mix.

## Execution rule

Ask once for all optional stages before any audio-changing execution. If the user chooses no
 extras, run the established mastering DSP preset. New declick, smoothing, and
width choices are explicit opt-ins; stem EQ/pan requires a named target stem, selected band,
and render path. Measure and listen before claiming improvement. Final WAV/MP3 delivery then
applies the mandatory maximum 2-second lead-in; individual stems retain their original start
so they remain aligned.
