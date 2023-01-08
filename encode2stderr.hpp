
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

const std::set<std::string> FORMAT_TYPES = {
    "c",   "d", "e",  "E",  "f",  "g",  "hi", "hu",  "hd",
    "i",   "l", "ld", "li", "lf", "Lf", "lu", "lli", "lld",
    "llu", "o", "p",  "s",  "u",  "x",  "n",
};

std::vector<std::string> split_var_names(std::string names);
std::vector<std::string> split_fmt_types(std::string fmt);
void print_stderr(std::string name, std::string type, const void *val_ptr);
char *gets_alt(char *buffer, size_t buflen, FILE *fp, std::string name);

template <class... Args>
int scanf_alt(const char *fmt, const char *names, Args const &...args) {
  int scanf_return_val = scanf(fmt, args...);

  // this tuple_size method to count args only works for c++11 and above
  int narg = std::tuple_size<decltype(std::make_tuple(args...))>::value;
  const void *values[] = {args...};

  // a dynamic buff for names to avoid mem issue
  size_t len = strlen(names) + 1;
  char *buff = new char[len];
  memset(buff, 0, len);
  strcpy(buff, names);
  std::vector<std::string> name_tokens = split_var_names(buff);
  std::vector<std::string> type_tokens = split_fmt_types(fmt);
  assert(name_tokens.size() == narg);
  assert(type_tokens.size() == narg);

  for (int i = 0; i < narg; i++) {
    print_stderr(name_tokens[i], type_tokens[i], values[i]);
  }
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
