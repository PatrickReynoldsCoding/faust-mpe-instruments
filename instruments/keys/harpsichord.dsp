declare name "Harpsichord";
declare range "130 1047";
declare ringout "1";
declare window "0.05 0.4";
declare description "Plucked quill strings with a jack damper: it stops when you lift. Slide adds the octave coupler.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

pick = sl.burst(3, mpe.trigger);
g    = 0.9965 * mpe.gate + 0.93 * (1 - mpe.gate) : si.smooth(0.9);
str(f, lvl) = sl.string(f, g, pick) * lvl;

process = (str(mpe.freq, 1) + str(min(mpe.freq * 2, 4800), 0.7 * mpe.slide)) * 1.2 : ma.tanh;
