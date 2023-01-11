#include "encode2stderr.hpp"

char **split_var_names(const char *names, int n) {
  char **names_arr = new char *[n];
  const char *dlim = ", ";

  char names_cpy[64];
  memset(names_cpy, '\0', sizeof(names));
  strcpy(names_cpy, names);

  int i = 0;
  char *token = strtok(names_cpy, dlim);
  char *buff = new char[sizeof(names)];
  memset(buff, '\0', sizeof(names));
  strcpy(buff, token);
  names_arr[i++] = buff;
  while ((token = strtok(NULL, dlim))) {
    buff = new char[sizeof(names)];
    memset(buff, '\0', sizeof(names));
    strcpy(buff, token);
    names_arr[i++] = buff;
  }

  return names_arr;
}

const std::set<std::string> FORMAT_TYPES = {
    "c",   "d", "e",  "E",  "f",  "g",  "hi", "hu",  "hd",
    "i",   "l", "ld", "li", "lf", "Lf", "lu", "lli", "lld",
    "llu", "o", "p",  "s",  "u",  "x",  "n",
};


std::vector<std::string> split_fmt_types(std::string fmt) {
  // ToDo: change to C implementation
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

void print_stderr(char *name, std::string type, const void *val_ptr) {
  std::string pfmt = "%s,%s,%" + type + "\n";

  // in POJ-104, only the following appears
  // c, s, u, lu, d, ld, lld, hd, f, lf
  // according to
  // https://www.cs.uic.edu/~jbell/CourseNotes/C_Programming/DataTypesSummary.pdf
  if (type == "c") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(char *)val_ptr);
  } else if (type == "s") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), (char *)val_ptr);
  } else if (type == "u") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(unsigned *)val_ptr);
  } else if (type == "lu") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(),
            *(unsigned long *)val_ptr);
  } else if (type == "d") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(int *)val_ptr);
  } else if (type == "ld") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(long *)val_ptr);
  } else if (type == "lld") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(long long *)val_ptr);
  } else if (type == "hd") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(short *)val_ptr);
  } else if (type == "f") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(float *)val_ptr);
  } else if (type == "lf" || type == "Lf") {
    fprintf(stderr, pfmt.c_str(), name, type.c_str(), *(double *)val_ptr);
  } else {
    assert(0);
  }
}

// https://stackoverflow.com/questions/1694036/why-is-the-gets-function-so-dangerous-that-it-should-not-be-used
char *gets_alt(char *buffer, size_t buflen, FILE *fp, std::string name) {
  if (fgets(buffer, buflen, fp) != 0) {
    buffer[strcspn(buffer, "\n")] = '\0';
    fprintf(stderr, "%s,s,%s\n", name.c_str(), buffer);
    return buffer;
  }
  return 0;
}
