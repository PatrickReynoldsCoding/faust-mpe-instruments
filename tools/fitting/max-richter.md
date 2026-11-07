# Max Richter piano: what was done, and how far to trust it

`instruments/keys/max-richter.dsp`, "Max Richter". Fitted to commercial recordings (two albums, the owner's own
copies, lossless; audio stays in `refs/richter/`, git-ignored; only fitted numbers are committed). **Nobody has
listened to it yet.** Listening files are made by the commands below; judge by ear.

## What it is

- The Steinway piano engine (`lib/piano.lib`, copied to `lib/richter.lib`) with its own tables (`lib/richter_fit.lib`).
- Tuning, stiffness, hammer softness by key and touch, and the body: fitted from 479 single notes in 10 tracks that
  measure as solo piano (stiff-string overtones like the Steinway's, and decaying), then by comparing 60-second
  passages (same notes, played through the instrument) with the recordings in third-octave bands.
- Loudness by key and touch follows the Steinway's. The recordings' own balance across the keyboard is phrasing,
  room and pedal; matched to it the top octave was unplayably quiet.
- `post` is stereo and runs once for all notes: the body, two allpass-comb decorrelators (the ears differ by a
  millisecond or less), a short room tail, and 88 sympathetic-string resonators (the pedal-down ringing).

## What was measured, honestly

- Tone, on four passages the fit never saw, recording minus instrument in third-octave bands 200 Hz-8 kHz:
  Richter instrument 4.2 dB (median over passages), Steinway 4.7 dB. Per passage 7.8 vs 7.4 dB. That is no clear
  win in this measure: a passage differs from its recording by about 7 dB whichever piano plays it, because the
  transcription is rough and the tracks differ from each other (their top end differs by 20 dB or more). What is
  clear: the recordings are much darker above 2 kHz than the Steinway, and the body now follows that.
- Stereo: the recordings' ears agree 0.62 on average (coherence, 100 Hz-8 kHz, whole passages), the instrument 0.90
  (0.7 above 3 kHz, 0.4 at 12 kHz, 0.95+ in the mids). Width is partial: more in the mids needs several
  milliseconds of smear, not tried without listening. The recordings show no pan by key (the lag between the ears
  has median 0 in every register), so per-key panning was not built and no engine change was needed.
- Decay: only 21 notes had a measurable early decay and they disagreed by register; left as the Steinway's.
- Sympathetic resonance level (-28 dB) and the room tail (-15 dB, 0.9 s) are chosen, not fitted.
- CPU: one note rendered offline takes 2.1 times the Steinway's (post: 88 resonators, a reverb, two combs). The post is
  per part, not per note.
- Sparse registers (below key 45 and above key 90) fall back on the Steinway's tables, weighted by how many Richter
  notes support them.

## Tracks used (the `songs` declare)

Horizon Variations, Shadow Journal, Vladimir's Blues, Old Song, The Trees, Written on the Sky (The Blue Notebooks);
On the Nature of Daylight (Piano Version), A Catalogue of Afternoons (The Blue Notebooks 20 Year Edition, disc 2);
While The Flood Rages, The City Was A Chaos (Intro) (While The Flood Rages). Chosen by the measurements above, not
by listening, so a stretch with something else playing could be in them.

## Reproduce

    python tools/fitting/piano/richter_notes.py             # measure the notes of every track
    python tools/fitting/piano/richter_fit.py select|init
    python tools/fitting/piano/richter_fit.py refit 4        # tables
    python tools/fitting/piano/richter_tone.py 4             # body, from whole passages
    python tools/fitting/piano/richter_fit.py anchor         # sparse keys fall back on the Steinway's
    python tools/fitting/piano/richter_fit.py level          # loudness as the Steinway's
    python tools/fitting/piano/richter_stereo.py, richter_itd.py   # the stereo measurements

## Not done

No per-key pan, no pedal control (the press-to-hold of the Steinway stays), no articulations, no change to the Steinway
piano, to `lib/mpe.lib` or to odo's engine. Listening comparisons: `refs/ab/richter/` (recording, Steinway, this,
same notes, same loudness).
