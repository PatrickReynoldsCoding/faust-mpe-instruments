declare version "1.0.0";
declare name "Duduk";
declare sound "reverb=0.4 reverbSize=0.7 reverbDamp=0.5 delay=0 brightness=1 drive=0 pressureCurve=0.85 release=0";
declare range "110 880";
declare description "Duduk, the Armenian double reed: warm, soft and breathy, its tone fitted to Equator2's Mellow Duduk played on a Seaboard. Press to blow: harder is louder and more nasal. Slide up opens the reed (brighter), slide down covers it (darker, more air). Glide and wiggle the finger for the scoops and turns; a note started while another sounds is slurred.";
declare artist "ROLI Seaboard demos (Equator2 Mellow Duduk)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (ROLI), 1:19-1:54, Equator2 Mellow Duduk (the upper line)";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
fit = library("duduk_fit.lib");        // tools/fitting/seaboard/brass-duduk/fit.py

// ---- breath: a soft start (air first, then the reed), slurs fade in under the last note ------
slur    = mpe.legato : ba.sAndH(mpe.trigger);
atk     = select2(slur, 0.05 + 0.06 * (1 - mpe.velocity), 0.045);
env     = en.asr(atk, 1, 0.16, mpe.gate) : si.smooth(ba.tau2pole(0.01));
since   = ba.countup(48000, mpe.trigger) / ma.SR;
press   = mpe.pressure : si.smooth(ba.tau2pole(0.04));
wander  = no.noise : fi.lowpass(1, 1.8) : *(150);           // about 1 rms: a held note breathes
breath  = (0.12 + 0.88 * press) * (1 + 0.05 * wander) : min(1.2);
reedOn  = min(1, env * 1.3) : pow(1.5);                      // the reed speaks a moment after the air
L       = breath * reedOn;

// ---- pitch: soft notes sag a little flat, a slow drift of a few cents --------------------------
sag     = -0.004 * (1 - press) - (1 - slur) * 0.01 * exp(-since / 0.06);
freq    = mpe.freq * (1 + sag + 0.0018 * wander) : max(20);
R       = log(mpe.freq / fit.fref) / log(2) : max(-0.8) : min(0.8) : si.smooth(ba.tau2pole(0.01));

// ---- tone: sawtooth through the fitted filter bank --------------------------------------------
reed    = (mpe.slide - 0.5) * 0.5 : si.smooth(ba.tau2pole(0.03));     // slide: open (+) or covered (-)
peak(fc, q, g) = fi.tf2(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)
with {
    A = ba.db2linear(g * 0.5); w = 2 * ma.PI * fc / ma.SR; al = sin(w) / (2 * q);
    b0 = 1 + al * A; b1 = -2 * cos(w); b2 = 1 - al * A;
    a0 = 1 + al / A; a1 = -2 * cos(w); a2 = 1 - al / A;
};
nb      = ba.count(fit.centres);
Lt      = L + reed : max(0) : min(1.25);
gain(i) = ba.take(i + 1, fit.a) + ba.take(i + 1, fit.b) * Lt + ba.take(i + 1, fit.c) * R;
bank    = seq(i, nb, peak(ba.take(i + 1, fit.centres), fit.q, gain(i)));
n(i)    = ba.take(i + 1, fit.norm);
level   = n(0) + n(1) * Lt + n(2) * Lt * Lt + n(3) * R + n(4) * R * R + n(5) * Lt * R;
// a soft top: the cane reed takes the edge off (a gentle low-pass that opens with the breath)
saw     = os.sawtooth(freq);
buzz    = saw : bank : *(ba.db2linear(-level)) : fi.lowpass(1, 3500 + 5000 * Lt);

// ---- air: breath through the reed, pulsing with it; more when soft or covered ---------------
airAmt  = 0.12 + 0.08 * (1 - press) + 0.12 * max(0, -reed * 2);
air     = no.noise : fi.bandpass(2, 600, 3200) : *(1 + 0.6 * saw) : *(airAmt * (0.4 + 0.6 * env));
puff    = no.noise : fi.bandpass(1, 500, 3000) : *((1 - slur) * 0.15 * exp(-since / 0.04));   // air before the reed

amp     = pow(breath, 1.3) * env;
process = (buzz * amp + air * pow(breath, 1.3) * env + puff * breath * mpe.gate) * 0.42;
