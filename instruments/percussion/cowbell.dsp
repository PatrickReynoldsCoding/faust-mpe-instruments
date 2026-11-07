declare name "Cowbell";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "400 1568";
declare ringout "1.5";
declare pitched "no";
declare window "0.03 0.3";
declare description "Two metal tones in the classic cowbell interval. Slide shortens or lengthens the ring.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

len  = 0.15 + 0.7 * mpe.slide;
tone = sl.modes(mpe.freq, (1, 1.504, 2.01, 2.58), (len, len * 0.8, len * 0.3, len * 0.2), (1, 0.9, 0.3, 0.15), 1, mpe.trigger);

process = (tone : fi.bandpass(1, mpe.freq * 0.9, mpe.freq * 4)) * (0.4 + 0.6 * mpe.velocity) * 0.9;
