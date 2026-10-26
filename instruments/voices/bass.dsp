declare name "Bass";
declare range "82 294";
declare description "Sung vowel (bass). Press to sing louder, slide to morph a - e - i - o - u.";
import("stdfaust.lib");
mpe = library("mpe.lib");
vocal = library("vocal.lib");

process = vocal.voice(1, mpe.freq, mpe.gate, mpe.pressure, mpe.slide) * 0.8;
