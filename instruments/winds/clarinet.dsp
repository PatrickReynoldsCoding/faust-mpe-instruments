declare name "Clarinet";
declare range "147 880";
declare description "Reed clarinet. Press to blow harder, slide to change the reed brightness.";
import("stdfaust.lib");
mpe = library("mpe.lib");

breath = mpe.gate * (0.46 + 0.44*mpe.pressure) : si.lag_ud(0.05, 0.08);
blow   = pm.blower(breath, 0.05, 2000, 5, 0);
reed   = 0.3 + 0.5*mpe.slide : si.smooth(ba.tau2pole(0.03));

process = pm.clarinetModel(pm.f2l(mpe.freq), blow, reed, 0.5) * 0.9;
