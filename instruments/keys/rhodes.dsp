declare name "Rhodes";
declare range "65 1047";
declare ringout "5";
declare description "Tine electric piano: a bell-like attack that mellows as it rings. Strike harder for bark; slide sets the tremolo.";
import("stdfaust.lib");
mpe = library("mpe.lib");

decay  = mpe.trigger : fi.pole(ba.tau2pole(1.8 / 5));
hold   = en.asr(0.002, 1, 0.25, mpe.gate);
env    = decay * (0.3 + 0.7 * hold);
index  = (0.3 + 2.5 * mpe.velocity) * (0.15 + 0.85 * decay);
tine   = os.oscp(mpe.freq, os.osc(mpe.freq) * index);
bell   = os.osc(mpe.freq * 7) * decay * decay * decay * 0.05 * mpe.velocity;
trem   = 1 - mpe.slide * 0.35 * (0.5 + 0.5 * os.osc(5.5));

process = (tine + bell) * env * trem * 0.5 * (0.5 + 0.5 * mpe.velocity + 0.4 * mpe.pressure);
