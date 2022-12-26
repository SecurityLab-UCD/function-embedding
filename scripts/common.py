import logging
from logging import error, info, warning
import os
from os import path
from typing import Iterable, Callable, Set, Tuple, TypeVar, Optional, Dict
import subprocess
from tqdm import tqdm

AFL = os.getenv("AFL")
if AFL == None:
    error("AFL not set, please tell me where AFL++ is.")
    exit(1)

LLVM = os.getenv("LLVM")
if LLVM == None:
    error("LLVM not set, please tell me where clang+llvm is.")
    exit(1)

CORES = os.getenv("CORES")
if CORES == None:
    import multiprocessing

    CORES = multiprocessing.cpu_count()
    warning(f"CORES not set, default to all cores. (nproc = {CORES})")

EMBDING_HOME = os.getenv("EMBDING_HOME")
if EMBDING_HOME == None:
    error("EMBDING_HOME not set, please tell me where the code is.")
    exit(1)

__T = TypeVar("__T")
__R = TypeVar("__R")


def unreachable(s: str = ""):
    error(f"Unreachable executed: {str}")
    exit(1)


def parallel_subprocess(
    iter: Iterable[__T],
    jobs: int,
    subprocess_creator: Callable[[__T], subprocess.Popen],
    on_exit: Optional[Callable[[subprocess.Popen], __R]] = None,
) -> Dict[__T, __R]:
    """
    Creates `jobs` subprocesses that run in parallel.
    `iter` contains input that is send to each subprocess.
    `subprocess_creator` creates the subprocess and returns a `Popen`.
    After each subprocess ends, `on_exit` will go collect user defined input and return.
    The return valus is a dictionary of inputs and outputs.

    User has to guarantee elements in `iter` is unique, or the output may be incorrect.
    """
    ret = {}
    processes: Set[Tuple[subprocess.Popen, __T]] = set()
    for input in tqdm(iter):
        processes.add((subprocess_creator(input), input))
        if len(processes) >= jobs:
            # wait for a child process to exit
            os.wait()
            exited_processes = [(p, i) for p, i in processes if p.poll() is not None]
            for p, i in exited_processes:
                processes.remove((p, i))
                if on_exit is not None:
                    ret[i] = on_exit(p)
    # wait for remaining processes to exit
    for p, i in processes:
        p.wait()
        # let `on_exit` to decide wait for or kill the process
        if on_exit is not None:
            ret[i] = on_exit(p)
    return ret


class ExprimentInfo:
    expr_path: str
    fuzzed: bool

    def __init__(self, expr_path):
        self.expr_path = expr_path

        try:
            with open(self.get_fuzzer_stats_path(), "r") as f:
                for line in f:
                    line = line.split(" : ")
                    self.__dict__[line[0].strip()] = line[1]
            self.run_time = int(self.run_time)
            self.bitmap_cvg = float(self.bitmap_cvg[-1])
            self.execs_per_sec = float(self.execs_per_sec)
            self.execs_done = int(self.execs_done)
        except:
            self.fuzzed = False

    def sufficiently_fuzzed(self):
        return self.fuzzed and self.bitmap_cvg > 50.0
