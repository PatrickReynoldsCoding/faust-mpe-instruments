declare version "2.0.0";       // 2.0.0: tone fitted to the SWAM trumpet in ROLI's BLOCK M demo (1.0.0 kept in versions/)
declare name "Trumpet";
declare sound "reverb=0.3 reverbSize=0.55 reverbDamp=0.45 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "165 1175";
declare description "Trumpet, its tone fitted to a SWAM trumpet played on a Seaboard. Press to blow: harder is louder and much brassier. Slide up for a brighter, tighter lip; slide right down for a mute. A note started while another sounds is slurred, without a new tongue.";
declare artist "ROLI Seaboard demos (SWAM trumpet)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (ROLI), 2:14-2:50, SWAM trumpet";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
fit = library("trumpet_fit.lib");      // tools/fitting/seaboard/brass-duduk/fit.py

// ---- breath -------------------------------------------------------------------------------
// A tongued note (legato 0) starts fast, with a little accent and a "t" of air; a slurred one
// (legato 1) fades in under the note it follows, with no new attack.
slur    = mpe.legato : ba.sAndH(mpe.trigger);
tongue  = 1 - slur;
atk     = select2(slur, 0.018 + 0.025 * (1 - mpe.velocity), 0.04);
env     = en.asr(atk, 1, 0.07, mpe.gate) : si.smooth(ba.tau2pole(0.004));
since   = ba.countup(48000, mpe.trigger) / ma.SR;            // seconds since the note started
accent  = 1 + tongue * (0.25 + 0.35 * mpe.velocity) * exp(-since / 0.06);
press   = mpe.pressure : si.smooth(ba.tau2pole(0.025));
// a held note is never quite still: slow wander of the breath and the lips
wander  = no.noise : fi.lowpass(1, 2.5) : *(130);            // about 1 rms
breath  = (0.1 + 0.9 * press) * (1 + 0.04 * wander) * accent : min(1.2);
L       = breath * min(1, env * 1.15);                      // the highs bloom as the note speaks

// ---- pitch: a tongued note speaks a little flat and settles; the lips wander a few cents ---
scoop   = tongue * (-0.012 - 0.01 * mpe.velocity) * exp(-since / 0.035);
freq    = mpe.freq * (1 + scoop + 0.0016 * wander) : max(20);
R       = log(mpe.freq / fit.fref) / log(2) : max(-0.7) : min(0.9) : si.smooth(ba.tau2pole(0.01));   // the fitted range

// ---- tone: sawtooth through the fitted filter bank -------------------------------------------
lip     = max(0, mpe.slide - 0.5) * 0.5;                    // slide up: tighter lip, brighter
peak(fc, q, g) = fi.tf2(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)
with {
    A = ba.db2linear(g * 0.5); w = 2 * ma.PI * fc / ma.SR; al = sin(w) / (2 * q);
    b0 = 1 + al * A; b1 = -2 * cos(w); b2 = 1 - al * A;
    a0 = 1 + al / A; a1 = -2 * cos(w); a2 = 1 - al / A;
};
nb      = ba.count(fit.centres);
Lt      = min(1.25, L + lip);
gain(i) = ba.take(i + 1, fit.a) + ba.take(i + 1, fit.b) * Lt + ba.take(i + 1, fit.c) * R;
bank    = seq(i, nb, peak(ba.take(i + 1, fit.centres), fit.q, gain(i)));
n(i)    = ba.take(i + 1, fit.norm);
level   = n(0) + n(1) * Lt + n(2) * Lt * Lt + n(3) * R + n(4) * R * R + n(5) * Lt * R;   // the bank's own loudness
buzz    = os.sawtooth(freq) : bank : *(ba.db2linear(-level));

// breath noise, and the tongue's "t" on a tongued attack
air     = no.noise : fi.bandpass(1, 1200, 4500) : *(0.012 * L * L);
tee     = no.noise : fi.bandpass(1, 2000, 7000) : *(tongue * (0.012 + 0.025 * mpe.velocity) * exp(-since / 0.01));

// slide right down: a straight-ish mute (thin, nasal, quieter)
mute    = (0.25 - mpe.slide) / 0.25 : max(0) : min(1) : si.smooth(ba.tau2pole(0.03));
muted(x) = x : fi.highpass(2, 700) : peak(1800, 2.5, 10) : fi.lowpass(2, 5000) : *(0.6);
tone    = buzz + air <: _, muted : *(1 - mute), *(mute) :> _;

amp     = pow(breath, 1.4) * env;
process = (tone * amp + tee * env) * 0.42;       // about -20 dBFS a note at pressure 0.6
