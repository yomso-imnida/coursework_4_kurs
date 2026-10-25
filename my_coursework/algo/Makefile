BUILD_DIR := build
DEBUG_DIR := build-debug

INPUT := ../layer_class_1_based_on_1/5_500.in
GRAPH := input/graph.txt
MATRIX := input/delays.txt

OUTPUT := ../outputdir/output.json
CONF := config.toml
COMMAND := misf
RANDOM := 1234

JOBS := $(shell nproc)

.PHONY: all configure build run run-old debug-configure debug-build debug debug-old gdb clean

all: build

configure:
	cmake -S . -B $(BUILD_DIR) \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5

build: configure
	cmake --build $(BUILD_DIR) -j$(JOBS)

run: build
	mkdir -p ../outputdir
	$(BUILD_DIR)/sched \
		--graph $(GRAPH) \
		--matrix $(MATRIX) \
		--output $(OUTPUT) \
		--conf $(CONF) \
		--command $(COMMAND) \
		--random $(RANDOM)

run-old: build
	mkdir -p ../outputdir
	$(BUILD_DIR)/sched \
		--input $(INPUT) \
		--output $(OUTPUT) \
		--conf $(CONF) \
		--command $(COMMAND) \
		--random $(RANDOM)

debug-configure:
	cmake -S . -B $(DEBUG_DIR) \
		-DCMAKE_BUILD_TYPE=Debug \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5

debug-build: debug-configure
	cmake --build $(DEBUG_DIR) -j$(JOBS)

debug: debug-build
	mkdir -p ../outputdir
	$(DEBUG_DIR)/sched \
		--graph $(GRAPH) \
		--matrix $(MATRIX) \
		--output $(OUTPUT) \
		--conf $(CONF) \
		--command $(COMMAND) \
		--random $(RANDOM)

debug-old: debug-build
	mkdir -p ../outputdir
	$(DEBUG_DIR)/sched \
		--input $(INPUT) \
		--output $(OUTPUT) \
		--conf $(CONF) \
		--command $(COMMAND) \
		--random $(RANDOM)

gdb: debug-build
	mkdir -p ../outputdir
	gdb --args $(DEBUG_DIR)/sched \
		--graph $(GRAPH) \
		--matrix $(MATRIX) \
		--output $(OUTPUT) \
		--conf $(CONF) \
		--command $(COMMAND) \
		--random $(RANDOM)

clean:
	rm -rf $(BUILD_DIR) $(DEBUG_DIR)
