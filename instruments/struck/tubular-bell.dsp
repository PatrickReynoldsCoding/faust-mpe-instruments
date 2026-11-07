declare name "Tubular Bell";
declare sound "reverb=0.55 reverbSize=0.7 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "261 1047";
declare ringout "9";
declare pitched "no";
declare window "0.05 1.0";
declare description "Orchestral chime: a long, ringing strike. Slide moves the hammer from soft to hard.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

hard = 0.4 + 0.6 * mpe.slide;
tone = sl.modes(mpe.freq, (0.5, 1, 1.19, 1.5, 2.0, 2.52, 3.01), (6, 6, 4.5, 4, 3, 2, 1.5), (0.3, 1, 0.5 * hard, 0.45 * hard, 0.5 * hard, 0.25 * hard, 0.15 * hard), 1, mpe.trigger);

process = tone * (0.35 + 0.65 * mpe.velocity) * 0.5;
