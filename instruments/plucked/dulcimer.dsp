declare name "Hammered Dulcimer";
declare range "130 1047";
declare ringout "5";
declare window "0.05 0.6";
declare description "Two strings per note, struck with little hammers: a shimmering, slightly chorused ring. Slide widens the beating.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

hit    = sl.burst(2.5, mpe.trigger) * (0.3 + 0.7 * mpe.velocity);
beat   = 1 + 0.0015 + 0.004 * mpe.slide;

process = (sl.string(mpe.freq, 0.9985, hit) + sl.string(mpe.freq * beat, 0.9985, hit)) * 1.2 : ma.tanh : *(0.6);
