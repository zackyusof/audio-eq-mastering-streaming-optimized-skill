#!/usr/bin/env python3
"""Mastering PROFILES — named presets for master.py, modeled on documented engineer
archetypes and genre targets, with per-profile MODULE settings.

IMPORTANT / HONEST SCOPE
  These are NOT any engineer's actual chain. Real mastering chains are proprietary craft.
  Each profile is a MODEL built from what is public: credits, studio gear lists, interviews,
  stated philosophy, and PUBLISHED ENGINEERING ANALYSES (e.g. Dream Theater: A View from the
  Top of the World, 2021, mixed AND mastered by Andy Sneap; Dream Theater 2013 mixed by
  Richard Chycki on an SSL Duality) — with OUR OWN measurable targets. Style targets, not
  replications.

Usage:
  profiles.py list                 -> one line per profile
  profiles.py guide                -> "which profile should I pick?" by genre
  profiles.py show <name>          -> full detail (engineer, basis, targets, chain)
  profiles.py args <name>          -> the master.py flag tokens (for scripting)

master.py consumes them via `--profile <name>` (explicit flags still override).
Module knobs: --comp-ratio/-attack/-release/-gr, --color-drive/-mix, --deess-f0/-range, --clip.
"""

PROFILES = {
    "modern-rock": {
        "engineer": "(house baseline)",
        "genre": "modern rock",
        "basis": "Our validated house chain. Tonal target sits a little on the BASS side (-2.1 dB/oct, the "
                 "darker end of the observed house band -1.58..-2.12). Support: a mild downward (bass-forward) "
                 "balance is the accepted music/room target preference (~1 dB/oct down), and iZotope TBC ships "
                 "a 'Bass Heavy' curve. NOTE: Schedin's DiVA thesis 'Target Spectrums For Mastering' (2021) "
                 "only shows rock vs vocal-electronic differ in the low end — it does NOT recommend a "
                 "bass-leaning rock target. Repair stages (declick + dehum 50) run first as a safety net.",
        "confidence": "validated on own material",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -2.1,
                    "notes": "bass-leaning; cut 250-400, presence 2-5k"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--dehum", "50", "--eq", "--deess",
                 "--harsh", "--translate", "--clip", "1.0", "--mono", "200",
                 "--tilt-target", "-2.1"],
    },
    "preferred": {
        "engineer": "(house preferred, researched 2026-10-11)",
        "genre": "modern rock",
        "basis": "Researched consensus of current published mastering guidance (NOT house defaults): "
                 "Sean Kim 7-step chain (2025, 28y) — gain-stage peaks -6..-3 in, corrective EQ (HPF 20-30, "
                 "mud 200-300 narrow 1-2 dB, harshness 8-10 kHz), glue 30 ms+/2:1-4:1/1-2 dB GR, tonal EQ "
                 "(air shelf, low-mid warmth, presence 3-5 kHz), mono lows <200 Hz, limiter -1 dBTP at 2-3 dB "
                 "GR ideal; Music Guy Mixing master-bus (2024) — HPF 20 Hz, +250 Hz warmth, -500 Hz boxiness, "
                 "1-2 kHz energy, dynamic 4-6 kHz harshness check, 10-12 kHz air shelf, all moves <=3 dB; "
                 "MixMasterAI rock — presence 2-5 kHz, kick 60-80/snare 200/cymbal 10 k, cut 250-400 box; "
                 "streaming -14 LUFS-I / -1 dBTP. DIFFERS from the no-comp house default by intent: published "
                 "consensus keeps LIGHT glue (1-2 dB GR, inaudible as compression); the Vol. 4 squash was "
                 "limiter GR 11-20 dB, not the 0.6-0.8 dB glue. Slope -2.1 dB/oct is our house measurement, "
                 "not a published number.",
        "confidence": "high (multi-source consensus, Oct 2026)",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -2.1,
                    "notes": "researched consensus; light glue kept intentionally (see basis)"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--declick", "--dehum", "50", "--eq", "--deess",
                 "--harsh", "--dyneq", "--dyneq-cap", "1.0", "--translate", "--clip", "1.0", "--comp",
                 "--mono", "200", "--tilt-target", "-2.1"],
    },
    "gateway": {
        "engineer": "Bob Ludwig (Gateway Mastering, 1992-2023)",
        "genre": "classic / art rock, pop crossover",
        "basis": "13 Grammys; AES Gold Medal; Mastered-for-iTunes consultant. Philosophy: translation "
                 "first, preserve dynamics, never over-limit, immaculate low end. Gateway closed 2023.",
        "confidence": "high (well documented)",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -1.8,
                    "notes": "gentle limiting, wide dynamics, tight controlled lows, no clip aggression"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--eq", "--deess", "--dyneq", "--translate",
                 "--comp", "--mono", "180", "--tilt-target", "-1.8",
                 "--comp-ratio", "2.0", "--comp-attack", "40", "--comp-release", "300", "--comp-gr", "1.0",
                 "--deess-range", "2.0"],
    },
    "sterling": {
        "engineer": "Ted Jensen (Sterling Sound, since 1975)",
        "genre": "rock / metal, major-label",
        "basis": "16 Grammy-winning albums; built the first all-digital mastering console (Neve DTC-1); "
                 "Apple MFiT consultant. Precision + clarity; loud but controlled; mid-forward. Metal doctrine: "
                 "minimal compression, long attack / short release (Mastering The Mix).",
        "confidence": "high (well documented)",
        "targets": {"lufs": -13.5, "tp": -1.0, "slope_dB_oct": -1.6, "pivot": 900,
                    "notes": "presence-forward, tight, controlled clip; hotter than the house default"},
        "args": ["--lufs", "-13.5", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.5", "--comp", "--mono", "200", "--tilt-target", "-1.6",
                 "--pivot", "900",
                 "--comp-ratio", "2.0", "--comp-attack", "45", "--comp-release", "130", "--comp-gr", "1.2",
                 "--deess-f0", "7500", "--deess-range", "2.0"],
    },
    "laporta": {
        "engineer": "Joe LaPorta (Sterling Sound, since 2013)",
        "genre": "modern alt / pop-rock",
        "basis": "Grammy Best Engineered Album (Blackstar, 2017); ROTY (Flowers, 2024). Punchy, "
                 "streaming-ready, wide but mono-safe across rock/alt/pop.",
        "confidence": "medium-high (documented credits)",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -1.7, "width": 1.10,
                    "notes": "punchy, modern, wide-but-safe, controlled dynamics"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.0", "--comp", "--multiband", "--mono", "200",
                 "--width", "1.10", "--tilt-target", "-1.7",
                 "--comp-ratio", "2.5", "--comp-attack", "20", "--comp-release", "200", "--comp-gr", "1.5",
                 "--deess-range", "3.0"],
    },
    "audiosiege": {
        "engineer": "Brad Boatright (Audiosiege, Portland OR)",
        "genre": "punk / hardcore / metal / doom",
        "basis": "Documented gear: Manley Massive Passive ME, Dangerous Bax, custom Sontec/Massenburg "
                 "DR-MQ5, Dave Hill Titan, Foote P3EX, Rocksonics MB-3X x2, Aphex Dominator II x2, "
                 "Louder Than Liftoff Silver Bullet, and a custom diode 'Massive Aggressor' saturator.",
        "confidence": "high (published gear list)",
        "targets": {"lufs": -13.5, "tp": -1.0, "slope_dB_oct": -1.5,
                    "notes": "saturated, dense, harmonic-rich, loud; multiband limiting + diode colour"},
        "args": ["--lufs", "-13.5", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "2.0", "--comp", "--multiband", "--color", "transformer",
                 "--mono", "200", "--tilt-target", "-1.5",
                 "--comp-ratio", "2.0", "--comp-attack", "50", "--comp-release", "120", "--comp-gr", "1.2",
                 "--color-drive", "0.35", "--color-mix", "0.4", "--deess-f0", "7500", "--deess-range", "2.0"],
    },
    "bogren": {
        "engineer": "Jens Bogren (Fascination Street Studios, Orebro)",
        "genre": "modern metal / heavy rock",
        "basis": "Stated philosophy: 'warmth of analog with precision of digital ... organic, clear, "
                 "full of life', built for translation. Producer-mixer-master; Bogren Digital tools.",
        "confidence": "medium-high (studio statements)",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -1.6,
                    "notes": "organic + clear, powerful, tight lows, controlled aggression"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.5", "--comp", "--multiband", "--color", "tape15",
                 "--mono", "200", "--tilt-target", "-1.6",
                 "--comp-ratio", "2.0", "--comp-attack", "40", "--comp-release", "150", "--comp-gr", "1.2",
                 "--color-drive", "0.4", "--color-mix", "0.5", "--deess-f0", "7200", "--deess-range", "2.0"],
    },
    "prog-metal": {
        "engineer": "Andy Sneap (mix+master) / Richard Chycki (mix) — Dream Theater",
        "genre": "progressive metal / modern metal",
        "basis": "Dream Theater 'A View from the Top of the World' (2021) was MIXED AND MASTERED by Andy "
                 "Sneap. Earlier 'Dream Theater' (2013) was mixed by Richard Chycki on an SSL Duality "
                 "(hybrid DAW+analog; UAD SSL 4000, Sonnox Oxford EQ). DT guitars: Mesa Mark IIC+/Mark V, "
                 "petrucci doubles everything, 3-12 guitar tracks/song + DI; drums 40+ mics with phase/leakage "
                 "control so the kit reads as ONE instrument; priority = separation + clarity inside density + "
                 "power. Doctrine (Mastering The Mix): minimal compression, long attack/short release, and LESS "
                 "saturation on already-distorted material.",
        "confidence": "medium (documented credits + techniques; no measured reference)",
        "targets": {"lufs": -13.5, "tp": -1.0, "slope_dB_oct": -1.6,
                    "notes": "tight lows, present highs, scooped low-mids; minimal comp, long attack/short release"},
        "args": ["--lufs", "-13.5", "--tp", "-1.0", "--declick", "--dehum", "50", "--eq", "--deess",
                 "--harsh", "--dyneq", "--translate", "--clip", "1.5", "--comp", "--multiband",
                 "--color", "transformer", "--mono", "200", "--tilt-target", "-1.6",
                 "--comp-ratio", "2.0", "--comp-attack", "50", "--comp-release", "120", "--comp-gr", "1.2",
                 "--color-drive", "0.35", "--color-mix", "0.4", "--deess-f0", "7500", "--deess-range", "2.0"],
    },
    "golden": {
        "engineer": "John Golden (Golden Mastering, Ventura CA, est. 1993)",
        "genre": "indie / garage / underground rock (also vinyl)",
        "basis": "Family-run since 1993; Neumann VMS-70 lacquer cutting. Known for organic depth, "
                 "warmth and weight; keeps dynamics, avoids heavy limiting; analog/tape friendly. Doctrine: "
                 "indie rock benefits from heavier glue (fast attack / slow release) + a little colour.",
        "confidence": "medium (reputation-level)",
        "targets": {"lufs": -14.5, "tp": -1.0, "slope_dB_oct": -2.0,
                    "notes": "warmer tone, wider dynamics, less limiting, tube colour"},
        "args": ["--lufs", "-14.5", "--tp", "-1.0", "--eq", "--deess", "--dyneq", "--translate",
                 "--comp", "--color", "tube", "--mono", "200", "--width", "1.05",
                 "--tilt-target", "-2.0",
                 "--comp-ratio", "4.0", "--comp-attack", "5", "--comp-release", "400", "--comp-gr", "2.5",
                 "--color-drive", "0.6", "--color-mix", "0.6", "--deess-f0", "6600", "--deess-range", "2.5"],
    },
    "lambert": {
        "engineer": "Joe Lambert (Joe Lambert Mastering, Westchester NY)",
        "genre": "rock / americana / indie",
        "basis": "Maselec MTC-1X + MLA-4 + 2012 limiter, Manley Massive Passive/Variable Mu, Weiss EQ1, "
                 "Sontec MES-431C, Anamod tape sim; KEF 207.2 full-range monitoring. 'Leave headroom ... "
                 "not necessary to make your mixes loud.' Apple Digital Masters approved.",
        "confidence": "high (published gear list)",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -1.8,
                    "notes": "weighted low end + guitar presence, analog/tape, controlled"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.0", "--comp", "--color", "tape15", "--mono", "200",
                 "--width", "1.10", "--tilt-target", "-1.8",
                 "--comp-ratio", "2.5", "--comp-attack", "30", "--comp-release", "250", "--comp-gr", "1.5",
                 "--color-drive", "0.5", "--color-mix", "0.5", "--deess-f0", "6800", "--deess-range", "2.5"],
    },
    "pop": {
        "engineer": "(genre target)",
        "genre": "pop / pop-rock",
        "basis": "Streaming-first pop target: bright, tight lows, wide, de-essed, controlled.",
        "confidence": "genre norm",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -1.4, "width": 1.15,
                    "notes": "brighter slope, tighter lows, wider, de-essed"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.0", "--comp", "--multiband", "--mono", "200",
                 "--width", "1.15", "--tilt-target", "-1.4",
                 "--comp-ratio", "2.5", "--comp-attack", "20", "--comp-release", "200", "--comp-gr", "1.5",
                 "--deess-range", "3.0"],
    },
    "metal": {
        "engineer": "(genre target, Bogren/Audiosiege/Sneap lineage)",
        "genre": "modern metal / djent / metalcore",
        "basis": "Genre norm: tight lows, aggressive but controlled, scooped low-mids, saturated-but-not-"
                 "over-saturated (less saturation the more distorted the source).",
        "confidence": "genre norm",
        "targets": {"lufs": -13.5, "tp": -1.0, "slope_dB_oct": -1.5,
                    "notes": "tight, aggressive, saturated, hot"},
        "args": ["--lufs", "-13.5", "--tp", "-1.0", "--eq", "--deess", "--harsh", "--dyneq",
                 "--translate", "--clip", "1.5", "--comp", "--multiband", "--color", "transformer",
                 "--mono", "200", "--tilt-target", "-1.5",
                 "--comp-ratio", "2.0", "--comp-attack", "50", "--comp-release", "120", "--comp-gr", "1.2",
                 "--color-drive", "0.35", "--color-mix", "0.4", "--deess-f0", "7500", "--deess-range", "2.0"],
    },
}


