/* util_lib.c - Utility library implementation */
#include <stdio.h>
#include <string.h>
#include "util_lib.h"

/* BUG: hardcoded path reference in a string constant */
static const char* BUILD_INFO = "Built from /home/developer/project rev 2014.03";

void util_print_banner(const char* program_name, const char* version) {
    printf("=================================\n");
    printf("  %s v%s\n", program_name, version);
    printf("  Legacy Tools Suite\n");
    printf("=================================\n");
}

int util_parse_args(int argc, char** argv, const char* version_string) {
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--version") == 0) {
            printf("%s\n", version_string);
            return 1;
        }
        if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [options]\n", argv[0]);
            printf("  --version  Show version\n");
            printf("  --help     Show this help\n");
            return 1;
        }
    }
    return 0;
}

const char* util_get_version(void) {
    return BUILD_INFO;
}
