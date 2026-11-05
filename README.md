# mpe-instruments

Playable instruments for an MPE controller (built for the Seaboard BLOCK), made with
Faust physical models and synths. One file per sound, a host that plays them, and a
small window to switch between them.

```
Seaboard -> seaboard-mpe (MPE-Clean:out) -> mpe-host -> speakers
                                              ^
                                       ui/switcher.py   (switch sounds, volume, panic)
```

Needs [seaboard-mpe](https://github.com/PatrickReynoldsCoding/seaboard-bridge) running first:
it keeps the MPE stream clean (no stuck notes). Change the input with `-m <name>`.

## Run

    ./run                    # builds, starts the host, opens the window
    ./run -i winds/flute     # start on a particular instrument
    make test                # builds and checks every instrument

Options (`build/mpe-host -h`): `-i` start instrument, `-t` transpose in semitones (the window's
Octave -/+ buttons change this live), `-r` pitch-bend range in semitones (default 48, the MPE
default), `-s` touch sensitivity for strike velocity, `-m` MIDI source, `-d` ALSA audio device,
`-p` audio buffer size, `-R` room (hall reverb on the whole mix, 0 = dry, default 0.5; the
window's Room slider changes it live), `-v` log notes and the values sent to each instrument
(for debugging).

If every key sounds the same, the controller is probably sending notes far above the instrument's
range (the host caps pitch at 5 kHz): use the Octave buttons, or `-t -72` for six octaves down.

## Layout

    instruments/<group>/<name>.dsp    one sound per file. The folder is the group in the window.
      strings/  violin, cello
      winds/    flute, clarinet
      plucked/  nylon-guitar, steel-guitar
      struck/   marimba, vibraphone
      voices/   soprano, tenor, bass
      synths/   pad, fm-keys, lead
      drums/    kit (one drum per note of the octave)
    lib/mpe.lib      the contract every instrument follows (below)
    lib/bowed.lib    shared bowed-string engine (violin, cello)
    lib/body_*.lib   violin and cello bodies, fitted to recordings (generated, see below)
    lib/vocal.lib    shared sung-vowel engine (the voices)
    src/             mpe-host.cpp (plays instruments), entry.cpp + loader.h (plugin loading),
                     room.dsp (the hall reverb)
    ui/switcher.py   the window (Python + built-in Tk, nothing to install)
    tools/           offline renderer and measuring tools
    tests/           checks run on every instrument, and on the host

## Add an instrument

Drop a `.dsp` file in the right folder, run `make`, and it appears in the window (restart
the host). Every instrument gets the same controls from `lib/mpe.lib`; it decides what they do:

| control    | meaning |
|------------|---------|
| `freq`     | Hz, pitch bend already applied |
| `gate`     | 1 while the finger is down |
| `pressure` | 0..1, how hard this finger presses |
| `slide`    | 0..1, finger position up/down the key |
| `velocity` | 0..1, how hard the note was struck |
| `legato`   | 1 if the note started while another was sounding (a slur); optional |

Smallest possible instrument:

    declare name "Sine";
    declare range "65 1047";           // playable range in Hz, used by the tests
    import("stdfaust.lib");
    mpe = library("mpe.lib");
    process = os.osc(mpe.freq) * mpe.gate * mpe.pressure : si.smooth(0.999) * 0.3;

Optional declarations the tests understand: `ringout "6"` (seconds it may keep ringing),
`window "0.04 0.4"` (when to judge a short percussive note), `pitched "no"`.

`make test` plays each instrument at three pitches and at the extremes of pressure and slide,
and checks for no blow-ups, real sound while held, silence after release, and pitch within
30 cents. `tools/grid.py <group/name> <hz,hz,...>` sweeps touch settings and lists every
note that is out of tune: use it after changing an instrument.

## Notes on how the sounds were tuned

I could not listen while building these, so they were tuned by measuring, not by ear.
Treat the numbers as a starting point and trust your ears over the tests.

- **Violin and cello** are fitted to recordings of solo Bach by two concert soloists. The
  engine (`lib/bowed.lib`) is a waveguide string with real stick-slip bow friction; a
  "virtual player" keeps the bow force where the string gives a clean tone, so pressure and
  slide never make it whistle or scratch. The body is 90 resonators fitted to the harmonic
  levels of the recordings, then corrected by playing the soloist's own phrases (their pitch,
  vibrato and dynamics) on the instrument and measuring what is still different.
  The vibrato, the loudness balance across the range and how the tone brightens with
  pressure are measured from the recordings too. Tools: `tools/timbre/` (see below).
- **Flute** pitch depends on how hard you blow and where the embouchure is. Slide controls
  tone, not embouchure, for that reason. Very light blowing is a little flat, as on a real flute.
- **Marimba**: the stock library one rings for 0.1 s, so it is rebuilt with a longer ring.

## Fitting the strings to recordings (tools/timbre/)

Needs a Python venv with numpy, scipy, soundfile (and torch + transformers for `clapcheck.py`),
and reference recordings in `refs/<player>/*.wav` (48 kHz; not in the repo, `refs/` is ignored).

    python refstats.py hahn          measure every recording (pitch, harmonic levels)
    python passages.py hahn          pick single-line passages and split them into notes
    python makebody.py violin        first body fit -> lib/body_violin.lib
    python refit.py violin           body correction rounds, lowest notes, loudness balance
    python evaluate.py violin --wav  scores, plus A/B files in refs/ab/ (recording vs instrument)
    python clapcheck.py violin current   a neural audio model's opinion (CLAP embeddings)

Other checks: `helmholtz.py` (where the bare string bows cleanly), `regprofile.py` (brightness
by register), `tilt.py` (brightness against loudness), `onsets.py` (attacks and slurs),
`amsplit.py` (vibrato shimmer), `vibstats.py` (a player's vibrato), `levelbal.py`.
