
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

// https://stackoverflow.com/questions/2124339/c-preprocessor-va-args-number-of-arguments
#define NUMARGS(...) (sizeof((int*){__VA_ARGS__}) / sizeof(int))

// @param val value to print to stderr
#define PRINT_STDERR(val) \
    fprintf(stderr, pfmt, name_tokens[i], type_tokens[i], val)
// do scanf and then print to stdout in format
//  variable_name type value
// Usage: same as scanf
#define SCANF_ALT(fmt, args...)                                                       \
    {                                                                                 \
        scanf(fmt, args);                                                             \
        int narg = NUMARGS(args);                                                     \
        char names[] = #args;                                                         \
        char* name_tokens[narg];                                                      \
        char type_tokens[narg];                                                       \
        int* values[] = {args};                                                       \
                                                                                      \
        int idx = 0;                                                                  \
        char* token = strtok(names, ", ");                                            \
        name_tokens[idx] = token;                                                     \
        while (token) {                                                               \
            token = strtok(NULL, ", ");                                               \
            name_tokens[++idx] = token;                                               \
        }                                                                             \
                                                                                      \
        idx = 0;                                                                      \
        int len = strlen(fmt);                                                        \
        for (int i = 0; i < len; i++) {                                               \
            if (fmt[i] == '%') {                                                      \
                type_tokens[idx] = fmt[i + 1];                                        \
                idx++;                                                                \
            }                                                                         \
        }                                                                             \
                                                                                      \
        for (int i = 0; i < narg; i++) {              \
            char pfmt[10] = "%s,%c,%";                \
            pfmt[7] = type_tokens[i];                 \
            pfmt[8] = '\n';                           \
            switch (type_tokens[i]) {                 \
                case 'd':                             \
                    PRINT_STDERR(*(int*)values[i]);   \
                    break;                            \
                case 'f':                             \
                    PRINT_STDERR(*(float*)values[i]); \
                    break;                            \
                default:                              \
                    PRINT_STDERR(*values[i]);         \
            }                                         \
        }                                             \
    }
