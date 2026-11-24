/* Minimal indented JSON writer for the monty-lab output contract. */
#ifndef MH_JSON_H
#define MH_JSON_H

#include "rational.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#define MH_JSON_DEPTH 16

typedef struct {
    FILE *out;
    int depth;
    bool first[MH_JSON_DEPTH];
    bool pending_key;
    bool failed;
} mh_json;

void mh_json_init(mh_json *w, FILE *out);
void mh_json_key(mh_json *w, const char *key);
void mh_json_begin_object(mh_json *w);
void mh_json_end_object(mh_json *w);
void mh_json_begin_array(mh_json *w);
void mh_json_end_array(mh_json *w);
void mh_json_string(mh_json *w, const char *value);
void mh_json_int(mh_json *w, int64_t value);
void mh_json_uint(mh_json *w, uint64_t value);
void mh_json_null(mh_json *w);
void mh_json_double(mh_json *w, double value);
void mh_json_frac(mh_json *w, const mh_frac *value);
void mh_json_finish(mh_json *w);

#endif
