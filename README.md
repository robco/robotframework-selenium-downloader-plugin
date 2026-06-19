[![Python Package CI](https://github.com/robco/robotframework-selenium-downloader-plugin/actions/workflows/python-package.yml/badge.svg)](https://github.com/robco/robotframework-selenium-downloader-plugin/actions/workflows/python-package.yml)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/robco)
[Support via Revolut](https://revolut.me/robco)

# SeleniumLibrary Grid Downloader Plugin

[![Robot Framework](https://img.shields.io/badge/Robot%20Framework-7.4.2%2B-brightgreen)](https://robotframework.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

GridDownloader is a SeleniumLibrary plugin for Robot Framework that retrieves files downloaded by a remote browser running on Selenium Grid.

It uses Selenium Grid managed downloads and Selenium Python's command executor, so Grid URL paths, authentication, proxies, TLS, and session handling stay aligned with Selenium itself.

## Requirements

- Python 3.10 or newer
- Robot Framework 7.4.2 or newer
- SeleniumLibrary 6.9.0 or newer
- Selenium 4.29.0 through 4.44.x, matching the SeleniumLibrary 6.9.0 supported range
- Selenium Grid 4 with managed downloads enabled on the Node:

```bash
java -jar selenium-server-<version>.jar node --enable-managed-downloads true
```

Selenium Grid managed downloads currently support Chrome, Edge, and Firefox. Files must be listed or downloaded while the browser session is still active because Grid cleans the session download directory when the session ends.

## Install

```bash
pip install -U robotframework-grid-downloader-plugin
```

## Keywords Documentation

Keywords documentation can be found [here](https://robco.github.io/robotframework-selenium-downloader-plugin/).

## Example Usage

```robotframework
*** Settings ***
Library   SeleniumLibrary  plugins=GridDownloader
Test Teardown  Close All Browsers

*** Variables ***
${BROWSER}           chrome
${URL}               https://www.example.com
${OPTIONS}           platform_name="windows"
${GRID_URL}          http://grid.example.com:4444/wd/hub
${DOWNLOAD_LINK}     xpath=//a[@id='download']
${FILENAME}          file1.txt
${EXPECTED_CONTENT}  Hello World

*** Test Cases ***
Download File And Check Content
    Open Browser    ${URL}    ${BROWSER}    remote_url=${GRID_URL}    options=${OPTIONS}
    Click Element   ${DOWNLOAD_LINK}
    Wait Until File Is Available To Download    ${FILENAME}    timeout=30 seconds    wait_step=1 second
    @{downloaded_files}=    Get List Of Downloaded Files
    Should Contain    ${downloaded_files}    ${FILENAME}
    ${content}=    Download File From Grid    ${FILENAME}
    ${content_text}=    Evaluate    $content.decode("utf-8")
    Should Be Equal As Strings    ${content_text}    ${EXPECTED_CONTENT}
    Delete Downloaded Files From Grid
```

## Capability Activation

By default, the plugin wraps SeleniumLibrary's `Open Browser` keyword and adds `se:downloadsEnabled=True` to Selenium options.

Automatic activation can be disabled:

```robotframework
Library   SeleniumLibrary  plugins=GridDownloader;activate_capability=No
```

When activation is disabled, set the capability yourself:

```robotframework
${OPTIONS}    enable_downloads=True
Open Browser    ${URL}    chrome    remote_url=${GRID_URL}    options=${OPTIONS}
```

## Keywords

- `Get List Of Downloaded Files` returns file names available for the active Grid session.
- `Wait Until File Is Available To Download` polls the Grid session until the named file is available.
- `Download File From Grid` downloads the file to Robot Framework's output directory by default and returns its bytes.
- `Delete Downloaded Files From Grid` removes downloadable files for the active Grid session.
