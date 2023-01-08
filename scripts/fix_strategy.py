from common import *
from typing import Callable, Tuple
from compile_report import *
from tqdm import tqdm
from functools import partial
import sys
from dataset import format_one_file

sys.path.append("./lib/sctokenizer")
import sctokenizer
from sctokenizer import Source, TokenType, Token
from functools import reduce
from compile_report import init_crash_report_from_stderr
from tqdm import tqdm
from replace_input import replace_file

CPP_TYPE_SET = {"int", "float", "double", "char", "wchar", "bool", "void", "long"}
ENCODE = False


def tokenize(paths: Tuple[str, str]):
    def token2tuple(token):
        # discard position
        return (token.token_value, token.token_type)

    # ! reading from txt file or temp fixed file without includes and defines
    # assembling includes and defines tokens is too complex
    txt_path, cpp_path = paths
    fpath = cpp_path + "~" if os.path.exists(cpp_path + "~") else txt_path
    tokens = sctokenizer.tokenize_file(filepath=fpath, lang="cpp")
    tokens = list(map(token2tuple, tokens))
    return tokens


def get_value(token: Tuple[str, TokenType]):
    token_val, token_type = token
    if token_type == TokenType.KEYWORD:
        return token_val + " "
    if token_type == TokenType.IDENTIFIER:
        return " " + token_val
    if token_type == TokenType.COMMENT_SYMBOL:
        return token_val + "\n"
    return token_val


# TODO: Should use an IOWrapper to write to file or string.
def assemble_tokens_and_write(tokens: List[Tuple[str, TokenType]], cpp_path: str):
    """write tokens to a temp-cpp file

    Args:
        tokens (List[Tuple[str, TokenType]]): list of tokens of the file
        cpp_path (str): path to the final cpp file to compile
    """

    with open(cpp_path + "~", "w") as f:
        f.write(reduce(lambda s, t: s + get_value(t), tokens, ""))


def write_fixed_file(cpp_path: str):
    """preprocess a fixed temp-cpp file with headers

    Args:
        cpp_path (str): path to write the cpp file
    """
    if not os.path.exists(cpp_path + "~"):
        return

    code = format_one_file(cpp_path + "~").stdout.read().decode()
    code = replace_file(code)
    code = code.replace("void main", "int main")
    with open(cpp_path, "w") as f:
        with open(path.join(EMBDING_HOME, "header.hpp"), "r") as hpp:
            header = hpp.read()
            f.write(header)
        # cat $EMBDING_HOME/encode2stderr.hpp >> $SRCDIR/$P.cpp
        with open(path.join(EMBDING_HOME, "encode2stderr.hpp"), "r") as hpp:
            header = hpp.read()
            f.write(header)
        # if there is additional macro defined, write them to f
        const_macro_path = path.join(EMBDING_HOME, "const_macro.hpp")
        if path.exists(const_macro_path):
            with open(const_macro_path, "r") as hpp:
                macro = hpp.read()
                f.write(macro)
            os.remove(const_macro_path)
        f.write(code)
    os.remove(cpp_path + "~")


class FixStrategy:
    _description: str
    _isMatch: Callable[[Report, CompilerReport], bool]
    _fix: Callable[[str, Report, CompilerReport], None]

    def __init__(self, description, isMatch, fix):
        self._description = description
        self._isMatch = isMatch
        self._fix = fix

    def __str__(self):
        return self._description

    def isMatch(self, r: Report, cr: CompilerReport) -> bool:
        return self._isMatch(r, cr)

    def fix(self, path, r, cr):
        self._fix(path, r, cr)


# Main does not return int
def _fix_main_returned_non_int(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)
    main_idx = tokens.index(("main", TokenType.IDENTIFIER))
    prev_val, prev_type = tokens[main_idx - 1]
    int_token = ("int", TokenType.KEYWORD)
    if prev_type == TokenType.KEYWORD and prev_val in CPP_TYPE_SET:
        # main type non int
        tokens[main_idx - 1] = int_token
    elif prev_val not in CPP_TYPE_SET:
        # main no type
        tokens = tokens[:main_idx] + [int_token] + tokens[main_idx:]
    else:
        error(f"undefined main return error: {cpp_path}")
    assemble_tokens_and_write(tokens, cpp_path)


fix_main_returned_non_int = FixStrategy(
    "main returned non int",
    lambda r, _: r.main_returned_non_int(),
    _fix_main_returned_non_int,
)


# Main has no return type
def _fix_main_has_no_return_type(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)
    main_idx = tokens.index(("main", TokenType.IDENTIFIER))
    int_token = ("int", TokenType.KEYWORD)
    tokens = tokens[:main_idx] + [int_token] + tokens[main_idx:]
    assemble_tokens_and_write(tokens, cpp_path)


main_has_no_return_type = FixStrategy(
    "main has no return type",
    lambda r, _: r.main_has_no_return_type(),
    _fix_main_has_no_return_type,
)


def _fix_use_of_std_keyword(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)
    keywords = cr.get_keywords_used()
    for i in range(len(tokens)):
        token_val, token_type = tokens[i]
        if token_val in keywords:
            tokens[i] = ("fixed_" + token_val, token_type)
    assemble_tokens_and_write(tokens, cpp_path)


# Cpp stdlib keyword
use_of_std_keyword = FixStrategy(
    "Used keywords in stdlib",
    lambda r, _: r.use_of_std_keyword(),
    _fix_use_of_std_keyword,
)


