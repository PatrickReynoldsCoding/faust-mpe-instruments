# Max Richter piano: what is in scope

Status: waiting for the reference files (CD rips, track titles). Nothing built yet.
Only this instruments repo is touched. Another agent is working on odo.

## Adding

- `instruments/keys/max-richter.dsp`: the instrument. Name "Max Richter" (not "Piano 2").
  One voice per finger, the same six controls as every instrument, no new options for the player.
  Stereo out of `post` (see below).
  Declares: `artist`, `songs` (every recording used, ` | ` separated), `reference_licence`,
  `status "current"`, `sound` (its own effects defaults), `range`, `description`, test hints.
- The engine is the existing `lib/piano.lib` (stiff strings, felt hammer, soundboard `post`),
  driven by a second set of fitted tables, `lib/richter_fit.lib` (generated, not hand-edited).
- A fitting script in `tools/fitting/piano/` (reusing `timbre/analysis.py`): measures the
  recordings and writes the tables. What is fitted: tone by register (spectral balance), how
  fast notes decay, hammer softness and its level by loudness, the quiet mechanical noise, and
  a fixed close-microphone room in `post` (using `lib/fx.lib`).
- Always-on sympathetic resonance inside the instrument (undamped strings ringing along, like a
  pedal held about half down), so the recordings' ringing is modelled and not forced into the
  hammer and decay tables. No control for it. Its CPU cost is measured with the engine bench.
- Stereo from the soundboard: `post` already may output two channels, and the soundboard is a bank
  of resonators, so each mode is tapped into left and right with its own weights, as a body
  radiates. A natural width for headphones, with no engine change.
- A local `refs/richter/SOURCES.md` listing every track (git-ignored, with the audio).
  The same titles go in the `songs` declare.
- `make test` passing for it, plus an A/B report against the recordings
  (`clapcheck.py` style) saying where it still differs.
- A short section in `README.md` and this folder's README.

## Not adding

- No audio in the repo: only fitted numbers.
- No change to the existing `keys/piano.dsp`, `lib/piano_fit.lib`, the cello, violin or any
  other instrument, and no change to `lib/mpe.lib` (the contract stays `mpe-voice/1`).
- No per-key pan (it needs the engine to keep voices stereo until `post`: odo and the computer
  host, the other agent's area). No new pedal control: the existing press-to-hold stays the
  only pedal. No articulations (not for a piano). Both are in "Room to grow" in odo's
  `INSTRUMENT_FORMAT.md`.
- No odo changes: no pack manifest edit, no engine or app code, no release. Until a pack
  lists it, odo puts it in "More sounds". Putting it in the Classical pack is a one-line
  change for whoever owns odo.
- No new instruments, and no improving the legacy sketches.
- No YouTube downloading unless you give a link and say so. CD rips are preferred.

## Needed from you

1. The CD rips (WAV or FLAC) in `refs/richter/`, tracks where the piano plays alone.
2. The track titles (and album), for the `songs` list.
3. Confirmation that using non-open recordings for fitting is fine. The licence declare will
   say so plainly and the audio stays local.

## Limits I expect

Finished pieces have no isolated single notes, so the fit describes the sound of this piano
and room, not every key individually as the Iowa set does for the Steinway. Notes under strings
or reverb in a track will be skipped or measured less well; solo passages are best.
