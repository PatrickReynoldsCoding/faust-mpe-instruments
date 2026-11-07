"""Match the long-term tone of keys/max-richter to the recordings, from whole passages.

Several one-minute passages of different solo-piano tracks are transcribed roughly (richter_transcribe.py),
played through the instrument (richter_render.py) and compared with the recording in third-octave bands
(richter_compare.py): same notes, so what differs is the instrument's tone (hammer, body, room, microphone).
Each track counts once (the median over the tracks, levels aligned over 200-1000 Hz), so one dark track cannot decide.
The difference, smoothed, goes into the body (the fitted resonator bank), a few rounds.

   python richter_tone.py [rounds=3]
"""
import os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import richter_fit as RF                                                  # noqa: E402
import richter_transcribe as T                                            # noqa: E402
import richter_render as R                                                # noqa: E402
import richter_compare as C                                               # noqa: E402

F, ROOT, SR = RF.F, RF.ROOT, RF.SR
PASSAGES = [("bn1_11.wav", 20), ("bn2_08.wav", 30), ("flood_05.wav", 40), ("bn1_06.wav", 5), ("bn2_01.wav", 60), ("bn1_10.wav", 30), ("bn1_08.wav", 20)]
CACHE = os.path.join(ROOT, "refs", "richter", "passages")


def passage(track, a):
    os.makedirs(CACHE, exist_ok=True)
    x, _ = sf.read(os.path.join(ROOT, "refs", "richter", "wav", track), start=int(a * SR), stop=int((a + 60) * SR), dtype="float32")
    npy = os.path.join(CACHE, f"{track[:-4]}_{a}.npy")
    if not os.path.exists(npy):
        np.save(npy, T.transcribe(x.mean(axis=1)))
    return x, np.load(npy)


def differences(inst="keys/max-richter"):
    diffs = []
    for track, a in PASSAGES:
        x, notes = passage(track, a)
        if len(notes) < 20:
            continue
        y = R.render(inst, notes)[:len(x)]
        c, lr = C.ltas(x); _, li = C.ltas(y)
        al = (c >= 200) & (c <= 1000)
        diffs.append((lr - lr[al].mean()) - (li - li[al].mean()))
    return c, np.array(diffs)


def main(rounds=3):
    for rnd in range(rounds):
        RF.rebuild()
        c, d = differences()
        med = np.median(d, axis=0)
        spread = np.std(d, axis=0)
        print(f"--- round {rnd}: recording minus instrument, median over {len(d)} passages (spread between passages)")
        for fc, m, s in zip(c, med, spread):
            print(f"  {fc:7.0f} Hz  {m:+6.1f}  (+-{s:4.1f})")
        rms = np.sqrt(np.mean([m ** 2 for fc, m in zip(c, med) if 200 <= fc <= 8000]))
        print(f"  rms of the median difference 200 Hz-8 kHz: {rms:.1f} dB")
        if rnd == rounds - 1:
            break
        P = dict(np.load(RF.PARAMS))
        grid = P["bodyGrid"]
        lg = np.log2(grid)
        ok = (c >= 50) & (c <= 12000)
        corr = np.interp(lg, np.log2(c[ok]), np.convolve(np.pad(med[ok], 1, mode="edge"), [0.25, 0.5, 0.25], "valid"))
        P["bodyDb"] = np.clip(P["bodyDb"] + 0.8 * corr, -60, 20)
        np.savez(RF.PARAMS, **P)
        F.write_lib(P); RF.fix_header()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
