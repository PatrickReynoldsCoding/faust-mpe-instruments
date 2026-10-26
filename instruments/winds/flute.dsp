declare name "Flute";
declare range "294 1047";
declare description "Breathy flute. Press to blow harder, slide to brighten or soften the tone.";
import("stdfaust.lib");
mpe = library("mpe.lib");

breath = mpe.gate * (0.58 + 0.30*mpe.pressure) : si.lag_ud(0.06, 0.10);
blow   = pm.blower(breath, 0.05, 2000, 5, 0);         // vibrato comes from your finger, not the model
mouth  = 0.5;                                          // moving the embouchure changes a flute's pitch, so keep it still
tone   = 1500 + 8500*mpe.slide : si.smooth(ba.tau2pole(0.03));   // slide softens or brightens the sound instead

// The model's real period is 0.694 x the requested one plus a fixed 32.5 samples (measured).
// Invert that so the note lands on the pitch you play.
// On top of that the pitch sags as you go up (measured at normal blowing pressure): about
// -8 cents at 294 Hz and 24 cents more for every octave. Raise the request to cancel it.
sag    = (8 + 24 * log(mpe.freq / 294) / log(2)) / 100;       // in semitones
period = 1 / (mpe.freq * ba.semi2ratio(sag));
tube   = pm.f2l(1 / max((period - 32.5 / ma.SR) / 0.694, 1 / 6000));

loudness = 0.35 + 0.65*mpe.pressure : si.smooth(ba.tau2pole(0.02));

process = pm.fluteModel(tube, mouth, blow) * 3.5 * loudness : fi.lowpass(2, tone) : ma.tanh : *(0.8);
