from common import *
from os import path
import os
from tqdm import tqdm
from typing import List, Tuple
import subprocess


def preprocess_textfile(txt_path, src_path):
    with open(src_path, "wb") as f:
        # cat $EMBDING_HOME/header.hpp >> $SRCDIR/$P.cpp
        with open(path.join(EMBDING_HOME, "header.hpp"), "rb") as hpp:
            header = hpp.read()
            f.write(header)
        with open(txt_path, "rb") as txt:
            code = txt.read()
            f.write(code)

        # TODO: cat $EMBDING_HOME/encode2stderr.hpp >> $SRCDIR/$P.cpp
        # TODO: python3.8 $EMBDING_HOME/scripts/replace_input.py $TXTDIR/$P.txt >> $SRCDIR/$P.cpp


def compile_one_file(p: Tuple[str, str]):
    src, dst = p
    # TODO: if src in blacklist, use another copmile strategy.
    return subprocess.Popen(
        [f"{AFL}/afl-clang-fast++", "-O0", src, "--std=c++11", "-o", dst],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


stderrs = []

DATASETDIR = path.join(EMBDING_HOME, "IBM")
SRCDIR = path.join(DATASETDIR, "src", "Project_CodeNet_C++1000")
TXTDIR = path.join(DATASETDIR, "txt", "Project_CodeNet_C++1000")
BINDIR = path.join(DATASETDIR, "build", "Project_CodeNet_C++1000")


def dump_stderr_on_exit(p: subprocess.Popen):
    # TODO: Change fixed ./O output file.
    with open("O", "a") as f:
        f.write(p.stderr.read().decode())


def mkdir_if_doesnt_exist(dir, template=TXTDIR):
    if not path.isdir(dir):
        os.makedirs(dir)
    for i in os.listdir(template):
        subdir = path.join(dir, str(i))
        if not path.isdir(subdir):
            os.makedirs(subdir)


def preprocess_all():
    if not path.isdir(TXTDIR):
        error(
            f"{TXTDIR} doesn't exist yet, please refer to README to download the dataset first."
        )
    mkdir_if_doesnt_exist(SRCDIR, TXTDIR)
    info("Preprocessing text files into codes")
    for i in tqdm(os.listdir(TXTDIR)):
        for p in os.listdir(path.join(TXTDIR, str(i))):
            p = p[:-4]
            txt_path = path.join(TXTDIR, str(i), str(p) + ".txt")
            src_path = path.join(SRCDIR, str(i), str(p) + ".cpp")
            if not path.isfile(src_path):
                preprocess_textfile(txt_path, src_path)


# TODO: replace CORES with command line arg.
def compile_all(jobs: int = CORES, on_exit=None):
    mkdir_if_doesnt_exist(BINDIR, SRCDIR)
    # Copy the files and do some preprocessing
    files_to_compile: List[Tuple[str, str]] = []
    info("Collecting codes to compile")
    for i in tqdm(os.listdir(SRCDIR)):
        for p in os.listdir(path.join(SRCDIR, str(i))):
            p = p[:-4]
            src_path = path.join(SRCDIR, str(i), str(p) + ".cpp")
            bin_path = path.join(BINDIR, str(i), str(p))
            if not path.isfile(bin_path):
                files_to_compile.append((src_path, bin_path))

    info("Compiling all the code")
    parallel_subprocess(files_to_compile, jobs, compile_one_file, on_exit)


def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    # preprocess_all()
    compile_all(on_exit=dump_stderr_on_exit)


if __name__ == "__main__":
    # TODO: Add
    main()
