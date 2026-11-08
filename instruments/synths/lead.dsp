declare version "1.1.0";       // 1.1.0: level evened out with the other sounds (the 1.0.0 is kept in versions/)
declare name "Lead";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 1047";
declare description "Singing mono-style lead. Press to open the filter and drive, slide to blend saw into square.";
import("stdfaust.lib");
mpe = library("mpe.lib");

blend  = mpe.slide : si.smooth(ba.tau2pole(0.03));
wave   = (1 - blend) * os.sawtooth(mpe.freq) + blend * os.square(mpe.freq);
cutoff = 600 + 6000 * mpe.pressure : si.smooth(ba.tau2pole(0.02));
amp    = mpe.gate * (0.5 + 0.5*mpe.pressure) : si.lag_ud(0.015, 0.12);
drive  = 1 + 3*mpe.pressure;

process = wave : fi.resonlp(min(cutoff, mpe.freq * 14), 1.3, 1) : *(drive) : ma.tanh : *(amp) * 0.3;     // 1.1.0: -2.4 dB (0.4 before), to -20 dBFS with the other sounds
