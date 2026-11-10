declare version "1.0.0";
declare name "Sync Funk";
declare sound "reverb=0.12 reverbSize=0.3 reverbDamp=0.5 delay=0 brightness=1 drive=0.15 pressureCurve=0.8 release=0";
declare range "36 523";
declare artist "ROLI Seaboard demos (Cypher2 Mean Hard-Sync Funk 5D)";
declare songs "Seaboard RISE x SWAM & Camelot Pro (ROLI), 1:02-1:34";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
declare description "Mean hard-sync funk bass, after Cypher2's Mean Hard-Sync Funk 5D. Strike hard and the note dives in from two octaves above; press to bring in the synced oscillator and open the filter until it snarls; slide up the key to push the sync higher. Short and tight when you lift.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// Fitted to the Seaboard demo (numbers in tools/fitting/seaboard/synths/README.md):
// - at rest the tone is a square/saw mix (harmonics 0 -13 -7 -23 -17 dB) through one pole at 8 x f0;
// - notes struck on the beat dive in from about two octaves (+12 semitones 30 ms in), falling with a 55 ms time constant;
// - the note stops within about 20 ms of the lift.
trig  = mpe.trigger;
since = ba.countup(ma.SR * 4, trig) / ma.SR;            // seconds since the strike
vel   = mpe.velocity;
dive  = 24 * max(0, min(1, (vel - 0.3) / 0.6)) * (1 - 0.6 * mpe.legato);
pitch = mpe.freq * ba.semi2ratio(dive * exp(-since / 0.055));

press = mpe.pressure : si.smooth(ba.tau2pole(0.02));
pp    = press * press;                                  // timbre comes in late: a normal touch keeps the fitted tone, a hard press snarls
slide = mpe.slide : si.smooth(ba.tau2pole(0.03));
bite  = exp(-since / 0.10) * vel * vel;         // the attack's snarl: sync and filter jump, then settle

// Master phase; the slave restarts with it (hard sync). The ratio sweeps with pressure, slide and the bite.
phase = os.lf_sawpos(pitch);
ratio = 1.6 + 4.5 * pp + 2.5 * slide + 2 * bite;
sync  = 2 * ma.frac(phase * ratio) - 1;
sq    = (phase < 0.5) * 2 - 1;
saw   = 2 * phase - 1;
base  = 0.62 * sq + 0.38 * saw;                         // the fitted rest tone
smix  = min(1, 0.9 * pp + 0.25 * slide * pp + 0.3 * bite);
osc   = base * (1 - 0.6 * smix) + sync * smix * 0.8;
rest  = fi.pole(p) * (1 - p) with { p = exp(-2 * ma.PI * min(pitch * 8, 6000) / ma.SR); };   // the fitted rest tone: one pole at 8 x f0

cut   = pitch * (10 + 30 * pp + 16 * bite + 8 * slide) : min(14000);
open  = min(1, 1.6 * pp + bite);                     // how far the rest filter is bypassed
tone  = osc : fi.dcblocker <: (rest * (1 - open)), *(open) :> fi.resonlp(cut, 0.9 + 2 * pp, 1);
amp   = mpe.gate * (0.55 + 0.25 * vel + 0.3 * press) : si.lag_ud(0.002, 0.018);

process = tone * amp * 0.42;
