declare name "Vibraphone";
declare range "175 1400";
declare ringout "8";
declare description "Struck metal bar with a damper: rings while your finger is down, stops when you lift. Press for tremolo.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// A vibraphone bar is tuned so its overtones sit at about 1x, 4x and 10x the pitch.
ratios = 1.0, 4.0, 10.0;
levels = 1.0, 0.45, 0.20;
decays = 5.0, 2.2, 0.9;                                  // seconds to fade while the finger is down

// Fading time: long while held, short once the damper comes down.
held(i) = ba.take(i+1, decays);
fade(i) = (mpe.gate * held(i) + (1 - mpe.gate) * 0.5) : si.smooth(ba.tau2pole(0.02));
// Q of a resonator that rings for `t` seconds at frequency f.
qFor(f, t) = max(1, ma.PI * f * t / 6.91);

mode(i) = fi.resonbp(f, qFor(f, fade(i)), ba.take(i+1, levels))
with { f = mpe.freq * ba.take(i+1, ratios); };

strike = no.noise * en.ar(0.0004, 0.005, mpe.trigger) * (0.5 + 0.5*mpe.velocity);
tremolo = 1 - mpe.pressure * 0.45 * (1 + os.osc(5.5)) * 0.5;

process = strike <: par(i, 3, mode(i)) :> _ : *(tremolo) * 1.3 * pow(200 / mpe.freq, 0.65);
