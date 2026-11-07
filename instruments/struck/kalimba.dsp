declare name "Kalimba";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "260 1047";
declare ringout "3";
declare window "0.04 0.5";
declare description "Thumb piano: soft metal tines in a wooden box. Slide changes how much of the buzz and click you hear.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

tone = sl.modes(mpe.freq, (1, 5.4, 12.1), (1.8, 0.3, 0.08), (1, 0.18, 0.05), 1, mpe.trigger);
tap  = sl.burst(3, mpe.trigger) : fi.lowpass(1, 1200 + 3000 * mpe.slide);

process = (tone + tap * 0.18) * (0.4 + 0.6 * mpe.velocity) * 0.9;
