declare name "Celesta";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "260 2093";
declare ringout "4";
declare window "0.04 0.5";
declare description "Struck steel plates, soft and glassy. Slide moves the hammer: bell-like to round.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

tone = sl.modes(mpe.freq, (1, 4, 9.2, 15), (2.2, 0.8, 0.3, 0.15), (1, 0.35 * (0.3 + 0.7 * (1 - mpe.slide)), 0.12 * (1 - mpe.slide), 0.05), 1, mpe.trigger);

process = tone * (0.35 + 0.65 * mpe.velocity) * 0.7;
