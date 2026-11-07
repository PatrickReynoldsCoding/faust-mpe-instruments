declare name "Glockenspiel";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "523 2093";
declare ringout "4";
declare window "0.04 0.6";
declare description "Steel bars, bright and ringing. Slide moves from a soft mallet to a hard one.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

hard = 0.3 + 0.7 * mpe.slide;
tone = sl.modes(mpe.freq, (1, 2.76, 5.4, 8.93), (3.0, 1.2, 0.5, 0.25), (1, 0.4 * hard, 0.25 * hard, 0.15 * hard), 1, mpe.trigger);

process = tone * (0.35 + 0.65 * mpe.velocity) * 0.75;
