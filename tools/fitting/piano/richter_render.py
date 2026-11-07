"""Play a rough transcription (richter_transcribe.py) through a piano instrument, offline, in stereo.

   python richter_render.py keys/max-richter notes.npy out.wav [--pedal 0]

The recording's level at each onset (dB at the fundamental) becomes a velocity by looking up, per key,
how loud the instrument itself is at the same measurement at velocity 0.15 / 0.5 / 0.9
(cached in refs/richter/calib-<instrument>.npz).
"""
import os, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import richter_transcribe as T                                            # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RENDER = os.path.join(ROOT, "build", "render")
SR = 48000


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def one(args):
    so, key, vel, hold, total, pressure = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        env = dict(os.environ, RENDER_STEREO="1")
        subprocess.run([RENDER, so, f.name, f"{hz(key):.4f}", f"{pressure}", "0.5", f"{vel:.3f}", f"{hold:.3f}", f"{total:.3f}"],
                       check=True, capture_output=True, env=env)
        return np.fromfile(f.name, dtype=np.float32).reshape(-1, 2)


def calibration(inst):
    so = os.path.join(ROOT, "build", inst + ".so")
    path = os.path.join(ROOT, "refs", "richter", "calib-" + inst.replace("/", "_") + ".npz")
    if os.path.exists(path) and os.path.getmtime(path) > os.path.getmtime(so):
        return np.load(path)["db"]
    vels = (0.15, 0.5, 0.9)
    jobs = [(so, k, v, 1.0, 1.6, 0.0) for k in range(21, 109) for v in vels]
    with Pool(12) as p:
        res = p.map(one, jobs)
    db = np.zeros((88, 3))
    for i, r in enumerate(res):
        k, j = divmod(i, 3)
        m = r.mean(axis=1)
        d = T.semis(T.cqt_db(m.astype(np.float32)))
        db[k, j] = d[k][:int(0.6 * SR / T.HOP)].max()
    np.savez(path, db=db)
    return db


def velocity(db_table, key, level):
    row = db_table[key - 21]
    v = np.interp(level, row, (0.15, 0.5, 0.9))
    if level > row[2]:
        v = 0.9 + (level - row[2]) / 20 * 0.1                              # beyond ff: a little further
    if level < row[0]:
        v = max(0.03, 0.15 - (row[0] - level) / 40 * 0.12)
    return float(min(1.0, max(0.03, v)))


def render(inst, notes, pedal=0.0, tail=4.0):
    so = os.path.join(ROOT, "build", inst + ".so")
    cal = calibration(inst)
    span = notes[:, 0].max() + notes[:, 3].max() + tail
    jobs = [(so, int(k), velocity(cal, int(k), lv), float(d), float(d) + tail, pedal) for _, k, lv, d in notes]
    with Pool(14) as p:
        parts = p.map(one, jobs, chunksize=4)
    y = np.zeros((int(span * SR) + 1, 2), dtype=np.float32)
    for (t, k, lv, d), x in zip(notes, parts):
        i = int(t * SR)
        n = min(len(x), len(y) - i)
        y[i:i + n] += x[:n]
    return y


if __name__ == "__main__":
    inst, npy, out = sys.argv[1:4]
    ped = float(sys.argv[sys.argv.index("--pedal") + 1]) if "--pedal" in sys.argv else 0.0
    y = render(inst, np.load(npy), ped)
    sf.write(out, y, SR, subtype="FLOAT")
    print(f"{len(y) / SR:.1f} s -> {out}")
