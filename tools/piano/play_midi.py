"""Play a MIDI file on an instrument, offline: every note through build/render (the same path
as one finger on the host), added up. Optionally stretched to a given length (to line it up
with a recording) and put in a room like the host's (a reverb 12 dB below the direct sound).

   python play_midi.py <group/name> <in.mid> <out.wav> [--seconds S] [--room] [--pedal P]
"""
import os, struct, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
from multiprocessing import Pool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SR = 48000


def read_midi(path):
    """[(start s, end s, note, velocity 0..1)] from a type 0/1 MIDI file (tempo map honoured)."""
    data = open(path, "rb").read()
    assert data[:4] == b"MThd"
    _, ntrk, div = struct.unpack(">HHH", data[8:14])
    pos, tracks = 14, []
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b"MTrk"
        ln = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        tracks.append(data[pos + 8:pos + 8 + ln]); pos += 8 + ln
    events, tempos = [], [(0, 500000)]
    for tr in tracks:
        i, t, status = 0, 0, 0
        while i < len(tr):
            d = 0
            while True:
                b = tr[i]; i += 1; d = (d << 7) | (b & 0x7F)
                if b < 0x80:
                    break
            t += d
            b = tr[i]
            if b >= 0x80:
                status = b; i += 1
            if status == 0xFF:
                typ = tr[i]; ln = tr[i + 1]; i += 2
                # variable-length meta length
                if ln & 0x80:
                    i -= 1; ln = 0
                    while True:
                        c = tr[i]; i += 1; ln = (ln << 7) | (c & 0x7F)
                        if c < 0x80:
                            break
                if typ == 0x51:
                    tempos.append((t, int.from_bytes(tr[i:i + 3], "big")))
                i += ln
            elif status in (0xF0, 0xF7):
                ln = 0
                while True:
                    c = tr[i]; i += 1; ln = (ln << 7) | (c & 0x7F)
                    if c < 0x80:
                        break
                i += ln
            else:
                hi = status & 0xF0
                n = 1 if hi in (0xC0, 0xD0) else 2
                args = tr[i:i + n]; i += n
                if hi == 0x90 and args[1] > 0:
                    events.append((t, "on", args[0], args[1], status & 0x0F))
                elif hi == 0x80 or (hi == 0x90 and args[1] == 0):
                    events.append((t, "off", args[0], 0, status & 0x0F))
    tempos.sort()

    def secs(tick):
        s, last_t, last_us = 0.0, 0, 500000
        for tt, us in tempos:
            if tt >= tick:
                break
            s += (tt - last_t) * last_us / div / 1e6; last_t, last_us = tt, us
        return s + (tick - last_t) * last_us / div / 1e6

    events.sort(key=lambda e: (e[0], e[1] == "on"))
    open_, notes = {}, []
    for t, kind, note, vel, ch in events:
        key = (note, ch)
        if kind == "on":
            if key in open_:
                s, v = open_.pop(key); notes.append((secs(s), secs(t), note, v))
            open_[key] = (t, vel / 127)
        elif key in open_:
            s, v = open_.pop(key); notes.append((secs(s), secs(t), note, v))
    return sorted(notes)


def render_note(args):
    so, f, vel, hold, tail, pressure = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as tf:
        subprocess.run([os.path.join(ROOT, "build", "render"), so, tf.name, f"{f:.4f}", f"{pressure}", "0.5",
                        f"{vel:.3f}", f"{hold:.4f}", f"{hold + tail:.4f}"], check=True, capture_output=True)
        return np.fromfile(tf.name, dtype=np.float32)


def room(x, t60=1.6, level_db=-12, seed=1):
    """A plain diffuse room: exponentially decaying noise, 12 dB below the direct sound."""
    rng = np.random.default_rng(seed)
    n = int(t60 * 1.2 * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-6.91 * t / t60)
    ir[:int(0.012 * SR)] = 0                                   # pre-delay
    ir *= 10 ** (level_db / 20) / np.sqrt(np.sum(ir ** 2))
    nfft = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x) + n]
    out = np.zeros(len(x) + n); out[:len(x)] += x; out += wet
    return out


def play(inst, mid, out, seconds=None, with_room=False, pressure=0.0, vel_scale=1.0, tail=2.5):
    notes = read_midi(mid)
    span = max(e for _, e, _, _ in notes)
    k = seconds / span if seconds else 1.0
    so = os.path.join(ROOT, "build", inst + ".so")
    jobs = [(so, 440 * 2 ** ((n - 69) / 12), min(1.0, v * vel_scale), max(0.03, (e - s) * k), tail, pressure)
            for s, e, n, v in notes]
    with Pool(4) as p:
        parts = p.map(render_note, jobs)
    y = np.zeros(int((span * k + tail + 1) * SR))
    for (s, e, n, v), x in zip(notes, parts):
        i = int(s * k * SR)
        y[i:i + len(x)] += x[:len(y) - i]
    if with_room:
        y = room(y)
    y *= 10 ** (-20 / 20) / max(1e-9, np.sqrt(np.mean(y[y != 0] ** 2)))   # -20 dB rms
    sf.write(out, y.astype(np.float32), SR, subtype="FLOAT")
    return len(notes), span * k


if __name__ == "__main__":
    a = sys.argv
    sec = float(a[a.index("--seconds") + 1]) if "--seconds" in a else None
    ped = float(a[a.index("--pedal") + 1]) if "--pedal" in a else 0.0
    n, dur = play(a[1], a[2], a[3], sec, "--room" in a, ped)
    print(f"{n} notes, {dur:.1f} s -> {a[3]}")
