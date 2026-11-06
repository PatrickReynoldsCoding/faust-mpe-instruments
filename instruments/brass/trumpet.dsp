declare name "Trumpet";
declare range "185 1047";
declare description "Bright brass. Press to blow harder (the tone gets brassier), slide moves toward a muted sound.";
import("stdfaust.lib");
mpe = library("mpe.lib");

swell  = en.asr(0.05, 1, 0.1, mpe.gate);
bright = 0.3 + 0.7 * mpe.pressure;
cutoff = 600 + 5500 * bright * swell * (1 - 0.6 * (1 - mpe.slide)) : si.smooth(ba.tau2pole(0.008));
vib    = 1 + 0.003 * os.osc(5.5) * en.asr(0.4, 1, 0.1, mpe.gate);
tone   = os.sawtooth(mpe.freq * vib) : fi.lowpass(2, min(cutoff, mpe.freq * 16));
amp    = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.03, 0.08);

process = tone * 1.2 : ma.tanh : *(amp) * 0.6;
