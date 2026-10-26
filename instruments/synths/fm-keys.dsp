declare name "FM Keys";
declare range "65 1047";
declare ringout "4";
declare description "FM electric piano. Strike for a bright tine; press into the key to keep it ringing and brighter.";
import("stdfaust.lib");
mpe = library("mpe.lib");

ratio  = 1.0;                                               // modulator : carrier, 1:1 gives the electric-piano tine
decay  = en.adsr(0.002, 1.1, 0.0, 0.35, mpe.gate);            // fades away like a struck tine
sustain = mpe.gate * mpe.pressure : si.lag_ud(0.05, 0.3);   // pressing keeps the sound alive
shape  = max(decay, sustain);                               // one envelope drives both brightness and loudness
index  = (0.6 + 2.2*mpe.velocity) * shape + 1.2 * sustain;
mod    = os.osc(mpe.freq * ratio) * index;
tone   = os.oscp(mpe.freq, mod);
bell   = os.osc(mpe.freq * 14) * decay * decay * 0.04 * mpe.velocity;   // the "tink" on the attack

process = (tone + bell) * shape * 0.5;
