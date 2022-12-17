from common import *
from os import path
import os
from typing import List, Tuple
import subprocess
from logging import error, info, warning
import argparse
from dataset import *
from functools import partial


def dump_stderr_on_exit(errfile: str, p: subprocess.Popen):
    with open(errfile, "ab") as f:
        try:
            _, stderr = p.communicate(timeout=15)
        except TimeoutExpired:
            p.kill()
            _, stderr = p.communicate()
        f.write(stderr)


def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="Build a dataset")
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        choices=["POJ104", "IBM1400", "IBM1000"],
        required=True,
        help="The dataset to copmile",
    )
    parser.add_argument(
        "-w", "--workdir", type=str, default="", help="The workdir to use."
    )
    parser.add_argument(
        "-j", "--jobs", type=int, help="Number of threads to use.", default=CORES
    )
    parser.add_argument(
        "-f", "--errfile", type=str, help="The file name to dump stderr", default="O"
    )

    args = parser.parse_args()
    workdir = args.workdir if args.workdir != "" else args.dataset

    if path.exists(workdir):
        warning(f"{workdir} exists")

    dataset = None
    if args.dataset == "POJ104":
        dataset = POJ104(workdir)
    elif args.dataset == "IBM1400":
        dataset = IBM(workdir)
    elif args.dataset == "IBM1000":
        dataset = IBM(workdir)
    dataset.preprocess_all()
    dataset.compile_all(
        jobs=args.jobs, on_exit=partial(dump_stderr_on_exit, args.errfile)
    )


if __name__ == "__main__":
    main()
