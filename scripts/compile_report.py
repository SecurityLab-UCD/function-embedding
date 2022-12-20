import argparse
import os
from typing import List
import subprocess
import re
from common import *

PROBLEMS = [1]


class Report:
    lines: Tuple[str]

    def __init__(self, lines):
        self.lines = tuple(lines)

    def __str__(self):
        return "\n".join(self.lines)

    def get_loc(self):
        return tuple(map(int, self.lines[0].split(":")[1:3]))

    def main_returned_non_int(self):
        return "'main' must return 'int'" in self.lines[0]

    def main_has_no_return_type(self):
        return (
            "C++ requires a type specifier for all declarations" in self.lines[0]
            and "main" in self.lines[1]
        )

    def struct_len_undefined(self):
        # TODO: (struct m*)calloc(n,L);
        use_malloc = len(self.lines) > 1 and bool(
            re.findall(".*\((.*)\) ?malloc\((.*)\)", self.lines[1])
        )
        return "use of undeclared identifier" in self.lines[0] and use_malloc

    def get_struct_len_definition(self):
        assert self.struct_len_undefined()
        return re.findall(".*\((.*)\) ?malloc\((.*)\)", self.lines[1])[0]

    def use_of_std_keyword(self):
        # rank string count function array
        if "reference to '" in self.lines[0] and "' is ambiguous" in self.lines[0]:
            keyword = self.lines[0].split("'")[1]
            std_keyword = "std::" + keyword
            for line in self.lines:
                if std_keyword in line:
                    return True
        return False

    def get_std_keyword(self):
        assert self.use_of_std_keyword()
        return self.lines[0].split("'")[1]

    def has_redefinition_of_symbol(self):
        if (
            "redefinition of '" in self.lines[0]
            and "' as different kind of symbol" in self.lines[0]
        ):
            symbol = self.lines[0].split("'")[1]
            return any(map(lambda line: symbol in line, self.lines))
        return False

    def get_redefined_symbol(self):
        assert self.has_redefinition_of_symbol()
        return self.lines[0].split("'")[1]

    def define_struct_no_semicolon(self):
        # error: 'library' cannot be defined in the result type of a function
        # struct library
        return (
            "cannot be defined in the result type of a function" in self.lines[0]
            and len(self.lines) > 1
            and "struct" in self.lines[1]
        )

    def get_struct_name(self):
        assert self.define_struct_no_semicolon()
        return self.lines[0].split("'")[1]

    def main_has_invalid_arg(self):
        return (
            "parameter of 'main'" in self.lines[0]
            and "must be of type" in self.lines[0]
        )

    def main_didnt_return_value(self):
        return "non-void function 'main' should return a value" in self.lines[0]


class CompilerReport:
    p: int
    i: int
    num_erros: int
    num_warnings: int
    error_list: List[Tuple[Report]]
    warning_list: List[Tuple[Report]]

    def __init__(self, lines):
        # Get Problem id and file id.
        first_line = lines[0]
        first_line = first_line.split(".cpp")[0]
        words = first_line.split("/")
        self.p = int(words[-2])
        self.i = int(words[-1])

        # Get # of warning and errors
        last_line = lines[-1]
        words = last_line.split(" ")
        if words[1] == "warning":
            self.num_warnings = int(words[0])
            self.num_errors = int(words[3]) if "error" in last_line else 0
        elif words[1] == "error":
            self.num_warnings = 0
            self.num_errors = int(words[0])

        # Split the report into seperate warnings and errors.
        self.error_list = []
        self.warning_list = []
        idx = 0
        while idx < len(lines) - 1:
            begin = idx
            idx += 1
            while (
                "error: " not in lines[idx]
                and "warning: " not in lines[idx]
                and "generated" not in lines[idx]
                or "too many errors emitted, stopping now" in lines[idx]
            ):
                idx += 1
            end = idx
            if "error: " in lines[begin]:
                self.error_list.append(Report(lines[begin:end]))
            elif "warning: " in lines[begin]:
                self.warning_list.append(Report(lines[begin:end]))
            else:
                print(lines[begin], begin, len(lines), lines)
                unreachable("Shouldn't be here")

    def get_path(self) -> Tuple[str, str]:
        txt_path = os.path.join(TXTDIR, str(self.p), str(self.i) + ".txt")
        cpp_path = os.path.join(SRCDIR, str(self.p), str(self.i) + ".cpp")
        return (txt_path, cpp_path)

    def get_keywords_used(self) -> Set[str]:
        ret = set()
        for r in self.error_list:
            if r.use_of_std_keyword():
                ret.add(r.get_std_keyword())
            if r.has_redefinition_of_symbol():
                ret.add(r.get_redefined_symbol())
        return ret

    def get_struct_len_definition(self) -> Set[str]:
        ret = set()
        for r in self.error_list:
            if r.struct_len_undefined():
                ret.add(r.get_struct_len_definition())
        return ret


def init_crash_report(p: subprocess.Popen):
    global reports
    reports.append(CompilerReport(p.stderr.read().decode().split("\n")))


def init_crash_report_from_stderr(p: str):
    reports: List[CompilerReport] = []
    if not path.isfile(p):
        error(f"{p} is not a valid path to dumped reports.")
    with open(p, "r") as f:
        lines = []
        info("Converting stderr into CompilerReport")
        for line in tqdm(f):
            lines.append(line[:-1])
            if "generated." in line:
                reports.append(CompilerReport(lines))
                lines = []

    return reports


def classify():
    reports = init_crash_report_from_stderr("./O")
    # compile_all(on_exit=init_crash_report)
    return reports


def set_global_DIR(txtdir: str, srcdir: str):
    global SRCDIR
    global TXTDIR
    SRCDIR = srcdir
    TXTDIR = txtdir


def main():
    reports = classify()
    print(len(reports))


if __name__ == "__main__":
    main()
