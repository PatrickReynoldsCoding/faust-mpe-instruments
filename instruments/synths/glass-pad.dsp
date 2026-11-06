declare name "Glass Pad";
declare range "65 1047";
declare description "Airy additive pad of sine partials. Slide brings in the upper partials, press adds shimmer.";
import("stdfaust.lib");
mpe = library("mpe.lib");

shim  = 0.002 * mpe.pressure;
part(k, g) = os.osc(mpe.freq * k * (1 + shim * os.osc(0.3 * k))) * g;
tone  = part(1, 1) + part(2, 0.5 * mpe.slide + 0.2) + part(3, 0.4 * mpe.slide) + part(4, 0.3 * mpe.slide) + part(6, 0.25 * mpe.slide) + part(8, 0.2 * mpe.slide);
amp   = mpe.gate * (0.4 + 0.6 * mpe.pressure) : si.lag_ud(0.4, 0.9);

process = tone * amp * 0.28;