def profile_args(name):
    """Return the master.py flag tokens for a profile (raises KeyError if unknown)."""
    return list(PROFILES[name]["args"])


GUIDE = """Which profile?  (pick by genre first, then sanity-check with tilt.py --measure)

  classic / art rock, max dynamics + translation ....... gateway
  modern rock band (guitars+vox must cut) ............... modern-rock
  modern rock, RESEARCHED consensus chain (preferred) ... preferred
  major-label rock/metal, louder, precision ............ sterling
  alt / indie / pop-rock, punchy + wide + streaming .... laporta
  punk / hardcore / metal / doom, saturated + dense .... audiosiege
  modern metal (djent/metalcore), organic but tight .... bogren   (hotter: metal)
  PROG METAL / Dream Theater lineage ................... prog-metal
  indie / garage / lo-fi, warmth + keeps dynamics ...... golden
  rock / americana, low-end weight + guitar presence ... lambert
  radio pop / pop-rock, bright + tight + wide .......... pop

Measurement hints (tilt.py --measure): slope < -2.3 dB/oct = dark/heavy, lean golden/lambert;
slope > -1.5 dB/oct = already bright, lean sterling/gateway (not pop/audiosiege).
Unknown genre -> use the CLOSEST profile and SAY SO; nothing fits -> modern-rock."""


