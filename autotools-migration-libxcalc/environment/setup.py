#!/usr/bin/env python3
"""Setup script for libxcalc legacy library conversion task."""

import os, sys, subprocess
from pathlib import Path

def create_directory_structure(base_path):
    for d in ["libxcalc/include/libxcalc", "libxcalc/src", "libxcalc/tests"]:
        (base_path / d).mkdir(parents=True, exist_ok=True)
        print(f"Created: {base_path / d}")

def create_header_files(base_path):
    h = """#ifndef LIBXCALC_H
#define LIBXCALC_H

#ifdef __cplusplus
extern "C" {
#endif

#define LIBXCALC_VERSION_MAJOR 2
#define LIBXCALC_VERSION_MINOR 3
#define LIBXCALC_VERSION_PATCH 1
#define LIBXCALC_VERSION_STRING "2.3.1"

typedef enum { XC_SUCCESS = 0, XC_ERROR_NULL_POINTER = -1, XC_ERROR_INVALID_EXPRESSION = -2, XC_ERROR_DIVISION_BY_ZERO = -3, XC_ERROR_SYNTAX_ERROR = -7, XC_ERROR_OUT_OF_MEMORY = -8 } xcalc_error_t;
typedef struct xcalc_expr_struct* xcalc_expr_t;
typedef double (*xcalc_func_ptr)(double args[], int nargs);
typedef struct { int enable_trigonometric; int enable_logarithmic; int enable_constants; } xcalc_config_t;
typedef struct { void* (*malloc)(size_t size); void* (*realloc)(void* ptr, size_t size); void (*free)(void* ptr); } xcalc_memory_t;

LIBXCALC_EXPORT xcalc_expr_t xcalc_create(xcalc_config_t* config);
LIBXCALC_EXPORT void xcalc_destroy(xcalc_expr_t expr);
LIBXCALC_EXPORT xcalc_error_t xcalc_parse(xcalc_expr_t expr, const char* expr_str);
LIBXCALC_EXPORT xcalc_error_t xcalc_evaluate(xcalc_expr_t expr, double* result);
LIBXCALC_EXPORT xcalc_error_t xcalc_eval(const char* expr_str, double* result);
LIBXCALC_EXPORT xcalc_error_t xcalc_set_variable(xcalc_expr_t expr, const char* name, double value);
LIBXCALC_EXPORT xcalc_error_t xcalc_get_variable(xcalc_expr_t expr, const char* name, double* value);
LIBXCALC_EXPORT const char* xcalc_get_version(void);
LIBXCALC_EXPORT xcalc_error_t xcalc_register_operator(xcalc_expr_t expr, const char* op_string, int precedence, int associativity);

#define XC_PI 3.14159265358979323846
#define XC_E  2.71828182845904523536

#ifdef __cplusplus
}
#endif
#endif
"""
    with open(base_path / "libxcalc/include/libxcalc/libxcalc.h", 'w') as f:
        f.write(h)
    print(f"Created: {base_path / 'libxcalc/include/libxcalc/libxcalc.h'}")

