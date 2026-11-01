// Plays an instrument from control curves, the way the host would, and writes raw float32.
//   render_curves <instrument.so> <controls.f32> <voices> <out.f32> [name=value ...]
// controls.f32 holds, for every 64-sample block and every voice, 6 floats:
//   freq, gate, pressure, slide, velocity, legato
// (shape blocks x voices x 6). Each voice is its own instrument copy, cleared before every
// note (gate 0 -> 1), like the host does. Extra name=value pairs set any other control.
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"
#include "faust/dsp/dsp.h"
#include "../../src/loader.h"

int main(int argc, char** argv) {
    if (argc < 5) { fprintf(stderr, "usage: render_curves so controls.f32 voices out.f32 [name=value...]\n"); return 1; }
    InstrumentLib lib;
    if (!loadInstrument(argv[1], "g", "i", lib)) { fprintf(stderr, "cannot load %s: %s\n", argv[1], dlerror()); return 1; }
    int nv = atoi(argv[3]);
    FILE* cf = fopen(argv[2], "rb");
    if (!cf) { perror(argv[2]); return 1; }
    std::vector<float> ctl;
    float buf[4096];
    size_t got;
    while ((got = fread(buf, sizeof(float), 4096, cf)) > 0) ctl.insert(ctl.end(), buf, buf + got);
    fclose(cf);
    const int sr = 48000, blk = 64;
    const int NC = 6;
    size_t nblocks = ctl.size() / (nv * NC);

    struct V { dsp* d; MapUI ui; FAUSTFLOAT *f, *g, *p, *s, *v, *l; float lastGate = 0; };
    std::vector<V> vs(nv);
    for (auto& v : vs) {
        v.d = lib.create();
        v.d->init(sr);
        v.d->buildUserInterface(&v.ui);
        v.d->instanceClear();
        v.f = v.ui.getParamZone("freq"); v.g = v.ui.getParamZone("gate"); v.p = v.ui.getParamZone("pressure");
        v.s = v.ui.getParamZone("slide"); v.v = v.ui.getParamZone("velocity"); v.l = v.ui.getParamZone("legato");
        for (int i = 5; i < argc; i++) {
            std::string a = argv[i];
            size_t eq = a.find('=');
            if (eq != std::string::npos)
                if (FAUSTFLOAT* z = v.ui.getParamZone(a.substr(0, eq))) *z = (float)atof(a.c_str() + eq + 1);
        }
    }
    int nout = vs[0].d->getNumOutputs();
    std::vector<std::vector<float>> bufs(nout, std::vector<float>(blk));
    std::vector<float*> outs(nout);
    for (int c = 0; c < nout; c++) outs[c] = bufs[c].data();
    std::vector<float> in(blk, 0.f);
    float* ins[1] = { in.data() };
    std::vector<float> out(nblocks * blk, 0.f);
    for (size_t b = 0; b < nblocks; b++) {
        for (int k = 0; k < nv; k++) {
            V& v = vs[k];
            const float* c = &ctl[(b * nv + k) * NC];
            if (c[1] > 0.5f && v.lastGate < 0.5f) v.d->instanceClear();   // new note on a cleared copy
            v.lastGate = c[1];
            if (v.f) *v.f = c[0];
            if (v.g) *v.g = c[1];
            if (v.p) *v.p = c[2];
            if (v.s) *v.s = c[3];
            if (v.v) *v.v = c[4];
            if (v.l) *v.l = c[5];
            v.d->compute(blk, ins, outs.data());
            for (int i = 0; i < blk; i++) {
                float s = 0;
                for (int ch = 0; ch < nout; ch++) s += bufs[ch][i];
                out[b * blk + i] += s / nout;
            }
        }
    }
    FILE* f = fopen(argv[4], "wb");
    fwrite(out.data(), sizeof(float), out.size(), f);
    fclose(f);
    return 0;
}
