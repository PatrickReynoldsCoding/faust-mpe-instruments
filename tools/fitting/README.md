# Fitting instruments to reference recordings

Everything used to make an instrument sound like a named recording lives here. The instruments
fitted so far: violin and cello (`timbre/`), piano (`piano/`). Run all commands from the repo root.

    timbre/   strings: measure recordings, find clean single-line passages, fit the body, correct
              it by playing the soloist's own phrases through the instrument, score the result.
              analysis.py (loading, pitch, partials) is shared with piano/.
    piano/    piano: measure single notes (Iowa MIS), fit per-key tables (lib/piano_fit.lib),
              render whole pieces from MIDI to compare with a recording.
    lab/      bowed-string test instruments (raw bow controls, no body).
    scan_pitch.py, scan_bow.py, try_attack.py   where a bowed string plays in tune, bow-attack trials.

General tools (`tools/grid.py`, `tools/pitch.py`, `tools/inspect_note.py`, `tools/render.cpp`) stay in
`tools/`: the tests use them.

## Setup

A venv with numpy, scipy, soundfile (and torch + transformers for the `clapcheck.py` scripts; this
machine's is `~/.venvs/strings-lab`). The scripts find the repo root themselves.

## References (`refs/`, git-ignored)

One folder per player or source, 48 kHz wav, each with a `SOURCES.md`: who, what, where from,
licence. Rule: only openly licensed or public-domain recordings are fitted to and shared; the repo
keeps the fitted numbers (`lib/body_*.lib`, `lib/piano_fit.lib`), never the audio. Current: Hilary
Hahn (violin), Yo-Yo Ma (cello), Iowa MIS Steinway B + Kimiko Ishizaka's CC0 *Open Well-Tempered
Clavier* (piano), see the project memory for the winds, harp and others.

## Fitting a new instrument (the order that worked)

1. Put the recordings in `refs/<player>/` and write `SOURCES.md`.
2. Measure: `timbre/refstats.py <player>` (strings), `piano/notes.py` (piano).
3. Make the first fit: `timbre/makebody.py <inst>` or `piano/fit.py init`.
4. Build (`make`), then correct against the recordings: `timbre/refit.py <inst>`, `piano/fit.py refit N`.
5. Score and listen: `timbre/evaluate.py <inst> --wav` (A/B files in `refs/ab/`), `clapcheck.py`.
6. `make test`, then `tools/grid.py <group/name> <hz,...>` for tuning across touch settings.

The step-by-step commands are in the main README, "Fitting the strings" and "Fitting the piano".
