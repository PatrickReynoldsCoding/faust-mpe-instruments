declare version "1.0.0";
declare name "Berlin";
declare sound "reverb=0.3 reverbSize=0.55 reverbDamp=0.45 delay=0.18 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "98 2093";
declare artist "ROLI Seaboard demos (Cypher2 Berlin Progression)";
declare songs "Seaboard RISE x SWAM & Camelot Pro (ROLI), 1:02-1:34";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
declare description "Berlin-school poly synth, after Cypher2's Berlin Progression: a bright, slightly synced square and saw that blooms at the strike and settles into a warm hold. Strike harder for a brighter bloom; press to open the filter and swell; slide up the key to sweep the sync and resonance. Lovely with the arpeggiator.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// Fitted to the Seaboard demo (numbers in tools/fitting/seaboard/synths/README.md):
// - held tone: harmonics 0 -11 -8 -18 -16 -17 -25 -26 dB: square, saw and a mild sync (ratio 1.2)
//   under a soft filter at about 13 x f0;
// - at the strike the 1-3 kHz band is 10 dB up and falls back within about 0.2 s (filter envelope);
// - attack under 10 ms, the level holds, pressure swells it.
trig  = mpe.trigger;
since = ba.countup(ma.SR * 4, trig) / ma.SR;
vel   = mpe.velocity;
press = mpe.pressure : si.smooth(ba.tau2pole(0.03));
slide = mpe.slide : si.smooth(ba.tau2pole(0.04));
bloom = exp(-since / 0.09) * (0.3 + 0.7 * vel);

// Square + saw + a saw synced to it.
osc(f, ph) = 0.44 * sq + 0.28 * saw + 0.28 * sync
with {
    p    = ma.frac(os.lf_sawpos(f) + ph);
    sq   = (p < 0.5) * 2 - 1;
    saw  = 2 * p - 1;
    sync = 2 * ma.frac(p * (1.19 + 3 * max(0, slide - 0.5) + 4 * bloom)) - 1;
};
f    = mpe.freq;
oscs = osc(f, 0);                                       // one set: the ensemble in post gives the width (a detuned pair beat the fundamental away)

cut  = f * (8 + 14 * press + 70 * bloom + 10 * max(0, slide - 0.5)) : min(16000);
tone = oscs : fi.dcblocker : fi.resonlp(cut, 0.5 + 2.4 * max(0, slide - 0.5) + 0.3 * press + 1.2 * bloom, 1);
amp  = mpe.gate * (0.6 + 0.15 * vel + 0.35 * press) : si.lag_ud(0.004, 0.25);

process = tone * amp * 0.34;
fx   = library("fx.lib");
post = _ <: (*(0.75) <: _, _), (fx.ensemble : *(0.4), *(0.4)) :> _, _;   // a little ensemble chorus for width
