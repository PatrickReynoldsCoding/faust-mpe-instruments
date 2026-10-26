// Finds and loads the compiled instruments: <dir>/<group>/<name>.so
#pragma once
#include <algorithm>
#include <dirent.h>
#include <dlfcn.h>
#include <string>
#include <sys/stat.h>
#include <vector>
#include "faust/dsp/dsp.h"

struct InstrumentLib {
    std::string id;           // "strings/cello"
    std::string group;        // "strings"
    std::string name;         // "Cello" (from `declare name`)
    std::string description;
    dsp* (*create)() = nullptr;
};

inline std::vector<std::string> listDir(const std::string& path) {
    std::vector<std::string> out;
    if (DIR* d = opendir(path.c_str())) {
        while (dirent* e = readdir(d))
            if (e->d_name[0] != '.') out.push_back(e->d_name);
        closedir(d);
    }
    std::sort(out.begin(), out.end());
    return out;
}

inline bool loadInstrument(const std::string& soPath, const std::string& group,
                           const std::string& stem, InstrumentLib& out) {
    // Handles stay open for the life of the process: the host may still be
    // running a voice from a library we have since switched away from.
    void* h = dlopen(soPath.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!h) return false;
    auto create = (dsp * (*)()) dlsym(h, "mpe_create");
    auto meta = (const char* (*)(const char*))dlsym(h, "mpe_meta");
    if (!create || !meta) return false;
    out.id = group + "/" + stem;
    out.group = group;
    out.name = meta("name")[0] ? meta("name") : stem;
    out.description = meta("description");
    out.create = create;
    return true;
}

inline std::vector<InstrumentLib> scanInstruments(const std::string& dir) {
    std::vector<InstrumentLib> libs;
    for (const std::string& group : listDir(dir)) {
        std::string gdir = dir + "/" + group;
        struct stat st;
        if (stat(gdir.c_str(), &st) != 0 || !S_ISDIR(st.st_mode)) continue;
        for (const std::string& f : listDir(gdir)) {
            if (f.size() < 4 || f.substr(f.size() - 3) != ".so") continue;
            InstrumentLib lib;
            if (loadInstrument(gdir + "/" + f, group, f.substr(0, f.size() - 3), lib)) libs.push_back(lib);
        }
    }
    return libs;
}
