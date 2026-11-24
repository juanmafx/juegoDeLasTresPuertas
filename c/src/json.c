/* Minimal indented JSON writer for the monty-lab output contract. */
#include "json.h"

#include <stdlib.h>
#include <string.h>

void mh_json_init(mh_json *w, FILE *out) {
    w->out = out;
    w->depth = 0;
    w->first[0] = true;
    w->pending_key = false;
}

static void indent(mh_json *w) {
    fputc('\n', w->out);
    for (int i = 0; i < w->depth; i++) {
        fputs("  ", w->out);
    }
}

static void element(mh_json *w) {
    if (w->pending_key) {
        w->pending_key = false;
        return;
    }
    if (w->depth == 0) {
        return;
    }
    if (!w->first[w->depth]) {
        fputc(',', w->out);
    }
    w->first[w->depth] = false;
    indent(w);
}

static void write_escaped(FILE *out, const char *value) {
    fputc('"', out);
    for (const unsigned char *p = (const unsigned char *)value; *p != '\0'; p++) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', out);
            fputc(*p, out);
        } else if (*p < 0x20) {
            fprintf(out, "\\u%04x", *p);
        } else {
            fputc(*p, out);
        }
    }
    fputc('"', out);
}

void mh_json_key(mh_json *w, const char *key) {
    element(w);
    write_escaped(w->out, key);
    fputs(": ", w->out);
    w->pending_key = true;
}

static void open_container(mh_json *w, char bracket) {
    element(w);
    fputc(bracket, w->out);
    w->depth++;
    w->first[w->depth] = true;
}

static void close_container(mh_json *w, char bracket) {
    bool empty = w->first[w->depth];
    w->depth--;
    if (!empty) {
        indent(w);
    }
    fputc(bracket, w->out);
}

void mh_json_begin_object(mh_json *w) { open_container(w, '{'); }

void mh_json_end_object(mh_json *w) { close_container(w, '}'); }

void mh_json_begin_array(mh_json *w) { open_container(w, '['); }

void mh_json_end_array(mh_json *w) { close_container(w, ']'); }

void mh_json_string(mh_json *w, const char *value) {
    element(w);
    write_escaped(w->out, value);
}

void mh_json_int(mh_json *w, int64_t value) {
    element(w);
    fprintf(w->out, "%lld", (long long)value);
}

void mh_json_uint(mh_json *w, uint64_t value) {
    element(w);
    fprintf(w->out, "%llu", (unsigned long long)value);
}

void mh_json_null(mh_json *w) {
    element(w);
    fputs("null", w->out);
}

void mh_json_double(mh_json *w, double value) {
    char text[40];
    for (int precision = 1; precision <= 17; precision++) {
        snprintf(text, sizeof text, "%.*g", precision, value);
        if (strtod(text, NULL) == value) {
            break;
        }
    }
    if (strpbrk(text, ".eEn") == NULL) {
        strcat(text, ".0");
    }
    element(w);
    fputs(text, w->out);
}

void mh_json_frac(mh_json *w, const mh_frac *value) {
    char text[MH_FRAC_TEXT];
    if (mh_frac_format(value, text, sizeof text) == NULL) {
        mh_json_null(w);
        return;
    }
    mh_json_string(w, text);
}

void mh_json_finish(mh_json *w) { fputc('\n', w->out); }
