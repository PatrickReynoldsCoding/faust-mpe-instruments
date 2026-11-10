# Cypher2 synths from the Seaboard RISE demo (synths/sync-funk, synths/berlin)

Reference: `refs/roli-seaboard/rise-funk-berlin.wav` (ROLI's video 1:02-1:34, a split: Cypher2
"Mean Hard-Sync Funk 5D" low, "Berlin Progression" high). Mono mix, no stereo to fit. Run from this folder.

    harm2.py WAV a:b ...        harmonic levels of a held note (F0LO/F0HI env set the f0 search)
    dive.py WAV a:b ...         pitch (MIDI) every 10 ms: the funk's dive into a note
    bands.py WAV t0 t1 [step]   band levels over time (200-400, 500-1k, 1-3k, 3-8k Hz)
    fitosc.py                   fits square/saw/sync mix and a filter to the measured harmonic profiles
    phrase.py                   plays the clip's own notes (Basic Pitch + measured bass onsets and dives)
                                through both instruments (needs build/render_curves) -> $SCRATCH/*-phrase.wav
    cmp.py REF REN              third-octave spectra and band-envelope correlation
    decay.py WAV f0:a:b:name    decay of one partial (used for the piano check)

What was measured (2026-11-10):

- Funk, held notes: harmonics 0 -13 -7 -23 -17 -24 -21 -19 -25 -32 dB (k1..k10, mean of 8 notes):
  a square/saw mix through a soft filter at about 8 x f0. The instrument at light pressure: 0 -12 -8 -18 -13
  -22 -16 -25 -19 -28 (about 3 dB rms off).
- Funk, notes struck on the beat dive in: MIDI 48 -> 29 in about 0.12 s (+12 st at 30 ms, +6 at 60, +3 at 90).
  The instrument at velocity 0.95 is within 1 semitone of that curve. Notes end within 20 ms of the lift.
- Berlin, held chord: harmonics 0 -11 -8 -18 -16 -17 -25 -26 -20; the instrument 0 -9 -4 -17 -13 -13 -20 -21 -16.
  At the strike the 1-3 kHz band is 10 dB up and falls back in 0.2 s (the instrument: 4 dB, 3-8 kHz 9 dB).
- The clip's phrase through both (funk x1.3, berlin x0.7): third-octave error 2.1 dB rms (40 Hz-8 kHz);
  band-envelope correlation 0.72 (30-200 Hz), 0.72 (250-1000), 0.56 (1-4 kHz), limited by the transcription.
