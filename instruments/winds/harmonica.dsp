declare name "Harmonica";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "261 1568";
declare description "Reed buzz in a small cavity. Press to blow, slide for the cupped-hands wah.";
import("stdfaust.lib");
mpe = library("mpe.lib");

reed   = os.pulsetrain(mpe.freq, 0.35) : fi.dcblocker;
wah    = 1200 + 2500 * mpe.slide;
breath = no.noise : fi.highpass(1, 3000) * 0.03;
amp    = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.03, 0.06);

process = ((reed : fi.resonlp(wah, 1.5, 1)) * 0.5 + breath) * amp * 0.9;
