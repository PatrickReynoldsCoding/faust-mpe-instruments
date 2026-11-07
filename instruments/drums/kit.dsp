declare name "Drum kit";
declare sound "reverb=0.08 reverbSize=0.245 reverbDamp=0.4 delay=0 brightness=1 drive=0 pressureCurve=1 release=0";
declare range "130 520";
declare pitched "no";
declare ringout "2";
declare window "0.005 0.15";
declare description "Synthesised drums, one per note of the octave, in the General MIDI order: C kick, C# rim, D snare, D# clap, E crash, F low tom, F# closed hat, G mid tom, G# pedal hat, A high tom, A# open hat, B cowbell. Strike harder for louder. Slide makes the drums ring longer, and a bend retunes them.";
import("stdfaust.lib");
mpe = library("mpe.lib");

// One voice that can be any of the drums: a tone with a falling pitch (the body of a kick or a
// tom) and a band of noise (snare wires, hats, cymbal, clap), each with its own decay. Which drum,
// and so the numbers below, is chosen by the note when it is struck.

trig = mpe.trigger;
note = 69 + 12*log(max(mpe.freq, 20)/440)/log(2);
struck = ba.sAndH(trig, rint(note));                     // the note as struck
k = int(struck - 12*floor(struck/12));                   // 0..11: which drum
tune = 2^((note - struck)/12);                           // a bend retunes the drum

// Per drum:   kick  rim   snare clap  crash ltom  chat  mtom  phat  htom  ohat  cowbell
pick(list) = list : ba.selectn(12, k);
f0 = pick((52,  1650, 190,  0,    0,    95,   0,    135,  0,    185,  0,    560));    // tone, Hz
f1 = pick((3.2, 1,    1.6,  1,    1,    1.7,  1,    1.6,  1,    1.5,  1,    1));      // starts this much higher..
pd = pick((0.035,0.01,0.02, 0.01, 0.01, 0.05, 0.01, 0.045,0.01, 0.04, 0.01, 0.01));   // ..and falls over this long, s
td = pick((0.45, 0.03,0.11, 0.01, 0.01, 0.4,  0.01, 0.42, 0.01, 0.35, 0.01, 0.22));   // tone decay, s
tl = pick((1.0,  0.45,0.55, 0,    0,    0.95, 0,    0.9,  0,    0.85, 0,    0.45));   // tone level
nf = pick((2500, 2800,4200, 1250, 7500, 1400, 9000, 1600, 8200, 1900, 9000, 3000));   // noise band centre, Hz
nq = pick((0.7,  2.5, 0.8,  1.4,  0.5,  1.0,  0.9,  1.0,  0.9,  1.0,  0.9,  1.0));    // noise band Q
nd = pick((0.012,0.02,0.17, 0.22, 1.1,  0.04, 0.045,0.04, 0.09, 0.04, 0.55, 0.01));   // noise decay, s
nl = pick((0.25, 0.5, 0.95, 1.0,  0.75, 0.12, 0.6,  0.12, 0.55, 0.12, 0.6,  0));      // noise level
cl = pick((0,    0,   0,    1,    0,    0,    0,    0,    0,    0,    0,    0));      // a clap: a few quick bursts first
sq = pick((0,    0,   0,    0,    0,    0,    0,    0,    0,    0,    0,    1));      // a square tone (the cowbell's clank)

t = (+(1) : *(1 - trig)) ~ _ : /(ma.SR);                  // seconds since the strike
ring = 0.6 + 0.8*mpe.slide;                              // slide: longer or shorter decays
dec(d) = exp(-t/max(d*ring, 0.001));

// The tone: its phase starts at 0 on every strike, so a kick always has the same thump.
fr = f0*tune*(1 + (f1 - 1)*exp(-t/pd));
ph = (+(fr/ma.SR) : ma.frac) ~ *(1 - trig);
osc = select2(sq > 0.5, sin(2*ma.PI*ph), (ph < 0.5)*2 - 1 : fi.lowpass(2, 4000))
    + sq*0.6*((ph*1.51 : ma.frac) < 0.5);                // the cowbell's second, inharmonic tone
tone = osc*dec(td)*tl;

// The noise: a band of it; a clap is three bursts 10 ms apart, then the tail.
burst(d) = (t >= d)*exp((d - t)/0.004)*(t < d + 0.01);
clapEnv = burst(0) + burst(0.011) + burst(0.022) + (t >= 0.03)*exp((0.03 - t)/max(nd*ring, 0.001));
nenv = select2(cl > 0.5, dec(nd), clapEnv);
noise = no.noise : fi.resonbp(min(nf*tune, 16000), nq, 1) : *(nenv*nl*2);

level = 0.15 + 0.85*min(mpe.velocity, 1);                // how hard it was struck
process = (tone + noise)*level*0.7 : ma.tanh;
