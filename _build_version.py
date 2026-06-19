import re
from pathlib import Path

_CHANGES = Path(__file__).with_name("CHANGES")
_VERSION_LINE = re.compile(r"^\s*(?P<version>[^,\s]+)\s*,")


def read_version(changes_path=_CHANGES):
    for line in Path(changes_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = _VERSION_LINE.match(line)
        if not match:
            raise ValueError(f"Unable to parse package version from CHANGES line: {line!r}")
        return match.group("version")
    raise ValueError("Unable to parse package version from CHANGES: file is empty")


__version__ = read_version()
