# check for all problems if input each has it corresponding output
import os
from multiprocessing import Pool
from functools import reduce
from typing import NewType, List
from common import EMBDING_HOME, CORES


def check_io(input_file_names: List[str], output_file_names: List[str]) -> str:
    err_msg = ""

    if input_file_names - output_file_names != set():
        err_msg += "input_csv missing:\n"
        err_msg += str(input_file_names - output_file_names) + "\n"
    elif output_file_names - input_file_names != set():
        err_msg += "output missing:\n"
        err_msg += str(output_file_names - input_file_names) + "\n"

    return err_msg


def check_queue(io_file_names: List[str], queue_file_names: List[str]) -> str:
    """
    io_file_names should be one of the io name lists
    this function is assumed to be used after check_io
    """
    err_msg = ""
    if queue_file_names - io_file_names != set():
        err_msg += "io missing:\n"
        err_msg += str(queue_file_names - io_file_names) + "\n"
    return err_msg


def check_integrity(dir_name: str) -> str:
    err_msg = ""

    try:
        input_files = set(
            map(lambda s: s.split(".csv")[0], os.listdir(dir_name + "/input_csv"))
        )
        output_files = set(os.listdir(dir_name + "/output"))
        queue_files = set(
            filter(lambda f: f[0] != ".", os.listdir(dir_name + "/queue"))
        )
        err_msg += check_io(input_files, output_files)
        err_msg += check_queue(output_files, queue_files)

    except Exception as e:
        err_msg += str(e) + "\n"

    if err_msg != "":
        err_msg = "Failed for {}\n".format(dir_name) + err_msg + "\n"

    return err_msg


if __name__ == "__main__":
    output_dir = (
        os.environ["OUTPUT"] if os.getenv("OUTPUT") else EMBDING_HOME + "/output"
    )
    n_process = CORES
    fuzzouts = [
        output_dir + "/{}/{}/default".format(i, p)
        for i in range(1, 105)
        for p in os.listdir(output_dir + "/{}".format(i))
    ]
    with Pool(n_process) as pool:
        print(reduce(lambda a, b: a + b, pool.map(check_integrity, fuzzouts)))