def profile_names():
    return list(PROFILES.keys())


def _line(name):
    p = PROFILES[name]
    t = p["targets"]
    return (f"{name:12s} | {p['engineer'][:44]:44s} | {p['genre'][:28]:28s} | "
            f"{t['lufs']:+.1f} LUFS  TP {t['tp']:+.1f}  slope {t['slope_dB_oct']:+.1f} dB/oct")


def main(argv=None):
    import sys
    a = sys.argv[1:] if argv is None else argv
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    if a[0] == "list":
        print(f"{'profile':12s} | {'engineer':44s} | {'genre':28s} | targets")
        print("-" * 118)
        for n in PROFILES:
            print(_line(n))
        print("\n(run `profiles.py guide` for the pick-by-genre guide, or `show <name>` for detail)")
        return
    if a[0] == "guide":
        print(GUIDE)
        return
    if a[0] == "args":
        print(" ".join(profile_args(a[1])))
        return
    if a[0] == "show":
        if len(a) < 2 or a[1] not in PROFILES:
            import sys as _s
            _s.exit(f"unknown profile {a[1:]!r}; known: {', '.join(PROFILES)}")
        p = PROFILES[a[1]]
        print(f"# profile: {a[1]}")
        print(f"engineer : {p['engineer']}")
        print(f"genre    : {p['genre']}")
        print(f"basis    : {p['basis']}")
        print(f"confidence: {p['confidence']}")
        print(f"targets  : {p['targets']}")
        print(f"chain    : {' '.join(p['args'])}")
        return
    import sys as _s
    _s.exit(f"usage: profiles.py {{list|guide|show <name>|args <name>}}")


if __name__ == "__main__":
    main()
