#!/usr/bin/env python3
"""Pack instruments as MESH instrument packages (.odoi), as odo's docs/formats/INSTRUMENT_FORMAT.md describes.

    tools/pack.py [-o build/packages] [--sounds packs-dir] [instruments/<group>/<name>.dsp ...]
    tools/pack.py --keep instruments/<group>/<name>.dsp ...

With no files, packs every instrument. A package is a zip:

    instrument.json   the manifest, made from the .dsp's `declare`s and Faust's own description
    instrument.dsp    the source, as written
    lib/*.lib         every library it imports (ours and Faust's), so it builds the same anywhere

The effects an instrument is meant to be heard with are its own: `declare sound "reverb=0.3 ..."`.
--sounds: a folder of odo's pack manifests (assets/packs/*.json), only for an instrument that has
no `declare sound` (older checkouts).
A package is only rebuilt when its .dsp or a library it uses is newer.

Old versions (odo's docs/formats/INSTRUMENT_FORMAT.md, "Versions sit side by side"): versions/<name>@<version>.odoi are
packages kept as they were, so a sound can be played as it was, or a change rolled back. They are
copied beside the new packages. Before changing how an instrument sounds, keep the version it is
now (--keep), then raise its `declare version`.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = {"freq", "gate", "pressure", "slide", "velocity", "legato"}
AUTHOR_ID = "patrickreynolds"


def declares(text):
    """Top-level `declare key "value";` lines (not those inside a library)."""
    return {k: v for k, v in re.findall(r'^\s*declare\s+(\w+)\s+"((?:[^"\\]|\\.)*)"\s*;', text, re.M)}


def describe(dsp, libdir, process):
    """Faust's JSON for `process` (or another name): libraries used, outputs, controls."""
    with tempfile.TemporaryDirectory() as t:
        cmd = ["faust", "-I", libdir, "-json", "-O", t, "-o", "out.cpp", dsp]
        if process != "process":
            cmd[1:1] = ["-pn", process]
        subprocess.run(cmd, check=True, capture_output=True)
        return json.load(open(os.path.join(t, os.path.basename(dsp) + ".json")))


def controls(ui):
    for item in ui:
        if "items" in item:
            yield from controls(item["items"])
        else:
            yield item


def sound_defaults(packs_dir):
    """id -> the effects odo's pack manifests give it."""
    out = {}
    for f in sorted(glob.glob(os.path.join(packs_dir, "*.json"))):
        p = json.load(open(f))
        base = p.get("defaults", {})
        for g in p.get("groups", []):
            for i in g.get("instruments", []):
                out.setdefault(i, dict(base, **p.get("overrides", {}).get(i, {})))
    return out


SOUND_KEYS = ("reverb", "reverbSize", "reverbDamp", "delay", "brightness", "drive", "pressureCurve", "release")


def own_sound(d):
    """The effects the instrument itself says it is meant to be heard with: `declare sound "reverb=0.3 delay=0 ..."`."""
    out = {}
    for pair in d.get("sound", "").split():
        k, _, v = pair.partition("=")
        if k in SOUND_KEYS:
            out[k] = float(v)
    return out


def references(d):
    """What a fitted instrument was made from: `declare artist`, `songs` (titles separated by " | "),
    `reference_licence`. None for an instrument that was not fitted to recordings."""
    songs = [t.strip() for t in d.get("songs", "").split("|") if t.strip()]
    if not songs and "artist" not in d:
        return None
    return {"artist": d.get("artist", ""), "songs": songs, "licence": d.get("reference_licence", "")}


