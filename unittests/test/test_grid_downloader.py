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

import base64
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from robot.libraries.BuiltIn import RobotNotRunningError
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.remote.command import Command
from SeleniumLibrary.keywords.browsermanagement import BrowserManagementKeywords

from GridDownloader import GridDownloader


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.driver = MagicMock()
    return context


@pytest.fixture
def grid_downloader(mock_context):
    return GridDownloader(mock_context, activate_capability="Yes")


@pytest.fixture
def grid_downloader_capability_disabled(mock_context):
    return GridDownloader(mock_context, activate_capability="No")


def _download_response(file_name="file.txt", content=b"Hello world\n", zip_member_name=None):
    zip_member_name = zip_member_name or file_name
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(zip_member_name, content)
    return {"value": {"filename": file_name, "contents": base64.b64encode(zip_buffer.getvalue()).decode("ascii")}}


def test_initialization_uses_robot_truthy_values(mock_context):
    assert GridDownloader(mock_context, activate_capability="Yes").force_download_capability is True
    assert GridDownloader(mock_context, activate_capability="true").force_download_capability is True
    assert GridDownloader(mock_context, activate_capability="No").force_download_capability is False
    assert GridDownloader(mock_context, activate_capability="0").force_download_capability is False


def test_browser_initialization(grid_downloader):
    assert grid_downloader.browser is not None
    assert isinstance(grid_downloader.browser, BrowserManagementKeywords)
    assert grid_downloader.output_dir


def test_get_rf_output_dir_robot_running(grid_downloader):
    with patch("robot.libraries.BuiltIn.BuiltIn.get_variable_value", return_value="/robot/output"):
        assert grid_downloader._get_rf_output_dir() == "/robot/output"


def test_get_rf_output_dir_robot_not_running(grid_downloader):
    with (
        patch("robot.libraries.BuiltIn.BuiltIn.get_variable_value", side_effect=RobotNotRunningError),
        patch("os.getcwd", return_value="/current/dir"),
    ):
        assert grid_downloader._get_rf_output_dir() == os.getcwd()


@patch("SeleniumLibrary.keywords.browsermanagement.BrowserManagementKeywords.open_browser")
def test_open_browser_adds_download_capability_when_options_are_missing(mock_open_browser, grid_downloader):
    mock_open_browser.return_value = "1"

    index = grid_downloader.open_browser("https://selenium.dev", browser="chrome")

    assert index == "1"
    assert mock_open_browser.call_args.kwargs["options"] == "enable_downloads=True"


@patch("SeleniumLibrary.keywords.browsermanagement.BrowserManagementKeywords.open_browser")
def test_open_browser_appends_download_capability_to_string_options(mock_open_browser, grid_downloader):
    mock_open_browser.return_value = "1"

    grid_downloader.open_browser("https://selenium.dev", browser="chrome", options='platform_name="WINDOWS"')

    assert mock_open_browser.call_args.kwargs["options"] == 'platform_name="WINDOWS";enable_downloads=True'


@patch("SeleniumLibrary.keywords.browsermanagement.BrowserManagementKeywords.open_browser")
def test_open_browser_does_not_duplicate_existing_download_capability(mock_open_browser, grid_downloader):
    options = 'platform_name="WINDOWS";set_capability("se:downloadsEnabled", True)'

    grid_downloader.open_browser("https://selenium.dev", browser="chrome", options=options)

    assert mock_open_browser.call_args.kwargs["options"] == options


@patch("SeleniumLibrary.keywords.browsermanagement.BrowserManagementKeywords.open_browser")
def test_open_browser_sets_download_capability_on_selenium_options_object(mock_open_browser, grid_downloader):
    options = ChromeOptions()

    grid_downloader.open_browser("https://selenium.dev", browser="chrome", options=options)

    assert mock_open_browser.call_args.kwargs["options"] is options
    assert options.capabilities["se:downloadsEnabled"] is True


@patch("SeleniumLibrary.keywords.browsermanagement.BrowserManagementKeywords.open_browser")
def test_open_browser_leaves_options_unchanged_when_capability_activation_is_disabled(
    mock_open_browser, grid_downloader_capability_disabled
):
    grid_downloader_capability_disabled.open_browser(
        "https://selenium.dev", browser="chrome", options='platform_name="WINDOWS"'
    )

    assert mock_open_browser.call_args.kwargs["options"] == 'platform_name="WINDOWS"'


def test_get_list_of_downloaded_files_success(grid_downloader, mock_context):
    mock_context.driver.get_downloadable_files.return_value = ["file1.txt", "file2.txt"]

    assert grid_downloader.get_list_of_downloaded_files() == ["file1.txt", "file2.txt"]
    mock_context.driver.get_downloadable_files.assert_called_once_with()


def test_get_list_of_downloaded_files_failure(grid_downloader, mock_context):
    mock_context.driver.get_downloadable_files.side_effect = WebDriverException("downloads not enabled")

    with pytest.raises(AssertionError, match="Failed to get list of downloaded files"):
        grid_downloader.get_list_of_downloaded_files()


