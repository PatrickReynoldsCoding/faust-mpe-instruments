declare name "Sync Lead";
declare range "130 1047";
declare description "Hard-sync lead. Press to sweep the synced oscillator up and make it scream.";
import("stdfaust.lib");
mpe = library("mpe.lib");

ratio = 1.2 + 5 * mpe.pressure + 2 * mpe.slide : si.smooth(ba.tau2pole(0.03));
phase = os.lf_sawpos(mpe.freq);
wave  = ma.frac(phase * ratio) * 2 - 1;
amp   = mpe.gate * (0.5 + 0.5 * mpe.pressure) : si.lag_ud(0.01, 0.1);

process = wave : fi.dcblocker : fi.lowpass(2, min(9000, mpe.freq * 20)) : *(amp) * 0.4;
