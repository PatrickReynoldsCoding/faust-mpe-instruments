// mpe-host: plays MPE instruments.
//
//   MPE-Clean:out  ->  [this program]  ->  speakers
//
// Loads every instrument found in build/<group>/<name>.so, runs one copy of the
// current instrument per MPE channel (one per finger), and sets the five controls
// from lib/mpe.lib on each copy: freq, gate, pressure, slide, velocity.
//
// Switch instruments while playing by writing commands to the control pipe
// (the window in ui/ does this):
//     load strings/cello      volume 0.8      transpose -12      panic      quit
// Current state is written to a file next to the pipe, for the window to read.

#include <alsa/asoundlib.h>
#include <atomic>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

#include "faust/dsp/dsp.h"
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"
#include "loader.h"

static const int kChannels = 16;      // MPE: channel 0 is the master, 1..15 carry notes
static const int kBlock = 64;
static std::atomic<bool> gRun{true};

// ---- MPE state, written by the MIDI thread and read by the audio thread -------------

struct ChannelState {
    std::atomic<int> note{-1};          // -1 = no note held
    std::atomic<int> noteOnCount{0};    // bumps on every note on
    std::atomic<float> bend{0};         // semitones
    std::atomic<float> pressure{0};     // 0..1
    std::atomic<float> slide{0.5f};     // 0..1
    std::atomic<float> velocity{0};     // 0..1, raw from the device
};
static ChannelState gCh[kChannels];
static float gBendRange = 48.f;         // MPE default for member channels
static float gVelocityScale = 5.f;      // the Block sends small velocities
static std::atomic<bool> gPanic{false};
static std::atomic<int> gTranspose{0};      // semitones added to every note (octave shift)
static bool gVerbose = false;             // -v: log notes and the values sent to each instrument

// ---- instruments ----------------------------------------------------------------------

// One loaded instrument: a copy per channel, and where to set its controls.
// A control is null when the instrument does not use it (Faust drops unused ones).
struct Slot {
    dsp* d = nullptr;
    MapUI ui;
    FAUSTFLOAT *freq = nullptr, *gate = nullptr, *pressure = nullptr, *slide = nullptr, *velocity = nullptr;
};
struct InstrumentSet {
    const InstrumentLib* lib;
    int outputs = 1;
    Slot slots[kChannels];
    InstrumentSet(const InstrumentLib* l, int sr) : lib(l) {
        for (int ch = 1; ch < kChannels; ch++) {
            Slot& s = slots[ch];
            s.d = lib->create();
            s.d->init(sr);
            s.d->buildUserInterface(&s.ui);
            s.freq = s.ui.getParamZone("freq");
            s.gate = s.ui.getParamZone("gate");
            s.pressure = s.ui.getParamZone("pressure");
            s.slide = s.ui.getParamZone("slide");
            s.velocity = s.ui.getParamZone("velocity");
            outputs = std::min(2, s.d->getNumOutputs());
        }
    }
    ~InstrumentSet() { for (Slot& s : slots) delete s.d; }
};

static std::vector<InstrumentLib> gLibs;
static std::atomic<InstrumentSet*> gPending{nullptr};   // control thread -> audio thread
static std::atomic<InstrumentSet*> gRetired{nullptr};   // audio thread -> control thread
static std::atomic<float> gVolume{0.8f};
static std::string gCurrentId;
static unsigned gSampleRate = 48000;

// ---- MIDI -----------------------------------------------------------------------------

