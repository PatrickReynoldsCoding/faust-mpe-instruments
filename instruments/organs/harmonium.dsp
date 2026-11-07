declare name "Harmonium";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "98 880";
declare description "Pump-organ reeds with a gentle tremulant. Press to blow harder, slide to open the stop.";
import("stdfaust.lib");
mpe = library("mpe.lib");

trem = 1 - 0.12 * (0.5 + 0.5 * os.osc(5));
tone = os.square(mpe.freq) * 0.5 + os.sawtooth(mpe.freq * 1.002) * 0.5 + 0.1 * os.osc(mpe.freq * 0.5);
cut  = 900 + 2200 * mpe.slide;
amp  = mpe.gate * (0.45 + 0.55 * mpe.pressure) : si.lag_ud(0.09, 0.12);

process = tone : fi.lowpass(2, min(cut, mpe.freq * 10)) : *(amp * trem) * 0.5;
