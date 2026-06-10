#include <stdio.h>
#include "core.h"
#include "utils.h"

int main(void) {
    printf("Starting application...\n");

    if (core_init() != 0) {
        printf("Failed to initialize core\n");
        return 1;
    }

    if (utils_init() != 0) {
        printf("Failed to initialize utils\n");
        return 1;
    }

    int result = utils_calculate(10, 5);
    printf("Calculation result: %d\n", result);

    printf("All tests completed successfully!\n");
    return 0;
}
