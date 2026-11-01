declare name "Cello";
declare range "65 880";
declare ringout "5";
declare description "Bowed cello, its tone fitted to recordings of a concert soloist. Press to bow: harder is louder and brighter. Slide moves the bow from near the bridge to over the fingerboard. Held notes get a natural vibrato unless you make your own.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib")[
    openStrings = (65.41, 98.0, 146.83, 220.0);     // C G D A
    body = library("body_cello.lib").body;          // tools/timbre/makebody.py
    t60Low = 2.5; t60High = 0.2; t60HighSlope = 0.4;   // less damping low down: keeps the low strings in clean Helmholtz motion
    bowForceLowHz = 150; bowForceLowExp = 0.1;            // heavier low strings need more bow force
    brightLoud = -3;
    registerTilt = 6.5; registerRef = 160;                   // darker low strings, brighter high ones (measured)
    vibRate = 5.9; vibCents = 9; vibDelay = 0.05; vibRateWander = 0.13; vibDepthWander = 0.6;
    levelPoints = (65.4, 91.8, 128.7, 180.6, 253.4, 355.6, 498.9, 700.0);
    levelDb = (6.2, -1.9, 1.6, -4.1, -2.5, -2.3, 2.7, 0.4);     // tools/timbre/levelbal.py
    outGain = 0.1;
];

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity, mpe.legato);
