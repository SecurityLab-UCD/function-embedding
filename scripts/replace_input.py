import argparse
from functools import reduce


def is_bool_exp(token: str) -> bool:
    bool_op = ["==", "!=", "&&", "||"]
    return any(map(lambda op: op in token, bool_op))


def to_cin(var: str) -> str:
    return "CIN({})".format(var.strip())


def replace_cin(line: str) -> str:
    tokens = line.split("cin")
    # print leading terms
    # for example, indentation, while(
    # print(tokens[0], end="")
    out_str = tokens[0]
    is_while_loop = "while" in tokens[0]

    # split the rest by >>, will have a empty str at index 0
    # ">>a;".split(">>") === ['', 'a']
    # " >>a;".split(">>") === [' ', 'a']
    # so slice the list from 1 to end
    var_tokens = tokens[1].split(">>")[1:]
    for i, token in enumerate(var_tokens):
        # split out the variable names
        # split by last delimiter
        dlim = ")" if is_while_loop else ";"
        token = token.rsplit(dlim, 1)

        if is_bool_exp(token[0]):
            exps = token[0].split("&&", 1)
            # print(to_cin(exps[0]) + " && ", end="")
            # print(exps[1], end="")
            out_str += to_cin(exps[0]) + " && "
            out_str += exps[1]
        else:
            # print(to_cin(token[0]), end="")
            out_str += to_cin(token[0])

        if i == len(var_tokens) - 1:
            end = ")" + token[1] if is_while_loop else ";\n"
            # print(end, end="")
            out_str += end
        else:
            connector = " && " if is_while_loop else "; "
            # print(connector, end="")
            out_str += connector
    return out_str


def replace_line(line: str) -> str:
    if "scanf" in line:
        return line.replace("scanf", "SCANF_ALT")
    elif "cin" in line:
        return replace_cin(line)
    else:
        return line


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="text replacement script",
        description="replace scanf and cin to customized SCANF_ALT and CIN macro",
    )
    parser.add_argument("filename", type=str, help="path to c/cpp file to be replaced")

    args = parser.parse_args()
    lines = open(args.filename, "r+").readlines()
    out_str = reduce(lambda a, b: a + b, map(replace_line, lines))
    print(out_str)  # add \n to end
