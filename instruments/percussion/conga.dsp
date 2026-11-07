declare name "Conga";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "180 700";
declare ringout "1";
declare pitched "no";
declare window "0.03 0.2";
declare description "Hand drum tuned to the note. Slide goes from an open tone through a muffled one to a slap.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

slap  = max(0, mpe.slide - 0.6) / 0.4;
open  = 1 - 0.7 * min(1, mpe.slide / 0.6);
fall  = 1 + 0.12 * (mpe.trigger : fi.pole(ba.tau2pole(0.015)));
tone  = sl.modes(mpe.freq * fall, (1, 1.58, 2.3), (0.45 * (0.3 + open), 0.2, 0.1), (1, 0.4, 0.2), 1, mpe.trigger);
snap  = sl.burst(4, mpe.trigger) : fi.highpass(2, 1500) * slap * 0.7;

process = (tone + snap) * (0.35 + 0.65 * mpe.velocity) * 0.9;
