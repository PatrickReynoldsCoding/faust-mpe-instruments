declare version "2.0.0";       // 2.0.0: refitted to the SWAM cello of ROLI's Seaboard demos (1.1.0, the concert-soloist fit, is kept in versions/)
declare name "Cello";
declare sound "reverb=0.475 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "65 880";
declare ringout "5";
declare artist "ROLI Seaboard demos (SWAM viola/cello)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (ROLI), SWAM cello 2:50-3:19 | Seaboard RISE x SWAM & Camelot Pro (ROLI, Heen-Wah Wai), SWAM cello, clarinet and oboe 0:17-0:46";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
declare description "Bowed cello, its tone fitted to the SWAM cello in ROLI's Seaboard demos. Press to bow: harder is louder and brighter. Slide moves the bow from near the bridge to over the fingerboard. Held notes get a natural vibrato unless you make your own.";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib")[
    openStrings = (65.41, 98.0, 146.83, 220.0);     // C G D A
    body = library("cello_body.lib").body;          // tools/fitting/seaboard/strings/swam.py body cello
    t60Low = 2.5; t60High = 0.2; t60HighSlope = 0.4;   // less damping low down: keeps the low strings in clean Helmholtz motion
    bowForceLowHz = 150; bowForceLowExp = 0.1;            // heavier low strings need more bow force
    brightLoud = -3;
    registerTilt = 6.5; registerRef = 160;                   // darker low strings, brighter high ones (measured)
    vibRate = 5.4; vibCents = 11; vibDelay = 0.1; vibRise = 0.3; vibRateWander = 0.13; vibDepthWander = 0.6;
    levelPoints = (65.4, 91.8, 128.7, 180.6, 253.4, 355.6, 498.9, 700.0);
    levelDb = (8.4, -0.8, 0.4, -2.7, -2.5, -2.1, -1.3, 0.7);     // tools/timbre/levelbal.py
    outGain = 0.138;                                // 2.0.0: to -20 dBFS with the other sounds
];

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity, mpe.legato);
post = bowed.post;                                  // body, ring, sympathetic strings: once for all notes
