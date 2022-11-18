# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Class for parsing and rendering a navigation table."""

import typing
import re

from .exceptions import NavigationTableParseError


_WHITESPACE = r"\s*"
_TABLE_HEADER_REGEX = (
    r"\|"
    rf"{_WHITESPACE}level{_WHITESPACE}\|"
    rf"{_WHITESPACE}path{_WHITESPACE}\|"
    rf"{_WHITESPACE}navlink{_WHITESPACE}\|"
)
_TABLE_HEADER_PATTERN = re.compile(_TABLE_HEADER_REGEX, re.IGNORECASE)
_TABLE_PATTERN = re.compile(rf"[\s\S]*{_TABLE_HEADER_REGEX}[\s\S]*\|?", re.IGNORECASE)
_FILLER_ROW_REGEX_COLUMN = rf"{_WHITESPACE}-+{_WHITESPACE}\|"
_FILLER_ROW_PATTERN = re.compile(rf"\|{_FILLER_ROW_REGEX_COLUMN * 3}")
_LEVEL_REGEX = rf"{_WHITESPACE}(\d+){_WHITESPACE}"
_PATH_REGEX = rf"{_WHITESPACE}([\w-]+){_WHITESPACE}"
_NAVLINK_TITLE_REGEX = r"[\w\- ]+?"
_NAVLINK_LINK_REGEX = r"[\w\/-]*"
_NAVLINK_REGEX = (
    rf"{_WHITESPACE}\[{_WHITESPACE}({_NAVLINK_TITLE_REGEX}){_WHITESPACE}\]{_WHITESPACE}"
    rf"\({_WHITESPACE}({_NAVLINK_LINK_REGEX}){_WHITESPACE}\){_WHITESPACE}"
)
_ROW_PATTERN = re.compile(rf"{_WHITESPACE}\|{_LEVEL_REGEX}\|{_PATH_REGEX}\|{_NAVLINK_REGEX}\|")


class Navlink(typing.NamedTuple):
    """Represents navlink of a table row of the navigation table.

    Attrs:
        title: The title of the documentation page.
        link: The relative URL to the documentation page or None if there is no link.
    """

    title: str
    link: str | None


class TableRow(typing.NamedTuple):
    """Represents one parsed row of the navigation table.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the row.
        navlink: The title and relative URL to the documentation page.
    """

    level: int
    path: str
    navlink: Navlink


def _filter_line(line: str) -> bool:
    """Check whether a line should be parsed.

    Args:
        line: The line to check.

    Returns:
        Whether the line should be parsed.
    """
    if _TABLE_HEADER_PATTERN.match(line) is not None:
        return True
    if _FILLER_ROW_PATTERN.match(line) is not None:
        return True
    if _ROW_PATTERN.match(line) is not None:
        return False
    return True


def _line_to_row(line: str) -> TableRow:
    """Parse a markdown table line.

    Args:
        line: The line to process.

    Returns:
        The parsed row.

    Raises:
        NavigationTableParseError: if no match is found for the line.
    """
    match = _ROW_PATTERN.match(line)

    if match is None:
        raise NavigationTableParseError(f"Invalid table row, {line=!r}")

    level = int(match.group(1))
    path = match.group(2)
    navlink_title = match.group(3)
    navlink_link = match.group(4)

    return TableRow(
        level=level,
        path=path,
        navlink=Navlink(title=navlink_title, link=navlink_link if navlink_link else None),
    )


def from_page(page: str) -> list[TableRow]:
    """Create an instance based on a markdown page.

    Algorithm:
        1.  Extract the table based on a regular expression looking for a 3 column table with
            the headers level, path and navlink (case insensitive). If the table is not found,
            assume that it is equivalent to a table without rows.
        2.  Process the rows line by line:
            2.1. If the row matches the header or filler pattern, skip it.
            2.2. Extract the level, path and navlink values.

    Args:
        page: The page to extract the rows from.

    """
    match = _TABLE_PATTERN.match(page)

    if match is None:
        return []

    table = match.group(0)
    return [_line_to_row(line) for line in table.splitlines() if not _filter_line(line)]
