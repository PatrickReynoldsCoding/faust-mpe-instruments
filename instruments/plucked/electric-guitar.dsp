declare name "Electric Guitar";
declare range "98 440";
declare ringout "6";
declare window "0.05 0.6";
declare description "Plucked electric string through an overdrive. Press to push the amp harder, slide to move the pickup.";
import("stdfaust.lib");
mpe = library("mpe.lib");

pluck = 0.2 + 0.7 * mpe.slide;
gain  = 0.4 + 0.6 * mpe.velocity;
dry   = pm.elecGuitar(pm.f2l(mpe.freq), pluck, 1, gain, mpe.gate);
push  = 3 + 12 * mpe.pressure;

process = dry * push : ma.tanh : fi.lowpass(2, 4500) : *(0.45);
