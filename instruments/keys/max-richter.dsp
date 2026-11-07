declare name "Max Richter";
declare sound "reverb=0.25 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare artist "Max Richter";
declare songs "Horizon Variations (The Blue Notebooks) | Shadow Journal (The Blue Notebooks) | Vladimir's Blues (The Blue Notebooks) | Old Song (The Blue Notebooks) | The Trees (The Blue Notebooks) | Written on the Sky (The Blue Notebooks) | On the Nature of Daylight, Piano Version (The Blue Notebooks 20 Year Edition, disc 2) | A Catalogue of Afternoons (The Blue Notebooks 20 Year Edition, disc 2) | While The Flood Rages (While The Flood Rages) | The City Was A Chaos, Intro (While The Flood Rages)";
declare reference_licence "Commercial recordings (the owner's own CDs/downloads): used only to measure the sound; the audio is not distributed, only fitted numbers.";
declare range "27.5 4186";
declare ringout "6";
declare window "0.05 0.5";
declare status "current";
declare description "A soft, close-miked piano after Max Richter's recordings: felt-dark, intimate, with the strings ringing on. Strike harder for louder and brighter. Press firmly as you lift to keep the note ringing (the sustain pedal for that note). Slide low on the key is the soft pedal.";
import("stdfaust.lib");
mpe = library("mpe.lib");
piano = library("richter.lib");

process = piano.voice(mpe.freq, mpe.gate, mpe.pressure, mpe.slide, mpe.velocity);
post = piano.post;                                  // the soundboard and the ringing strings: once for all notes
