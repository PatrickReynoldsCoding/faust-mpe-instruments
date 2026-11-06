"""An outside opinion on the piano: LAION CLAP (music) embeddings of Ishizaka's recordings
against the same pieces played from MIDI on our instruments (tools/piano/play_midi.py).

   python clapcheck.py keys/piano synths/fm-keys ...     (renders into refs/ab/piano/<tag>/)

  paired  cosine similarity, recording vs instrument, same piece, clip by clip in time order
  MMD     kernel distance between the recording's clips and the instrument's (0 = same as sets)
  label   zero-shot: probability of "a grand piano" among the labels below"""
import glob, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "timbre"))
import clapcheck as C                                                    # noqa: E402
import analysis as A                                                     # noqa: E402
import play_midi                                                         # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MIDI = os.environ.get("PIANO_MIDI", os.path.join(ROOT, "refs", "wtc-midi"))
LABELS = ["a grand piano", "an upright piano", "an electric piano", "a harpsichord", "a synthesizer",
          "a music box", "a pipe organ", "a marimba", "a harp", "a toy piano"]


def active_span(x, thresh_db=-40):
    e = np.sqrt(np.convolve(x * x, np.ones(4800) / 4800, "same"))
    on = np.where(e > e.max() * 10 ** (thresh_db / 20))[0]
    return on[0], on[-1]


def main(insts):
    base = os.path.join(ROOT, "refs", "ab", "piano")
    pieces = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(MIDI, "*.mid")))
    R = []
    for p in pieces:
        x = A.load(os.path.join(ROOT, "refs", "ishizaka", p + ".wav"))
        a, b = active_span(x)
        R.append(C.embed(C.clips_from(x[a:b]) if hasattr(C, "clips_from") else clips_of(x[a:b])))
    Rall = np.concatenate(R)
    T = C.text_embed(LABELS)

    def probs(E):
        lg = 100 * E @ T.T
        p = np.exp(lg - lg.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        return p.mean(0)
    h = len(Rall) // 2
    sig = C.mmd(Rall[:h], Rall[h:])[1]
    pr = probs(Rall)
    print(f"{len(pieces)} pieces, {len(Rall)} clips of 5 s")
    print(f"{'':18s}{'paired cos':>11s}{'MMD':>9s}{'P(grand)':>10s}   most likely label")
    print(f"{'Ishizaka':18s}{'1.000':>11s}{C.mmd(Rall[:h], Rall[h:], sig)[0]:9.4f}{pr[0]:10.3f}   {LABELS[int(np.argmax(pr))]}  (MMD: first half vs second half)")
    for inst in insts:
        tag = inst.replace("/", "-")
        os.makedirs(os.path.join(base, tag), exist_ok=True)
        I = []
        for p, r in zip(pieces, R):
            x = A.load(os.path.join(ROOT, "refs", "ishizaka", p + ".wav"))
            a, b = active_span(x)
            out = os.path.join(base, tag, p + ".wav")
            if not os.path.exists(out):
                play_midi.play(inst, os.path.join(MIDI, p + ".mid"), out, seconds=(b - a) / A.SR, with_room=True)
            y = A.load(out)
            a2, b2 = active_span(y)
            I.append(C.embed(clips_of(y[a2:b2])))
        pc = np.mean([np.mean(np.sum(r[:len(i)] * i[:len(r)], 1)) for r, i in zip(R, I)])
        Iall = np.concatenate(I)
        pr = probs(Iall)
        print(f"{inst:18s}{pc:11.3f}{C.mmd(Rall, Iall, sig)[0]:9.4f}{pr[0]:10.3f}   {LABELS[int(np.argmax(pr))]}"
              f"  ({', '.join(f'{LABELS[j][2:] if LABELS[j][1] == " " else LABELS[j][3:]} {pr[j]:.2f}' for j in np.argsort(-pr)[:3])})")


def clips_of(x, sec=5.0):
    n = int(sec * A.SR)
    out = []
    for a in range(0, len(x) - n + 1, n):
        c = x[a:a + n]
        r = np.sqrt(np.mean(c ** 2))
        if r > 1e-4:
            out.append((c / r * 0.1).astype(np.float32))
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
