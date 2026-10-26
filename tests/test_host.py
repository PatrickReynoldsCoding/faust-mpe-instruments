"""Starts the real mpe-host against a fake controller, switches instruments through
the control pipe the way the window does, and checks it stays healthy.
No hardware or speakers needed (audio goes to ALSA's `null` device).

Run:  python3 tests/test_host.py
"""
import os, subprocess, sys, tempfile, time
import rtmidi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ui"))
from switcher import read_state, send_command, group_instruments

failures = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"   {detail}"))
    if not cond: failures.append(name)

def wait_for(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond(): return True
        time.sleep(0.05)
    return False

runtime = tempfile.mkdtemp()                       # private control dir, so a real host is untouched
env = dict(os.environ, XDG_RUNTIME_DIR=runtime)
ctl = os.path.join(runtime, "mpe-host", "ctl")
state_file = os.path.join(runtime, "mpe-host", "state")

host = subprocess.Popen([os.path.join(ROOT, "build/mpe-host"), "-d", "null", "-m", "TestSource", "-i", "strings/cello"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
try:
    check("host writes its state file", wait_for(lambda: read_state(state_file) is not None))
    st = read_state(state_file) or {"instruments": [], "current": ""}
    ids = [i["id"] for i in st["instruments"]]
    check("host lists the instruments", len(ids) >= 2, ids)
    check("starts on the requested instrument", st["current"] == "strings/cello", st["current"])
    check("instruments carry group and name",
          all(i["group"] and i["name"] for i in st["instruments"]), st["instruments"][:2])
    check("window groups them by folder", len(group_instruments(st["instruments"])) >= 1)

    # fake controller plays while we switch
    dev = subprocess.Popen([sys.executable, "-c", """
import sys, rtmidi
m = rtmidi.MidiOut(name="TestSource"); m.open_virtual_port("out"); print("ready", flush=True)
for line in sys.stdin: m.send_message([int(x, 16) for x in line.split()])
"""], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    dev.stdout.readline()
    send = lambda *b: (dev.stdin.write(" ".join("%02x" % x for x in b) + "\n"), dev.stdin.flush())
    time.sleep(1.5)                                # host finds the device
    send(0x91, 60, 80); send(0xD1, 100); send(0xB1, 74, 64)
    time.sleep(0.3)

    for target in [i for i in ids if i != "strings/cello"][:3] + ["strings/cello"]:
        ok = send_command(f"load {target}", ctl)
        switched = wait_for(lambda: (read_state(state_file) or {}).get("current") == target)
        check(f"switch to {target} while a note is held", ok and switched)
        check(f"host still running after {target}", host.poll() is None)

    send_command("volume 0.5", ctl)
    check("volume command is reflected", wait_for(lambda: abs((read_state(state_file) or {}).get("volume", 0) - 0.5) < 0.01))
    before = (read_state(state_file) or {}).get("current")
    send_command("load no/such-instrument", ctl)
    time.sleep(0.4)
    check("unknown instrument is ignored", (read_state(state_file) or {}).get("current") == before and host.poll() is None)
    send_command("panic", ctl); send(0x81, 60, 0); time.sleep(0.3)
    check("panic keeps the host alive", host.poll() is None)

    send_command("quit", ctl)
    try:
        code = host.wait(timeout=5)
    except subprocess.TimeoutExpired:
        host.kill(); code = None
    check("quit exits cleanly", code == 0, f"exit code {code}")
    check("state file removed on exit", not os.path.exists(state_file))
    dev.kill()
finally:
    if host.poll() is None:
        host.kill()
    out = host.stdout.read()
    print("\n--- host log ---\n" + out.strip())

check("window reports not running when the host is gone", read_state(state_file) is None)
check("sending to a missing host fails politely", send_command("panic", ctl) is False)
print(f"\n{len(failures)} failed" if failures else "\nall passed")
sys.exit(1 if failures else 0)
