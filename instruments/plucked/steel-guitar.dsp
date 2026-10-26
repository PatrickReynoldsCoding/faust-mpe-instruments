declare name "Steel Guitar";
declare range "98 659";
declare ringout "8";
declare description "Plucked steel string. Slide sets where the string is plucked; it rings after you lift.";
import("stdfaust.lib");
mpe = library("mpe.lib");

pluck = 0.15 + 0.7*mpe.slide;
gain  = 0.3 + 0.7*mpe.velocity;

process = pm.guitar(pm.f2l(mpe.freq), pluck, gain, mpe.gate) * 12 : ma.tanh : *(0.6);
