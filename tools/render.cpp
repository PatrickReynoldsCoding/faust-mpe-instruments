// Offline renderer: plays one note through one instrument, writes raw float32.
//   render <instrument.so> <out.f32> freq pressure slide velocity [hold_s] [total_s]
// Drives the instrument exactly as the host does: gate 0 -> 1 on a cleared
// instrument, controls updated every 64 samples, gate -> 0 after hold_s.
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"
#include "faust/dsp/dsp.h"
#include "../src/loader.h"

int main(int argc, char** argv) {
    if (argc < 7) { fprintf(stderr, "usage: render so out freq pressure slide velocity [hold] [total]\n"); return 1; }
    std::string so = argv[1];
    float freq = atof(argv[3]), pressure = atof(argv[4]), slide = atof(argv[5]), velocity = atof(argv[6]);
    float hold = argc > 7 ? atof(argv[7]) : 1.5f, total = argc > 8 ? atof(argv[8]) : hold + 2.f;
    // Optional extra controls after the 8 fixed args: name=value (used by lab instruments).
    std::vector<std::pair<std::string, float>> extra;
    for (int i = 9; i < argc; i++) {
        std::string a = argv[i];
        size_t eq = a.find('=');
        if (eq != std::string::npos) extra.push_back({a.substr(0, eq), (float)atof(a.c_str() + eq + 1)});
    }

    InstrumentLib lib;
    if (!loadInstrument(so, "g", "i", lib)) { fprintf(stderr, "cannot load %s: %s\n", so.c_str(), dlerror()); return 1; }
    const int sr = 48000, blk = 64, n = int(total * sr) / blk * blk;
    dsp* d = lib.create();
    d->init(sr);
    MapUI ui;
    d->buildUserInterface(&ui);
    d->instanceClear();
    // An instrument only has the controls it uses (Faust drops the rest).
    auto zone = [&](const char* name) { return ui.getParamZone(name); };
    FAUSTFLOAT *zFreq = zone("freq"), *zPress = zone("pressure"), *zSlide = zone("slide"),
               *zVel = zone("velocity"), *zGate = zone("gate");
    for (auto& e : extra) if (FAUSTFLOAT* z = ui.getParamZone(e.first.c_str())) *z = e.second;
    std::vector<float> out(n), in(blk, 0.f);
    float* ins[1] = { in.data() };
    for (int i = 0; i < n; i += blk) {
        float t = float(i) / sr;
        if (zFreq) *zFreq = freq;
        if (zPress) *zPress = pressure;
        if (zSlide) *zSlide = slide;
        if (zVel) *zVel = velocity;
        if (zGate) *zGate = t < hold ? 1.f : 0.f;
        // Instruments may have 1 or 2 outputs; mix to mono.
        int nout = d->getNumOutputs();
        std::vector<std::vector<float>> bufs(nout, std::vector<float>(blk));
        std::vector<float*> outs(nout);
        for (int c = 0; c < nout; c++) outs[c] = bufs[c].data();
        d->compute(blk, ins, outs.data());
        for (int k = 0; k < blk; k++) {
            float s = 0;
            for (int c = 0; c < nout; c++) s += bufs[c][k];
            out[i + k] = s / nout;
        }
    }
    FILE* f = fopen(argv[2], "wb");
    fwrite(out.data(), sizeof(float), n, f);
    fclose(f);
    return 0;
}
