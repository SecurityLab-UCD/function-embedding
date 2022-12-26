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
import requests
import tarfile
import random
from functools import partial
import argparse
import yaml
from multiprocessing import Pool


def dump_stderr_on_exit(errfile: str, p: subprocess.Popen):
    with open(errfile, "ab") as f:
        try:
            _, stderr = p.communicate(timeout=15)
        except TimeoutExpired:
            p.kill()
            _, stderr = p.communicate()
        f.write(stderr)


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


def fuzz_one_file(p: Tuple[str, str], timeout: int, seeds: str):
    bin, out = p
    process = subprocess.Popen(
        [f"{AFL}/afl-fuzz", "-V", str(timeout), "-i", seeds, "-o", out, bin],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Sleep half a second for AFL to bind core.
    subprocess.run(["sleep", "0.5"])
    return process


def format_one_file(src: str):
    return subprocess.Popen(
        [f"{LLVM}/bin/clang-format", src],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_one_file(paths: Tuple[str, str, str, str], timeout="1m"):
    bin_to_run, fuzz_in, output, input_csv = paths
    with open(fuzz_in, "rb") as fin, open(output, "wb") as fout, open(
        input_csv, "wb"
    ) as ferr:
        return subprocess.Popen(
            ["timeout", str(timeout), bin_to_run],
            stdin=fin,
            stdout=fout,
            stderr=ferr,
        )


def check_one_fuzz_stat(fuzz_stat: str, min_thresh: int) -> bool:
    if not path.exists(fuzz_stat):
        return False
    with open(fuzz_stat, "r") as f:
        stat = yaml.safe_load(f)
        return stat["run_time"] >= min_thresh


def coin_toss(percentage: float):
    return random.random() <= percentage / 100.0

def fuzzed(out_path):
    # TODO: Test stats in `fuzzer_stats` to validate the fuzzing result.
    # TODO: Add command line to override this. Aka force re-fuzz
    return path.isdir(out_path) and path.isfile(path.join(out_path, "default", "fuzzer_stats"))

def built(bin_path):
    return path.isfile(bin_path)

class DataSet:
    def __init__(self, workdir, txtdir, language):
        self.workdir = path.abspath(workdir)
        self.txtdir = path.join(self.workdir, txtdir)
        self.srcdir = path.join(self.workdir, "src")
        self.bindir = path.join(self.workdir, "build")
        self.outdir = path.join(self.workdir, "fuzz")
        self.lang = language

    def download(self):
        pass

    def preprocess_all(self):
        if not path.isdir(self.srcdir):
            info("Preprocessing not set, using symlink...")
            if not path.isdir(self.txtdir):
                error(
                    f"{self.txtdir} doesn't exist yet, please download the dataset first."
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

    def build(self, jobs: int = CORES, on_exit=None, sample=100):
        self.mkdir_if_doesnt_exist(self.bindir)
        # Copy the files and do some preprocessing
        files_to_compile: List[Tuple[str, str]] = []
        info("Collecting codes to compile")
        for i in tqdm(os.listdir(self.srcdir)):
            for p in os.listdir(path.join(self.srcdir, str(i))):
                if path.isdir(os.path.abspath(p)):
                    warning(f"{i}/{p} is a dir, is the dataset correct?")
                p = p[:-4]
                src_path = path.join(self.srcdir, str(i), str(p) + ".cpp")
                bin_path = path.join(self.bindir, str(i), str(p))
                if not built(bin_path) and coin_toss(sample):
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

    def fuzz(
        self, jobs: int = CORES, timeout=60, seeds="seeds", on_exit=None, sample=100
    ):
        """
        Fuzz the program
        """
        self.mkdir_if_doesnt_exist(self.outdir)
        bins_to_fuzz: List[Tuple[str, str]] = []
        info("Collecting binaries to fuzz")
        for i in tqdm(os.listdir(self.bindir)):
            for p in os.listdir(path.join(self.bindir, str(i))):
                if path.isdir(os.path.abspath(p)):
                    warning(f"{i}/{p} is a dir, is the dataset correct?")
                bin_path = path.join(self.bindir, str(i), str(p))
                out_path = path.join(self.outdir, str(i), str(p))
                if path.isfile(bin_path) and not fuzzed(out_path) and coin_toss(sample):
                    bins_to_fuzz.append((bin_path, out_path))

        seeds = path.abspath(seeds)
        info(f"Fuzzing all {len(bins_to_fuzz)} binaries")
        parallel_subprocess(
            bins_to_fuzz,
            jobs,
            lambda r: fuzz_one_file(r, timeout=timeout, seeds=seeds),
            on_exit,
        )

    def check_fuzz(self, jobs: int = CORES, min_thresh: int = 5):
        """
        Check Fuzzing Completeness
        """
        f_to_check: List[str] = []
        info("Collecting problems to check")
        for i in tqdm(os.listdir(self.bindir)):
            for p in os.listdir(path.join(self.bindir, str(i))):
                if path.isdir(os.path.abspath(p)):
                    warning(f"{i}/{p} is a dir, is the dataset correct?")

                bin_path = path.join(self.bindir, str(i), str(p))
                if path.isfile(bin_path):
                    fuzzer_stats = path.join(
                        self.outdir, str(i), str(p), "default", "fuzzer_stats"
                    )
                    f_to_check.append(fuzzer_stats)

        info(f"Checking all {len(f_to_check)} output directories")
        with Pool(jobs) as p:
            fuzz_stats = p.map(
                partial(check_one_fuzz_stat, min_thresh=min_thresh), f_to_check
            )
            if not all(fuzz_stats):
                warning(
                    f"{fuzz_stats.count(False)}/{len(f_to_check)} binaries failed fuzzing"
                )
            else:
                info("All possible binaries has valid fuzzing results")

    def postprocess(self, jobs: int = CORES, on_exit=None, sample=100, timeout="1m"):
        """
        Run the program with fuzzing inputs
        """
        bins_to_run: List[Tuple[str, str, str, str]] = []

        info("Collecting binaries to run")
        for i in tqdm(os.listdir(self.bindir)):
            for p in os.listdir(path.join(self.bindir, str(i))):
                if path.isdir(os.path.abspath(p)):
                    warning(f"{i}/{p} is a dir, is the dataset correct?")

                bin_path = path.join(self.bindir, str(i), str(p))
                fuzz_out = path.join(self.outdir, str(i), str(p), "default")

                # skip if current problem is not fuzzed nor selected by sample
                if not (path.isdir(path.join(fuzz_out, "queue")) and coin_toss(sample)):
                    continue

                input_csv_dir = path.join(fuzz_out, "input_csv")
                output_dir = path.join(fuzz_out, "output")
                if not path.isdir(input_csv_dir):
                    os.makedirs(input_csv_dir)
                if not path.isdir(output_dir):
                    os.makedirs(output_dir)

                for q in os.listdir(path.join(fuzz_out, "queue")):
                    fuzz_input_path = path.join(fuzz_out, "queue", str(q))
                    if path.isdir(fuzz_input_path):
                        continue
                    output = path.join(output_dir, str(q))
                    input_csv = path.join(input_csv_dir, str(q) + ".csv")
                    bins_to_run.append((bin_path, fuzz_input_path, output, input_csv))

        info(f"Runninng {len(bins_to_run)} binaries")
        parallel_subprocess(
            bins_to_run, jobs, partial(run_one_file, timeout=timeout), on_exit=on_exit
        )


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
    SUBSET = ["C++1000", "C++1400", "Python", "Java"]

    def __init__(self, workdir, subset):
        self.subset = subset
        if subset not in IBM.SUBSET:
            error(f"Incorrect subset given, only {IBM.SUBSET} allowed.")
            exit(1)
        DataSet.__init__(self, workdir, self.get_subset_name(), "C/C++")

    def get_subset_name(self):
        return f"Project_CodeNet_{self.subset}"

    def get_tar_name(self):
        return f"{self.get_subset_name()}.tar.gz"

    def get_download_path(self):
        return f"https://dax-cdn.cdn.appdomain.cloud/dax-project-codenet/1.0.0/{self.get_tar_name()}"

    def download(self):
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        else:
            warning(f"{self.workdir} already exists")

        tar_path = path.join(self.workdir, self.get_tar_name())
        if not os.path.isfile(tar_path):
            info("Downloading dataset...")
            url = self.get_download_path()
            response = requests.get(url, stream=True)
            # Download with a nice looking progress bar
            # https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests
            total_size_in_bytes = int(response.headers.get("content-length", 0))
            block_size = 1024
            progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
            with open(tar_path, "wb") as file:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    file.write(data)
            progress_bar.close()
        else:
            info("tar already exists.")

        if not os.path.isdir(self.txtdir):
            info("Extracting dataset, may take a while...")
            with tarfile.open(tar_path) as tar:
                # Go over each member
                for m in tqdm(tar.getmembers()):
                    # Extract member
                    tar.extract(member=m, path=self.workdir)
            info("Extraction done.")
        else:
            info("Extracted dataset already exists.")


def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="Build a dataset")
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        choices=["POJ104", "C++1400", "C++1000"],
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
        "-e", "--errfile", type=str, help="The file name to dump stderr", default="O"
    )
    parser.add_argument(
        "-p",
        "--pipeline",
        type=str,
        help="The stage of the job to run",
        default="all",
        choices=[
            "all",
            "download",
            "preprocess",
            "compile",
            "fuzz",
            "check",
            "postprocess",
        ],
    )
    parser.add_argument(
        "-s",
        "--sample",
        type=float,
        help="Only compile and fuzz on a small percentage of dataset (0~100).",
        default=100.0,
    )
    parser.add_argument(
        "-t", "--time", type=str, help="Time to fuzz one program", default="1m"
    )
    parser.add_argument(
        "-tr", "--time_to_run", type=str, help="Time to run one program", default="1m"
    )
    parser.add_argument(
        "-i", "--seeds", type=str, help="Seeds to initialize fuzzing", default="seeds"
    )

    args = parser.parse_args()
    workdir = args.workdir if args.workdir != "" else args.dataset

    if path.exists(workdir):
        warning(f"{workdir} exists")

    if args.sample <= 0 or args.sample > 100:
        error("Sample rate has to be confined between 1 and 100")

    dataset = None
    if args.dataset == "POJ104":
        dataset = POJ104(workdir)
    elif args.dataset == "C++1400":
        dataset = IBM(workdir, args.dataset)
    elif args.dataset == "C++1000":
        dataset = IBM(workdir, args.dataset)
    else:
        unreachable("No dataset provided.")

    def convert_to_seconds(s: str) -> int:
        seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return int(s[:-1]) * seconds_per_unit[s[-1]]

    args.time = convert_to_seconds(args.time)

    if args.pipeline == "all":
        dataset.download()
        dataset.preprocess_all()
        dataset.build(jobs=args.jobs, sample=args.sample)
        dataset.fuzz(jobs=args.jobs, timeout=args.time, seeds=args.seeds)
        dataset.postprocess(jobs=args.jobs, timeout=args.time_to_run)
    elif args.pipeline == "download":
        dataset.download()
    elif args.pipeline == "preprocess":
        dataset.preprocess_all()
    elif args.pipeline == "compile":
        dataset.build(
            jobs=args.jobs,
            sample=args.sample,
            on_exit=partial(dump_stderr_on_exit, args.errfile),
        )
    elif args.pipeline == "fuzz":
        dataset.fuzz(
            jobs=args.jobs, timeout=args.time, seeds=args.seeds, sample=args.sample
        )
    elif args.pipeline == "check":
        dataset.check_fuzz(jobs=args.jobs)
    elif args.pipeline == "postprocess":
        dataset.postprocess(
            jobs=args.jobs, timeout=args.time_to_run, sample=args.sample
        )
    else:
        unreachable("Unkown pipeline provided")


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    main()
