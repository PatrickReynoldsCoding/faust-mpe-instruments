"""Build and play instruments from Python: single notes, or whole phrases from control curves."""
import os, subprocess, tempfile
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SR, BLK = 48000, 64
LAB = os.path.join(ROOT, "build-lab", "timbre")


def build(dsp):
    """Compile a .dsp (anywhere) into a plugin. Rebuilds when the .dsp or lib/ changed."""
    dsp = os.path.abspath(dsp)
    os.makedirs(LAB, exist_ok=True)
    stem = dsp.replace(ROOT + "/", "").replace("/", "_")[:-4]
    cpp, so = os.path.join(LAB, stem + ".cpp"), os.path.join(LAB, stem + ".so")
    libs = [os.path.join(ROOT, "lib", f) for f in os.listdir(os.path.join(ROOT, "lib"))]
    newest = max(os.path.getmtime(p) for p in [dsp] + libs)
    if not os.path.exists(so) or os.path.getmtime(so) < newest:
        inc = ["-I", os.path.join(ROOT, "lib"), "-I", os.path.dirname(dsp)]
        subprocess.run(["faust", *inc, "-lang", "cpp", "-i", "-cn", "Instrument", "-o", cpp, dsp], check=True)
        defs = [f'-DGEN="{cpp}"']
        if any(l.startswith("post") and "=" in l for l in open(dsp)):       # the stage all voices share
            pcpp = cpp[:-4] + ".post.cpp"
            subprocess.run(["faust", *inc, "-lang", "cpp", "-i", "-pn", "post", "-cn", "InstrumentPost", "-o", pcpp, dsp], check=True)
            defs.append(f'-DGENPOST="{pcpp}"')
        subprocess.run(["g++", "-O2", "-std=c++17", "-w", "-shared", "-fPIC", *defs, "-o", so,
                        os.path.join(ROOT, "src", "entry.cpp")], check=True)
    return so


def render(so, ctl, extra=None):
    """ctl: array (blocks, voices, 6) of freq, gate, pressure, slide, velocity, legato per 64-sample block."""
    ctl = np.ascontiguousarray(ctl, dtype=np.float32)
    nv = ctl.shape[1]
    with tempfile.TemporaryDirectory() as d:
        c, o = os.path.join(d, "c.f32"), os.path.join(d, "o.f32")
        ctl.tofile(c)
        args = [os.path.join(ROOT, "build", "render_curves"), so, c, str(nv), o]
        args += [f"{k}={v}" for k, v in (extra or {}).items()]
        subprocess.run(args, check=True)
        return np.fromfile(o, dtype=np.float32).astype(np.float64)


def note_ctl(freq, pressure=0.7, slide=0.5, velocity=0.7, hold=1.5, total=None, vib_hz=0.0, vib_cents=0.0,
             vib_delay=0.0):
    """Controls for one note. freq/pressure may be callables of time (s)."""
    total = total if total is not None else hold + 1.0
    n = int(total * SR / BLK)
    t = np.arange(n) * BLK / SR
    f = freq(t) if callable(freq) else np.full(n, float(freq))
    if vib_cents:
        ramp = np.clip((t - vib_delay) / 0.3, 0, 1)
        f = f * 2 ** (vib_cents * ramp * np.sin(2 * np.pi * vib_hz * t) / 1200)
    p = pressure(t) if callable(pressure) else np.full(n, float(pressure))
    ctl = np.zeros((n, 1, 6))
    ctl[:, 0, 0] = f; ctl[:, 0, 1] = t < hold; ctl[:, 0, 2] = p; ctl[:, 0, 3] = slide; ctl[:, 0, 4] = velocity
    return ctl


def note(so, *a, extra=None, **kw):
    return render(so, note_ctl(*a, **kw), extra)
