declare name "Trombone";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "82 523";
declare description "Warm, round brass with a slow lip. Press to push the tone brassy, slide for a muted wah.";
import("stdfaust.lib");
mpe = library("mpe.lib");

swell  = en.asr(0.1, 1, 0.12, mpe.gate);
cutoff = 350 + (1200 + 3500 * mpe.pressure) * swell * (0.4 + 0.6 * mpe.slide) : si.smooth(ba.tau2pole(0.01));
vib    = 1 + 0.003 * os.osc(5) * en.asr(0.5, 1, 0.1, mpe.gate);
tone   = os.sawtooth(mpe.freq * vib) : fi.lowpass(2, min(cutoff, mpe.freq * 14));
amp    = mpe.gate * (0.45 + 0.55 * mpe.pressure) : si.lag_ud(0.06, 0.1);

process = tone * 1.2 : ma.tanh : *(amp) * 0.6;
