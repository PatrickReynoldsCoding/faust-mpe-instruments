declare name "Clarinet";
declare version "2.0.0";
declare sound "reverb=0.3 reverbSize=0.5 reverbDamp=0.45 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "147 1568";
declare description "B-flat clarinet fitted to SWAM's on a Seaboard. Press to blow: from a hollow, nearly pure pianissimo to a reedy forte. Hollow (odd harmonics) in the low register, rounder above. Slide moves the embouchure: down darker, up brighter. Slurred notes join without a new tongued attack.";
declare artist "ROLI Seaboard demos (SWAM clarinet)";
declare songs "Seaboard RISE x SWAM & Camelot Pro (ROLI, performed by Heen-Wah Wai), 0:17-0:46, SWAM clarinet in a cello | clarinet | oboe split";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
reed = library("reed_engine.lib");
fit = library("clarinet_fit.lib");

// A cylinder: only odd harmonics in the low (chalumeau) register, more even ones from the
// throat notes up (sounding about F#4 to B4) and in the clarion.
f      = mpe.freq;
odd    = 0.86 - 0.30 * max(0, min(1, log(f / 330) / log(2) / 0.6)) - 0.12 * max(0, min(1, log(f / 900) / log(2)));
regs   = pow(f / 220, 0 - fit.reg);

process = reed.voice(f, odd, fit.lo * regs, fit.hi * regs, 0.5, 0.03, 1700, 0.7, 0.45, 0, 0.3) * 0.5 * pow(mpe.freq / 330, 0 - fit.lvl);   // level across the range, fitted
post = reed.body(fit.eq, fit.out);
