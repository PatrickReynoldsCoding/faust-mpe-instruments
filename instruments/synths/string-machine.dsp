declare name "String Machine";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "65 1047";
declare description "Vintage ensemble strings: detuned saws, slow chorus. Press to brighten, slide for the swell.";
import("stdfaust.lib");
mpe = library("mpe.lib");
fx = library("fx.lib");

chorus(f) = (os.sawtooth(f * (1 + 0.003 * os.osc(0.6))) + os.sawtooth(f * (1 - 0.003 * os.oscp(0.5, 1.7))) + os.sawtooth(f * 1.002)) / 3;
tone   = chorus(mpe.freq) + 0.08 * chorus(mpe.freq * 0.5);
cutoff = 800 + 4000 * (0.2 + 0.8 * mpe.pressure) : si.smooth(ba.tau2pole(0.03));
amp    = mpe.gate * (0.5 + 0.5 * mpe.pressure) : si.lag_ud(0.05 + 0.4 * (1 - mpe.slide), 0.4);

process = tone : fi.lowpass(2, min(cutoff, mpe.freq * 12)) : *(amp) * 0.45;

// The ensemble chorus, once for all the notes.
post = fx.ensemble;
