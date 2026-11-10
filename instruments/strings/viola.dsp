declare version "1.0.0";
declare name "Viola";
declare sound "reverb=0.4 reverbSize=0.35 reverbDamp=0.45 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 1320";
declare ringout "4";
declare description "Bowed viola, its tone fitted to the SWAM viola in ROLI's Seaboard demos. Press to bow: harder is louder and brighter. Slide moves the bow from near the bridge to over the fingerboard. Held notes get a natural vibrato unless you make your own.";
declare artist "ROLI Seaboard demos (SWAM viola/cello)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (ROLI), SWAM viola 1:03-1:19 | Seaboard RISE x SWAM & Camelot Pro (ROLI, Heen-Wah Wai), Equator piano + SWAM viola 0:46-1:02";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
bowed = library("bowed.lib")[
    openStrings = (130.81, 196.0, 293.66, 440.0);   // C G D A
    body = library("viola_body.lib").body;          // tools/fitting/seaboard/strings/swam.py body viola
    t60Low = 2.0; t60High = 0.14; t60HighSlope = 0.9;
    bowForceLowHz = 120; bowForceLowExp = 0.05;
    brightLoud = 6;
    bowJitter = 0.04; frictionNoise = 0.015;
    registerTilt = 4; registerRef = 450;
    vibRate = 5.4; vibCents = 9; vibDelay = 0.15; vibRise = 0.3; vibRateWander = 0.1; vibDepthWander = 0.5;
    levelPoints = (130.8, 176.1, 237.0, 319.0, 429.3, 577.9, 777.9, 1047.0);
    levelDb = (6.1, 6.1, 2.8, -1.3, -2.4, -4.7, -3.1, -3.5);
    outGain = 0.245;                                // -20 dBFS with the other sounds
];

process = bowed.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity, mpe.legato);
post = bowed.post;                                  // body, ring, sympathetic strings: once for all notes
