// CPU cost of the violin and cello per voice, for a phone (or any machine).
// Built by phonebench.sh with the generated Faust code of both instruments.
#include <chrono>
#include <cstdio>
#include <vector>
#include "faust/dsp/dsp.h"
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"
#include VIOLIN_CPP
#include CELLO_CPP

template <class T> double bench(const char* name, float freq) {
    const int sr = 48000, blk = 64, voices = 8, seconds = 5;
    std::vector<T> v(voices);
    std::vector<MapUI> ui(voices);
    for (int k = 0; k < voices; k++) {
        v[k].init(sr); v[k].buildUserInterface(&ui[k]);
        *ui[k].getParamZone("freq") = freq * (1 + 0.06f * k); *ui[k].getParamZone("gate") = 1;
        *ui[k].getParamZone("pressure") = 0.6f; *ui[k].getParamZone("slide") = 0.5f; *ui[k].getParamZone("velocity") = 0.6f;
    }
    std::vector<float> in(blk, 0), out(blk);
    float* ins[1] = { in.data() }; float* outs[1] = { out.data() };
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < sr * seconds / blk; i++) for (int k = 0; k < voices; k++) v[k].compute(blk, ins, outs);
    double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    double per = dt / seconds / voices * 100;
    printf("%-8s %.2f%% of one core per voice  (8 voices: %.0f%%)\n", name, per, per * 8);
    return per;
}

int main() {
    bench<Violin>("violin", 330);
    bench<Cello>("cello", 110);
}
