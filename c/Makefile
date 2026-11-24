# Builds the monty-lab CLI and runs the self-contained tests, plain and with sanitizers.
CC ?= gcc
CSTD = -std=c17
WARNINGS = -Wall -Wextra -Werror -pedantic -Wshadow -Wconversion -Wsign-conversion
DEFINES = -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -O2 -g
SANITIZE = -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer
LDLIBS = -lm
PYTHON ?= python3

LIB_SOURCES = src/rational.c src/prng.c src/model.c src/solver.c src/optimum.c \
              src/simulator.c src/json.c src/cli.c
HEADERS = $(wildcard src/*.h)
BUILD = build

.PHONY: all test test-plain test-sanitize conformance conformance-sanitize report clean

all: $(BUILD)/monty-lab

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/monty-lab: $(LIB_SOURCES) src/main.c $(HEADERS) | $(BUILD)
	$(CC) $(CSTD) $(WARNINGS) $(DEFINES) $(CFLAGS) -o $@ $(LIB_SOURCES) src/main.c $(LDLIBS)

$(BUILD)/monty-lab-sanitize: $(LIB_SOURCES) src/main.c $(HEADERS) | $(BUILD)
	$(CC) $(CSTD) $(WARNINGS) $(DEFINES) -O1 -g $(SANITIZE) -o $@ $(LIB_SOURCES) src/main.c $(LDLIBS)

$(BUILD)/test-runner: $(LIB_SOURCES) tests/test_main.c $(HEADERS) | $(BUILD)
	$(CC) $(CSTD) $(WARNINGS) $(DEFINES) $(CFLAGS) -Isrc -o $@ $(LIB_SOURCES) tests/test_main.c $(LDLIBS)

$(BUILD)/test-runner-sanitize: $(LIB_SOURCES) tests/test_main.c $(HEADERS) | $(BUILD)
	$(CC) $(CSTD) $(WARNINGS) $(DEFINES) -O1 -g $(SANITIZE) -Isrc -o $@ $(LIB_SOURCES) tests/test_main.c $(LDLIBS)

test: test-plain test-sanitize

test-plain: $(BUILD)/test-runner
	./$(BUILD)/test-runner

test-sanitize: $(BUILD)/test-runner-sanitize
	./$(BUILD)/test-runner-sanitize

conformance: $(BUILD)/monty-lab
	$(PYTHON) -I ../tools/conformance.py --cli "$(CURDIR)/$(BUILD)/monty-lab"

conformance-sanitize: $(BUILD)/monty-lab-sanitize
	$(PYTHON) -I ../tools/conformance.py --cli "$(CURDIR)/$(BUILD)/monty-lab-sanitize"

report: $(BUILD)/test-runner $(BUILD)/test-runner-sanitize $(BUILD)/monty-lab $(BUILD)/monty-lab-sanitize
	sh tools/report.sh

clean:
	rm -rf $(BUILD)
