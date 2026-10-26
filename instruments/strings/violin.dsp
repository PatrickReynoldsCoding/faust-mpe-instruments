declare name "Violin";
declare range "196 1000";
declare description "Bowed string. Press to bow, slide to move the bow towards the bridge.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib");

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide,
                      270, 500, 2500,
                      0.15, 0.60,
                      0.45, 0.30,
                      0.06, 0.14,
                      0.05, 0.08);
