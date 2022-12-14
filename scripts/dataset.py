from common import *
from whitelist import *
from fix_strategy import *
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


ENCODE_INPUT = False

def dump_stderr_on_exit(errfile: str, p: subprocess.Popen):
    with open(errfile, "ab") as f:
        try:
            _, stderr = p.communicate(timeout=15)
        except TimeoutExpired:
            p.kill()
            _, stderr = p.communicate()
        f.write(stderr)


def compile_one_file(p: Tuple[str, str], lang: str):
    src, dst = p
    cmd = []

    if lang == "C/C++":
        # TODO: if src in blacklist, use another copmile strategy.
        cmd = [
            f"{AFL}/afl-clang-fast++",
            "-O0",
            src,
            "./encode2stderr.so",
            "--std=c++11",
            "-o",
            dst,
        ]

        # TODO: this method to get file id only works for POJ104
        f_id = src.rsplit("src/")[1].split(".cpp")[0]
        if f_id in POJ104_NO_MATH_H_LIST:
            cmd.append("-D_NO_MATH_H_")
        if ENCODE_INPUT:
            cmd.append("-D_ENCODE_INPUT_")
    elif lang == "Java":
        cmd = ["javac", src, "-d", dst]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def fuzz_one_file(p: Tuple[str, str], timeout: int, seeds: str, lang):
    bin, out = p
    cmd = [
        f"{AFL}/afl-fuzz",
        "-D",
        "-V",
        str(timeout),
        "-i",
        seeds,
        "-o",
        out,
        "-t",
        "50",
    ]
    if lang == "Python":
        cmd[0] = "py-afl-fuzz"
        cmd.append("python3")
    cmd.append(bin)
    process = subprocess.Popen(
        cmd,
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


def run_one_file(paths: Tuple[str, str, str, str], lang: str, timeout="1m"):
    bin_to_run, fuzz_in, output, input_csv = paths
    run_cmd = ""
    if lang == "C/C++":
        run_cmd = bin_to_run
    elif lang == "Java":
        bin_dir = path.dirname(bin_to_run)
        class_name = path.basename(bin_to_run).split(".class")[0]
        run_cmd = f"java -cp {bin_dir} {class_name}"
    elif lang == "Python":
        run_cmd = f"python3 {bin_to_run}"

    with open(fuzz_in, "rb") as fin, open(output, "wb") as fout, open(
        input_csv, "wb"
    ) as ferr:
        # remove output file if timeout
        return subprocess.Popen(
            [
                "bash",
                "-c",
                f"timeout {timeout} {run_cmd}; if [[ $? -eq 124 ]]; then rm {output}; fi",
            ],
            stdin=fin,
            stdout=fout,
            stderr=ferr,
        )


def coin_toss(percentage: float):
    return random.random() <= percentage / 100.0


class DataSet:
    def __init__(self, workdir, txtdir, language):
        self.workdir = path.abspath(workdir)
        self.txtdir = path.join(self.workdir, txtdir)
        self.srcdir = path.join(self.workdir, "src")
        self.bindir = path.join(self.workdir, "build")
        self.outdir = path.join(self.workdir, "fuzz")
        self.lang = language
        self.update_problems()

    def update_problems(self):
        if path.isdir(self.txtdir):
            self.problems = os.listdir(self.txtdir)

    def download(self):
        pass

    def set_problems(self, problem_range: str):
        """manully set a range of problem to run

        Args:
            problem_range (str): range(start, end)
        """
        try:
            # ToDo: check for unallowed functions b4 eval
            pr = eval(problem_range)
        except Exception as e:
            logging.error(f"cannot eval range: {e}")
            exit(1)

        if pr is None:
            return

        assert isinstance(pr, Iterable), "Invalid problem range given"
        assert (
            max(pr) < len(self.problems) and min(pr) >= 0
        ), "Range selection index out of range"

        self.problems = [self.problems[i] for i in pr]

    def for_all_src(self):
        for i in tqdm(self.problems):
            for p in os.listdir(path.join(self.srcdir, str(i))):
                p = path.splitext(p)[0]
                yield (i, p)

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
        for i in self.problems:
            subdir = path.join(dir, str(i))
            if not path.isdir(subdir):
                os.makedirs(subdir)

    def build(self, jobs: int = CORES, on_exit=None, sample=100, built=None):
        if built is None:
            built = lambda bin_path: path.isfile(bin_path)
        self.mkdir_if_doesnt_exist(self.bindir)
        # Copy the files and do some preprocessing
        files_to_compile: List[Tuple[str, str]] = []
        info("Collecting codes to compile")
        for (i, p) in self.for_all_src():
            if path.isdir(os.path.abspath(p)):
                warning(f"{i}/{p} is a dir, is the dataset correct?")
            src_path = path.join(self.srcdir, str(i), str(p) + ".cpp")
            bin_path = path.join(self.bindir, str(i), str(p))
            if not built(bin_path) and coin_toss(sample):
                files_to_compile.append((src_path, bin_path))

        info("Compiling all the code")
        parallel_subprocess(
            files_to_compile,
            jobs,
            lambda r: compile_one_file(r, lang=self.lang),
            on_exit,
        )

    def remove_comments(self, text: str) -> str:
        # https://stackoverflow.com/questions/241327/remove-c-and-c-comments-using-python
        def replacer(match):
            s = match.group(0)
            if s.startswith("/"):
                return " "  # note: a space and not an empty string
            else:
                return s

        if self.lang in ["C/C++", "Java"]:
            pattern = re.compile(
                r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
                re.DOTALL | re.MULTILINE,
            )
        else:
            error("language not supported for removing comments")

        return re.sub(pattern, replacer, text)

    def fuzz(
        self,
        jobs: int = CORES,
        timeout=60,
        seeds="seeds",
        on_exit=None,
        sample=100,
        fuzzed=None,
    ):
        """
        Fuzz the program
        """
        if fuzzed is None:
            fuzzed = lambda out_path: ExprimentInfo(out_path).sufficiently_fuzzed()
        self.mkdir_if_doesnt_exist(self.outdir)
        bins_to_fuzz: List[Tuple[str, str]] = []
        info("Collecting binaries to fuzz")
        for i in tqdm(self.problems):
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
            lambda r: fuzz_one_file(r, timeout=timeout, seeds=seeds, lang=self.lang),
            on_exit,
        )

    def postprocess(self, jobs: int = CORES, sample=100, timeout="1m"):
        """
        Run the program with fuzzing inputs
        """
        bins_to_run: List[Tuple[str, str, str, str]] = []

        info("Collecting binaries to run")
        for i in tqdm(self.problems):
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
        timeout_info = parallel_subprocess(
            bins_to_run,
            jobs,
            lambda r: run_one_file(r, self.lang, timeout=timeout),
            on_exit=None,
        )

    def get_paths(self, i, p) -> Tuple[str, str]:
        bin_path = path.join(self.bindir, str(i), str(p))
        fuzz_out = path.join(self.outdir, str(i), str(p))

        if self.lang == "Java":
            bin_path += ".class"
            fuzz_out += ".class"
        elif self.lang == "Python":
            bin_path += ".py"
            fuzz_out += ".py"

        return bin_path, fuzz_out

    def summarize(self):
        num_programs = 0
        num_built = 0
        num_fuzzed = 0
        num_sufficiently_fuzzed = 0
        info("Summarizing dataset result")
        for (i, p) in self.for_all_src():
            bin_path, fuzz_out = self.get_paths(i, p)
            num_programs += 1
            if path.isfile(bin_path):
                num_built += 1
                expr = ExprimentInfo(fuzz_out)
                if expr.fuzzed:
                    num_fuzzed += 1
                    num_sufficiently_fuzzed += 1 if expr.bitmap_cvg > 40 else 0
        print(
            f"""
            Number of programs in the dataset: {num_programs} (100.0%)
            Number of programs compiled: {num_built} ({num_built / num_programs * 100:.2f}%)
            Number of programs fuzzed: {num_fuzzed} ({num_fuzzed / num_programs * 100:.2f}%)
            Number of programs reached above 40% coverage: {num_sufficiently_fuzzed} ({num_sufficiently_fuzzed / num_programs * 100:.2f}%)
        """
        )

    def fix(self, errfile: str, jobs: int = CORES, on_exit=None):
        warning("Fix strategy not implemented")


