declare name "Supersaw";
declare range "65 1047";
declare description "Seven detuned saws. Slide spreads them wider, press opens the filter.";
import("stdfaust.lib");
mpe = library("mpe.lib");

spread = 0.0015 + 0.0045 * mpe.slide : si.smooth(ba.tau2pole(0.03));
saws   = par(i, 7, os.sawtooth(mpe.freq * (1 + (i - 3) * spread))) :> /(7);
cutoff = 1500 + 7000 * mpe.pressure : si.smooth(ba.tau2pole(0.02));
amp    = mpe.gate * (0.5 + 0.5 * mpe.pressure) : si.lag_ud(0.01, 0.25);

process = saws : fi.lowpass(2, min(cutoff, mpe.freq * 16)) : *(amp) * 0.7;
