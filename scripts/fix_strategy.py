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


def get_value(token_tuple):
    if token_tuple[1] == TokenType.KEYWORD:
        return token_tuple[0] + " "
    if token_tuple[1] == TokenType.COMMENT_SYMBOL:
        return token_tuple[0] + "\n"
    return token_tuple[0]


def write_tokens(tokens, fpath: str):
    fixed_file = reduce(lambda s, token: s + get_value(token), tokens, "")
    with open(fpath, "w") as f:
        f.write(fixed_file)


class FixStrategy:
    _description: str
    _isMatch: Callable[[Report, CompilerReport], bool]
    _fix: Callable[[str, Report, CompilerReport]]

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
def _fix_main_returned_non_int(cpp_path: str, _, _):
    with open(cpp_path, "r") as f:
        lines = f.readlines()
    idx = 0
    while idx < len(lines):
        if "void main(" in lines[idx]:
            lines[idx] = lines[idx].replace("void main(", "int main(")
            break
        idx += 1
    with open(cpp_path, "w") as f:
        f.writelines(lines)


fix_main_returned_non_int = FixStrategy(
    "main returned non int",
    lambda r, _: r.main_returned_non_int(),
    _fix_main_returned_non_int,
)


# Main has no return type
def _fix_main_has_no_return_type(cpp_path: str, _, _):
    with open(cpp_path, "r") as f:
        lines = f.readlines()
    idx = 0
    while idx < len(lines):
        if "main(" in lines[idx]:
            lines[idx] = lines[idx].replace("main(", "int main(")
            break
        idx += 1
    with open(cpp_path, "w") as f:
        f.writelines(lines)


main_has_no_return_type = FixStrategy(
    "main returned non int",
    lambda r, _: r.main_has_no_return_type(),
    _fix_main_has_no_return_type,
)


def _fix_use_of_std_keyword(cpp_path: str, _, cr: CompilerReport):
    keywords = cr.get_keywords_used()
    # TODO: Tokenize and replace keywords


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
        for line in tqdm(f):
            lines.append(line[:-1])
            if "generated." in line:
                cr = CompilerReport(lines)
                info("New report created")
                for r in cr.error_list:
                    for strategy in FIX_STRATEGIES:
                        if strategy.isMatch(r, cr):
                            info(f'Strategy "{strategy}" matches')
                            strategy.fix(cr.get_path(), r, cr)
                lines = []


if __name__ == "__main__":
    main()