class POJ104(DataSet):
    def __init__(self, workdir):
        DataSet.__init__(self, workdir, "ProgramData", "C/C++")
        self.format_list: List[str] = [
            f"{self.txtdir}/{file_id}.txt" for file_id in POJ104_FORMAT_LIST
        ]

    def download(self):
        if path.isdir(self.txtdir):
            return
        cur_path = os.getcwd()
        info("Downloading dataset repo.")
        os.system("git clone https://github.com/microsoft/CodeXGLUE.git .CodeXGLUE")
        os.system(
            f"ln -s .CodeXGLUE/Code-Code/Clone-detection-POJ-104/dataset/ {self.workdir}"
        )
        os.chdir(path.join(cur_path, self.workdir))
        info("Downloading dataset, may take a while.")
        os.system("gdown https://drive.google.com/uc?id=0B2i-vWnOu7MxVlJwQXN6eVNONUU")
        info("Extracting dataset.")
        os.system("tar -xvf programs.tar.gz")
        # Not good but import it doesn't really work
        exec(open("preprocess.py").read())
        os.chdir(cur_path)

    def preprocess_all(self):
        if not path.isdir(self.txtdir):
            warning(f"{self.txtdir} doesn't exist yet.")
            self.download()
        self.mkdir_if_doesnt_exist(self.srcdir)
        info("Preprocessing text files into codes")
        for i in tqdm(self.problems):
            for p in os.listdir(path.join(self.txtdir, str(i))):
                p = path.splitext(p)[0]
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

            code = self.remove_comments(code)
            code = replace_file(code, ENCODE_INPUT)
            # sed -i 's/void main/int main/g' $SRCDIR/$P.cpp
            code = code.replace("void main", "int main")
            f.write(code)

    def fix(self, errfile: str, jobs: int = CORES, on_exit=None):
        # apply fix scripts
        set_global_DIR(self.txtdir, self.srcdir)

        with open(errfile, "r") as f:
            lines = []
            lines_in_file = f.readlines()
            info("Converting stderr into CompilerReport")
            for line in tqdm(lines_in_file):
                lines.append(line[:-1])
                if "generated." in line:
                    cr = CompilerReport(lines)
                    for r in cr.error_list:
                        for strategy in FIX_STRATEGIES:
                            if strategy.isMatch(r, cr):
                                strategy.fix(cr.get_path(), r, cr)
                    lines = []
                    write_fixed_file(cr.get_path()[1])
        self.build(jobs=jobs)


