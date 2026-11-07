declare name "Accordion";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "130 1047";
declare description "Musette accordion: three reeds, two slightly out of tune. Press is the bellows, slide the register from dark to bright.";
import("stdfaust.lib");
mpe = library("mpe.lib");

reed(f) = os.sawtooth(f) * 0.6 + os.square(f) * 0.4;
tone    = (reed(mpe.freq) + reed(mpe.freq * 1.006) + reed(mpe.freq * 0.994)) / 3;
cutoff  = 1200 + 4000 * mpe.slide;
amp     = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.04, 0.06);

process = tone : fi.lowpass(2, min(cutoff, mpe.freq * 12)) : *(amp) * 0.55;
