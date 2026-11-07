declare name "Toy Piano";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "260 2093";
declare ringout "3";
declare pitched "no";
declare window "0.04 0.4";
declare description "Tiny metal bars, clinky and out of tune with themselves. Slide changes the click.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

tone  = sl.modes(mpe.freq, (1, 2.76, 5.4, 8.9), (1.0, 0.4, 0.15, 0.08), (1, 0.5, 0.3, 0.2), 1, mpe.trigger);
click = sl.burst(2, mpe.trigger) * mpe.slide * 0.3;

process = (tone + click) * (0.4 + 0.6 * mpe.velocity) * 0.7;
