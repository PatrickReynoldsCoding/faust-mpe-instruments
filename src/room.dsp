// The room the instruments play in: a concert-hall reverb (Faust's zita_rev1) on the whole
// mix, after all the voices are added up. amount 0 = dry; the default puts the reverb about
// 12 dB below the direct sound, like the solo recordings the strings were fitted to.
declare name "room";
import("stdfaust.lib");

amount = hslider("amount", 0.5, 0, 1, 0.01) : si.smoo;
hall = re.zita_rev1_stereo(25, 200, 6000, 2.4, 2.0, 48000);
process = _, _ <: (_, _), hall : ro.interleave(2, 2) : par(i, 2, mix)
with {
    mix(dry, wet) = dry + wet*amount*WET;
    WET = 0.95;     // amount 0.5: reverb energy 12 dB below the dry sound (measured; RT60 ~1.8 s)
};
