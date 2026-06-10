#ifndef UTIL_LIB_H
#define UTIL_LIB_H

/* Utility library header */
void util_print_banner(const char* program_name, const char* version);
int util_parse_args(int argc, char** argv, const char* version_string);
const char* util_get_version(void);

#endif /* UTIL_LIB_H */
