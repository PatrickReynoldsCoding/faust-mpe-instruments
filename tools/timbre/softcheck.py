"""How soft can a note be, and how gently does it start? Plays Seaboard-like touches: a strike
velocity (after the host's x5) and pressure that creeps up over ~330 ms to a level, as in the
captured sessions. Prints, per touch: time to reach -20 dB and -3 dB of the note's held level,
and the held level relative to a firm note (velocity 0.5, pressure 0.8).
   python softcheck.py [plugin.so ...]   (default: the current violin and cello)"""
import sys, os, numpy as np
import synth as S

TOUCHES = [("feather (v .06, p .02)", 0.06, 0.02), ("light (v .12, p .05)", 0.12, 0.05), ("soft (v .12, p .2)", 0.12, 0.2),
           ("medium (v .3, p .5)", 0.3, 0.5), ("strike (v 1, p .8)", 1.0, 0.8)]

def level_curve(x):
    e = np.convolve(x ** 2, np.ones(240) / 240, "same")[::240]           # 5 ms
    return 10 * np.log10(e + 1e-14)

def run(so, f):
    ref = None
    out = []
    for name, v, p in [("firm", 0.5, 0.8)] + TOUCHES:
        press = lambda t, p=p: p * np.clip(t / 0.33, 0, 1) ** 1.5
        x = S.note(so, f, press, 0.5, v, hold=1.5, total=1.5)
        L = level_curve(x)
        held = np.median(L[160:280])                                   # 0.8-1.4 s
        t20 = np.argmax(L > held - 20) * 5; t3 = np.argmax(L > held - 3) * 5
        if ref is None: ref = held; continue
        out.append((name, t20, t3, held - ref))
    return out

if __name__ == "__main__":
    sos = sys.argv[1:] or [S.build(os.path.join(S.ROOT, "instruments/strings/violin.dsp")), S.build(os.path.join(S.ROOT, "instruments/strings/cello.dsp"))]
    for so in sos:
        f = 110 if "cello" in so else 440
        print(f"\n{os.path.basename(so)} at {f} Hz          to -20 dB   to -3 dB   held level vs firm")
        for name, t20, t3, rel in run(so, f):
            print(f"  {name:24s} {t20:6d} ms  {t3:6d} ms  {rel:+6.1f} dB")
