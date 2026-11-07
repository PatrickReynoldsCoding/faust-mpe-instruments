declare name "Rhodes";
declare sound "reverb=0.3 reverbSize=0.3 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "65 1047";
declare ringout "5";
declare description "Tine electric piano: a bell-like attack that mellows as it rings. Strike harder for bark; slide sets the tremolo.";
import("stdfaust.lib");
mpe = library("mpe.lib");
fx = library("fx.lib");

decay  = mpe.trigger : fi.pole(ba.tau2pole(1.8 / 5));
hold   = en.asr(0.002, 1, 0.25, mpe.gate);
env    = decay * (0.3 + 0.7 * hold);
index  = (0.3 + 2.5 * mpe.velocity) * (0.15 + 0.85 * decay);
tine   = os.oscp(mpe.freq, os.osc(mpe.freq) * index);
bell   = os.osc(mpe.freq * 7) * decay * decay * decay * 0.05 * mpe.velocity;
trem   = 1 - mpe.slide * 0.35 * (0.5 + 0.5 * os.osc(5.5));

process = (tine + bell) * env * trem * 0.5 * (0.5 + 0.5 * mpe.velocity + 0.4 * mpe.pressure);

// The amp's small spring-like room, once for all the notes.
post = fx.room(0.25, 0.45);
