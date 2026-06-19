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

import os
import shutil
from contextlib import suppress


class Utils:
    """
    Unit testing utility class.
    """

    @staticmethod
    def create_directory(directory):
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def delete_directory(directory):
        with suppress(FileNotFoundError):
            shutil.rmtree(directory)

    @staticmethod
    def create_file(directory, file_name):
        Utils.create_directory(directory)
        with open(os.path.join(directory, file_name), "w") as file:
            file.write("test")

    @staticmethod
    def remove_file(filename):
        if os.path.exists(filename):
            os.remove(filename)
