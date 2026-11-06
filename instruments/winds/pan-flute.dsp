declare name "Pan Flute";
declare range "261 1568";
declare description "Breathy blown pipe. Press to blow, slide for the amount of breath noise.";
import("stdfaust.lib");
mpe = library("mpe.lib");

f      = mpe.freq;
air    = no.noise : fi.resonbp(f, 12 + 20 * (1 - mpe.slide), 1);
tone   = os.osc(f) + 0.12 * os.osc(2 * f) + 0.04 * os.osc(3 * f);
chiff  = no.noise : fi.resonbp(f * 2, 3, 1) * en.ar(0.003, 0.05, mpe.gate);
amp    = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.05, 0.1);

process = (tone * 0.5 + air * (0.6 + 1.6 * mpe.slide) + chiff * 0.1) * amp * 0.2;
