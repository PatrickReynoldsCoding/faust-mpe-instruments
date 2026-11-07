declare name "Bass Guitar";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "41 262";
declare ringout "4";
declare window "0.05 0.6";
declare description "Plucked electric bass. Slide moves from a muted thumb to a bright slap.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

pick = sl.burst(5, mpe.trigger) : fi.lowpass(1, 300 + 3000 * mpe.slide) : *(0.4 + 0.6 * mpe.velocity);
g    = 0.9985 * mpe.gate + 0.97 * (1 - mpe.gate) : si.smooth(0.95);

process = sl.string(mpe.freq, g, pick) * 6 : ma.tanh : *(0.7);
