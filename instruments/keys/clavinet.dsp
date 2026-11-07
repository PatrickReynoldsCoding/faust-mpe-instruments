declare name "Clavinet";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "98 1047";
declare ringout "2";
declare window "0.05 0.4";
declare description "Funky plucked clav. Slide is the wah, strike for a sharper bite.";
import("stdfaust.lib");
mpe = library("mpe.lib");

decay = mpe.trigger : fi.pole(ba.tau2pole(0.45 / 5));
env   = decay * en.asr(0.001, 1, 0.04, mpe.gate);
wave  = os.pulsetrain(mpe.freq, 0.2) : fi.dcblocker;
cut   = 400 + (1000 + 4000 * mpe.slide) * (0.3 + 0.7 * decay) * (0.5 + 0.5 * mpe.velocity);

process = wave : fi.lowpass(2, min(cut, mpe.freq * 14)) : *(env) * 0.55;
