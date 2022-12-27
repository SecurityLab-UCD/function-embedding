from common import *
from typing import List, Tuple, Set, Dict
import re
from tqdm import tqdm
from os import path
import argparse
import json
import bisect

AbortReason = str
AbortTest = str


class Report:
    lines: List[str]
    p: int
    i: int
    abort: Tuple[AbortTest, AbortReason]

    def __init__(self, lines):
        self.lines = lines
        # Get Problem id and file id.
        first_line = lines[0]
        words = first_line.split("/")
        self.p = int(words[-2])
        self.i = int(words[-1])
        matches = re.findall(
            "PROGRAM ABORT : Test case '(.*)' results in a (.*)", lines[-2]
        )
        if matches:
            self.abort = matches[0]
        else:
            self.abort = ("", lines[-2].split(":")[1])

    def get_path(self):
        bin_path = path.join(str(self.p), str(self.i))
        return bin_path

    def __str__(self):
        return "\n".join(self.lines)

    def __eq__(self, o):
        return self.abort == o.abort

    def __hash__(self):
        return hash(str(self.abort) + str(self.i) + str(self.p))


class FuzzerReport:
    reports: List[Report] = []

    def __init__(self, reports):
        self.reports = reports

    def to_reason_dict(self) -> Dict[AbortReason, List[Tuple[int, int, AbortTest]]]:
        """
        find abort reasons and their corresponding file and test
        """
        ret = {}
        for r in self.reports:
            test, reason = r.abort
            p = (r.p, r.i, test)
            if reason in ret.keys():
                ret[reason].append(p)
            else:
                ret[reason] = [p]
        return ret

    def to_test_dict(self) -> Dict[AbortTest, List[str]]:
        ret = {}
        for r in self.reports:
            test, _ = r.abort
            p = r.get_path()
            if test in ret.keys():
                ret[test].append(p)
            else:
                ret[test] = [p]
        return ret

    def to_problem_map(self, bindir) -> Dict[str, str]:
        def get_seed(test: AbortTest) -> str:
            return test.split("orig:")[1] if test != "" else ""

        ret = {
            path.join(bindir, r.get_path()): get_seed(r.abort[0]) for r in self.reports
        }
        return ret


def init_reports(fpath):
    reports: List[Report] = []
    with open(fpath, "r") as f:
        lines = []
        lines_in_file = f.readlines()
        info("Converting stderr into FuzzReport")
        for line in tqdm(lines_in_file):
            if line != "\n":
                lines.append(line[:-1])
            if "Location :" in line:
                reports.append(Report(lines))
                lines = []
    return reports


def main():

    parser = argparse.ArgumentParser(description="Analyze Fuzzer Output")

    parser.add_argument(
        "-o",
        "--outfile",
        type=str,
        help="The file name read fuzzer output from",
        default="O-fuzz",
    )

    args = parser.parse_args()
    reports = init_reports(args.outfile)
    fr = FuzzerReport(reports)
    d = fr.to_reason_dict()
    no_valid_seed = d[" We need at least one valid input seed that does not crash!"]
    print(len(no_valid_seed))
    pd = {}
    for p, i, _ in no_valid_seed:
        if p in pd.keys():
            bisect.insort(pd[p], i)
        else:
            pd[p] = [i]

    json.dump(pd, open("no_valid_seed.json", "w"))


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    main()