class IBM(DataSet):
    SUBSET = ["C++1000", "C++1400", "Python800", "Java250"]

    def __init__(self, workdir, subset):
        self.subset = subset
        if subset not in IBM.SUBSET:
            error(f"Incorrect subset given, only {IBM.SUBSET} allowed.")
            exit(1)
        DataSet.__init__(self, workdir, self.get_subset_name(), self.get_lang())

    def get_subset_name(self):
        return f"Project_CodeNet_{self.subset}"

    def get_lang(self):
        if self.subset in ["C++1000", "C++1400"]:
            return "C/C++"
        elif self.subset == "Python800":
            return "Python"
        elif self.subset == "Java250":
            return "Java"
        else:
            unreachable("No language specified.")

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


class IBMPython800(IBM):
    def __init__(self, workdir, subset):
        IBM.__init__(self, workdir, subset)

    def preprocess_one(self, txt_path, src_path):
        with open(src_path, "w") as f:
            f.writelines(["import afl\n", "afl.init()\n", "import os\n"])
            with open(txt_path, "r", errors="replace") as txt:
                code = txt.read()
                f.write(code)
            f.writelines(["\nos._exit(0)\n"])

    def preprocess_all(self):
        if not path.isdir(self.txtdir):
            warning(f"{self.txtdir} doesn't exist yet.")
            self.download()
        self.mkdir_if_doesnt_exist(self.srcdir)
        info("Preprocessing text files into codes")
        for i in tqdm(self.problems):
            for p in os.listdir(path.join(self.txtdir, str(i))):
                p = path.splitext(p)[0]
                txt_path = path.join(self.txtdir, str(i), str(p) + ".py")
                src_path = path.join(self.srcdir, str(i), str(p) + ".py")
                if not path.isfile(src_path):
                    self.preprocess_one(txt_path, src_path)

    def build(self, jobs: int = CORES, on_exit=None, sample=100, built=None):
        if not path.isdir(self.srcdir):
            warning(f"{self.srcdir} doesn't exist yet, preprocessing first.")
            self.preprocess_all()
        info(f"Python code doesn't need to be compiled, using symlink to {self.srcdir}")
        # By default there is no preprocessing.
        os.symlink(self.srcdir, self.bindir)


