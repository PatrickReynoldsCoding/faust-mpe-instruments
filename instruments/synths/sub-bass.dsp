declare name "Sub Bass";
declare sound "reverb=0.05 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "41 262";
declare description "Deep sine bass. Press to add grit, slide to add a harmonic or two.";
import("stdfaust.lib");
mpe = library("mpe.lib");

grit = 1 + 4 * mpe.pressure;
tone = os.osc(mpe.freq) + mpe.slide * 0.4 * os.osc(2 * mpe.freq);
amp  = mpe.gate * (0.6 + 0.4 * mpe.velocity) : si.lag_ud(0.005, 0.12);

process = tone * grit : ma.tanh : *(amp) * 0.8;
