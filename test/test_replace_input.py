import sys

sys.path.append(".")
from scripts.replace_input import replace_line


# test scanf
assert replace_line('scanf("%d", &x);') == 'SCANF_ALT("%d", &x);'
assert (
    replace_line('while(scanf("%d", &x) != EOF)') == 'while(SCANF_ALT("%d", &x) != EOF)'
)

# test cin
assert replace_line("cin >> a;") == "CIN(a);"
assert replace_line("cin >> a >> b;") == "{CIN(a); CIN(b);}"
assert replace_line("cin >> a[0][0];") == "CIN(a[0][0]);"
assert replace_line("  while(cin>>str[++n])") == "  while(CIN_LOOP(str[++n]))"
assert replace_line("while(cin>>str[n])n++;") == "while(CIN_LOOP(str[n]))n++;"
assert (
    replace_line("while(cin>>str>>substr){")
    == "while(CIN_LOOP(str) && CIN_LOOP(substr)){"
)
assert replace_line("while(cin>>n&&n)") == "while(CIN_LOOP(n) && n)"
assert (
    replace_line("while(cin>>n>>m && n!=0 && m!=0)")
    == "while(CIN_LOOP(n) && CIN_LOOP(m) &&  n!=0 && m!=0)"
)
assert (
    replace_line("while(cin>>a>>b>>c>>d>>e>>f&&(a!=0||b!=0||c!=0||d!=0||e!=0||f!=0))")
    == "while(CIN_LOOP(a) && CIN_LOOP(b) && CIN_LOOP(c) && CIN_LOOP(d) && CIN_LOOP(e) && CIN_LOOP(f) && (a!=0||b!=0||c!=0||d!=0||e!=0||f!=0))"
)

assert replace_line("for (cin >> n; n > 0; n--)") == "for (CIN_LOOP(n); n > 0; n--)"
assert (
    replace_line("for (cin>>n; n--; cout<<factorize(a,2)<<endl)")
    == "for (CIN_LOOP(n); n--; cout<<factorize(a,2)<<endl)"
)
assert (
    replace_line("for (i = 0, cin >> n; i < n; i++)")
    == "for (i = 0, CIN_LOOP(n); i < n; i++)"
)

assert replace_line("temp = cin.get();") == "temp = cin.get();"

assert (
    replace_line("while (cin >> temp, temp != -1)")
    == "while (CIN_LOOP(temp) &&  temp != -1)"
)
assert (
    replace_line("while(cin>>n>>m,n||m)") == "while(CIN_LOOP(n) && CIN_LOOP(m) && n||m)"
)

assert replace_line("for(i=0;i<n;++i)cin>>a[i];") == "for(i=0;i<n;++i)CIN(a[i]);"