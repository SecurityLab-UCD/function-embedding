
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

char **split_var_names(const char *names, int n);
std::vector<std::string> split_fmt_types(const char *fmt);
void print_stderr(char *name, std::string type, const void *val_ptr);
char *gets_alt(char *buffer, size_t buflen, FILE *fp, std::string name);

template <class... Args>
int scanf_alt(const char *fmt, const char *names, Args const &...args) {
  int scanf_return_val = scanf(fmt, args...);

  // this tuple_size method to count args only works for c++11 and above
  int narg = std::tuple_size<decltype(std::make_tuple(args...))>::value;
  const void *values[] = {args...};

  // a dynamic buff for names to avoid mem issue
  char **name_tokens = split_var_names(names, narg);
  std::vector<std::string> type_tokens = split_fmt_types(fmt);
  assert(type_tokens.size() == narg);

  for (int i = 0; i < narg; i++) {
    print_stderr(name_tokens[i], type_tokens[i], values[i]);
    delete name_tokens[i];
  }
  delete name_tokens;
  return scanf_return_val;
}

#ifdef _ENCODE_INPUT_
// do scanf and then print to stdout in format
//  variable_name type value
// Usage: same as scanf
#define SCANF_ALT(fmt, args...) scanf_alt(fmt, #args, args)

// macro for cin
#define CIN_LOOP(x)                                                            \
  [&x]() {                                                                     \
    std::cin >> x;                                                             \
    if (std::cin.good()) {                                                     \
      std::cerr << #x << ",," << x << "\n";                                    \
    }                                                                          \
    return std::cin.good();                                                    \
  }()

// macro for cin
#define CIN(x)                                                                 \
  {                                                                            \
    std::cin >> x;                                                             \
    std::cerr << #x << ",," << x << "\n";                                      \
  }

#define GETS_ALT(str) gets_alt(str, sizeof(str), stdin, #str)

#else
// `gets` was deprecated in C++11 and removed from C++14
// so alway replace it
#define GETS_ALT(str) fgets(str, sizeof(str), stdin)
#endif
