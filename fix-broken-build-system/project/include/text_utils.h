#ifndef TEXT_UTILS_H
#define TEXT_UTILS_H

#include <stddef.h>

/* Text processing utilities */
int count_words(const char* text);
int count_lines(const char* text);
char* to_uppercase(char* dest, const char* src, size_t max_len);
char* to_lowercase(char* dest, const char* src, size_t max_len);
int str_reverse(char* dest, const char* src, size_t max_len);

#endif /* TEXT_UTILS_H */
