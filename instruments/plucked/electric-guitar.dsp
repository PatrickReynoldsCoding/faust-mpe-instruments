declare name "Electric Guitar";
declare sound "reverb=0.2 reverbSize=0.245 reverbDamp=0.4 delay=0.2 brightness=1 drive=0.2 pressureCurve=1 release=0";
declare status "legacy";
declare range "98 440";
declare ringout "6";
declare window "0.05 0.6";
declare description "Plucked electric string through an overdrive. Press to push the amp harder, slide to move the pickup.";
import("stdfaust.lib");
mpe = library("mpe.lib");
fx = library("fx.lib");

pluck = 0.2 + 0.7 * mpe.slide;
gain  = 0.4 + 0.6 * mpe.velocity;
dry   = pm.elecGuitar(pm.f2l(mpe.freq), pluck, 1, gain, mpe.gate);
push  = 3 + 12 * mpe.pressure;

process = dry * push : ma.tanh : *(0.45);

// The cabinet and the room it is in, once for all the notes.
post = fx.cab : fx.room(0.18, 0.5);