def test_delete_downloaded_files_from_grid(grid_downloader, mock_context):
    grid_downloader.delete_downloaded_files_from_grid()

    mock_context.driver.delete_downloadable_files.assert_called_once_with()


def test_delete_downloaded_files_from_grid_failure(grid_downloader, mock_context):
    mock_context.driver.delete_downloadable_files.side_effect = WebDriverException("downloads not enabled")

    with pytest.raises(AssertionError, match="Failed to delete downloaded files"):
        grid_downloader.delete_downloaded_files_from_grid()


def test_download_file_from_grid_uses_selenium_command_and_saves_content(grid_downloader, mock_context, tmp_path):
    mock_context.driver.execute.return_value = _download_response()

    content = grid_downloader.download_file_from_grid("file.txt", save_path=tmp_path)

    assert content == b"Hello world\n"
    assert (tmp_path / "file.txt").read_bytes() == b"Hello world\n"
    mock_context.driver.execute.assert_called_once_with(Command.DOWNLOAD_FILE, {"name": "file.txt"})


def test_download_file_from_grid_creates_save_directory(grid_downloader, mock_context, tmp_path):
    save_path = tmp_path / "downloads"
    mock_context.driver.execute.return_value = _download_response()

    grid_downloader.download_file_from_grid("file.txt", save_path=save_path)

    assert (save_path / "file.txt").exists()


def test_download_file_from_grid_reports_missing_file(grid_downloader, mock_context, tmp_path):
    mock_context.driver.execute.side_effect = WebDriverException("Cannot find file")

    with pytest.raises(AssertionError, match="File not found"):
        grid_downloader.download_file_from_grid("missing.txt", save_path=tmp_path)


def test_download_file_from_grid_rejects_unsafe_zip_paths(grid_downloader, mock_context, tmp_path):
    mock_context.driver.execute.return_value = _download_response(file_name="evil.txt", zip_member_name="../evil.txt")

    with pytest.raises(AssertionError, match="unsafe downloaded file path"):
        grid_downloader.download_file_from_grid("evil.txt", save_path=tmp_path / "downloads")

    assert not (tmp_path / "evil.txt").exists()


def test_download_file_from_grid_reports_unexpected_response(grid_downloader, mock_context, tmp_path):
    mock_context.driver.execute.return_value = {"value": {}}

    with pytest.raises(AssertionError, match="unexpected response"):
        grid_downloader.download_file_from_grid("file.txt", save_path=tmp_path)


def test_download_file_from_grid_reports_invalid_contents(grid_downloader, mock_context, tmp_path):
    mock_context.driver.execute.return_value = {"value": {"contents": "not-valid-base64"}}

    with pytest.raises(AssertionError, match="invalid file contents"):
        grid_downloader.download_file_from_grid("file.txt", save_path=tmp_path)


def test_wait_until_file_is_available_to_download_supports_robot_time_strings(grid_downloader):
    with (
        patch.object(grid_downloader, "get_list_of_downloaded_files", side_effect=[[], ["file.txt"]]),
        patch("GridDownloader.GridDownloader.sleep") as mock_sleep,
    ):
        grid_downloader.wait_until_file_is_available_to_download(
            "file.txt", timeout="5 seconds", wait_step="0.1 seconds"
        )

    mock_sleep.assert_called_once()


def test_wait_until_file_is_available_to_download_reports_available_files(grid_downloader):
    with (
        patch.object(grid_downloader, "get_list_of_downloaded_files", return_value=["other.txt"]),
        pytest.raises(AssertionError, match=r"Downloaded files: \['other.txt'\]"),
    ):
        grid_downloader.wait_until_file_is_available_to_download(
            "file.txt", timeout="0.01 seconds", wait_step="0.01 seconds"
        )


def test_wait_until_file_is_available_to_download_rejects_zero_wait_step(grid_downloader):
    with pytest.raises(ValueError, match="wait_step must be greater than zero"):
        grid_downloader.wait_until_file_is_available_to_download("file.txt", wait_step=0)


def test_libdoc_exposes_plugin_keywords_with_stable_open_browser_signature(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    libdoc_json = tmp_path / "libdoc.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robot.libdoc",
            "--format",
            "JSON",
            "SeleniumLibrary::plugins=GridDownloader",
            str(libdoc_json),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(libdoc_json.read_text())
    keywords = {keyword["name"]: keyword for keyword in data["keywords"]}

    assert "Download File From Grid" in keywords
    assert "Delete Downloaded Files From Grid" in keywords
    assert "Wait Until File Is Available To Download" in keywords
    assert [arg["name"] for arg in keywords["Open Browser"]["args"][:4]] == ["url", "browser", "alias", "remote_url"]
    assert all(arg["kind"] != "VAR_POSITIONAL" for arg in keywords["Open Browser"]["args"])
