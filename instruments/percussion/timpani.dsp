declare name "Timpani";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "73 196";
declare ringout "4";
declare pitched "no";
declare window "0.05 0.8";
declare description "Kettle drum tuned to the note you play. Strike harder for a bigger thump; slide moves the stick from the centre to the rim.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

drop  = 1 + 0.25 * (mpe.trigger : fi.pole(ba.tau2pole(0.03)));
rim   = mpe.slide;
tone  = sl.modes(mpe.freq * drop, (1, 1.5, 1.99, 2.44, 2.89), (1.8, 1.2, 0.9, 0.6, 0.4), (1 - 0.7 * rim, 0.5, 0.35 + 0.4 * rim, 0.25, 0.15), 1, mpe.trigger);
thump = sl.burst(8, mpe.trigger) : fi.lowpass(2, 300) * 0.5;

process = (tone + thump) * (0.35 + 0.65 * mpe.velocity) * 0.9;
