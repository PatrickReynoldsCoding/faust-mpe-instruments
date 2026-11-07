declare name "Alto Sax";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "139 880";
declare description "Reedy saxophone. Press for volume and growl, slide for the amount of edge.";
import("stdfaust.lib");
mpe = library("mpe.lib");

vib   = 1 + 0.003 * os.osc(5.2) * en.asr(0.35, 1, 0.1, mpe.gate);
edge  = 0.3 + 0.7 * mpe.slide;
wave  = os.sawtooth(mpe.freq * vib) * (0.5 + 0.5 * edge) + os.square(mpe.freq * vib) * (0.5 - 0.3 * edge);
cut   = 900 + 2800 * mpe.pressure * edge;
breath = no.noise : fi.highpass(1, 1500) * 0.02 * mpe.pressure;
amp   = mpe.gate * (0.45 + 0.55 * mpe.pressure) : si.lag_ud(0.04, 0.08);

process = ((wave : fi.lowpass(2, min(cut, mpe.freq * 12))) * 1.4 : ma.tanh) + breath : *(amp) * 0.6;
