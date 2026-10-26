declare name "Cello";
declare range "65 523";
declare description "Bowed string, lower body and a slower, heavier bow.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib");

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide,
                      110, 200, 1800,
                      0.20, 0.55,
                      0.55, 0.25,
                      0.08, 0.14,
                      0.06, 0.15);
