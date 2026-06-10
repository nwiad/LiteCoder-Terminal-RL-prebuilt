#include <stdio.h>
#include "core.h"
#include "utils.h"

int utils_init(void) {
    printf("Utils module initialized\n");
    return core_init();
}

int utils_calculate(int a, int b) {
    int processed = core_process(a);
    return processed + b;
}
