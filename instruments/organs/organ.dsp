declare name "Drawbar Organ";
declare range "65 1047";
declare description "Tonewheel organ. Slide moves the drawbars from mellow to bright, press adds the rotary-speaker shimmer.";
import("stdfaust.lib");
mpe = library("mpe.lib");

bars  = os.osc(mpe.freq * 0.5) * 0.2 + os.osc(mpe.freq) + os.osc(mpe.freq * 2) * (0.3 + 0.7 * mpe.slide)
      + os.osc(mpe.freq * 3) * 0.6 * mpe.slide + os.osc(mpe.freq * 4) * 0.5 * mpe.slide + os.osc(mpe.freq * 6) * 0.3 * mpe.slide;
shimmer = 1 - 0.25 * mpe.pressure * (0.5 + 0.5 * os.osc(6.5));
click = no.noise * en.ar(0.0005, 0.012, mpe.gate) * 0.05;
amp   = mpe.gate : si.lag_ud(0.006, 0.04);

process = (bars * 0.25 * amp + click) * shimmer;
