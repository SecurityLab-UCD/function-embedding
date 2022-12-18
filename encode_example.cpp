#include "encode2stderr.hpp"

using namespace std;

int main(int argc, char **argv) {
  printf("SCANF_ALT: float and int separate by space\n");
  float a;
  int b;
  SCANF_ALT("%f %d", &a, &b);

  printf("SCANF_ALT: char and string separate by comma\n");
  char c;
  char d[64];
  SCANF_ALT(" %c,%s", &c, d);

  printf("SCANF_ALT: char as ptr+2\n");
  char str[64];
  SCANF_ALT(" %c", str + 2);

  printf("SCANF_ALT: long\n");
  long li_var;
  SCANF_ALT(" %ld", &li_var);

  printf("SCANF_ALT: ptr_var to short (enter short int)\n");
  // this is also test by the string case
  short si_var;
  short *ptr_var = &si_var;
  SCANF_ALT(" %hd", ptr_var);

  string loop_msg = "Enter int, or exit with EOF (CTRL+D)\n";
  int scanf_loop_buff;
  cout << loop_msg;
  while (SCANF_ALT(" %d", &scanf_loop_buff) != EOF) {
    cout << loop_msg;
  }

  cout << "CIN int\n";
  int e;
  CIN(e);

  cout << "CIN float\n";
  float f;
  CIN(f);

  cout << "CIN char\n";
  char g;
  CIN(g);

  cout << "CIN string\n";
  std::string h;
  CIN(h);

  int cin_loop_buff;
  cout << loop_msg;
  while (CIN_LOOP(cin_loop_buff)) {
    cout << loop_msg;
  }

  printf("GETS_ALT: enter a string\n");
  char string[256];
  GETS_ALT(string); // warning: unsafe (see fgets instead)

  return 0;
}