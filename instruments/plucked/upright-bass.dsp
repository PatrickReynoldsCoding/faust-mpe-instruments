declare name "Upright Bass";
declare version "1.0.0";
declare range "36 262";
declare ringout "4";
declare window "0.05 0.6";
declare sound "reverb=0.18 reverbSize=0.35 reverbDamp=0.55 delay=0 brightness=1 drive=0 pressureCurve=0.8 release=0";
declare description "Pizzicato jazz double bass: a woody thump, a round low ring and the finger on the string. Strike harder for a brighter, slappier pluck. Keep pressing to let the note ring on; ease off and it dies away like a short pizz. Slide moves the plucking finger from over the fingerboard (round) toward the bridge (growl). Wiggle for vibrato, slide the finger for glides.";
declare artist "ROLI Seaboard demos (Kontakt upright bass)";
declare songs "Seaboard BLOCK M: Any instrument is possible. Anywhere. (upright bass, 0:00-0:26)";
declare reference_licence "ROLI's YouTube demos, all rights reserved: audio not distributed, only fitted numbers";
import("stdfaust.lib");
mpe = library("mpe.lib");
st  = library("upright_string.lib");
fit = library("upright_fit.lib");

// Everything costly is worked out once a block from the raw controls (the string smooths what it needs).
f    = mpe.freq;
v    = mpe.velocity * (1 - 0.4 * mpe.legato);          // a slur is a soft left-hand hammer-on
tone = mpe.slide;
p    = mpe.pressure;
held = mpe.gate : si.smooth(0.995);                    // ~10 ms: lifting damps, without a click

// The pluck: the finger pulls the string and lets go. A soft pluck is a slow, round push (low
// cut-off); a hard one snaps (higher cut-off, and the string slaps the fingerboard).
// (Cut-offs follow the note: below its fundamental the string cannot keep what the finger gives.)
fc    = min(6000, f * (1.6 + 12 * v * v + 4 * tone));
pluck = mpe.trigger * (0.25 + 0.75 * v) : st.nodenormal : fi.lowpass(2, fc) : fi.highpass(2, max(25, 0.6 * f))
      : pos with {
          // where the finger is: a comb that thins the partials it sits on
          pos(x) = x - 0.85 * de.fdelay(4096, ma.SR / f * (0.19 + 0.12 * tone), x);
      };
// The finger on the string (skin on a wound string), and the slap at a hard pluck.
noise = no.noise * en.ar(0.0008, 0.012, mpe.trigger) : st.nodenormal
      : fi.bandpass(1, 900, 2600) : *(0.006 + 0.05 * v * v * v);

// While pressed: firm pressure lets it ring (3 dB/s), a light touch is a short pizz (28 dB/s).
// Lifted: the left hand stops it (160 dB/s), the highs first.
sustain = 3 + 25 * (1 - p) * (1 - p);
loss    = 0.52 - 0.22 * tone;

// (the higher notes speak louder: reg evens them out)
level = (1 + 0.25 * p) * (55 / max(36, f)) ^ 0.55 * ba.db2linear(fit.out) : st.smoo(mpe.trigger);
voice = st.string(mpe.trigger, f, sustain, loss, 160, 0.85, held, pluck + noise) : fi.dcblocker : *(level);

process = voice;

// The instrument's body and the close microphone, once for all the notes.
post = st.nodenormal : st.body(25, fit.eq);
