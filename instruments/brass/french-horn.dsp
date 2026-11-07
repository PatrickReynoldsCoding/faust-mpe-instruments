declare name "French Horn";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "87 698";
declare description "Mellow, distant horn that swells in. Press to brighten, slide for a stopped, brassy edge.";
import("stdfaust.lib");
mpe = library("mpe.lib");

swell  = en.asr(0.18, 1, 0.25, mpe.gate);
stopped = mpe.slide;
cutoff = 450 + (800 + 2200 * mpe.pressure) * swell * (1 + 0.6 * stopped) : si.smooth(ba.tau2pole(0.02));
vib    = 1 + 0.0025 * os.osc(4.8) * en.asr(0.6, 1, 0.1, mpe.gate);
tone   = (os.sawtooth(mpe.freq * vib) * 0.7 + os.osc(mpe.freq * vib) * 0.5) : fi.lowpass(3, min(cutoff, mpe.freq * 10));
amp    = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.1, 0.2);

process = tone * amp * 0.9;
