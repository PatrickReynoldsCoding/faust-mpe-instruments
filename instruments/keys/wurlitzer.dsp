declare name "Wurlitzer";
declare range "65 1047";
declare ringout "4";
declare description "Reed electric piano: reedy and a little rough when played hard. Slide adds growl.";
import("stdfaust.lib");
mpe = library("mpe.lib");

decay = mpe.trigger : fi.pole(ba.tau2pole(1.3 / 5));
env   = decay * (0.25 + 0.75 * en.asr(0.002, 1, 0.2, mpe.gate));
wave  = os.osc(mpe.freq) + 0.5 * os.osc(2 * mpe.freq) + 0.25 * os.osc(3 * mpe.freq);
drive = 1 + (1 + 4 * mpe.slide) * (0.3 + 0.7 * mpe.velocity);

process = (wave * drive + 0.3 : ma.tanh : fi.dcblocker) * env * 0.5;