static void midiThread(snd_seq_t* seq) {
    while (gRun) {
        snd_seq_event_t* ev = nullptr;
        int r = snd_seq_event_input(seq, &ev);
        if (r < 0) {
            if (r == -ENOSPC) { gPanic = true; continue; }     // overrun: a note-off may be lost
            if (r == -EAGAIN) continue;
            break;
        }
        if (!ev) continue;
        int ch = ev->data.note.channel & 15;
        if (ch == 0 && (ev->type == SND_SEQ_EVENT_NOTEON || ev->type == SND_SEQ_EVENT_NOTEOFF)) continue;
        ChannelState& c = gCh[ch];
        switch (ev->type) {
        case SND_SEQ_EVENT_NOTEON:
            if (ev->data.note.velocity > 0) {
                c.bend = 0;
                c.pressure = 0;
                c.velocity = ev->data.note.velocity / 127.f;
                c.note = ev->data.note.note;
                c.noteOnCount++;
            } else {
                c.note = -1;
            }
            break;
        case SND_SEQ_EVENT_NOTEOFF: c.note = -1; break;
        case SND_SEQ_EVENT_PITCHBEND: c.bend = ev->data.control.value / 8192.f * gBendRange; break;
        case SND_SEQ_EVENT_CHANPRESS: c.pressure = ev->data.control.value / 127.f; break;
        case SND_SEQ_EVENT_CONTROLLER:
            if (ev->data.control.param == 74 && ch != 0) c.slide = ev->data.control.value / 127.f;
            else if (ev->data.control.param == 120 || ev->data.control.param == 123) gPanic = true;
            break;
        default: break;
        }
    }
}

static bool clientPresent(snd_seq_t* seq, const std::string& match) {
    snd_seq_client_info_t* ci;
    snd_seq_client_info_alloca(&ci);
    snd_seq_client_info_set_client(ci, -1);
    while (snd_seq_query_next_client(seq, ci) >= 0)
        if (std::string(snd_seq_client_info_get_name(ci)).find(match) != std::string::npos) return true;
    return false;
}

static bool connectToSource(snd_seq_t* seq, int myClient, int myPort, const std::string& match) {
    snd_seq_client_info_t* ci;
    snd_seq_client_info_alloca(&ci);
    snd_seq_client_info_set_client(ci, -1);
    while (snd_seq_query_next_client(seq, ci) >= 0) {
        if (std::string(snd_seq_client_info_get_name(ci)).find(match) == std::string::npos) continue;
        int client = snd_seq_client_info_get_client(ci);
        snd_seq_port_info_t* pi;
        snd_seq_port_info_alloca(&pi);
        snd_seq_port_info_set_client(pi, client);
        snd_seq_port_info_set_port(pi, -1);
        while (snd_seq_query_next_port(seq, pi) >= 0) {
            unsigned caps = snd_seq_port_info_get_capability(pi);
            if (!(caps & SND_SEQ_PORT_CAP_READ) || !(caps & SND_SEQ_PORT_CAP_SUBS_READ)) continue;
            snd_seq_port_subscribe_t* sub;
            snd_seq_port_subscribe_alloca(&sub);
            snd_seq_addr_t src = { (unsigned char)client, (unsigned char)snd_seq_port_info_get_port(pi) };
            snd_seq_addr_t dst = { (unsigned char)myClient, (unsigned char)myPort };
            snd_seq_port_subscribe_set_sender(sub, &src);
            snd_seq_port_subscribe_set_dest(sub, &dst);
            if (snd_seq_get_port_subscription(seq, sub) == 0) return false;     // already connected
            if (snd_seq_subscribe_port(seq, sub) == 0) {
                printf("MIDI: connected to '%s' (%d:%d)\n", snd_seq_client_info_get_name(ci), src.client, src.port);
                fflush(stdout);
                return true;
            }
        }
    }
    return false;
}

// ---- control pipe and state file --------------------------------------------------------

static std::string gCtlDir, gCtlPipe, gStateFile;

static void writeState() {
    std::string tmp = gStateFile + ".tmp";
    FILE* f = fopen(tmp.c_str(), "w");
    if (!f) return;
    fprintf(f, "pid=%d\ncurrent=%s\nvolume=%.2f\ntranspose=%d\n", (int)getpid(), gCurrentId.c_str(), gVolume.load(), gTranspose.load());
    for (const InstrumentLib& l : gLibs)
        fprintf(f, "instrument=%s\t%s\t%s\t%s\n", l.id.c_str(), l.group.c_str(), l.name.c_str(), l.description.c_str());
    fclose(f);
    rename(tmp.c_str(), gStateFile.c_str());
}

