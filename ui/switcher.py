#!/usr/bin/env python3
"""A very small window to switch instruments.

Talks to mpe-host through a pipe and reads its state from a file, both in
$XDG_RUNTIME_DIR/mpe-host/. Needs nothing but Python's built-in Tk.
"""
import errno
import os
import tkinter as tk
from tkinter import ttk

CTL_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "mpe-host")
CTL_PIPE = os.path.join(CTL_DIR, "ctl")
STATE_FILE = os.path.join(CTL_DIR, "state")
POLL_MS = 400
COLUMNS = 3


def read_state(path=STATE_FILE):
    """State as a dict, or None if the host is not running.

    {"current": "strings/cello", "volume": 0.8,
     "instruments": [{"id", "group", "name", "description"}, ...]}"""
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    state = {"current": "", "volume": 0.8, "pid": 0, "transpose": 0, "instruments": []}
    for line in lines:
        key, _, value = line.partition("=")
        if key == "current":
            state["current"] = value
        elif key == "volume":
            state["volume"] = float(value or 0.8)
        elif key == "transpose":
            state["transpose"] = int(value or 0)
        elif key == "pid":
            state["pid"] = int(value or 0)
        elif key == "instrument":
            parts = (value.split("\t") + ["", "", "", ""])[:4]
            state["instruments"].append(dict(zip(("id", "group", "name", "description"), parts)))
    # A leftover file from a host that crashed: the process is gone.
    if state["pid"]:
        try:
            os.kill(state["pid"], 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            pass
    return state


def send_command(command, pipe=CTL_PIPE):
    """Send one line to the host. False if the host is not listening."""
    try:
        fd = os.open(pipe, os.O_WRONLY | os.O_NONBLOCK)    # ENXIO if nobody has it open
    except OSError as e:
        if e.errno in (errno.ENXIO, errno.ENOENT):
            return False
        raise
    try:
        os.write(fd, (command + "\n").encode())
    finally:
        os.close(fd)
    return True


def group_instruments(instruments):
    """[(group, [instrument, ...]), ...] keeping the host's order."""
    groups = {}
    for inst in instruments:
        groups.setdefault(inst["group"], []).append(inst)
    return list(groups.items())


class Switcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MPE Instruments")
        self.minsize(420, 200)
        self.status = tk.StringVar(value="Looking for mpe-host...")
        self.buttons = {}
        self.shown_ids = None
        self.volume_after = None

        ttk.Label(self, textvariable=self.status, font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True, padx=12)

        octave = ttk.Frame(self)
        octave.pack(fill="x", padx=12, pady=(8, 0))
        ttk.Label(octave, text="Octave").pack(side="left")
        ttk.Button(octave, text="-", width=3, command=lambda: self.shift(-12)).pack(side="left", padx=(8, 2))
        self.octave_label = tk.StringVar(value="0")
        ttk.Label(octave, textvariable=self.octave_label, width=5, anchor="center").pack(side="left")
        ttk.Button(octave, text="+", width=3, command=lambda: self.shift(12)).pack(side="left", padx=(2, 8))
        ttk.Label(octave, text="(shifts every key; use it if notes sound too high or too low)").pack(side="left")
        self.transpose = 0

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=12, pady=10)
        ttk.Label(bottom, text="Volume").pack(side="left")
        self.volume = tk.DoubleVar(value=80)
        ttk.Scale(bottom, from_=0, to=100, variable=self.volume, command=self.on_volume).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(bottom, text="All notes off", command=lambda: self.send("panic")).pack(side="right")

        self.style = ttk.Style(self)
        self.style.configure("Current.TButton", font=("TkDefaultFont", 10, "bold"))
        self.after(50, self.poll)

    def send(self, command):
        if not send_command(command):
            self.status.set("mpe-host is not running")

    def shift(self, semitones):
        self.transpose = max(-96, min(96, self.transpose + semitones))
        self.octave_label.set(f"{self.transpose // 12:+d}")
        self.send(f"transpose {self.transpose}")

    def on_volume(self, _value):
        if self.volume_after:
            self.after_cancel(self.volume_after)
        self.volume_after = self.after(80, lambda: self.send(f"volume {self.volume.get() / 100:.2f}"))

    def rebuild(self, instruments):
        for child in self.body.winfo_children():
            child.destroy()
        self.buttons = {}
        for group, items in group_instruments(instruments):
            frame = ttk.LabelFrame(self.body, text=group.capitalize())
            frame.pack(fill="x", pady=4)
            for i, inst in enumerate(items):
                b = ttk.Button(frame, text=inst["name"], command=lambda iid=inst["id"]: self.send(f"load {iid}"))
                b.grid(row=i // COLUMNS, column=i % COLUMNS, padx=4, pady=4, sticky="ew")
                self.buttons[inst["id"]] = b
            for col in range(COLUMNS):
                frame.columnconfigure(col, weight=1, uniform="b")

    def poll(self):
        state = read_state()
        if state is None:
            self.status.set("mpe-host is not running")
        else:
            ids = [i["id"] for i in state["instruments"]]
            if ids != self.shown_ids:
                self.rebuild(state["instruments"])
                self.shown_ids = ids
            self.transpose = state["transpose"]                       # the host is the source of truth
            self.octave_label.set(f"{self.transpose // 12:+d}")
            names = {i["id"]: i["name"] for i in state["instruments"]}
            self.status.set(f"Playing: {names.get(state['current'], state['current'])}")
            for iid, b in self.buttons.items():
                b.configure(style="Current.TButton" if iid == state["current"] else "TButton")
                b.state(["pressed"] if iid == state["current"] else ["!pressed"])
        self.after(POLL_MS, self.poll)


if __name__ == "__main__":
    Switcher().mainloop()
