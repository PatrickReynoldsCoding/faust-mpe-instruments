declare name "Oboe";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "233 1568";
declare description "Double reed: nasal and focused. Press to blow harder (and brighter), slide moves the reed's squeeze.";
import("stdfaust.lib");
mpe = library("mpe.lib");

vib   = 1 + 0.004 * (0.3 + 0.7 * mpe.pressure) * os.osc(5.4) * en.asr(0.3, 1, 0.1, mpe.gate);
reed  = os.sawtooth(mpe.freq * vib);
form  = reed <: (fi.resonbp(1100, 3, 1), fi.resonbp(2800, 4, 1), _ * 0.15) :> _;
breath = no.noise : fi.resonbp(min(mpe.freq * 2, 6000), 2, 1) * 0.03;
amp   = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.04, 0.07);

process = (form * (0.5 + 0.5 * mpe.slide) + reed * 0.1 + breath) * amp * 0.45;
