import sys

sys.path.append(".")
from scripts.replace_input import replace_line


# test scanf
assert replace_line('scanf("%d", &x);') == 'SCANF_ALT("%d", &x);'
assert (
    replace_line('while(scanf("%d", &x) != EOF)') == 'while(SCANF_ALT("%d", &x) != EOF)'
)

# test cin
assert replace_line("cin >> a;") == "CIN(a);\n"
assert replace_line("cin >> a >> b;") == "CIN(a); CIN(b);\n"
assert replace_line("cin >> a[0][0];") == "CIN(a[0][0]);\n"
assert replace_line("  while(cin>>str[++n])") == "  while(CIN(str[++n]))"
assert replace_line("while(cin>>str[n])n++;") == "while(CIN(str[n]))n++;"
assert replace_line("while(cin>>str>>substr){") == "while(CIN(str) && CIN(substr)){"
assert replace_line("while(cin>>n&&n)") == "while(CIN(n) && n)"
assert (
    replace_line("while(cin>>n>>m && n!=0 && m!=0)")
    == "while(CIN(n) && CIN(m) &&  n!=0 && m!=0)"
)
assert (
    replace_line("while(cin>>a>>b>>c>>d>>e>>f&&(a!=0||b!=0||c!=0||d!=0||e!=0||f!=0))")
    == "while(CIN(a) && CIN(b) && CIN(c) && CIN(d) && CIN(e) && CIN(f) && (a!=0||b!=0||c!=0||d!=0||e!=0||f!=0))"
)
