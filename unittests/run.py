#!/usr/bin/env python
# Apache License 2.0
#
# Copyright (c) 2026 Róbert Malovec
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os
import shutil
import sys
from contextlib import suppress
from os.path import abspath, dirname

from pytest import main as py_main

CURRENT_DIR = dirname(abspath(__file__))
OUTPUT_DIR = "results_unit"
sys.path.insert(0, "unittest/test/")


def recreate_output_dir(output_dir):
    """
    Recreates output directory.
    :param output_dir: The output directory path.
    """
    with suppress(FileNotFoundError):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)


def argument_parser():
    """
    Builder of an argument parser object.
    :return: parser object
    """
    parser = argparse.ArgumentParser(description="SeleniumLibrary Grid Downloader Plugin Unit Testing.")
    parser.add_argument("-o", "--output", help="Unit Testing output directory.")
    return parser


def run_unit_tests():
    """
    Unit tests executor.
    """
    args = vars(argument_parser().parse_args())
    results_directory = args["output"] or OUTPUT_DIR
    recreate_output_dir(results_directory)
    output_file = os.path.join(results_directory, "report.xml")
    try:
        result = py_main(
            [
                f"--rootdir={CURRENT_DIR}",
                "-p",
                "no:cacheprovider",
                f"--junitxml={output_file}",
                CURRENT_DIR,
            ]
        )
    finally:
        sys.path.pop(0)
    return result


if __name__ == "__main__":
    sys.exit(run_unit_tests())