def pack(dsp, out_dir, libdir, sounds):
    group = os.path.basename(os.path.dirname(dsp))
    stem = os.path.splitext(os.path.basename(dsp))[0]
    old_id = f"{group}/{stem}"
    text = open(dsp).read()
    d = declares(text)
    has_post = re.search(r"^post\s*=", text, re.M) is not None

    main = describe(dsp, libdir, "process")
    libs = set(main["library_list"])
    channels = 1
    if has_post:
        post = describe(dsp, libdir, "post")
        libs |= set(post["library_list"])
        channels = post["outputs"]
    target = os.path.join(out_dir, f"{stem}.odoi")
    newest = max(os.path.getmtime(p) for p in [dsp, __file__, *libs])
    if os.path.exists(target) and os.path.getmtime(target) >= newest:
        return target, False

    knobs = []
    for c in controls(main["ui"]):
        if c["label"] in CONTRACT or c["type"] in ("vbargraph", "hbargraph"):
            continue
        knobs.append({"id": c["label"], "name": c["label"], "type": "switch" if c["type"] in ("checkbox", "button") else "number",
                      "min": c.get("min", 0), "max": c.get("max", 1), "step": c.get("step", 0), "default": c.get("init", 0)})
    rng = [float(x) for x in d.get("range", "").split()] or None
    manifest = {
        "format": 1,
        "contract": d.get("contract", "mpe-voice/1"),
        "id": d.get("id", f"{AUTHOR_ID}/{stem}"),
        "version": d.get("version", "1.0.0"),
        "aliases": [old_id],
        "name": d.get("name", stem),
        "description": d.get("description", ""),
        "author": d.get("author", "Patrick Reynolds"),
        "licence": d.get("licence", "MIT"),
        "range": rng,
        "channels": channels,
        "post": has_post,
        "status": d.get("status", "current"),
        "tags": [group],
        "knobs": knobs,
        "sound": dict(sounds.get(old_id, {}), **own_sound(d)),
        "references": references(d),
        "tests": {k: d[k] for k in ("ringout", "window", "pitched") if k in d},
        "faust": main["version"],
    }
    os.makedirs(out_dir, exist_ok=True)
    tmp = target + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("instrument.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        z.writestr("instrument.dsp", text)
        for lib in sorted(libs):
            z.write(lib, "lib/" + os.path.basename(lib))
    os.replace(tmp, target)
    return target, True


VERSIONS = os.path.join(HERE, "versions")


def keep(dsp, libdir, sounds):
    """Pack the instrument as it is now into versions/<name>@<version>.odoi, never over one kept before."""
    with tempfile.TemporaryDirectory() as t:
        made, _ = pack(dsp, t, libdir, sounds)
        with zipfile.ZipFile(made) as z:
            m = json.loads(z.read("instrument.json"))
        stem = os.path.splitext(os.path.basename(dsp))[0]
        target = os.path.join(VERSIONS, f"{stem}@{m['version']}.odoi")
        if os.path.exists(target):
            sys.exit(f"{target} is kept already: raise the instrument's `declare version` first")
        os.makedirs(VERSIONS, exist_ok=True)
        shutil.copyfile(made, target)
        return target


def copy_kept(out_dir, current):
    """versions/*.odoi beside the new packages; one that is the version an instrument is now is left out."""
    n = 0
    for f in sorted(glob.glob(os.path.join(VERSIONS, "*.odoi"))):
        name = os.path.basename(f)
        stem, _, ver = name[:-len(".odoi")].partition("@")
        if current.get(stem) == ver:
            continue
        target = os.path.join(out_dir, name)
        if not os.path.exists(target) or os.path.getmtime(target) < os.path.getmtime(f):
            shutil.copyfile(f, target)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "build", "packages"))
    ap.add_argument("--sounds", help="folder of odo's pack manifests (assets/packs)")
    ap.add_argument("--keep", action="store_true", help="keep the named instruments' versions now in versions/")
    ap.add_argument("dsp", nargs="*")
    a = ap.parse_args()
    files = a.dsp or sorted(glob.glob(os.path.join(HERE, "instruments", "*", "*.dsp")))
    sounds = sound_defaults(a.sounds) if a.sounds else {}
    stems = [os.path.splitext(os.path.basename(f))[0] for f in files]
    dup = {s for s in stems if stems.count(s) > 1}
    if dup:
        sys.exit(f"two instruments share a name: {sorted(dup)} (their ids would clash)")
    if a.keep:
        if not a.dsp:
            sys.exit("--keep: name the instruments to keep")
        for f in files:
            print("kept", keep(f, os.path.join(HERE, "lib"), sounds))
        return
    made = 0
    current = {}
    for f in files:
        target, new = pack(f, a.out, os.path.join(HERE, "lib"), sounds)
        made += new
        with zipfile.ZipFile(target) as z:
            current[os.path.splitext(os.path.basename(f))[0]] = json.loads(z.read("instrument.json"))["version"]
    old = copy_kept(a.out, current) if not a.dsp else 0
    print(f"{len(files)} packages in {a.out} ({made} rebuilt){f', {old} older versions' if old else ''}")


if __name__ == "__main__":
    main()
