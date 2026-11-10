declare name "Tenor Sax";
declare version "1.0.0";
declare sound "reverb=0.3 reverbSize=0.45 reverbDamp=0.45 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "104 880";
declare description "Tenor saxophone fitted to SWAM's on a Seaboard. Press to blow: soft and round to loud and edgy. Slide down for a breathy subtone, up for a brighter edge and, near the top, a growl. Slurred notes (a finger down before the last lifts) join without a new tongued attack.";
declare artist "ROLI Seaboard demos (SWAM tenor sax)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (ROLI), 1:54-2:14, SWAM tenor sax";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
reed = library("reed_engine.lib");
fit = library("sax_fit.lib");

sl     = mpe.slide : si.smooth(ba.tau2pole(0.03));
growl  = max(0, sl - 0.68) / 0.32;
subt   = max(0, 0.35 - sl) / 0.35;
regs   = pow(mpe.freq / 220, 0 - fit.reg);      // higher notes: fewer harmonics, as fitted
noise  = 0.035 * (1 + 2.0 * subt);

process = reed.voice(mpe.freq, 0.04, fit.lo * regs, fit.hi * regs, 0.45, noise, 2300, 0.8, 0.5, growl, 1.0) * 0.5 * (1 - 0.3 * growl) * pow(mpe.freq / 220, 0 - fit.lvl);   // level across the range, fitted
post = reed.body(fit.eq, fit.out);
