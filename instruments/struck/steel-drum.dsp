declare name "Steel Drum";
declare range "261 1047";
declare ringout "4";
declare window "0.04 0.6";
declare description "Tuned pan with its octave and twelfth, pulsing slowly as it rings. Slide sets the pulse.";
import("stdfaust.lib");
mpe = library("mpe.lib");
sl = library("synth.lib");

pulse = 1 + 0.003 + 0.01 * mpe.slide;
tone  = sl.modes(mpe.freq, (1, 2, 3, 4.1), (2.2, 1.6, 0.8, 0.3), (1, 0.6, 0.25, 0.1), 1, mpe.trigger)
      + 0.4 * sl.modes(mpe.freq * pulse, (1, 2), (2.0, 1.4), (1, 0.5), 1, mpe.trigger);

process = tone * (0.35 + 0.65 * mpe.velocity) * 0.6;
