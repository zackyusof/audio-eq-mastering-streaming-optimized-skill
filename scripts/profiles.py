#!/usr/bin/env python3
"""Mastering PROFILE - the single house default used by master.py.

This tool ships ONE profile: the house default chain and target (modern rock). There are no
engineer-derived presets and no profile selection. Real mastering chains are proprietary craft,
and modelling a named engineer's chain would misrepresent it - so this build does not try.

The house target sits a little on the BASS side (-2.1 dB/oct): a mild bass-forward balance is
the accepted music/room target preference (~1 dB/oct down).

Usage:
  profiles.py list | show <name> | args <name>      (one profile: modern-rock)

master.py consumes it via `--profile modern-rock`; with no --profile flag the same defaults run.
Explicit user flags always override the profile.
"""
PROFILES = {
    "modern-rock": {
        "engineer": "(house default)",
        "genre": "modern rock",
        "basis": "The house chain and target, validated on own material. Tonal target sits a little on "
                 "the BASS side (-2.1 dB/oct): a mild downward (bass-forward) balance is the accepted "
                 "music/room target preference (~1 dB/oct down) and iZotope TBC ships a 'Bass Heavy' "
                 "curve. NOTE: Schedin's DiVA thesis 'Target Spectrums For Mastering' (2021) only shows "
                 "rock vs vocal-electronic differ in the low end - it does NOT recommend a bass-leaning "
                 "rock target. The dehum repair stage runs first as a safety net.",
        "confidence": "validated on own material",
        "targets": {"lufs": -14.0, "tp": -1.0, "slope_dB_oct": -2.1,
                    "notes": "bass-leaning; cut 250-400, presence 2-5k"},
        "args": ["--lufs", "-14.0", "--tp", "-1.0", "--dehum", "50", "--eq", "--deess",
                 "--harsh", "--translate", "--clip", "1.0", "--mono", "200",
                 "--tilt-target", "-2.1"],
    },
}


def profile_args(name):
    """Return the master.py flag tokens for a profile (raises KeyError if unknown)."""
    return list(PROFILES[name]["args"])


GUIDE = """One profile ships with this tool - the house default (`modern-rock`).

  -14.0 LUFS-I / -1.0 dBTP / slope -2.1 dB/oct, chain: dehum 50, EQ, de-ess, harshness,
  low-end translation, soft-clip 1.0, mono <200 Hz, tilt toward -2.1.

There is no profile selection: run the default pipeline. Any explicit master.py flag overrides
the corresponding default."""


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