// Builds the new instrument off the audio thread, hands it over, and frees the old one
// once the audio thread has let go of it.
static bool switchTo(const std::string& id) {
    const InstrumentLib* lib = nullptr;
    for (const InstrumentLib& l : gLibs) if (l.id == id) lib = &l;
    if (!lib) { fprintf(stderr, "unknown instrument '%s'\n", id.c_str()); return false; }
    InstrumentSet* fresh = new InstrumentSet(lib, gSampleRate);
    gPending.store(fresh);
    for (int i = 0; i < 200 && gPending.load() && gRun; i++) usleep(5000);     // wait for the swap
    delete gRetired.exchange(nullptr);
    gCurrentId = id;
    printf("Instrument: %s (%s)\n", lib->name.c_str(), id.c_str());
    fflush(stdout);
    writeState();
    return true;
}

static void controlThread() {
    int fd = open(gCtlPipe.c_str(), O_RDWR | O_NONBLOCK);       // O_RDWR: never sees EOF
    if (fd < 0) { perror("control pipe"); return; }
    std::string buf;
    while (gRun) {
        char tmp[256];
        ssize_t n = read(fd, tmp, sizeof(tmp));
        if (n <= 0) { usleep(20000); continue; }
        buf.append(tmp, n);
        size_t nl;
        while ((nl = buf.find('\n')) != std::string::npos) {
            std::string line = buf.substr(0, nl);
            buf.erase(0, nl + 1);
            if (line.rfind("load ", 0) == 0) switchTo(line.substr(5));
            else if (line.rfind("volume ", 0) == 0) { gVolume = std::min(1.f, std::max(0.f, (float)atof(line.c_str() + 7))); writeState(); }
            else if (line.rfind("transpose ", 0) == 0) { gTranspose = std::max(-96, std::min(96, atoi(line.c_str() + 10))); writeState(); }
            else if (line == "panic") gPanic = true;
            else if (line == "quit") gRun = false;
        }
    }
    close(fd);
}

// ---- audio ------------------------------------------------------------------------------

struct VoiceRuntime {
    int seenNoteOn = 0;
    bool sounding = false;
    float freq = 440, pressure = 0, slide = 0.5f, level = 0;
    int quietBlocks = 0;
    int logTick = 0;
};

static float smoothTo(float cur, float target, float coef) { return cur + (target - cur) * coef; }
static float noteToHz(float note) { return 440.f * std::pow(2.f, (note - 69.f) / 12.f); }

