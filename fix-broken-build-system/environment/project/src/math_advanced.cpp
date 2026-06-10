/* math_advanced.cpp - Advanced math functions */
/* BUG: missing #include <cmath> */
#include "math_advanced.h"

/* BUG: using deprecated/invalid C++ - implicit int return, old-style cast */
double quadratic_root(double a, double b, double c) {
    double discriminant = b * b - 4 * a * c;
    if (discriminant < 0) return 0.0;
    /* BUG: sqrt not declared - missing cmath */
    return (-b + sqrt(discriminant)) / (2 * a);
}

int is_prime(int n) {
    if (n <= 1) return 0;
    if (n <= 3) return 1;
    if (n % 2 == 0 || n % 3 == 0) return 0;
    /* BUG: using 'register' storage class - deprecated in C++17 */
    register int i;
    for (i = 5; i * i <= n; i += 6) {
        if (n % i == 0 || n % (i + 2) == 0)
            return 0;
    }
    return 1;
}

double matrix_det_2x2(double a, double b, double c, double d) {
    return a * d - b * c;
}
