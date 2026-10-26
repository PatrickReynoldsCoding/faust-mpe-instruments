# Build everything:  make
# One sound = one file in instruments/<group>/<name>.dsp
FAUST   ?= faust
CXXFLAGS ?= -O2 -std=c++17 -Wall
DSPS    := $(shell find instruments -name '*.dsp' | sort)
SOS     := $(patsubst instruments/%.dsp,build/%.so,$(DSPS))
LIBS    := $(wildcard lib/*.lib)

all: $(SOS) build/mpe-host build/render

build/%.cpp: instruments/%.dsp $(LIBS)
	@mkdir -p $(dir $@)
	$(FAUST) -I lib -lang cpp -i -cn Instrument -o $@ $<

build/%.so: build/%.cpp src/entry.cpp
	$(CXX) $(CXXFLAGS) -w -shared -fPIC -DGEN='"$(abspath $<)"' -o $@ src/entry.cpp

build/render: tools/render.cpp src/loader.h
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $< -ldl

build/mpe-host: src/mpe-host.cpp src/loader.h
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $< -lasound -lpthread -ldl

test: all
	python3 tests/test_instruments.py

clean:
	rm -rf build

.PHONY: all test clean