int main(int argc, char** argv) {
    std::string pcmName = "default", midiMatch = "MPE-Clean", buildDir, initial;
    snd_pcm_uframes_t period = 128;
    {   // default build dir: ../build relative to this binary
        char exe[1024];
        ssize_t n = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
        std::string p = n > 0 ? std::string(exe, n) : ".";
        buildDir = p.substr(0, p.find_last_of('/'));
    }
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        auto next = [&]() { return i + 1 < argc ? std::string(argv[++i]) : std::string(); };
        if (a == "-d") pcmName = next();
        else if (a == "-m") midiMatch = next();
        else if (a == "-r") gBendRange = atof(next().c_str());
        else if (a == "-s") gVelocityScale = atof(next().c_str());
        else if (a == "-p") period = atoi(next().c_str());
        else if (a == "-b") buildDir = next();
        else if (a == "-i") initial = next();
        else if (a == "-v") gVerbose = true;
        else if (a == "-t") gTranspose = atoi(next().c_str());
        else {
            fprintf(stderr, "usage: %s [-i group/name] [-b build-dir] [-d pcm] [-m midi-name] [-r bend-semitones]\n"
                            "          [-s velocity-scale] [-p period-frames] [-t transpose-semitones] [-v]\n", argv[0]);
            return 1;
        }
    }
    signal(SIGINT, [](int) { gRun = false; });
    signal(SIGTERM, [](int) { gRun = false; });
    setvbuf(stdout, nullptr, _IOLBF, 0);

    gLibs = scanInstruments(buildDir);
    if (gLibs.empty()) { fprintf(stderr, "no instruments found in %s (run `make`)\n", buildDir.c_str()); return 1; }
    printf("Found %zu instruments in %s\n", gLibs.size(), buildDir.c_str());
    if (initial.empty()) {
        initial = gLibs[0].id;
        for (const InstrumentLib& l : gLibs) if (l.id == "strings/cello") initial = l.id;
    }

    // control pipe + state file
    const char* rt = getenv("XDG_RUNTIME_DIR");
    gCtlDir = std::string(rt ? rt : "/tmp") + "/mpe-host";
    mkdir(gCtlDir.c_str(), 0700);
    gCtlPipe = gCtlDir + "/ctl";
    gStateFile = gCtlDir + "/state";
    unlink(gCtlPipe.c_str());
    if (mkfifo(gCtlPipe.c_str(), 0600) != 0) { perror("mkfifo"); return 1; }

    // MIDI
    snd_seq_t* seq;
    if (snd_seq_open(&seq, "default", SND_SEQ_OPEN_INPUT, 0) < 0) { fprintf(stderr, "cannot open ALSA sequencer\n"); return 1; }
    snd_seq_set_client_name(seq, "MPE-Host");
    snd_seq_set_client_pool_input(seq, 4000);
    int port = snd_seq_create_simple_port(seq, "in", SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE,
                                          SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    int myClient = snd_seq_client_id(seq);
    std::thread midi(midiThread, seq);
    std::thread watcher([=]() {                 // keeps looking for the source, so a restart or replug just works
        snd_seq_t* s2;
        if (snd_seq_open(&s2, "default", SND_SEQ_OPEN_DUPLEX, 0) < 0) return;
        snd_seq_set_client_name(s2, "MPE-Host-connect");
        bool wasPresent = false;
        while (gRun) {
            bool present = clientPresent(s2, midiMatch);
            if (wasPresent && !present) { gPanic = true; fprintf(stderr, "MIDI: '%s' disappeared, releasing all notes\n", midiMatch.c_str()); }
            wasPresent = present;
            if (present) connectToSource(s2, myClient, port, midiMatch);
            for (int i = 0; i < 10 && gRun; i++) usleep(100000);
        }
        snd_seq_close(s2);
    });

    // Audio
    snd_pcm_t* pcm;
    if (snd_pcm_open(&pcm, pcmName.c_str(), SND_PCM_STREAM_PLAYBACK, 0) < 0) { fprintf(stderr, "cannot open audio device '%s'\n", pcmName.c_str()); return 1; }
    snd_pcm_uframes_t bufsize = period * 4;
    int err = snd_pcm_set_params(pcm, SND_PCM_FORMAT_FLOAT_LE, SND_PCM_ACCESS_RW_INTERLEAVED, 2, gSampleRate, 1,
                                 (unsigned)(1e6 * bufsize / gSampleRate));
    if (err < 0) { fprintf(stderr, "audio setup failed: %s\n", snd_strerror(err)); return 1; }
    printf("Audio: '%s', %u Hz, ~%.1f ms buffer. Bend range +/-%.0f semitones.\n",
           pcmName.c_str(), gSampleRate, 1000.0 * bufsize / gSampleRate, gBendRange);

    InstrumentSet* cur = nullptr;
    {
        const InstrumentLib* first = &gLibs[0];
        for (const InstrumentLib& l : gLibs) if (l.id == initial) first = &l;
        cur = new InstrumentSet(first, gSampleRate);
        gCurrentId = first->id;
        printf("Instrument: %s (%s)\n", first->name.c_str(), first->id.c_str());
    }
    writeState();
    std::thread control(controlThread);

    const float dt = float(kBlock) / gSampleRate;
    auto coef = [&](float tau) { return 1.f - std::exp(-dt / tau); };
    const float cFreq = coef(0.004f), cPress = coef(0.012f), cSlide = coef(0.02f);
    const int quietLimit = int(0.4f / dt);

    VoiceRuntime rt_[kChannels];
    std::vector<float> in(kBlock, 0.f), outL(kBlock), outR(kBlock), mixL(kBlock), mixR(kBlock), stereo(kBlock * 2);
    float* ins[1] = { in.data() };

    while (gRun) {
        if (InstrumentSet* fresh = gPending.exchange(nullptr)) {     // instrument switch
            gRetired.store(cur);
            cur = fresh;
            for (int ch = 1; ch < kChannels; ch++) {
                rt_[ch].sounding = false;
                if (gCh[ch].note.load() >= 0) rt_[ch].seenNoteOn = gCh[ch].noteOnCount.load() - 1;   // restart held notes
            }
        }
        if (gPanic.exchange(false))
            for (int ch = 0; ch < kChannels; ch++) { gCh[ch].note = -1; gCh[ch].pressure = 0; }

        std::fill(mixL.begin(), mixL.end(), 0.f);
        std::fill(mixR.begin(), mixR.end(), 0.f);
        for (int ch = 1; ch < kChannels; ch++) {
            Slot& sl = cur->slots[ch];
            VoiceRuntime& v = rt_[ch];
            ChannelState& c = gCh[ch];
            int note = c.note.load();
            int cnt = c.noteOnCount.load();
            bool held = note >= 0;

            if (cnt != v.seenNoteOn) {                   // a new note on this channel
                v.seenNoteOn = cnt;
                if (!held) { v.sounding = false; }
                else {
                    v.sounding = true;
                    v.quietBlocks = 0;
                    v.freq = noteToHz(note + gTranspose.load() + c.bend.load());
                    v.pressure = c.pressure.load();
                    v.slide = c.slide.load();
                    sl.d->instanceClear();               // so `gate > gate'` sees a clean 0 -> 1
                    if (gVerbose)
                        printf("note on: ch %d note %d -> %.1f Hz  controls found: freq=%d gate=%d pressure=%d slide=%d velocity=%d\n",
                               ch, note, v.freq, sl.freq != nullptr, sl.gate != nullptr, sl.pressure != nullptr, sl.slide != nullptr, sl.velocity != nullptr);
                }
            }
            if (!v.sounding) continue;

            if (held) {                                  // after release, freeze pitch so ringing notes don't drift
                v.freq = smoothTo(v.freq, noteToHz(note + gTranspose.load() + c.bend.load()), cFreq);
                v.pressure = smoothTo(v.pressure, c.pressure.load(), cPress);
                v.slide = smoothTo(v.slide, c.slide.load(), cSlide);
            }
            v.freq = std::min(std::max(v.freq, 20.f), 5000.f);

            if (sl.freq) *sl.freq = v.freq;
            if (sl.gate) *sl.gate = held ? 1.f : 0.f;
            if (sl.pressure) *sl.pressure = v.pressure;
            if (sl.slide) *sl.slide = v.slide;
            if (sl.velocity) *sl.velocity = std::min(1.f, c.velocity.load() * gVelocityScale);

            if (gVerbose && ++v.logTick % 375 == 0)          // about every half second
                printf("  ch %d: freq %.1f gate %.0f pressure %.2f slide %.2f velocity %.2f   level %.4f\n",
                       ch, v.freq, held ? 1.f : 0.f, v.pressure, v.slide, std::min(1.f, c.velocity.load() * gVelocityScale), v.level);
            float* outs[2] = { outL.data(), outR.data() };
            sl.d->compute(kBlock, ins, outs);
            const float* r = cur->outputs > 1 ? outR.data() : outL.data();
            float e = 0;
            for (int i = 0; i < kBlock; i++) { mixL[i] += outL[i]; mixR[i] += r[i]; e += outL[i] * outL[i]; }
            v.level = smoothTo(v.level, std::sqrt(e / kBlock), 0.2f);
            if (!held) v.quietBlocks = (v.level < 3e-5f) ? v.quietBlocks + 1 : 0;
            if (!held && v.quietBlocks > quietLimit) v.sounding = false;    // fully decayed
        }
        const float vol = gVolume.load();
        for (int i = 0; i < kBlock; i++) {               // soft limiter
            stereo[2 * i] = std::tanh(mixL[i] * vol * 1.5f) * 0.7f;
            stereo[2 * i + 1] = std::tanh(mixR[i] * vol * 1.5f) * 0.7f;
        }
        snd_pcm_sframes_t n = snd_pcm_writei(pcm, stereo.data(), kBlock);
        if (n < 0) snd_pcm_recover(pcm, (int)n, 1);
    }
    gRun = false;
    snd_pcm_drain(pcm);
    snd_pcm_close(pcm);
    control.join();
    watcher.join();
    midi.detach();
    unlink(gCtlPipe.c_str());
    unlink(gStateFile.c_str());
    return 0;
}
