import argparse
import os
from typing import List


def classify(path):
    pass


def main():
    parser = argparse.ArgumentParser(description="Decrypt compiler error messages.")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="./seeds/",
        help="The directory containing input seeds, default to ./seeds",
    )


if __name__ == "__main__":
    main()
