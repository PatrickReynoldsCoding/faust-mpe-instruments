declare name "Oboe";
declare version "2.0.0";
declare sound "reverb=0.3 reverbSize=0.5 reverbDamp=0.45 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "233 1568";
declare description "Oboe fitted to SWAM's on a Seaboard: a double reed, nasal and focused, its strongest harmonics around 1.2-2 kHz. Press to blow: soft and sweet to loud and penetrating. Slide moves the reed's squeeze: down darker, up brighter. Slurred notes join without a new tongued attack.";
declare artist "ROLI Seaboard demos (SWAM oboe)";
declare songs "Seaboard RISE x SWAM & Camelot Pro (ROLI, performed by Heen-Wah Wai), 0:17-0:46, SWAM oboe in a cello | clarinet | oboe split";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
reed = library("reed_engine.lib");
fit = library("oboe_fit.lib");

f      = mpe.freq;
regs   = pow(f / 330, 0 - fit.reg);

process = reed.voice(f, 0.03, fit.lo * regs, fit.hi * regs, 0.4, 0.022, 2600, 0.8, 0.5, 0, 0.6) * 0.5 * pow(mpe.freq / 440, 0 - fit.lvl);   // level across the range, fitted
post = reed.body(fit.eq, fit.out);
