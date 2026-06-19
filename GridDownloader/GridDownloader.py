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

"""
This module provides functionalities for downloading files from remote Selenium Grid web testing node.
"""

import base64
import binascii
import io
import os
import zipfile
from time import monotonic, sleep
from typing import Any

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.utils import is_truthy, timestr_to_secs
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.command import Command
from SeleniumLibrary.base import LibraryComponent, keyword
from SeleniumLibrary.keywords.browsermanagement import BrowserManagementKeywords


class GridDownloader(LibraryComponent):
    """
    `GridDownloader` is a SeleniumLibrary Plugin that interacts with a Selenium Grid instance to download files
    from the remote test machine to the local machine.

    It provides functionality to enable file downloads on the remote grid, download files, list files, and wait for
    files to be available for download.

    Selenium Grid nodes must be started with managed downloads enabled:
    | java -jar selenium-server-<version>.jar node --enable-managed-downloads true |

    Files must be downloaded while the browser session is still active.

    == Usage ==

    Example import with automatic download browser capability enablement:
    | ***** Settings *****
    |
    | Library   SeleniumLibrary    plugins=GridDownloader


    Example import without automatic browser capability enablement:
    | ***** Settings *****
    |
    | Library   SeleniumLibrary    plugins=GridDownloader;activate_capability=No

    If automatic download browser capability enablement is disabled you need to set this capability manually
    in your browser options.

    == Example - automatic capability activation ENABLED ==

    | *** Settings ***
    |
    | Library   SeleniumLibrary  plugins=GridDownloader
    |
    | Test Teardown  Close All Browsers
    |
    |
    | *** Variables ***
    |
    | ${BROWSER}        chrome
    | ${URL}            https://www.example.com
    | ${options}        platform_name="windows"
    | ${GRID_URL}       http://grid.com:4444/wd/hub
    | ${DOWNLOAD_LINK}  xpath=//a[@id='download']
    | ${FILENAME}       file1.txt
    |
    | *** Test Cases ***
    |
    | Download File From Grid
    |    Open Browser    ${URL}    ${BROWSER}    remote_url=${GRID_URL}    options=${options}
    |    Click Element   ${DOWNLOAD_LINK}
    |    Wait Until File Is Available To Download  ${FILENAME}
    |    Get List Of Downloaded Files
    |    ${content}=  Download File From Grid  ${FILENAME}
    |    ${content_text}=  Evaluate  $content.decode("utf-8")
    |    Should Be Equal As Strings  ${content_text}  Hello world
    |    Delete Downloaded Files From Grid

    == Example - automatic capability activation DISABLED ==

    | *** Settings ***
    |
    | Library   SeleniumLibrary  plugins=GridDownloader;activate_capability=No
    |
    | Test Teardown  Close All Browsers
    |
    |
    | *** Variables ***
    |
    | ${BROWSER}        chrome
    | ${URL}            https://www.example.com
    | ${options}        platform_name="windows";enable_downloads=True
    | ${GRID_URL}       http://grid.com:4444/wd/hub
    | ${DOWNLOAD_LINK}  xpath=//a[@id='download']
    | ${FILENAME}       file1.txt
    |
    | *** Test Cases ***
    |
    | Download File From Grid
    |    Open Browser    ${URL}    ${BROWSER}    remote_url=${GRID_URL}    options=${options}
    |    Click Element   ${DOWNLOAD_LINK}
    |    Wait Until File Is Available To Download  ${FILENAME}
    |    Get List Of Downloaded Files
    |    ${content}=  Download File From Grid  ${FILENAME}
    |    ${content_text}=  Evaluate  $content.decode("utf-8")
    |    Should Be Equal As Strings  ${content_text}  Hello world
    |    Delete Downloaded Files From Grid
    """

    DOWNLOADS_CAPABILITY = "enable_downloads=True"
    WAIT_TIMEOUT = 30
    WAIT_STEP = 2

    def __init__(self, ctx, activate_capability: str = "Yes"):
        """
        Initializes the GridDownloader library.

        === Arguments details ===

        `ctx`: SeleniumLibrary context.

        `activate_capability`: If set to "Yes", the library will automatically activate the download capability
                                    on the browser.
        """
        LibraryComponent.__init__(self, ctx)
        self.browser = BrowserManagementKeywords(ctx)
        self.output_dir = self._get_rf_output_dir()

        self.force_download_capability = is_truthy(activate_capability)

    @keyword
    def open_browser(
        self,
        url: str | None = None,
        browser: str = "firefox",
        alias: str | None = None,
        remote_url: bool | str = False,
        desired_capabilities: dict | str | None = None,
        ff_profile_dir: Any = None,
        options: Any = None,
        service_log_path: str | None = None,
        executable_path: str | None = None,
        service: Any = None,
    ) -> str:
        """
        Opens a browser using SeleniumLibrary original keyword with the given arguments and enables file downloading
        capability on the Selenium Grid.

        If `activate_capability` is set to "Yes" during initialization, this keyword automatically adds
        the download capability to the browser options.

        SeleniumLibrary *Open Browser* documentation can be seen
        [https://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Open%20Browser|here].

        === Usage examples ===

        | Open Browser | https://www.example.com | chrome | options=platform_name="WINDOWS" |
        """
        if self.force_download_capability:
            options = self._enable_downloads_in_options(options)

        return self.browser.open_browser(
            url=url,
            browser=browser,
            alias=alias,
            remote_url=remote_url,
            desired_capabilities=desired_capabilities,
            ff_profile_dir=ff_profile_dir,
            options=options,
            service_log_path=service_log_path,
            executable_path=executable_path,
            service=service,
        )

    # pylint:disable=too-many-locals
    @keyword
    def download_file_from_grid(self, filename, save_path=None, verify=None):
        """
        Downloads a file from the remote Selenium Grid node to the local machine.

        === Arguments details ===

        `filename`: Name of the file to download.

        `save_path`: Local path where the file should be saved.
                          If not provided, Robot Framework's output directory is used.

        `verify`: Deprecated and ignored. TLS verification is handled by Selenium's command executor.

        === Usage examples ===

        | Download File From Grid | example.txt |
        | Download File From Grid | example.txt | /local/path |
        | ${file_content}=  Download File From Grid | example.txt |
        """
        if not save_path:
            save_path = self._get_rf_output_dir()

        response = self._download_file(filename)
        contents = self._get_download_contents(response, filename)
        saved_file, file_content = self._extract_downloaded_file(contents, filename, save_path)

        logger.info(f"File {saved_file} downloaded successfully.")
        return file_content

    @keyword
    def get_list_of_downloaded_files(self, verify=None):
        """
        Returns a list of downloaded files from the remote Selenium Grid node.

        === Arguments details ===

        `verify`: Deprecated and ignored. TLS verification is handled by Selenium's command executor.

        === Usage examples ===

        | @{files} = | Get List Of Downloaded Files |
        """

        try:
            self._ensure_download_api_available("get_downloadable_files")
            files = self.driver.get_downloadable_files()
            logger.debug(f"List of downloaded files: {files}")
            return files
        except WebDriverException as e:
            logger.debug(f"Failed to get list of downloaded files. Set 'se:downloadsEnabled' capability: {e}")
            raise AssertionError(
                "Failed to get list of downloaded files. Make sure the Selenium Grid node was started with "
                "--enable-managed-downloads true and the browser session has 'se:downloadsEnabled' set to true. "
                f"Original error: {e}"
            ) from e

    @keyword
    def delete_downloaded_files_from_grid(self):
        """
        Deletes all downloadable files for the active Selenium Grid session.

        === Usage examples ===

        | Delete Downloaded Files From Grid |
        """
        try:
            self._ensure_download_api_available("delete_downloadable_files")
            self.driver.delete_downloadable_files()
            logger.info("Downloaded files deleted from Selenium Grid session.")
        except WebDriverException as e:
            logger.debug(f"Failed to delete downloaded files. Set 'se:downloadsEnabled' capability: {e}")
            raise AssertionError(
                "Failed to delete downloaded files. Make sure the Selenium Grid node was started with "
                "--enable-managed-downloads true and the browser session has 'se:downloadsEnabled' set to true. "
                f"Original error: {e}"
            ) from e

    @keyword
    def wait_until_file_is_available_to_download(self, filename, timeout=None, wait_step=None):
        """
        Waits until the file is available to download on the remote Selenium Grid test machine.

        === Arguments details ===

        `filename`: Name of the file to wait for.

        `timeout`: (default is 30 seconds) Maximum time (in seconds) to wait before raising an error.

        `wait_step`: (default is 2 seconds) Time interval (in seconds) between checks.

        === Usage examples ===

        | Wait Until File Is Available To Download | example.txt |
        | Wait Until File Is Available To Download | example.txt | timeout=60 | wait_step=5 |
        """

        timeout = self._to_seconds(timeout, self.WAIT_TIMEOUT, "timeout")
        wait_step = self._to_seconds(wait_step, self.WAIT_STEP, "wait_step")

        deadline = monotonic() + timeout
        downloaded_files = []

        while True:
            downloaded_files = self.get_list_of_downloaded_files()
            if filename in downloaded_files:
                logger.info(f"File {filename} available to download.")
                return

            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleep(min(wait_step, remaining))

        raise AssertionError(
            f"File {filename} was not available to download in {timeout:g} seconds. "
            f"Downloaded files: {downloaded_files}"
        )

    def _enable_downloads_in_options(self, options):
        if options is None:
            return self.DOWNLOADS_CAPABILITY

        if isinstance(options, str):
            if self._downloads_enabled_in_string_options(options):
                return options
            separator = "" if not options.strip() or options.rstrip().endswith(";") else ";"
            return f"{options}{separator}{self.DOWNLOADS_CAPABILITY}"

        if isinstance(options, list):
            return [self._enable_downloads_in_options(option) for option in options]

        if self._downloads_enabled_in_options_object(options):
            return options

        if hasattr(options, "enable_downloads"):
            options.enable_downloads = True
            return options

        if hasattr(options, "set_capability"):
            options.set_capability("se:downloadsEnabled", True)
            return options

        raise TypeError(
            "Cannot activate Selenium Grid downloads for the supplied options object. "
            "Pass Selenium options as a string or as an object supporting 'enable_downloads' or 'set_capability'."
        )

    @staticmethod
    def _downloads_enabled_in_string_options(options):
        return "se:downloadsEnabled" in options or "enable_downloads" in options

    @staticmethod
    def _downloads_enabled_in_options_object(options):
        capabilities = getattr(options, "capabilities", None)
        return isinstance(capabilities, dict) and bool(capabilities.get("se:downloadsEnabled"))

    def _download_file(self, filename):
        try:
            self._ensure_download_api_available("execute")
            return self.driver.execute(Command.DOWNLOAD_FILE, {"name": filename})
        except WebDriverException as e:
            if self._is_file_not_found_error(e):
                raise AssertionError(f"Failed to download {filename}: File not found.") from e
            logger.debug(f"Failed to download {filename}. Set 'se:downloadsEnabled' capability: {e}")
            raise AssertionError(
                f"Failed to download {filename}. Make sure the Selenium Grid node was started with "
                "--enable-managed-downloads true and the browser session has 'se:downloadsEnabled' set to true. "
                f"Original error: {e}"
            ) from e

    @staticmethod
    def _get_download_contents(response, filename):
        try:
            return response["value"]["contents"]
        except (KeyError, TypeError) as e:
            raise AssertionError(
                f"Failed to download {filename}: Selenium Grid returned an unexpected response."
            ) from e

    def _extract_downloaded_file(self, contents, filename, save_path):
        target_dir = os.path.abspath(os.fspath(save_path))
        os.makedirs(target_dir, exist_ok=True)

        try:
            zip_content = base64.b64decode(contents, validate=True)
            with io.BytesIO(zip_content) as zip_buffer, zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                member = self._select_zip_member(zip_ref, filename)
                output_path = self._safe_zip_member_path(target_dir, member.filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with zip_ref.open(member) as unzipped_file:
                    file_content = unzipped_file.read()
                with open(output_path, "wb") as output_file:
                    output_file.write(file_content)
                return output_path, file_content
        except (binascii.Error, TypeError, zipfile.BadZipFile) as e:
            raise AssertionError(f"Failed to download {filename}: Selenium Grid returned invalid file contents.") from e

    @staticmethod
    def _select_zip_member(zip_ref, filename):
        file_members = [member for member in zip_ref.infolist() if not member.is_dir()]
        if not file_members:
            raise AssertionError(f"Failed to download {filename}: Selenium Grid returned an empty archive.")

        for member in file_members:
            if member.filename == filename or member.filename.replace("\\", "/").split("/")[-1] == filename:
                return member

        return file_members[0]

    @staticmethod
    def _safe_zip_member_path(target_dir, member_name):
        output_path = os.path.abspath(os.path.join(target_dir, member_name))
        if os.path.commonpath([target_dir, output_path]) != target_dir:
            raise AssertionError(f"Refusing to extract unsafe downloaded file path: {member_name}")
        return output_path

    def _ensure_download_api_available(self, method_name):
        if not hasattr(self.driver, method_name):
            raise AssertionError(
                "Selenium Grid download support requires Selenium 4 downloadable-file APIs. "
                "Use a current robotframework-seleniumlibrary release with Selenium 4."
            )

    @staticmethod
    def _is_file_not_found_error(error):
        return "cannot find file" in str(error).lower() or "file not found" in str(error).lower()

    @staticmethod
    def _to_seconds(value, default, name):
        seconds = timestr_to_secs(default if value is None else value)
        if seconds < 0:
            raise ValueError(f"{name} must be zero or greater.")
        if name == "wait_step" and seconds == 0:
            raise ValueError("wait_step must be greater than zero.")
        return seconds

    @staticmethod
    def _get_rf_output_dir():
        """
        Returns Robot Framework output directory path
        If Robot Framework is not running, returns the current working directory.
        """
        try:
            output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}")
        except RobotNotRunningError:
            output_dir = os.getcwd()

        return output_dir
