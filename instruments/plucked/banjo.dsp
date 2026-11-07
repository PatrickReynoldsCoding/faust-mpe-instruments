declare name "Banjo";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 784";
declare ringout "1.5";
declare window "0.05 0.4";
declare description "Bright, twangy plucked string with a drum-head ring. Slide moves the pick toward the bridge.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

pick  = sl.burst(1.5 + 2 * (1 - mpe.slide), mpe.trigger) * (0.4 + 0.6 * mpe.velocity);
g     = 0.992 * mpe.gate + 0.95 * (1 - mpe.gate) : si.smooth(0.95);
head  = fi.resonbp(520, 6, 1);

process = sl.string(mpe.freq, g, pick) <: (_, head * 1.5) :> _ : *(2.2) : ma.tanh : *(0.6);