def _fix_struct_len_undefined(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)
    var_pairs = list(cr.get_struct_len_definition())
    _, len_vars = tuple(zip(*var_pairs))
    for i in range(len(tokens)):
        token_val, token_type = tokens[i]
        if token_val in len_vars:
            struct_size_var, len_var = var_pairs[len_vars.index(token_val)]
            tokens[i] = (f"sizeof({struct_size_var})", token_type)
    assemble_tokens_and_write(tokens, cpp_path)


struct_len_undefined = FixStrategy(
    "Used LEN as stuct size but undefined",
    lambda r, _: r.struct_len_undefined(),
    _fix_struct_len_undefined,
)


def _fix_type_cannot_be_returned(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)
    struct_name = r.get_struct_name()
    defn_idx = tokens.index((struct_name, TokenType.IDENTIFIER))
    # insert token after first } after struct definition
    struct_end_idx = (
        tokens[defn_idx:].index(("}", TokenType.SPECIAL_SYMBOL)) + defn_idx + 1
    )
    tokens = (
        tokens[:struct_end_idx]
        + [(";", TokenType.SPECIAL_SYMBOL)]
        + tokens[struct_end_idx:]
    )

    assemble_tokens_and_write(tokens, cpp_path)


struct_missing_semicolon = FixStrategy(
    "Define a struct with no semicolon at the end",
    lambda r, _: r.define_struct_no_semicolon(),
    _fix_type_cannot_be_returned,
)


def _fix_main_invalid_arg(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    tokens = tokenize(paths)

    main_arg_tokens = [
        ("int", TokenType.KEYWORD),
        ("argc", TokenType.IDENTIFIER),
        (",", TokenType.OPERATOR),
        ("char", TokenType.KEYWORD),
        ("*", TokenType.OPERATOR),
        ("*", TokenType.OPERATOR),
        ("argv", TokenType.IDENTIFIER),
    ]
    main_idx = tokens.index(("main", TokenType.IDENTIFIER))
    start_idx = main_idx + 2
    end_idx = (
        tokens[main_idx:].index((")", TokenType.SPECIAL_SYMBOL)) + main_idx
    )  # insert arg tokens B4 first ) after main
    tokens = tokens[:start_idx] + main_arg_tokens + tokens[end_idx:]
    assemble_tokens_and_write(tokens, cpp_path)


invalid_main_arg = FixStrategy(
    "main arguments not (int argc, char **argv)",
    lambda r, _: r.main_has_invalid_arg(),
    _fix_main_invalid_arg,
)


def _fix_main_didnt_return_value(paths: Tuple[str, str], r: Report, cr: CompilerReport):
    txt_path, cpp_path = paths
    fpath = cpp_path + "~" if os.path.exists(cpp_path + "~") else txt_path
    with open(fpath, "r") as f:
        lines = f.readlines()

    # current f has no headers
    offset = 0
    with open(path.join(EMBDING_HOME, "header.hpp")) as f:
        offset += len(f.readlines())
    with open(path.join(EMBDING_HOME, "encode2stderr.hpp")) as f:
        offset += len(f.readlines())
    if path.exists(path.join(EMBDING_HOME, "const_macro.hpp")):
        with open(path.join(EMBDING_HOME, "const_macro.hpp")) as f:
            offset += len(f.readlines())

    (ret_ln, _) = r.get_loc()
    ret_ln -= offset
    lines[ret_ln - 1] = lines[ret_ln - 1].replace("return", "return 0")
    with open(cpp_path + "~", "w") as f:
        f.writelines(lines)


main_return_value = FixStrategy(
    "main didn't return zero",
    lambda r, _: r.main_didnt_return_value(),
    _fix_main_didnt_return_value,
)


def _fix_undeclared_identifier_macro(
    paths: Tuple[str, str], r: Report, cr: CompilerReport
):
    txt_path, cpp_path = paths
    macro_name = r.get_undefined_macro()
    macro_defn = f"#define {macro_name} 100\n"
    with open(path.join(EMBDING_HOME, "const_macro.hpp"), "a") as hpp:
        hpp.write(macro_defn)
    if not path.exists(cpp_path + "~"):
        with open(cpp_path + "~", "w") as f:
            with open(txt_path, "r", errors="replace") as txt:
                f.write(txt.read())


undeclared_identifier_macro = FixStrategy(
    "has undeclared identifier which should be a macro",
    lambda r, _: r.has_undeclared_identifier_macro(),
    _fix_undeclared_identifier_macro,
)


# Special cases
# TODO: No special case yet.
SPECIAL_CASE_LIST: List[Tuple[int, int]] = []


def in_special_case_list(_: Report, cr: CompilerReport):
    return (cr.p, cr.i) in SPECIAL_CASE_LIST


def _fix_special_case(cpp_path: str):
    pass


special_cases = FixStrategy(
    "special cases",
    in_special_case_list,
    _fix_special_case,
)

FIX_STRATEGIES = [
    fix_main_returned_non_int,
    main_has_no_return_type,
    use_of_std_keyword,
    struct_len_undefined,
    struct_missing_semicolon,
    invalid_main_arg,
    # `undeclared_identifier_macro` may change the line numebr used in `main_return_value`
    # so these two need to be in order
    undeclared_identifier_macro,
    main_return_value,
    special_cases,
]


def main():
    pass_file


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    main()
