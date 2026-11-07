declare name "Xylophone";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "261 2093";
declare ringout "2";
declare window "0.03 0.3";
declare description "Dry, hard wooden bars tuned to a bright twelfth. Slide moves from the middle of the bar to the edge.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

tone = sl.modes(mpe.freq, (1, 3, 6.05), (0.5, 0.25, 0.1), (1, 0.45 + 0.4 * mpe.slide, 0.2 * mpe.slide), 1, mpe.trigger);
tick = sl.burst(1.5, mpe.trigger) : fi.highpass(1, 2000) * 0.1;

process = (tone + tick) * (0.35 + 0.65 * mpe.velocity) * 0.8;
