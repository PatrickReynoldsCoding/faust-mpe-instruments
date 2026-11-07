declare name "Harp";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "98 1047";
declare ringout "10";
declare window "0.05 0.6";
declare description "Concert harp: soft plucked strings that ring on. Slide moves the pluck from the middle (round) to the soundboard (bright).";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

pick = sl.burst(4, mpe.trigger) : fi.lowpass(1, 1500 + 6000 * mpe.slide) : *(0.3 + 0.7 * mpe.velocity);

process = sl.string(mpe.freq, 0.9988, pick) * 2.5 : ma.tanh : *(0.6);