def create_source_file(base_path):
    s = """#include "libxcalc.h"
#include <ctype.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

typedef enum { XC_TOKEN_NUMBER, XC_TOKEN_IDENTIFIER, XC_TOKEN_OPERATOR, XC_TOKEN_LEFT_PAREN, XC_TOKEN_RIGHT_PAREN, XC_TOKEN_EOF, XC_TOKEN_ERROR } xcalc_token_type_t;
typedef struct { xcalc_token_type_t type; char text[256]; double num_value; } xcalc_token_t;
typedef enum { XC_NODE_CONSTANT, XC_NODE_VARIABLE, XC_NODE_UNARY_OP, XC_NODE_BINARY_OP } xcalc_node_type_t;
typedef struct xcalc_node_struct { xcalc_node_type_t type; double constant_value; int op_code; struct xcalc_node_struct* left; struct xcalc_node_struct* right; } xcalc_node_t;
#define XC_VAR_TABLE_SIZE 256
typedef struct var_entry { char name[128]; double value; struct var_entry* next; } var_entry_t;

struct xcalc_expr_struct { xcalc_config_t config; const char* input_ptr; xcalc_token_t current_token; xcalc_node_t* parse_tree; int had_error; char error_msg[1024]; var_entry_t* var_table[XC_VAR_TABLE_SIZE]; };

static const struct { const char* n; double v; } builtin_constants[] = { {"pi", XC_PI}, {"e", XC_E}, {NULL, 0} };

LIBXCALC_EXPORT xcalc_expr_t xcalc_create(xcalc_config_t* config) {
    xcalc_expr_t e = (xcalc_expr_t)malloc(sizeof(struct xcalc_expr_struct));
    if (!e) return NULL;
    memset(e, 0, sizeof(struct xcalc_expr_struct));
    if (config) memcpy(&e->config, config, sizeof(xcalc_config_t));
    else e->config.enable_constants = 1;
    for (int i = 0; i < XC_VAR_TABLE_SIZE; i++) e->var_table[i] = NULL;
    for (int i = 0; builtin_constants[i].n; i++) xcalc_set_variable(e, builtin_constants[i].n, builtin_constants[i].v);
    return e;
}

LIBXCALC_EXPORT void xcalc_destroy(xcalc_expr_t expr) {
    if (!expr) return;
    if (expr->parse_tree) free(expr->parse_tree);
    for (int i = 0; i < XC_VAR_TABLE_SIZE; i++) {
        var_entry_t* entry = expr->var_table[i];
        while (entry) { var_entry_t* next = entry->next; free(entry); entry = next; }
    }
    free(expr);
}

static unsigned int xcalc_hash(const char* s) { unsigned int h = 5381; int c; while ((c = *s++)) h = ((h << 5) + h) ^ c; return h % XC_VAR_TABLE_SIZE; }

static void xcalc_next_token(xcalc_expr_t expr) {
    while (expr->input_ptr && (*expr->input_ptr == ' ' || *expr->input_ptr == '\t')) expr->input_ptr++;
    if (!expr->input_ptr || *expr->input_ptr == '\0') { expr->current_token.type = XC_TOKEN_EOF; return; }
    const char* s = expr->input_ptr;
    if ((*s >= '0' && *s <= '9') || (*s == '.' && s[1] >= '0')) {
        char* e; expr->current_token.num_value = strtod(s, &e);
        int l = e - s; if (l > 255) l = 255; strncpy(expr->current_token.text, s, l); expr->current_token.text[l] = '\0';
        expr->current_token.type = XC_TOKEN_NUMBER; expr->input_ptr = e; return;
    }
    if ((*s >= 'a' && *s <= 'z') || (*s >= 'A' && *s <= 'Z') || *s == '_') {
        int l = 0; while ((s[l] >= 'a' && s[l] <= 'z') || (s[l] >= 'A' && s[l] <= 'Z') || (s[l] >= '0' && s[l] <= '9') || s[l] == '_') l++;
        if (l > 255) l = 255; strncpy(expr->current_token.text, s, l); expr->current_token.text[l] = '\0';
        expr->current_token.type = XC_TOKEN_IDENTIFIER; expr->input_ptr += l; return;
    }
    if (strncmp(s, "**", 2) == 0) { strcpy(expr->current_token.text, "**"); expr->current_token.type = XC_TOKEN_OPERATOR; expr->input_ptr += 2; return; }
    char c = *s; expr->current_token.text[0] = c; expr->current_token.text[1] = '\0';
    if (c == '+' || c == '-' || c == '*' || c == '/' || c == '^') expr->current_token.type = XC_TOKEN_OPERATOR;
    else if (c == '(') expr->current_token.type = XC_TOKEN_LEFT_PAREN;
    else if (c == ')') expr->current_token.type = XC_TOKEN_RIGHT_PAREN;
    else { expr->current_token.type = XC_TOKEN_ERROR; expr->had_error = 1; return; }
    expr->input_ptr++;
}

static xcalc_node_t* xcalc_parse_expr(xcalc_expr_t expr);

static xcalc_node_t* xcalc_parse_primary(xcalc_expr_t expr) {
    xcalc_next_token(expr);
    xcalc_node_t* n = (xcalc_node_t*)malloc(sizeof(xcalc_node_t));
    if (!n) return NULL; memset(n, 0, sizeof(xcalc_node_t));
    if (expr->current_token.type == XC_TOKEN_NUMBER) { n->type = XC_NODE_CONSTANT; n->constant_value = expr->current_token.num_value; }
    else if (expr->current_token.type == XC_TOKEN_LEFT_PAREN) { free(n); n = xcalc_parse_expr(expr); xcalc_next_token(expr); if (expr->current_token.type != XC_TOKEN_RIGHT_PAREN) expr->had_error = 1; }
    else if (expr->current_token.type == XC_TOKEN_OPERATOR && (strcmp(expr->current_token.text, "-") == 0 || strcmp(expr->current_token.text, "+") == 0)) {
        n->type = XC_NODE_UNARY_OP; n->op_code = (strcmp(expr->current_token.text, "-") == 0) ? 0 : 1; n->right = xcalc_parse_primary(expr);
    }
    else { free(n); return NULL; }
    return n;
}

static xcalc_node_t* xcalc_parse_pow(xcalc_expr_t expr) {
    xcalc_node_t* left = xcalc_parse_primary(expr);
    if (!left) return NULL;
    while (1) {
        xcalc_next_token(expr);
        if (expr->current_token.type != XC_TOKEN_OPERATOR || strcmp(expr->current_token.text, "**") != 0) { expr->input_ptr--; break; }
        xcalc_node_t* n = (xcalc_node_t*)malloc(sizeof(xcalc_node_t));
        if (!n) return left; memset(n, 0, sizeof(xcalc_node_t));
        n->type = XC_NODE_BINARY_OP; n->op_code = 2; n->left = left; n->right = xcalc_parse_pow(expr);
        left = n;
    }
    return left;
}

static xcalc_node_t* xcalc_parse_term(xcalc_expr_t expr) {
    xcalc_node_t* left = xcalc_parse_pow(expr);
    if (!left) return NULL;
    while (1) {
        xcalc_next_token(expr);
        if (expr->current_token.type != XC_TOKEN_OPERATOR) { expr->input_ptr--; break; }
        const char* op = expr->current_token.text;
        if (strcmp(op, "*") != 0 && strcmp(op, "/") != 0) { expr->input_ptr--; break; }
        xcalc_node_t* n = (xcalc_node_t*)malloc(sizeof(xcalc_node_t));
        if (!n) return left; memset(n, 0, sizeof(xcalc_node_t));
        n->type = XC_NODE_BINARY_OP; n->op_code = (strcmp(op, "*") == 0) ? 3 : 4;
        n->left = left; n->right = xcalc_parse_pow(expr);
        left = n;
    }
    return left;
}

static xcalc_node_t* xcalc_parse_expr(xcalc_expr_t expr) {
    xcalc_node_t* left = xcalc_parse_term(expr);
    if (!left) return NULL;
    while (1) {
        xcalc_next_token(expr);
        if (expr->current_token.type != XC_TOKEN_OPERATOR) { expr->input_ptr--; break; }
        const char* op = expr->current_token.text;
        if (strcmp(op, "+") != 0 && strcmp(op, "-") != 0) { expr->input_ptr--; break; }
        xcalc_node_t* n = (xcalc_node_t*)malloc(sizeof(xcalc_node_t));
        if (!n) return left; memset(n, 0, sizeof(xcalc_node_t));
        n->type = XC_NODE_BINARY_OP; n->op_code = (strcmp(op, "+") == 0) ? 0 : 1;
        n->left = left; n->right = xcalc_parse_term(expr);
        left = n;
    }
    return left;
}

static double xcalc_eval_node(xcalc_node_t* node) {
    if (!node) return 0.0;
    if (node->type == XC_NODE_CONSTANT) return node->constant_value;
    if (node->type == XC_NODE_UNARY_OP) return (node->op_code == 0) ? -xcalc_eval_node(node->right) : xcalc_eval_node(node->right);
    if (node->type == XC_NODE_BINARY_OP) {
        double a = xcalc_eval_node(node->left);
        double b = xcalc_eval_node(node->right);
        switch (node->op_code) { case 0: return a + b; case 1: return a - b; case 2: return pow(a, b); case 3: return a * b; case 4: return b != 0 ? a / b : 0; }
    }
    return 0.0;
}

LIBXCALC_EXPORT xcalc_error_t xcalc_parse(xcalc_expr_t expr, const char* expr_str) {
    if (!expr || !expr_str) return XC_ERROR_NULL_POINTER;
    if (expr->parse_tree) free(expr->parse_tree);
    expr->had_error = 0; expr->input_ptr = expr_str;
    expr->parse_tree = xcalc_parse_expr(expr);
    if (expr->had_error || !expr->parse_tree) return XC_ERROR_SYNTAX_ERROR;
    return XC_SUCCESS;
}

LIBXCALC_EXPORT xcalc_error_t xcalc_evaluate(xcalc_expr_t expr, double* result) {
    if (!expr || !result) return XC_ERROR_NULL_POINTER;
    if (!expr->parse_tree) return XC_ERROR_INVALID_EXPRESSION;
    *result = xcalc_eval_node(expr->parse_tree);
    return XC_SUCCESS;
}

LIBXCALC_EXPORT xcalc_error_t xcalc_eval(const char* expr_str, double* result) {
    xcalc_expr_t expr = xcalc_create(NULL);
    xcalc_error_t err = xcalc_parse(expr, expr_str);
    if (err == XC_SUCCESS) err = xcalc_evaluate(expr, result);
    xcalc_destroy(expr);
    return err;
}

LIBXCALC_EXPORT xcalc_error_t xcalc_set_variable(xcalc_expr_t expr, const char* name, double value) {
    if (!expr || !name) return XC_ERROR_NULL_POINTER;
    unsigned int h = xcalc_hash(name);
    var_entry_t* e = expr->var_table[h];
    while (e) { if (strcmp(e->name, name) == 0) { e->value = value; return XC_SUCCESS; } e = e->next; }
    e = (var_entry_t*)malloc(sizeof(var_entry_t));
    if (!e) return XC_ERROR_OUT_OF_MEMORY;
    strncpy(e->name, name, 127); e->value = value; e->next = expr->var_table[h];
    expr->var_table[h] = e;
    return XC_SUCCESS;
}

LIBXCALC_EXPORT xcalc_error_t xcalc_get_variable(xcalc_expr_t expr, const char* name, double* value) {
    if (!expr || !name || !value) return XC_ERROR_NULL_POINTER;
    unsigned int h = xcalc_hash(name);
    var_entry_t* e = expr->var_table[h];
    while (e) { if (strcmp(e->name, name) == 0) { *value = e->value; return XC_SUCCESS; } e = e->next; }
    return XC_ERROR_UNDEFINED_VARIABLE;
}

LIBXCALC_EXPORT const char* xcalc_get_version(void) { return LIBXCALC_VERSION_STRING; }
LIBXCALC_EXPORT xcalc_error_t xcalc_register_operator(xcalc_expr_t expr, const char* op_string, int precedence, int associativity) { return XC_SUCCESS; }
"""
    with open(base_path / "libxcalc/src/libxcalc.c", 'w') as f:
        f.write(s)
    print(f"Created: {base_path / 'libxcalc/src/libxcalc.c'}")

