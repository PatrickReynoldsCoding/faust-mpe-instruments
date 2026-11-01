"""An outside opinion: how close does a neural audio model (LAION CLAP, music version) think the
instrument is to the recording? Uses the A/B files that `evaluate.py --wav` writes.

  paired   cosine similarity of recording and instrument embeddings, same passage (1 = same)
  MMD      kernel distance between the set of recording clips and the set of instrument
           clips (0 = indistinguishable as sets; KAD-style, works with few clips)
  label    zero-shot: probability the model gives the right instrument label among
           violin / cello / viola / synthesizer / organ / flute / voice / electric guitar

   python clapcheck.py violin current old ...      (tags = folders under refs/ab/violin/)"""
import os, sys, glob, numpy as np
import analysis as A

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = "laion/larger_clap_music"
LABELS = ["a solo violin", "a solo cello", "a solo viola", "a synthesizer", "a pipe organ", "a flute",
          "a singing voice", "an electric guitar"]
_m = None


def model():
    global _m
    if _m is None:
        import torch
        from transformers import ClapModel, ClapProcessor
        torch.set_num_threads(4)
        _m = (ClapModel.from_pretrained(MODEL).eval(), ClapProcessor.from_pretrained(MODEL))
    return _m


def clips(path, sec=5.0):
    x = A.load(path)
    n = int(sec * A.SR)
    out = []
    for a in range(0, len(x) - n + 1, n):
        c = x[a:a + n]
        r = np.sqrt(np.mean(c ** 2))
        if r > 1e-4:
            out.append((c / r * 0.1).astype(np.float32))
    return out


def embed(cl):
    import torch
    m, p = model()
    embs = []
    for i in range(0, len(cl), 8):
        inp = p(audio=cl[i:i + 8], sampling_rate=48000, return_tensors="pt")
        with torch.no_grad():
            e = m.get_audio_features(**inp)
        e = e.pooler_output if hasattr(e, "pooler_output") else e
        embs.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    return np.concatenate(embs)


def text_embed(labels):
    import torch
    m, p = model()
    inp = p(text=labels, return_tensors="pt", padding=True)
    with torch.no_grad():
        e = m.get_text_features(**inp)
    e = e.pooler_output if hasattr(e, "pooler_output") else e
    return torch.nn.functional.normalize(e, dim=-1).numpy()


def mmd(X, Y, sigma=None):
    Z = np.concatenate([X, Y])
    d2 = np.sum((Z[:, None] - Z[None]) ** 2, -1)
    sigma = sigma or np.sqrt(np.median(d2[d2 > 0]) / 2)
    K = np.exp(-d2 / (2 * sigma ** 2))
    n = len(X)
    kxx, kyy, kxy = K[:n, :n], K[n:, n:], K[:n, n:]
    return float((kxx.sum() - np.trace(kxx)) / (n * (n - 1)) + (kyy.sum() - np.trace(kyy)) / (len(Y) * (len(Y) - 1)) - 2 * kxy.mean()), sigma


def main(inst, tags):
    base = os.path.join(ROOT, "refs", "ab", inst)
    right = {"violin": 0, "cello": 1}[inst]
    rec_files = sorted(glob.glob(os.path.join(base, tags[0], "*-1-recording.wav")))
    R = [embed(clips(f)) for f in rec_files]
    Rall = np.concatenate(R)
    T = text_embed(LABELS)
    def label_prob(E):
        logits = 100 * E @ T.T
        p = np.exp(logits - logits.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        return float(p[:, right].mean())
    # a reference scale: the recording against itself, split in two halves
    h = len(Rall) // 2
    sig = mmd(Rall[:h], Rall[h:])[1]
    print(f"{'':16s}{'paired cos':>12s}{'MMD':>10s}{'P(' + LABELS[right][2:] + ')':>14s}")
    print(f"{'recording':16s}{'1.000':>12s}{mmd(Rall[:h], Rall[h:], sig)[0]:10.4f}{label_prob(Rall):14.3f}   (MMD: first half vs second half)")
    for tag in tags:
        files = sorted(glob.glob(os.path.join(base, tag, "*-2-instrument-in-room.wav")))
        I = [embed(clips(f)) for f in files]
        pc = np.mean([np.mean(np.sum(r[:len(i)] * i[:len(r)], 1)) for r, i in zip(R, I)])
        Iall = np.concatenate(I)
        print(f"{tag:16s}{pc:12.3f}{mmd(Rall, Iall, sig)[0]:10.4f}{label_prob(Iall):14.3f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
