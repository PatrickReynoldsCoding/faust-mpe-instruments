declare name "808 Boom";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "41 196";
declare ringout "3";
declare window "0.1 1.0";
declare description "Long sine kick that falls into the note. Press to hold the boom, slide for the length of the fall.";
import("stdfaust.lib");
mpe = library("mpe.lib");

fall  = mpe.trigger : fi.pole(ba.tau2pole(0.02 + 0.06 * mpe.slide));
f     = mpe.freq * (1 + 2.5 * fall);
env   = max(mpe.trigger : fi.pole(ba.tau2pole(0.5 / 3)), en.asr(0.001, 1, 0.1, mpe.gate) * mpe.pressure);
click = mpe.trigger : fi.pole(ba.tau2pole(0.003));

process = (os.osc(f) * 1.6 : ma.tanh) * env * (0.5 + 0.5 * mpe.velocity) * 0.7 + click * 0.1;