def create_makefile(base_path):
    lines = []
    lines.append("# ============================================================================")
    lines.append("# LIBXCALC LEGACY MAKEFILE")
    lines.append("# Generated: 2005-01-15")
    lines.append("# ============================================================================")
    lines.append("")
    lines.append("# Compiler settings - hard-coded paths")
    lines.append("CC = /usr/bin/gcc")
    lines.append("CPP = /usr/bin/cpp")
    lines.append("AR = /usr/bin/ar")
    lines.append("RANLIB = /usr/bin/ranlib")
    lines.append("")
    lines.append("# Compiler flags - specific to this machine")
    lines.append("CFLAGS = -O2 -Wall -Wextra -Wno-unused-parameter -fPIC -g")
    lines.append("CPPFLAGS = -I../include -I../include/libxcalc -D_XOPEN_SOURCE=600")
    lines.append("LDFLAGS = -L./lib -Wl,-rpath,/usr/local/lib")
    lines.append("")
    lines.append("# Installation directories - hard-coded to /usr/local")
    lines.append("PREFIX = /usr/local")
    lines.append("EXEC_PREFIX = $(PREFIX)")
    lines.append("BINDIR = $(EXEC_PREFIX)/bin")
    lines.append("LIBDIR = $(EXEC_PREFIX)/lib")
    lines.append("INCLUDEDIR = $(PREFIX)/include")
    lines.append("")
    lines.append("LIBNAME = libxcalc")
    lines.append("LIBMAJOR = 2")
    lines.append("LIBMINOR = 3")
    lines.append("LIBPATCH = 1")
    lines.append("LIBVERSION = $(LIBMAJOR).$(LIBMINOR).$(LIBPATCH)")
    lines.append("SOVERSION = $(LIBMAJOR)")
    lines.append("")
    lines.append("# Source files - hard-coded list")
    lines.append("SRCS = libxcalc.c")
    lines.append("OBJS = libxcalc.o")
    lines.append("")
    lines.append(".PHONY: all")
    lines.append("all: dirs $(LIBNAME).a $(LIBNAME).so.$(SOVERSION)")
    lines.append("")
    lines.append(".PHONY: dirs")
    lines.append("dirs:")
    lines.append("@if [ ! -d lib ]; then mkdir -p lib; fi")
    lines.append("@if [ ! -d obj ]; then mkdir -p obj; fi")
    lines.append("")
    lines.append("$(LIBNAME).a: $(OBJS)")
    lines.append("$(AR) rcs lib/$(LIBNAME).a $(OBJS)")
    lines.append("$(RANLIB) lib/$(LIBNAME).a")
    lines.append("")
    lines.append("$(LIBNAME).so.$(SOVERSION): $(SRCS)")
    lines.append("$(CC) $(CFLAGS) $(CPPFLAGS) -shared -fPIC -Wl,-soname,$(LIBNAME).so.$(SOVERSION) -o lib/$(LIBNAME).so.$(SOVERSION) $(SRCS)")
    lines.append("")
    lines.append("%.o: ../src/%.c")
    lines.append("$(CC) $(CFLAGS) $(CPPFLAGS) -MMD -MP -c $< -o obj/$@")
    lines.append("")
    lines.append(".PHONY: install")
    lines.append("install: all")
    lines.append("@if [ ! -d $(DESTDIR)$(LIBDIR) ]; then mkdir -p $(DESTDIR)$(LIBDIR); fi")
    lines.append("@if [ ! -d $(DESTDIR)$(INCLUDEDIR)/libxcalc ]; then mkdir -p $(DESTDIR)$(INCLUDEDIR)/libxcalc; fi")
    lines.append("cp lib/$(LIBNAME).so.$(SOVERSION) $(DESTDIR)$(LIBDIR)/")
    lines.append("cp lib/$(LIBNAME).a $(DESTDIR)$(LIBDIR)/")
    lines.append("cp ../include/libxcalc/libxcalc.h $(DESTDIR)$(INCLUDEDIR)/libxcalc/")
    lines.append("")
    lines.append(".PHONY: clean")
    lines.append("clean:")
    lines.append("@if [ -d obj ]; then rm -f obj/*.o; fi")
    lines.append("@if [ -d lib ]; then rm -f lib/*.a lib/*.so*; fi")
    lines.append("")
    for i in range(150):
        lines.append(f"# Platform config section {i+1}")
        lines.append(f"CFLAGS_PLT_{i} = -O2 -Wall -DFLAG_{i}=1")
    lines.append("")
    lines.append("# Solaris specific settings")
    lines.append("SOLARIS_CFLAGS = -xO3 -xdepend")
    lines.append("# AIX specific settings")
    lines.append("AIX_CFLAGS = -O3 -qmaxmem=8192")
    lines.append("# FreeBSD specific settings")
    lines.append("FREEBSD_CFLAGS = -O2 -pipe")
    lines.append("# End of Makefile")
    
    mpath = base_path / "libxcalc/Makefile"
    with open(mpath, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Created: {mpath}")
    with open(mpath, 'r') as f:
        print(f"Makefile line count: {sum(1 for _ in f)}")

def create_test_file(base_path):
    t = """#include <stdio.h>
#include <math.h>
#include "libxcalc.h"

int main() {
    double result;
    xcalc_eval("2 + 3", &result); printf("2 + 3 = %f\n", result);
    xcalc_eval("10 - 4", &result); printf("10 - 4 = %f\n", result);
    xcalc_eval("6 * 7", &result); printf("6 * 7 = %f\n", result);
    xcalc_eval("2 ** 3", &result); printf("2 ** 3 = %f\n", result);
    xcalc_eval("pi", &result); printf("pi = %f\n", result);
    xcalc_eval("e", &result); printf("e = %f\n", result);
    printf("Version: %s\n", xcalc_get_version());
    return 0;
}
"""
    with open(base_path / "libxcalc/tests/test_xcalc.c", 'w') as f:
        f.write(t)
    print(f"Created: {base_path / 'libxcalc/tests/test_xcalc.c'}")

def create_documentation(base_path):
    with open(base_path / "libxcalc/README.md", 'w') as f:
        f.write("# libxcalc - Mathematical Expression Parser Library\n\n## Overview\nlibxcalc is a C library for parsing and evaluating mathematical expressions.\n\n## Building\n    cd libxcalc\n    make\n    make install\n\n## License\nMIT License\n")
    print(f"Created: {base_path / 'libxcalc/README.md'}")
    with open(base_path / "libxcalc/CHANGELOG", 'w') as f:
        f.write("# libxcalc Changelog\n\n## Version 2.3.1 (2024-03-20)\n- Fixed memory leak\n- Added functions\n\n## Version 2.0.0 (2022-11-01)\n- Major API redesign\n")
    print(f"Created: {base_path / 'libxcalc/CHANGELOG'}")
    with open(base_path / "libxcalc/LICENSE", 'w') as f:
        f.write("MIT License\n\nCopyright (c) 2005-2024 libxcalc Team\n")
    print(f"Created: {base_path / 'libxcalc/LICENSE'}")

def verify_build(base_path):
    print("\nVerifying build...")
    try:
        src = base_path / "libxcalc/src/libxcalc.c"
        inc = base_path / "libxcalc/include"
        result = subprocess.run(["/usr/bin/gcc", "-c", "-Wall", "-I" + str(inc), str(src), "-o", "/tmp/libxcalc_test.o"], capture_output=True, text=True, cwd=str(base_path / "libxcalc"))
        if result.returncode == 0:
            print("Build verification successful!")
            if os.path.exists("/tmp/libxcalc_test.o"):
                os.remove("/tmp/libxcalc_test.o")
        else:
            print(f"Build failed: {result.stderr}")
    except Exception as e:
        print(f"Verification error: {e}")

def main():
    print("="*60)
    print("libxcalc Legacy Library Setup")
    print("="*60 + "\n")
    base_path = Path.cwd()
    print(f"Working directory: {base_path}\n")
    create_directory_structure(base_path)
    print()
    create_header_files(base_path)
    print()
    create_source_file(base_path)
    print()
    create_makefile(base_path)
    print()
    create_test_file(base_path)
    print()
    create_documentation(base_path)
    print()
    verify_build(base_path)
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
