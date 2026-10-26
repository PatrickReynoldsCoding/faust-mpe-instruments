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
`-p` audio buffer size, `-v` log notes and the values sent to each instrument (for debugging).

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
    lib/mpe.lib      the contract every instrument follows (below)
    lib/bowed.lib    shared bowed-string engine (violin, cello)
    lib/vocal.lib    shared sung-vowel engine (the voices)
    src/             mpe-host.cpp (plays instruments), entry.cpp + loader.h (plugin loading)
    ui/switcher.py   the window (Python + built-in Tk, nothing to install)
    tools/           offline renderer and measuring tools
    tests/           checks run on every instrument, and on the host

## Add an instrument

Drop a `.dsp` file in the right folder, run `make`, and it appears in the window (restart
the host). Every instrument gets the same five controls from `lib/mpe.lib`; it decides what they do:

| control    | meaning |
|------------|---------|
| `freq`     | Hz, pitch bend already applied |
| `gate`     | 1 while the finger is down |
| `pressure` | 0..1, how hard this finger presses |
| `slide`    | 0..1, finger position up/down the key |
| `velocity` | 0..1, how hard the note was struck |

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

- **Bowed strings** drop to the wrong mode (an octave off) if the bow is too close to the
  bridge on high notes, too far from it on low notes, or starts too slowly. `lib/bowed.lib`
  and the two string files hold the limits found by scanning (`tools/scan_bow.py`).
- **Flute** pitch depends on how hard you blow and where the embouchure is. Slide controls
  tone, not embouchure, for that reason. Very light blowing is a little flat, as on a real flute.
- **Marimba**: the stock library one rings for 0.1 s, so it is rebuilt with a longer ring.
