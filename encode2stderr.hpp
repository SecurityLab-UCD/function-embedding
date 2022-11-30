
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include <algorithm>
#include <iostream>
#include <iterator>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

std::vector<std::string> split_var_names(std::string names) {
    std::istringstream ss(names);
    std::string token;
    std::vector<std::string> res;

    while (std::getline(ss, token, ',')) {
        // trim front white space
        if (token[0] == ' ') {
            token = token.substr(1);
        }
        res.push_back(token);
    }
    return res;
}

const std::set<std::string> FORMAT_TYPES = {
    "c",
    "d",
    "e",
    "E",
    "f",
    "g",
    "hi",
    "hu",
    "i",
    "l",
    "ld",
    "li",
    "lf",
    "Lf",
    "lu",
    "lli",
    "lld",
    "llu",
    "o",
    "p",
    "s",
    "u",
    "x",
    "n",
    "%",
};

std::vector<std::string> split_fmt_types(std::string fmt) {
    std::istringstream ss(fmt);
    std::string token;
    std::vector<std::string> res;
    std::set<std::string> possible_types;

    while (std::getline(ss, token, '%')) {
        possible_types.clear();
        // get all possible types
        // e.g. lld -> l, ll, lld
        if (token.length() > 3) {
            token = token.substr(0, 3);
        }
        switch (token.length()) {
            case 3:
                possible_types.insert(token.substr(0, 3));
            case 2:
                possible_types.insert(token.substr(0, 2));
            case 1:
                possible_types.insert(token.substr(0, 1));
            default:
                break;
        }

        // use the longest possible type
        // e.g. if possible are l, ll, lld, then choose lld
        std::string chosed_type = "";
        for (std::string type : possible_types) {
            if (FORMAT_TYPES.find(type) != FORMAT_TYPES.end() &&
                type.length() > chosed_type.length()) {
                chosed_type = type;
            }
        }
        if (chosed_type != "") {
            res.push_back(chosed_type);
        }
    }
    return res;
}

void print_stderr(std::string name, std::string type, void* val_ptr) {
    std::string pfmt = "%s,%s,%" + type + "\n";
    // TODO: complete for all types
    if (type == "d") {
        fprintf(stderr, pfmt.c_str(), name.c_str(), type.c_str(), *(int*)val_ptr);
    } else if (type == "f") {
        fprintf(stderr, pfmt.c_str(), name.c_str(), type.c_str(), *(float*)val_ptr);
    } else if (type == "lf" || type == "Lf") {
        fprintf(stderr, pfmt.c_str(), name.c_str(), type.c_str(), *(double*)val_ptr);
    } else {
        // set default type to int
        // as %d is the most common
        fprintf(stderr, pfmt.c_str(), name.c_str(), type.c_str(), *(int*)val_ptr);
    }
}

// do scanf and then print to stdout in format
//  variable_name type value
// Usage: same as scanf
#define SCANF_ALT(fmt, args...)                                                   \
    {                                                                             \
        scanf(fmt, args);                                                         \
        /* this tuple_size method to count args only works for c++11 and above */ \
        int narg = std::tuple_size<decltype(std::make_tuple(args))>::value;       \
        std::string names = #args;                                                \
        std::vector<std::string> name_tokens = split_var_names(names);            \
        std::vector<std::string> type_tokens = split_fmt_types(fmt);              \
        void* values[] = {args};                                                  \
        assert(name_tokens.size() == narg);                                       \
        assert(type_tokens.size() == narg);                                       \
                                                                                  \
        for (int i = 0; i < narg; i++) {                                          \
            print_stderr(name_tokens[i], type_tokens[i], values[i]);              \
        }                                                                         \
    }

// macro for cin
#define CIN(x)                                \
    {                                         \
        std::cin >> x;                        \
        std::cerr << #x << ",," << x << "\n"; \
    }