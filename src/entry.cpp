// Wraps one generated Faust instrument as a loadable plugin (.so).
// Built once per instruments/<group>/<name>.dsp, with GEN = the generated C++.
#include <map>
#include <string>
#include "faust/dsp/dsp.h"
#include "faust/gui/meta.h"
#include "faust/gui/UI.h"
#ifndef GEN
#error "build with -DGEN='\"path/to/generated.cpp\"'"
#endif
#include GEN

extern "C" {

dsp* mpe_create() { return new Instrument(); }

// Value of a `declare <key> "<value>";` line in the .dsp, or "" if absent.
const char* mpe_meta(const char* key) {
    static std::map<std::string, std::string> declared;
    static bool loaded = false;
    if (!loaded) {
        struct Collect : Meta {
            std::map<std::string, std::string>& out;
            explicit Collect(std::map<std::string, std::string>& o) : out(o) {}
            void declare(const char* k, const char* v) override { out[k] = v; }
        } collect(declared);
        Instrument tmp;
        tmp.metadata(&collect);
        loaded = true;
    }
    auto it = declared.find(key);
    return it == declared.end() ? "" : it->second.c_str();
}

}
