#include <stdlib.h>
#include <string.h>
#include "mini.h"

int mini_strlen(const char *str) {
    int len = 0;
    if (!str) return 0;
    while (str[len] != '\0') {
        len++;
    }
    return len;
}

char *mini_strdup(const char *str) {
    if (!str) return NULL;
    int len = mini_strlen(str);
    char *dup = (char *)malloc(len + 1);
    if (!dup) return NULL;
    int i;
    for (i = 0; i < len; i++) {
        dup[i] = str[i];
    }
    dup[len] = '\0';
    return dup;
}

void mini_reverse(char *str) {
    if (!str) return;
    int len = mini_strlen(str);
    int i;
    for (i = 0; i < len / 2; i++) {
        char temp = str[i];
        str[i] = str[len - 1 - i];
        str[len - 1 - i] = temp;
    }
}

int mini_add(int a, int b) {
    return a + b;
}

int mini_multiply(int a, int b) {
    return a * b;
}
