"""Refit an instrument to its recordings after changing the engine or its settings: the
lowest notes' fundamentals (fundfix.py), body correction rounds (evaluate.py + makebody.py),
then the loudness balance across the range (levelbal.py). Uses the real
instrument file, and the plugins in build-lab/ (a running host is not disturbed).
   python refit.py violin [rounds=3]"""
import sys, subprocess, os
PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))

def run(*args, show=None):
    r = subprocess.run([PY, *args], cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
    lines = r.stdout.strip().splitlines()
    for l in (lines if show is None else [l for l in lines if any(k in l for k in show)]):
        print("   ", l)

def main(inst, rounds=3):
    # the lowest notes first: the envelope rounds after it then have the last word
    print(f"[{inst}] low fundamentals")
    run("fundfix.py", inst, "--apply", show=["difference"])
    run("makebody.py", inst, "--correct", show=["wrote"])
    for i in range(rounds):
        print(f"[{inst}] body round {i + 1}")
        run("evaluate.py", inst, "--correction", show=["envelope error", "timbre error"])
        run("makebody.py", inst, "--apply-diff", show=["accumulated"])
    print(f"[{inst}] loudness balance")
    run("levelbal.py", inst, "--apply", show=["correction", "updated"])
    print(f"[{inst}] final")
    run("evaluate.py", inst, show=["envelope", "timbre", "noise", "vibrato", "centroid", "level corr"])

if __name__ == "__main__":
    kw = dict(a.split("=") for a in sys.argv[2:])
    main(sys.argv[1], int(kw.get("rounds", 3)))
