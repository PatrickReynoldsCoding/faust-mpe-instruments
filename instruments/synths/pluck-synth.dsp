declare name "Pluck Synth";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 1047";
declare ringout "2";
declare window "0.05 0.4";
declare description "Short synth pluck: a saw whose filter closes after the strike. Slide sets how long it rings.";
import("stdfaust.lib");
mpe = library("mpe.lib");

decay  = 0.12 + 0.9 * mpe.slide;
env    = mpe.trigger : fi.pole(ba.tau2pole(decay / 5));
body   = mpe.trigger : fi.pole(ba.tau2pole((0.2 + 1.5 * mpe.slide) / 5));
cutoff = 300 + 6000 * env * (0.3 + 0.7 * mpe.velocity);
tone   = (os.sawtooth(mpe.freq) + os.sawtooth(mpe.freq * 1.003)) * 0.5;

process = tone : fi.lowpass(2, min(cutoff, mpe.freq * 16)) : *(body) * 0.8;
