declare name "Tenor";
declare range "130 440";
declare description "Sung vowel (tenor). Press to sing louder, slide to morph a - e - i - o - u.";
import("stdfaust.lib");
mpe = library("mpe.lib");
vocal = library("vocal.lib");

process = vocal.voice(4, mpe.freq, mpe.gate, mpe.pressure, mpe.slide) * 0.8;
