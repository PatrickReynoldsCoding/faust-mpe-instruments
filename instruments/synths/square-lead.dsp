declare name "Square Lead";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "130 1047";
declare description "Pulse-width-modulated square lead. Slide sets the width, press adds vibrato.";
import("stdfaust.lib");
mpe = library("mpe.lib");

vib   = 1 + 0.008 * mpe.pressure * os.osc(5.5);
duty  = 0.5 - 0.4 * mpe.slide * (0.6 + 0.4 * os.osc(0.7));
wave  = os.pulsetrain(mpe.freq * vib, duty) : fi.dcblocker;
amp   = mpe.gate * (0.6 + 0.4 * mpe.pressure) : si.lag_ud(0.01, 0.1);

process = wave : fi.lowpass(1, 5000) : *(amp) * 0.4;
