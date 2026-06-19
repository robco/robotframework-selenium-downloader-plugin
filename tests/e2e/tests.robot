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

*** Settings ***
Documentation     Selenium Library Grid Downloader Plugin e2e tests
Library   OperatingSystem
Library   SeleniumLibrary  plugins=GridDownloader

Test Teardown  Close All Browsers


*** Variables ***
${DOWNLOAD_URL}           https://www.selenium.dev/selenium/web/downloads/download.html
${DOWNLOAD_LINK}          file-1
${FILENAME}               file_1.txt
${EXPECTED_CONTENT}       Hello, World!

${BROWSER}                chrome
${options}                ${EMPTY}
${SELENIUM_GRID_HUB_URL}  https://selenium.grid.com:4444/wd/hub
${WAIT_TIMEOUT}           30 seconds


*** Test Cases ***
Download file from Selenium Grid
   Launch Browser
   Wait Until Element Is Visible  ${DOWNLOAD_LINK}
   Click Element  ${DOWNLOAD_LINK}
   Wait Until File Is Available To Download  ${FILENAME}  timeout=${WAIT_TIMEOUT}  wait_step=1 second
   @{files}=  Get List Of Downloaded Files
   Should Contain  ${files}  ${FILENAME}
   ${content}=  Download File From Grid  ${FILENAME}
   File Should Exist  ${OUTPUT_DIR}${/}${FILENAME}
   ${content_text}=  Evaluate  $content.decode("utf-8").strip()
   Should Be Equal As Strings  ${content_text}  ${EXPECTED_CONTENT}
   Delete Downloaded Files From Grid
   @{files_after_delete}=  Get List Of Downloaded Files
   Should Not Contain  ${files_after_delete}  ${FILENAME}


*** Keywords ***
Launch Browser
   [Documentation]  Start specified browser using remote grid
   Open Browser
   ...  ${DOWNLOAD_URL}
   ...  ${BROWSER}
   ...  remote_url=${SELENIUM_GRID_HUB_URL}
   ...  options=${options}
