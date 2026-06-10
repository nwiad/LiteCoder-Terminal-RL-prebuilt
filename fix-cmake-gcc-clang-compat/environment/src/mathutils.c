// mathutils.c - Math utility implementations

#include "mathutils.h"

int factorial(int n) {
    if (n < 0) return -1;
    if (n == 0) return 1;
    int result = 1;
    for (int i = 1; i <= n; i++)
        result = result * i;
    return result;
}

double safe_divide(double numerator, double denominator, int *error_flag) {
    if (denominator == 0.0) {
        *error_flag = 1;
        return 0.0;
    }
    *error_flag = 0;
    return numerator / denominator;
}
