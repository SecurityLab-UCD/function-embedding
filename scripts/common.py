import logging
from logging import error, info, warn
import os
from os import path
from typing import Iterable, Callable, Set, Tuple, TypeVar, Optional, Dict
import subprocess
from tqdm import tqdm

POJ = os.getenv("POJ")
if POJ == None:
    error("POJ not set, please tell me where the code is.")
    exit(1)
DATASETDIR = path.join(POJ, "dataset")
SRCDIR = path.join(DATASETDIR, "src")
TXTDIR = path.join(DATASETDIR, "ProgramData")
BINDIR = path.join(DATASETDIR, "build", "bin")

AFL = os.getenv("AFL")
if AFL == None:
    error("AFL not set, please tell me where AFL++ is.")
    exit(1)

TIMEOUT = os.getenv("TIMEOUT")
if TIMEOUT == None:
    info("TIMEOUT not set, please tell me how long do you want to fuzz")

CORES = os.getenv("CORES")
if CORES == None:
    import multiprocessing

    CORES = multiprocessing.cpu_count()
    warn(f"CORES not set, default to all cores. (nproc = {CORES})")

EMBDING_HOME = os.getenv("EMBDING_HOME")
if EMBDING_HOME == None:
    error("EMBDING_HOME not set, please tell me where the code is.")
    exit(1)

NUMSUBDIR = 1

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
        if on_exit is not None:
            ret[i] = on_exit(p)
    return ret
