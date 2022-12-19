from common import *
from whitelist import *
from os import path
import os
from tqdm import tqdm
from typing import List, Tuple
import subprocess
import re
from logging import error, info, warning
from replace_input import replace_file


def compile_one_file(p: Tuple[str, str]):
    src, dst = p
    # TODO: if src in blacklist, use another copmile strategy.
    cmd = [f"{AFL}/afl-clang-fast++", "-O0", src, "--std=c++11", "-o", dst]

    # TODO: this method to get file id only works for POJ104
    f_id = src.rsplit("src/")[1].split(".cpp")[0]
    if f_id in POJ104_NO_MATH_H_LIST:
        cmd.append("-D_NO_MATH_H_")

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def format_one_file(src: str):
    return subprocess.Popen(
        [f"{LLVM}/bin/clang-format", src],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class DataSet:
    def __init__(self, workdir, txtdir, language):
        self.workdir = path.abspath(workdir)
        self.txtdir = path.join(self.workdir, txtdir)
        self.srcdir = path.join(self.workdir, "src")
        self.bindir = path.join(self.workdir, "build")
        self.lang = language

    def download(self):
        pass

    def preprocess_all(self):
        if not path.isdir(self.txtdir):
            # TODO: Call download here.
            error(
                f"{self.txtdir} doesn't exist yet, please refer to README to download the dataset first."
            )
        # By default there is no preprocessing.
        os.symlink(self.txtdir, self.srcdir)

    def mkdir_if_doesnt_exist(self, dir):
        if not path.isdir(dir):
            os.makedirs(dir)
        for i in os.listdir(self.txtdir):
            subdir = path.join(dir, str(i))
            if not path.isdir(subdir):
                os.makedirs(subdir)

    def compile_all(self, jobs: int = CORES, on_exit=None):
        self.mkdir_if_doesnt_exist(self.bindir)
        # Copy the files and do some preprocessing
        files_to_compile: List[Tuple[str, str]] = []
        info("Collecting codes to compile")
        for i in tqdm(os.listdir(self.srcdir)):
            for p in os.listdir(path.join(self.srcdir, str(i))):
                p = p[:-4]
                src_path = path.join(self.srcdir, str(i), str(p) + ".cpp")
                bin_path = path.join(self.bindir, str(i), str(p))
                if not path.isfile(bin_path):
                    files_to_compile.append((src_path, bin_path))

        info("Compiling all the code")
        parallel_subprocess(files_to_compile, jobs, compile_one_file, on_exit)

    def remove_comments(self, text: str) -> str:
        # https://stackoverflow.com/questions/241327/remove-c-and-c-comments-using-python
        def replacer(match):
            s = match.group(0)
            if s.startswith("/"):
                return " "  # note: a space and not an empty string
            else:
                return s

        if self.lang == "C/C++":
            pattern = re.compile(
                r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
                re.DOTALL | re.MULTILINE,
            )
        else:
            error("language not supported for removing comments")

        return re.sub(pattern, replacer, text)


class POJ104(DataSet):
    def __init__(self, workdir):
        DataSet.__init__(self, workdir, "ProgramData", "C/C++")
        self.format_list: List[str] = [
            f"{self.txtdir}/{file_id}.txt" for file_id in POJ104_FORMAT_LIST
        ]

    def download(self):
        # TODO: Download it to some hidden place, and link data to self.txtdir
        pass

    def preprocess_all(self):
        if not path.isdir(self.txtdir):
            # TODO: Call download here.
            error(
                f"{self.txtdir} doesn't exist yet, please refer to README to download the dataset first."
            )
        self.mkdir_if_doesnt_exist(self.srcdir)
        info("Preprocessing text files into codes")
        for i in tqdm(os.listdir(self.txtdir)):
            for p in os.listdir(path.join(self.txtdir, str(i))):
                p = p[:-4]
                txt_path = path.join(self.txtdir, str(i), str(p) + ".txt")
                src_path = path.join(self.srcdir, str(i), str(p) + ".cpp")
                if not path.isfile(src_path):
                    self.preprocess_one(txt_path, src_path)

    def preprocess_one(self, txt_path, src_path):
        with open(src_path, "w") as f:
            # cat $EMBDING_HOME/header.hpp >> $SRCDIR/$P.cpp
            with open(path.join(EMBDING_HOME, "header.hpp"), "r") as hpp:
                header = hpp.read()
                f.write(header)
            # cat $EMBDING_HOME/encode2stderr.hpp >> $SRCDIR/$P.cpp
            with open(path.join(EMBDING_HOME, "encode2stderr.hpp"), "r") as hpp:
                header = hpp.read()
                f.write(header)
            # $LLVMPATH/bin/clang-format $TXTDIR/$P.txt > $SRCDIR/$P.temp.cpp
            # python3.8 $EMBDING_HOME/scripts/replace_input.py $SRCDIR/$P.temp.cpp >> $SRCDIR/$P.cpp
            if txt_path in self.format_list:
                code = format_one_file(txt_path).stdout.read().decode(errors="replace")
            else:
                with open(txt_path, "r", errors="replace") as txt:
                    code = txt.read()
            code = replace_file(self.remove_comments(code))
            # sed -i 's/void main/int main/g' $SRCDIR/$P.cpp
            code = code.replace("void main", "int main")
            f.write(code)


class IBM(DataSet):
    def download(self):
        pass
