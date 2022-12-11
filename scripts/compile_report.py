import argparse
import os
from typing import List
from build import compile_all
import subprocess
from common import *

PROBLEMS = [1]


class Report:
    lines: Tuple[str]

    def __init__(self, lines):
        self.lines = tuple(lines)

    def main_returned_non_int(self):
        return "'main' must return 'int'" in self.lines[0]

    def main_has_no_return_type(self):
        return (
            "C++ requires a type specifier for all declarations" in self.lines[0]
            and "main()" in self.lines[1]
        )

    def struct_len_undefined(self):
        return "use of undeclared identifier" in self.lines[0] and True
        # TODO: regex match "(struct A \*)malloc(B);"

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
            self.num_errors = int(words[3])
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

    def get_path(self) -> str:
        return os.path.join(SRCDIR, str(self.p), str(self.i) + ".cpp")

    def get_keywords_used(self) -> List[str]:
        ret = []
        for r in self.error_list:
            if r.use_of_std_keyword():
                ret.append(r.get_std_keyword())
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
    init_crash_report_from_stderr("./O")
    # compile_all(on_exit=init_crash_report)


def main():
    classify()
    print(len(reports))


if __name__ == "__main__":
    main()
