
BLOSC_PATH=/opt/lib/blosc
OPENVDB_PATH=/opt/lib/openvdb

OPENVDB_LIBS=-Wl,-rpath,$(OPENVDB_PATH)/lib -L$(OPENVDB_PATH)/lib -lopenvdb
BLOSC_LIBS=-Wl,-rpath,$(BLOSC_PATH)/lib -L$(BLOSC_PATH)/lib -lblosc
MISC_LIBS=-ldl -lm -lz -lHalf -ltbb -lboost_iostreams -lboost_system -lrt -ljemalloc

all : openvdb_blend_smoke.bin

openvdb_blend_smoke.bin: openvdb_blend_smoke.cpp
	g++ -pthread -O3 -DNDEBUG -o $@ $^ -isystem $(OPENVDB_PATH)/include $(OPENVDB_LIBS) $(BLOSC_LIBS) $(MISC_LIBS)
