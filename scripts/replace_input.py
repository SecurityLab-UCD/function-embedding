# this script print an keyword replaced file to stdout
import sys

fpath = sys.argv[1]
lines = open(fpath, "r+").readlines()

for line in lines:
    if "scanf" in line:
        replacement = line.replace("scanf", "SCANF_ALT")
        print(replacement, end="")
    elif "cin" in line:
        tokens = line.split("cin")
        indent = tokens[0]
        # split the rest by >>, will have a empty str at index 0
        # ">>a;".split(">>") === ['', 'a']
        # " >>a;".split(">>") === [' ', 'a']
        # so slice the list from 1 to end
        tokens = tokens[1].split(">>")[1:]
        for token in tokens:
            print(indent, end="")
            # split out the variable names
            token = token.split(";")[0]
            print("CIN({});".format(token.strip()))
    else:
        print(line, end="")

print("")  # add \n to end
