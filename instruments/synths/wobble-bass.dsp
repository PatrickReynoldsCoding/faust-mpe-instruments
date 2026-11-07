declare name "Wobble Bass";
declare sound "reverb=0.05 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "41 262";
declare description "Saw bass with a filter that wobbles. Slide sets the wobble speed, press the depth.";
import("stdfaust.lib");
mpe = library("mpe.lib");

rate   = 1 + 7 * mpe.slide;
wobble = 0.5 + 0.5 * os.osc(rate);
cutoff = 120 + (400 + 3500 * mpe.pressure) * wobble;
amp    = mpe.gate : si.lag_ud(0.005, 0.1);

process = (os.sawtooth(mpe.freq) + os.sawtooth(mpe.freq * 1.005)) * 0.5 : fi.resonlp(min(cutoff, mpe.freq * 16), 3, 1) : ma.tanh : *(amp) * 0.6;
