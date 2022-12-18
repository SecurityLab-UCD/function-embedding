import argparse
import re
from functools import reduce
from typing import List


def is_bool_exp(token: str) -> bool:
    bool_op = ["==", "!=", "&&", "||"]
    return any(map(lambda op: op in token, bool_op))


def replace_cin(line: str) -> str:
    tokens = line.split("cin")
    # print leading terms
    # for example, indentation, while(, for(
    out_str = tokens[0]
    is_while_cond = "while" in tokens[0]
    is_for_init = "for" in tokens[0] and tokens[0].count("(") != tokens[0].count(")")
    # is_for_init = "for" in tokens[0]
    cin_macro = "CIN_LOOP" if is_while_cond or is_for_init else "CIN"

    # split the rest by >>, will have a empty str at index 0
    # ">>a;".split(">>") === ['', 'a']
    # " >>a;".split(">>") === [' ', 'a']
    # so slice the list from 1 to end
    var_tokens = tokens[1].split(">>")[1:]
    for i, token in enumerate(var_tokens):
        # split out the variable names
        # split by last delimiter
        dlim = ")" if is_while_cond else ";"
        token = token.split(dlim, 1) if is_for_init else token.rsplit(dlim, 1)

        if is_bool_exp(token[0]):
            exps = token[0].split("&&", 1)
            if len(exps) == 1 and "," in exps[0]:
                exps = token[0].split(",")
            out_str += "{}({})".format(cin_macro, exps[0].strip()) + " && "
            out_str += exps[1]
        else:
            out_str += "{}({})".format(cin_macro, token[0].strip())

        if i == len(var_tokens) - 1:
            # keep the original splited ending
            org_end = token[1] if len(token) > 1 else ""
            end = ")" if is_while_cond else ";"
            out_str += end + org_end
        else:
            connector = " && " if is_while_cond else "; "
            out_str += connector

    if not (is_while_cond or is_for_init) and out_str.count("CIN") > 1:
        return "{" + out_str + "}"
    return out_str


def replace_line(line: str) -> str:
    # replace `gets` which is deprecated
    if "gets" in line:
        line = line.replace("gets", "GETS_ALT")
    if "scanf" in line:
        # check if no args, like scanf("\n");
        if line[line.find("(") + 1 : line.find(")")].split('"')[-1] == "":
            return line
        return line.replace("scanf", "SCANF_ALT")
    elif "cin" in line:
        idx = line.index("cin")
        if line[idx + 3] == ".":
            return line
        return replace_cin(line)
    else:
        return line


def replace_file(f: str) -> str:
    # or replace_file : List[str] -> str
    # call open().readlines() outside
    lines = f.splitlines(True)
    return reduce(lambda a, b: a + b, map(replace_line, lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="text replacement script",
        description="replace scanf and cin to customized SCANF_ALT and CIN macro",
    )
    parser.add_argument("filename", type=str, help="path to c/cpp file to be replaced")

    args = parser.parse_args()
    f = open(args.filename, "r+").read()
    # out_str = reduce(lambda a, b: a + b, map(replace_line, lines))
    # print(out_str)  # add \n to end
    print(replace_file(f))
