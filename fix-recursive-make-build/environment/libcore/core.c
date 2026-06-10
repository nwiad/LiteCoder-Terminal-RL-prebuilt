#include <stdio.h>
#include "core.h"

int core_init(void) {
    printf("Core module initialized\n");
    return 0;
}

int core_process(int value) {
    return value * 2;
}
