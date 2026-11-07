declare name "Whistle";
declare sound "reverb=0.35 reverbSize=0.4 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "523 2093";
declare description "A pure whistle with a little air. Press for vibrato, slide for airiness.";
import("stdfaust.lib");
mpe = library("mpe.lib");

vib  = 1 + 0.006 * mpe.pressure * os.osc(6) * en.asr(0.25, 1, 0.1, mpe.gate);
air  = no.noise : fi.resonbp(mpe.freq, 30, 1) * (0.5 + 2 * mpe.slide);
amp  = mpe.gate * (0.5 + 0.5 * mpe.pressure) : si.lag_ud(0.04, 0.08);

process = (os.osc(mpe.freq * vib) * 0.5 + air * 0.5) * amp * 0.25;
