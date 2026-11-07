declare name "bowed lab";
// Raw bow controls, for finding the stable region. Not a playable instrument.
import("stdfaust.lib");
freq  = hslider("freq", 130, 20, 2000, 0.01);
vel   = hslider("vel", 0.4, 0, 1, 0.001);
press = hslider("press", 0.5, 0, 1, 0.001);
pos   = hslider("pos", 0.15, 0.02, 0.5, 0.001);
gate  = hslider("gate", 0, 0, 1, 1);
b1 = hslider("b1", 110, 60, 1500, 1);
b2 = hslider("b2", 200, 60, 1500, 1);
b3 = hslider("b3", 1800, 500, 5000, 1);
len = pm.f2l(1.0 / max(1.0/freq - 12.1/ma.SR, 1.0/4000));
seg(l) = pm.stringSegment(8, l);
body = (_, bo, _) with { bo = _ <: (fi.resonbp(b1,3,0.7), fi.resonbp(b2,3,0.8), fi.resonbp(b3,1.5,0.5)) :> _; };
process = pm.endChain(pm.chain(pm.violinNuts : seg(len*pos) : pm.violinBow(press, gate*vel) : seg(len*(1-pos)) : pm.violinBridge : body : pm.out)) * 0.5;
