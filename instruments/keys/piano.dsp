declare version "1.2.0";       // 1.2.0: a harder, brighter hammer and a fuller bass, after the Equator piano in ROLI's RISE demo; 1.1.0: level evened out (1.0.0 and 1.1.0 are kept in versions/)
declare name "Piano";
declare sound "reverb=0.475 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "27.5 4186";
declare ringout "6";
declare window "0.05 0.5";
declare artist "Steinway B (University of Iowa MIS); ROLI Seaboard demos (Equator Acoustic Piano)";
declare songs "Seaboard RISE x SWAM & Camelot Pro (ROLI, performed by Heen-Wah Wai), Equator Acoustic Piano + SWAM viola 0:46-1:02";
declare reference_licence "University of Iowa MIS piano single notes (Steinway B, free to use): the key-by-key fit. ROLI's YouTube demo, all rights reserved: audio not distributed, only fitted numbers (the 1.2.0 hammer and tone, from third-octave bands and partial levels of its left-hand chords)";
declare description "Grand piano, fitted to recordings of a Steinway B, note by note, its tone brightened after the Equator piano in ROLI's Seaboard RISE demo. Strike harder for louder and brighter. Press firmly as you lift to keep the note ringing (the sustain pedal for that note; a medium press is a half pedal). Slide low on the key is the soft pedal: quieter and veiled.";
import("stdfaust.lib");
mpe = library("mpe.lib");
piano = library("piano.lib");

process = piano.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity) : *(0.71);   // 1.1.0: -3 dB, to -20 dBFS with the other sounds
post = piano.post;                                  // the soundboard: once for all notes
