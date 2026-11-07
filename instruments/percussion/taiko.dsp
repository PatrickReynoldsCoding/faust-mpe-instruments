declare name "Taiko";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "55 220";
declare ringout "3";
declare pitched "no";
declare window "0.05 0.5";
declare description "Big Japanese drum: a deep boom with a skin slap. Slide moves from the middle to the rim.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

fall  = mpe.trigger : fi.pole(ba.tau2pole(0.05));
body  = sl.modes(mpe.freq * (1 + 0.5 * fall), (1, 1.6, 2.3), (1.2, 0.6, 0.3), (1, 0.4, 0.2), 1, mpe.trigger);
slap  = sl.burst(10, mpe.trigger) : fi.bandpass(2, 400 + 1500 * mpe.slide, 3000) * 0.5;

process = (body + slap) * (0.3 + 0.7 * mpe.velocity) * 1.1 : ma.tanh;