def instrument_one_dir_java(p: Tuple[str, str]):
    bin_dir, bin_instrumented_dir = p
    return subprocess.Popen(
        [
            "java",
            "-cp",
            f"{KELINCI}/instrumentor/build/libs/kelinci.jar",
            "edu.cmu.sv.kelinci.instrumentor.Instrumentor",
            "-i",
            bin_dir,
            "-o",
            bin_instrumented_dir,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def fuzz_one_file_java(p: Tuple[str, str, str], timeout: int, seeds: str):
    # bind a free port
    port = get_local_open_port()

    bin_instrumented_dir, class_name, out = p

    start_kelinci_server = [
        "java",
        "-cp",
        bin_instrumented_dir,
        "edu.cmu.sv.kelinci.Kelinci",
        "--port",
        port,
        class_name,
        "@@",
    ]
    run_afl = [
        f"{AFL}/afl-fuzz",
        "-D",
        "-V",
        str(timeout),
        "-i",
        seeds,
        "-o",
        out,
        "-t",
        "50",
        f"{KELINCI}/fuzzerside/interface",
        "@@",
    ]
    server = subprocess.Popen(
        start_kelinci_server,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    process = subprocess.Popen(
        run_afl,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Sleep half a second for AFL to bind core.
    subprocess.run(["sleep", "0.5"])
    return server, process


class IBMJava250(IBM):
    def __init__(self, workdir):
        IBM.__init__(self, workdir, "Java250")
        self.instdir = path.join(self.workdir, "instrumented")

    def preprocess_all(self):
        if not path.isdir(self.txtdir):
            warning(f"{self.txtdir} doesn't exist yet.")
            self.download()
        self.mkdir_if_doesnt_exist(self.srcdir)
        info("Preprocessing text files into codes")
        for i in tqdm(self.problems):
            for p in os.listdir(path.join(self.txtdir, str(i))):
                txt_path = path.join(self.txtdir, str(i), str(p))
                src_path = path.join(self.srcdir, str(i), str(p))
                if not path.isfile(src_path):
                    class_name = p.split(".java")[-2]
                    self.preprocess_one(txt_path, src_path, class_name)

    def preprocess_one(self, txt_path, src_path, class_name):
        with open(src_path, "w") as f:
            with open(txt_path, "r") as txt:
                code = txt.read()
            code = self.remove_comments(code)
            code = code.replace("Main", class_name)
            f.write(code)

    def build(self, jobs: int = CORES, on_exit=None, sample=100, built=None):
        if built is None:
            built = lambda bin_path: path.isfile(bin_path)

        self.mkdir_if_doesnt_exist(self.bindir)
        self.mkdir_if_doesnt_exist(self.instdir)
        # Copy the files and do some preprocessing
        files_to_compile: List[Tuple[str, str]] = []
        dirs_to_instrument: Set[Tuple[str, str]] = set()

        info("Collecting codes to compile")

        for (i, p) in self.for_all_src():
            if path.isdir(os.path.abspath(p)):
                warning(f"{i}/{p} is a dir, is the dataset correct?")
            src_path = path.join(self.srcdir, str(i), str(p) + ".java")
            bin_dir = path.join(self.bindir, str(i))
            bin_path = path.join(bin_dir, str(p) + ".class")
            inst_dir = path.join(self.instdir, str(i))
            if not built(bin_path) and coin_toss(sample):
                files_to_compile.append((src_path, bin_dir))
                dirs_to_instrument.add((bin_dir, inst_dir))

        info("Compiling all the code")
        parallel_subprocess(
            files_to_compile,
            jobs,
            lambda r: compile_one_file(r, self.lang),
            on_exit=on_exit,
        )
        info("Instrumenting all the code")
        parallel_subprocess(
            dirs_to_instrument, jobs, instrument_one_dir_java, on_exit=None
        )

    def fuzz(
        self,
        jobs: int = CORES,
        timeout=60,
        seeds="seeds",
        on_exit=None,
        sample=100,
        fuzzed=None,
    ):
        """
        Fuzz the program
        """
        if fuzzed is None:
            fuzzed = lambda out_path: ExprimentInfo(out_path).sufficiently_fuzzed()
        self.mkdir_if_doesnt_exist(self.outdir)
        bins_to_fuzz: List[Tuple[str, str, str]] = []
        info("Collecting binaries to fuzz")
        for i in tqdm(self.problems):
            for p in os.listdir(path.join(self.bindir, str(i))):
                if path.isdir(os.path.abspath(p)):
                    warning(f"{i}/{p} is a dir, is the dataset correct?")
                bin_dir = path.join(self.instdir, str(i))
                class_name = p.split(".class")[0]
                out_path = path.join(self.outdir, str(i), p)
                if (
                    path.isfile(path.join(bin_dir, str(p)))
                    and not fuzzed(out_path)
                    and coin_toss(sample)
                    and "$" not in class_name
                ):
                    bins_to_fuzz.append((bin_dir, class_name, out_path))

        seeds = path.abspath(seeds)
        info(f"Fuzzing all {len(bins_to_fuzz)} binaries")
        parallel_subprocess_pair(
            bins_to_fuzz,
            jobs,
            lambda r: fuzz_one_file_java(r, timeout=timeout, seeds=seeds),
            on_exit,
        )


def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="Build a dataset")
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        choices=["POJ104", "C++1400", "C++1000", "Python800", "Java250"],
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
            "fix",
            "fuzz",
            "postprocess",
            "summarize",
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
        "-ft", "--fuzztime", type=str, help="Time to fuzz one program", default="1m"
    )
    parser.add_argument(
        "-st",
        "--singletime",
        type=str,
        help="Time to run one single program",
        default="1m",
    )
    parser.add_argument(
        "-i", "--seeds", type=str, help="Seeds to initialize fuzzing", default="seeds"
    )
    parser.add_argument(
        "-r",
        "--range",
        type=str,
        help="A string of python iterable object, or None",
        default="None",
    )
    parser.add_argument("--encode", action="store_true")
    parser.add_argument("--no-encode", dest="encode", action="store_false")
    parser.set_defaults(encode=False)

    args = parser.parse_args()
    workdir = args.workdir if args.workdir != "" else args.dataset

    if path.exists(workdir):
        warning(f"{workdir} exists")

    if args.sample <= 0 or args.sample > 100:
        error("Sample rate has to be confined between 1 and 100")
    
    global ENCODE_INPUT
    ENCODE_INPUT = args.encode

    dataset = None
    if args.dataset == "POJ104":
        dataset = POJ104(workdir)
    # Keep the elif chain in case any dataset needs special handling
    elif args.dataset in ["C++1400", "C++1000"]:
        dataset = IBM(workdir, args.dataset)
    elif args.dataset == "Python800":
        dataset = IBMPython800(workdir, args.dataset)
    elif args.dataset == "Java250":
        dataset = IBMJava250(workdir)
    else:
        unreachable("No dataset provided.")

    def convert_to_seconds(s: str) -> int:
        seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return int(s[:-1]) * seconds_per_unit[s[-1]]

    args.fuzztime = convert_to_seconds(args.fuzztime)
    dataset.set_problems(args.range)

    if args.pipeline == "all":
        dataset.download()
        dataset.update_problems()
        dataset.preprocess_all()
        dataset.build(jobs=args.jobs, sample=args.sample)
        dataset.fix(args.errfile, jobs=args.jobs)
        dataset.fuzz(jobs=args.jobs, timeout=args.fuzztime, seeds=args.seeds)
        dataset.postprocess(jobs=args.jobs, timeout=args.singletime)
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
            jobs=args.jobs, timeout=args.fuzztime, seeds=args.seeds, sample=args.sample
        )
    elif args.pipeline == "postprocess":
        dataset.postprocess(jobs=args.jobs, timeout=args.singletime, sample=args.sample)
    elif args.pipeline == "summarize":
        dataset.summarize()
    elif args.pipeline == "fix":
        dataset.fix(args.errfile, jobs=args.jobs)
    else:
        unreachable("Unkown pipeline provided")


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    main()
