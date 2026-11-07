declare name "Chip Lead";
declare sound "reverb=0.25 reverbSize=0.35 reverbDamp=0.4 delay=0.12 brightness=1 drive=0 pressureCurve=1 release=0";
declare status "legacy";
declare range "130 1047";
declare description "8-bit game-console pulse. Slide steps the pulse width 12.5 / 25 / 50 percent; press adds arpeggio-style vibrato.";
import("stdfaust.lib");
mpe = library("mpe.lib");

duty = select3(int(mpe.slide * 2.99), 0.125, 0.25, 0.5);
vib  = 1 + 0.01 * mpe.pressure * os.osc(6);
wave = os.lf_pulsetrainpos(mpe.freq * vib, duty) * 2 - 1;
crush = floor(wave * 4 + 0.5) / 4;
amp  = mpe.gate : si.lag_ud(0.002, 0.03);

process = crush * amp * 0.3;
