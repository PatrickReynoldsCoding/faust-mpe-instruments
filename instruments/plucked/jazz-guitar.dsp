declare name "Jazz Guitar";
declare version "1.0.0";
declare range "82 1047";
declare ringout "5";
declare window "0.05 0.6";
declare sound "reverb=0.25 reverbSize=0.4 reverbDamp=0.5 delay=0 brightness=1 drive=0 pressureCurve=0.8 release=0";
declare description "Hollow-body archtop on the neck pickup: warm, round and woody, for chords and single lines. Strike harder for more pick and a brighter note. Keep pressing to let it ring; a light touch is a short, comped chord. Slide moves the pick from the neck (round) toward the bridge (sharper). Wiggle for vibrato, slide the finger to bend.";
declare artist "ROLI Seaboard demos (Kontakt jazz guitar)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (jazz guitar, 0:26-1:03)";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
st  = library("upright_string.lib");
fit = library("jazzgtr_fit.lib");

// Everything costly is worked out once a block from the raw controls (the string smooths what it needs).
f    = mpe.freq;
v    = mpe.velocity * (1 - 0.4 * mpe.legato);          // a slur is a hammer-on: softer
tone = mpe.slide;
p    = mpe.pressure;
held = mpe.gate : si.smooth(0.995);

// The pick: a soft stroke is a round push, a hard one snaps (higher cut-off) and clicks.
// (Cut-offs follow the note: below its fundamental the string cannot keep what the pick gives.)
fc    = min(5000, f * (1.5 + 5 * v * v + 3 * tone));
pick  = mpe.trigger * (0.3 + 0.7 * v) : st.nodenormal : fi.lowpass(2, fc) : fi.highpass(1, 0.7 * f) : pos
with {
    // where the pick strikes (from the neck pickup's end of the string toward the bridge)
    pos(x) = x - 0.8 * de.fdelay(1024, ma.SR / f * (0.24 - 0.12 * tone), x);
};
click = no.noise * en.ar(0.0003, 0.004, mpe.trigger) : st.nodenormal : fi.bandpass(1, 1500, 5000) : *(0.0006 + 0.004 * v * v);

// While pressed: firm pressure rings on (3 dB/s), a light touch is a short note (24 dB/s).
// Lifted: the fretting hand lets go and the strings are damped (110 dB/s), the highs first.
sustain = 3 + 21 * (1 - p) * (1 - p);
loss    = 0.18 - 0.1 * tone;

// The neck pickup sees the string a quarter of the way along: it hums the low partials and
// thins some upper ones; the hollow body and the amp do the rest (post).
pickup(x) = x - 0.5 * de.fdelay(1024, ma.SR / f * 0.27, x);

level = (1 + 0.2 * p) * (196 / max(82, f)) ^ 0.3 * ba.db2linear(fit.out) : st.smoo(mpe.trigger);
voice = st.string(mpe.trigger, f, sustain, loss, 110, 0.7, held, pick + click) : pickup : fi.dcblocker : *(level);

process = voice;

// The pickup and its cable (a resonant lowpass: the reference falls 12 dB just above 1.8 kHz),
// then the hollow body and the amp (fitted bands), once for all the notes.
post = st.nodenormal : fi.resonlp(1700, 1.5, 1) : fi.lowpass(1, 2400) : st.body(63, fit.eq);
