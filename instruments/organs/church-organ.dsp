declare name "Church Organ";
declare range "65 1047";
declare description "Pipe organ with a breathy chiff. Slide pulls stops (flute, principal, full); the pipes speak slowly and fade with the room.";
import("stdfaust.lib");
mpe = library("mpe.lib");

f      = mpe.freq;
flute  = os.osc(f) + 0.2 * os.osc(2 * f);
prin   = os.osc(f) + 0.5 * os.osc(2 * f) + 0.4 * os.osc(3 * f) + 0.3 * os.osc(4 * f) + 0.15 * os.osc(6 * f);
full   = prin + 0.5 * os.osc(0.5 * f) + 0.35 * os.osc(8 * f) + 0.3 * os.osc(1.5 * f);
mix    = select2(mpe.slide > 0.5, flute + (prin - flute) * (mpe.slide * 2), prin + (full - prin) * ((mpe.slide - 0.5) * 2));
chiff  = no.noise : fi.resonbp(min(f * 3, 8000), 4, 1) * en.ar(0.002, 0.07, mpe.gate) * 0.5;
amp    = mpe.gate : si.lag_ud(0.07, 0.25);

process = (mix * 0.2 * amp + chiff * 0.12) : fi.lowpass(1, 6000);
