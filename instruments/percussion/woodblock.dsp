declare name "Woodblock";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "523 2093";
declare ringout "1";
declare pitched "no";
declare window "0.01 0.1";
declare description "A hollow tok. Slide changes the size of the block.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

tone = sl.modes(mpe.freq * (0.8 + 0.4 * mpe.slide), (1, 2.4, 3.9), (0.08, 0.05, 0.03), (1, 0.4, 0.2), 1, mpe.trigger);
tick = sl.burst(1, mpe.trigger) : fi.bandpass(2, 2500, 5000) * 0.3;

process = (tone + tick) * (0.4 + 0.6 * mpe.velocity) * 0.9;
