#!/usr/bin/env bash
# Build phonebench for the phone (Android NDK, arm64) and run it over adb; or with
# `./phonebench.sh host` build and run it on this machine.
set -e
cd "$(dirname "$0")"
ROOT=../../..
OUT=$ROOT/build-lab/phonebench; mkdir -p $OUT
FAUSTINC=$HOME/repos/mpe-instruments-android/engine/third_party/faust/include
faust -I $ROOT/lib -lang cpp -i -cn Violin -o $OUT/violin.cpp $ROOT/instruments/strings/violin.dsp
faust -I $ROOT/lib -lang cpp -i -cn Cello -o $OUT/cello.cpp $ROOT/instruments/strings/cello.dsp
DEF=(-DVIOLIN_CPP="\"$OUT/violin.cpp\"" -DCELLO_CPP="\"$OUT/cello.cpp\"")
if [ "$1" = host ]; then
    g++ -O3 -std=c++17 -w -I$FAUSTINC "${DEF[@]}" -o $OUT/phonebench-host phonebench.cpp && $OUT/phonebench-host
    exit
fi
source $HOME/repos/mpe-instruments-android/tools/env.sh
CXX=$(ls -d $ANDROID_HOME/ndk/*/toolchains/llvm/prebuilt/linux-x86_64/bin | head -1)/aarch64-linux-android31-clang++
$CXX -O3 -std=c++17 -w -static-libstdc++ -I$FAUSTINC "${DEF[@]}" -o $OUT/phonebench-arm64 phonebench.cpp
adb push $OUT/phonebench-arm64 /data/local/tmp/phonebench >/dev/null
adb shell /data/local/tmp/phonebench
