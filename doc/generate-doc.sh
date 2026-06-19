#!/bin/bash
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

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
output_path="${1:-${repo_dir}/docs/index.html}"

mkdir -p "$(dirname "${output_path}")"
python -m robot.libdoc --name "SeleniumLibrary Grid Downloader Plugin" "SeleniumLibrary::plugins=GridDownloader" "${output_path}"

# Libdoc embeds the Python runtime, OS, and absolute source paths in the HTML.
# It also writes a generation timestamp. Normalize those fields so docs do not
# change when the CI image, local checkout path, or generation time changes.
perl -0pi -e '
  s#<meta content="Robot Framework [^"]+" name="Generator">#<meta content="Robot Framework libdoc" name="Generator">#g;
  s#("generated": ")[^"]+(")#$1$2#g;
  s#("source": ")[^"]*/site-packages/(SeleniumLibrary/[^"]+")#$1$2#g;
  s#("source": ")[^"]*/(GridDownloader/GridDownloader\.py")#$1$2#g;
' "${output_path}"
