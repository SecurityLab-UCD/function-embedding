from common import *
from typing import Callable
from compile_report import *
import sctokenizer
from sctokenizer import Source, TokenType, Token
from functools import reduce
from compile_report import init_crash_report_from_stderr
from tqdm import tqdm

CPP_TYPE_SET = {"int", "float", "double", "char", "wchar", "bool", "void"}


def tokenize(fpath: str):
    def token2tuple(token):
        # discard position
        return (token.token_value, token.token_type)

    tokens = sctokenizer.tokenize_file(filepath=fpath, lang="cpp")
    tokens = list(map(token2tuple, tokens))
    return tokens


# TODO: Should use an IOWrapper to write to file or string.
def assemble_tokens_and_write(tokens, cpp_path: str):
    with open(cpp_path, "w") as f:
        for i in range(len(tokens)):
            token_val, token_type = tokens[i]
            f.write(token_val)
            if token_type == TokenType.KEYWORD:
                f.write(" ")
            if token_type == TokenType.COMMENT_SYMBOL:
                f.write("\n")
            if (
                token_type == TokenType.OPERATOR
                and token_val == ">"
                and tokens[i - 2][1] == TokenType.OPERATOR
                and tokens[i - 2][0] == "<"
                and tokens[i - 3][1] == TokenType.KEYWORD
                and tokens[i - 3][0] == "include"
            ):
                f.write("\n")
            if token_val == "{" or token_val == "}" or token_val == ";":
                f.write("\n")


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
def _fix_main_returned_non_int(cpp_path: str, r: Report, cr: CompilerReport):
    tokens = tokenize(cpp_path)
    main_idx = tokens.index(("main", TokenType.IDENTIFIER))
    prev_val, prev_type = tokens[main_idx - 1]
    int_token = ("int", TokenType.KEYWORD)
    if prev_type == TokenType.KEYWORD and prev_val in CPP_TYPE_SET:
        tokens[main_idx - 1] = int_token
    assemble_tokens_and_write(tokens, cpp_path)


fix_main_returned_non_int = FixStrategy(
    "main returned non int",
    lambda r, _: r.main_returned_non_int(),
    _fix_main_returned_non_int,
)


# Main has no return type
def _fix_main_has_no_return_type(cpp_path: str, r: Report, cr: CompilerReport):
    tokens = tokenize(cpp_path)
    main_idx = tokens.index(("main", TokenType.IDENTIFIER))
    int_token = ("int", TokenType.KEYWORD)
    tokens = tokens[:main_idx] + [int_token] + tokens[main_idx:]
    assemble_tokens_and_write(tokens, cpp_path)


main_has_no_return_type = FixStrategy(
    "main has no return type",
    lambda r, _: r.main_has_no_return_type(),
    _fix_main_has_no_return_type,
)


def _fix_use_of_std_keyword(cpp_path: str, r: Report, cr: CompilerReport):
    tokens = tokenize(cpp_path)
    keywords = cr.get_keywords_used()
    for i in range(len(tokens)):
        token_val, token_type = tokens[i]
        if token_val in keywords:
            tokens[i] = ("_" + token_val, token_type)
    assemble_tokens_and_write(tokens, cpp_path)


# Cpp stdlib keyword
use_of_std_keyword = FixStrategy(
    "Used keywords in stdlib",
    lambda r, _: r.use_of_std_keyword(),
    _fix_use_of_std_keyword,
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
    special_cases,
]


def main():
    with open("./O", "r") as f:
        lines = []
        info("Converting stderr into CompilerReport")
        for line in f:
            lines.append(line[:-1])
            if "generated." in line:
                cr = CompilerReport(lines)
                for r in cr.error_list:
                    for strategy in FIX_STRATEGIES:
                        if strategy.isMatch(r, cr):
                            strategy.fix(cr.get_path(), r, cr)
                lines = []


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    main()
