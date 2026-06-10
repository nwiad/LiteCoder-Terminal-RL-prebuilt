/* text_utils.cpp - Text processing utilities */
/* BUG: missing includes for ctype.h functions (toupper, tolower) */
#include "text_utils.h"
/* BUG: missing <cstring> or <string.h> for strlen */

int count_words(const char* text) {
    int count = 0;
    int in_word = 0;
    while (*text) {
        if (*text == ' ' || *text == '\t' || *text == '\n') {
            in_word = 0;
        } else if (!in_word) {
            in_word = 1;
            count++;
        }
        text++;
    }
    return count;
}

int count_lines(const char* text) {
    int count = 0;
    while (*text) {
        if (*text == '\n') count++;
        text++;
    }
    return count;
}

char* to_uppercase(char* dest, const char* src, size_t max_len) {
    size_t i;
    /* BUG: strlen not declared */
    size_t len = strlen(src);
    if (len >= max_len) len = max_len - 1;
    for (i = 0; i < len; i++) {
        /* BUG: toupper not declared */
        dest[i] = toupper((unsigned char)src[i]);
    }
    dest[len] = '\0';
    return dest;
}

char* to_lowercase(char* dest, const char* src, size_t max_len) {
    size_t i;
    size_t len = strlen(src);
    if (len >= max_len) len = max_len - 1;
    for (i = 0; i < len; i++) {
        dest[i] = tolower((unsigned char)src[i]);
    }
    dest[len] = '\0';
    return dest;
}

int str_reverse(char* dest, const char* src, size_t max_len) {
    size_t len = strlen(src);
    if (len >= max_len) len = max_len - 1;
    size_t i;
    for (i = 0; i < len; i++) {
        dest[i] = src[len - 1 - i];
    }
    dest[len] = '\0';
    return 0;
}
