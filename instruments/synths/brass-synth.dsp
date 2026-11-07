declare name "Brass Synth";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "82 1047";
declare description "Analog brass: the filter swells open after the attack. Press for more bite, slide for a brighter horn.";
import("stdfaust.lib");
mpe = library("mpe.lib");

swell  = en.asr(0.09, 1, 0.15, mpe.gate);
cutoff = 300 + (1200 + 3500 * mpe.pressure) * (0.4 + 0.6 * mpe.slide) * swell : si.smooth(ba.tau2pole(0.01));
tone   = (os.sawtooth(mpe.freq * 0.996) + os.sawtooth(mpe.freq * 1.004)) * 0.5;
amp    = mpe.gate * (0.55 + 0.45 * mpe.pressure) : si.lag_ud(0.04, 0.12);

process = tone : fi.lowpass(2, min(cutoff, mpe.freq * 14)) : *(amp) * 0.7;
