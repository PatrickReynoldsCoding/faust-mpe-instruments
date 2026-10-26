declare name "Soprano";
declare range "262 880";
declare description "Sung vowel (soprano). Press to sing louder, slide to morph a - e - i - o - u.";
import("stdfaust.lib");
mpe = library("mpe.lib");
vocal = library("vocal.lib");

process = vocal.voice(3, mpe.freq, mpe.gate, mpe.pressure, mpe.slide) * 0.8;
