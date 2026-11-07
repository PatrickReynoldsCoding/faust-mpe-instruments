"""The stereo image of the Richter piano, from the selected single notes.

For every selected note, its first 0.4 s in both channels is compared band by band (third-octave):
  ild(f)   left minus right level, dB, averaged over notes (and by register: low / middle / high keys)
  coh(f)   inter-channel coherence, 1 = the same signal in both ears, 0 = unrelated
and the left/right balance of a note against its key.
   python richter_stereo.py       -> refs/richter/stereo.npz and a printout
"""
import os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import richter_fit as RF                                                  # noqa: E402

SR = 48000
CENTRES = 31.5 * 2 ** (np.arange(0, 28) / 3)
CENTRES = CENTRES[CENTRES < 16000]


def main():
    d = np.load(RF.DATA)
    ok = RF.select_mask()
    idx = np.where(ok)[0]
    nfft = 16384
    f = np.fft.rfftfreq(nfft, 1 / SR)
    bands = [(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6)) for c in CENTRES]
    acc = {"low": [], "mid": [], "high": []}
    cache = {}
    for i in idx:
        tr = str(d["track"][i]); t = float(d["t"][i]); k = int(d["midi"][i])
        if tr not in cache:
            cache = {tr: sf.read(os.path.join(ROOT, "refs", "richter", "wav", tr), dtype="float32")[0]}
        x = cache[tr]
        seg = x[int(t * SR):int((t + 0.4) * SR)]
        if len(seg) < nfft // 2:
            continue
        w = np.hanning(len(seg))
        Lf = np.fft.rfft(seg[:, 0] * w, nfft); Rf = np.fft.rfft(seg[:, 1] * w, nfft)
        row = []
        for b in bands:
            pl = np.sum(np.abs(Lf[b]) ** 2) + 1e-20; pr = np.sum(np.abs(Rf[b]) ** 2) + 1e-20
            cr = np.sum(Lf[b] * np.conj(Rf[b]))
            row.append((10 * np.log10(pl / pr), np.abs(cr) / np.sqrt(pl * pr), pl + pr))
        acc["low" if k < 52 else "mid" if k < 76 else "high"].append(row)
    out = {}
    for name, rows in acc.items():
        if not rows:
            continue
        a = np.array(rows)                                                 # notes, bands, 3
        w = a[:, :, 2] / a[:, :, 2].sum(axis=0, keepdims=True)
        out[name + "_ild"] = (a[:, :, 0] * w).sum(axis=0); out[name + "_coh"] = (a[:, :, 1] * w).sum(axis=0)
        out[name + "_n"] = len(rows)
    lr = d["lr_db"][ok]; mid = d["midi"][ok]
    slope, icpt = np.polyfit(mid, np.clip(lr, -12, 12), 1)
    out["pan_slope_db_per_key"] = slope; out["pan_icpt"] = icpt; out["centres"] = CENTRES
    np.savez(os.path.join(ROOT, "refs", "richter", "stereo.npz"), **out)
    print(f"notes by register: " + ", ".join(f"{n} {out[n + '_n']}" for n in acc if n + "_n" in out))
    print(f"left-right balance of a note against its key: {slope:+.3f} dB per key ({slope * 12:+.2f} dB per octave); "
          f"at middle C {slope * 60 + icpt:+.1f} dB")
    print("  band Hz   " + "   ".join(f"{n:>13s}" for n in ("low ild/coh", "mid ild/coh", "high ild/coh")))
    for j, c in enumerate(CENTRES):
        cells = []
        for n in ("low", "mid", "high"):
            cells.append(f"{out[n + '_ild'][j]:+5.1f} / {out[n + '_coh'][j]:.2f}" if n + "_ild" in out else "      -      ")
        print(f"  {c:7.0f}   " + "   ".join(cells))


if __name__ == "__main__":
    main()
