declare version "1.1.0";       // 1.1.0: level evened out with the other sounds (the 1.0.0 is kept in versions/)
declare name "Violin";
declare sound "reverb=0.475 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "196 1760";
declare ringout "4";
declare description "Bowed violin, its tone fitted to recordings of a concert soloist. Press to bow: harder is louder and brighter. Slide moves the bow from near the bridge to over the fingerboard. Held notes get a natural vibrato unless you make your own.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib")[
    openStrings = (196, 293.66, 440, 659.26);       // G D A E
    body = library("body_violin.lib").body;         // tools/timbre/makebody.py
    levelPoints = (196.0, 268.2, 367.0, 502.1, 687.0, 940.1, 1286.3, 1760.0);
    levelDb = (5.1, -1.2, -2.2, -5.8, -1.4, -3.3, 2.5, 6.3);     // tools/timbre/levelbal.py
    brightLoud = 10;                                // brighter when digging in, as measured
    registerTilt = 3.5; registerRef = 700;          // darker G and D strings (measured)
    outGain = 0.151;                                // 1.1.0: +3.6 dB, to -20 dBFS with the other sounds
];

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity, mpe.legato);
post = bowed.post;                                  // body, ring, sympathetic strings: once for all notes
