declare name "Piano";
declare range "27.5 4186";
declare ringout "6";
declare window "0.05 0.5";
declare description "Grand piano, fitted to recordings of a Steinway B, note by note. Strike harder for louder and brighter. Press firmly as you lift to keep the note ringing (the sustain pedal for that note; a medium press is a half pedal). Slide low on the key is the soft pedal: quieter and veiled.";
import("stdfaust.lib");
mpe = library("mpe.lib");
piano = library("piano.lib");

process = piano.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity);
post = piano.post;                                  // the soundboard: once for all notes
