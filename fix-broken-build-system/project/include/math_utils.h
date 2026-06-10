#ifndef MATH_UTILS_H
#define MATH_UTILS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Function declarations - some have wrong signatures vs implementation */
int factorial(int n);
double power(double base, int exp);
int fibonacci(int n);
double average(int* arr, int size);  /* implementation uses float* instead */
int gcd(int a, int b);

#ifdef __cplusplus
}
#endif

#endif /* MATH_UTILS_H */
