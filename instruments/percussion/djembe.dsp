declare name "Djembe";
declare sound "reverb=0.2 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "130 523";
declare ringout "1";
declare pitched "no";
declare window "0.03 0.2";
declare description "Goblet hand drum from the physical-model library. Slide changes where the hand strikes.";
import("stdfaust.lib");
mpe = library("mpe.lib");

hit = pm.strikeModel(10, 5000 + 6000 * mpe.slide, 0.5, 0.3 + 0.7 * mpe.velocity, mpe.gate);

process = hit : pm.djembeModel(mpe.freq) * 4 : ma.tanh : *(0.8);
