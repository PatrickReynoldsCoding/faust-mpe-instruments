declare name "Pad";
declare range "65 1047";
declare description "Warm detuned saw pad. Press to open the filter, slide to add brightness; slow attack and release.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// Three saws, a few cents apart, left and right slightly different for width.
saws(f, spread) = (os.sawtooth(f * (1 - spread)) + os.sawtooth(f) + os.sawtooth(f * (1 + spread))) / 3;
cutoff = 350 + 5500 * (0.1 + 0.9*mpe.pressure) * (0.35 + 0.65*mpe.slide) : si.smooth(ba.tau2pole(0.03));
amp    = mpe.gate * (0.4 + 0.6*mpe.pressure) : si.lag_ud(0.35, 0.7);
tone(spread) = saws(mpe.freq, spread) : fi.lowpass(2, min(cutoff, mpe.freq * 12)) : *(amp);

process = tone(0.004), tone(0.006) : *(0.5), *(0.5);
