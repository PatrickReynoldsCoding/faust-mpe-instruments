declare name "Violin";
declare range "196 1760";
declare ringout "4";
declare description "Bowed violin, its tone fitted to recordings of a concert soloist. Press to bow: harder is louder and brighter. Slide moves the bow from near the bridge to over the fingerboard. Held notes get a natural vibrato unless you make your own.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib")[
    openStrings = (196, 293.66, 440, 659.26);       // G D A E
    body = library("body_violin.lib").body;         // tools/timbre/makebody.py
    levelPoints = (196.0, 268.2, 367.0, 502.1, 687.0, 940.1, 1286.3, 1760.0);
    levelDb = (3.7, -2.0, -2.9, -6.0, -1.2, -2.6, 3.1, 7.9);     // tools/timbre/levelbal.py
    brightLoud = 10;                                // brighter when digging in, as measured
    outGain = 0.1;
];

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity);
