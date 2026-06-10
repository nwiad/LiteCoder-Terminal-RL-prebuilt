#ifndef STRING_HELPERS_H
#define STRING_HELPERS_H

#ifdef __cplusplus
extern "C" {
#endif

int string_length(const char* str);
int string_compare(const char* a, const char* b);
char* string_concat(char* dest, const char* src, int max_len);

#ifdef __cplusplus
}
#endif

#endif /* STRING_HELPERS_H */
