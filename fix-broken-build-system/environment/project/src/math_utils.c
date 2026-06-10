/* math_utils.c - Basic math utilities */
/* BUG: missing #include for stdlib.h and stdio.h */
#include "/home/developer/libs/custom/include/math_utils.h"  /* BUG: hardcoded path */

int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

double power(double base, int exp) {
    double result = 1.0;
    int i;
    for (i = 0; i < exp; i++) {
        result *= base;
    }
    return result;
}

int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

/* BUG: signature mismatch - header says int* but implementation uses float* */
double average(float* arr, int size) {
    double sum = 0.0;
    int i;
    for (i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum / size;
}

int gcd(int a, int b) {
    while (b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}
