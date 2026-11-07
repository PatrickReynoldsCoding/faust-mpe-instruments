declare name "body test";
import("stdfaust.lib");
mpe = library("mpe.lib");
b = library("body_cello.lib");
process = (1 - 1') * mpe.gate : b.body;
