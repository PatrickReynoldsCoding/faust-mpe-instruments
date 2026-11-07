declare name "Acid Bass";
declare sound "reverb=0.05 reverbSize=0.245 reverbDamp=0.4 delay=0.2 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "65 523";
declare description "Squelchy resonant saw bass. Strike for a bigger filter snap, slide for resonance, press to open.";
import("stdfaust.lib");
mpe = library("mpe.lib");

snap   = en.ar(0.002, 0.25, mpe.gate) * (0.3 + 0.7 * mpe.velocity);
cutoff = 150 + 300 * mpe.pressure * 8 + 3500 * snap : si.smooth(ba.tau2pole(0.005));
q      = 1.5 + 6 * mpe.slide;
amp    = mpe.gate : si.lag_ud(0.003, 0.08);

process = os.sawtooth(mpe.freq) : fi.resonlp(min(cutoff, mpe.freq * 14), q, 1) : ma.tanh : *(amp) * 0.55;
