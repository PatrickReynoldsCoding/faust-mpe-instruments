declare name "Marimba";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 1047";
declare ringout "4";
declare window "0.04 0.4";
declare description "Struck wooden bar. Slide changes where the mallet hits the bar.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// The library's own marimba rings for 0.1 s (maxT60 = 0.1), so rebuild it from its parts
// with a longer ring.
ring     = 1.4;                                              // seconds for the lowest mode to die away
position = int(mpe.slide * 3.99);                            // which part of the bar is struck, 0..3
gain     = 0.3 + 0.7*mpe.velocity;

strike = pm.strikeModel(10, 6500, 0.5, gain, mpe.gate);
bar    = pm.marimbaBarModel(mpe.freq, position, ring, 1, 5) : pm.marimbaResTube(pm.f2l(mpe.freq));

process = strike : bar : *(0.8) * 2.5;
