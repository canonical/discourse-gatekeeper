# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for parsing and rendering a navigation table."""

import re
import string
import typing

from . import types_
from .discourse import Discourse
from .exceptions import DiscourseError, NavigationTableParseError, PagePermissionError, ServerError

_WHITESPACE = r"\s*"
_TABLE_HEADER_REGEX = (
    rf"{_WHITESPACE}\|"
    rf"{_WHITESPACE}level{_WHITESPACE}\|"
    rf"{_WHITESPACE}path{_WHITESPACE}\|"
    rf"{_WHITESPACE}navlink{_WHITESPACE}\|{_WHITESPACE}"
)
_TABLE_HEADER_PATTERN = re.compile(_TABLE_HEADER_REGEX, re.IGNORECASE)
_TABLE_PATTERN = re.compile(rf"[\s\S]*{_TABLE_HEADER_REGEX}[\s\S]*\|?", re.IGNORECASE)
_FILLER_ROW_REGEX_COLUMN = rf"{_WHITESPACE}-+{_WHITESPACE}\|"
_FILLER_ROW_PATTERN = re.compile(rf"{_WHITESPACE}\|{_FILLER_ROW_REGEX_COLUMN * 3}{_WHITESPACE}")
_LEVEL_REGEX = rf"{_WHITESPACE}(\d+)?{_WHITESPACE}"
_PATH_REGEX = rf"{_WHITESPACE}([\w-]+){_WHITESPACE}"
_PUNCTUATION = string.punctuation.replace("/", "\\/")
_NAVLINK_TITLE_REGEX = rf"[\w\- {_PUNCTUATION}]+?"
_NAVLINK_LINK_REGEX = r"[\w\/-]*"
_NAVLINK_REGEX = (
    rf"{_WHITESPACE}\[{_WHITESPACE}({_NAVLINK_TITLE_REGEX}){_WHITESPACE}\]{_WHITESPACE}"
    rf"\({_WHITESPACE}({_NAVLINK_LINK_REGEX}){_WHITESPACE}\){_WHITESPACE}"
)
_ROW_PATTERN = re.compile(rf"{_WHITESPACE}\|{_LEVEL_REGEX}\|{_PATH_REGEX}\|{_NAVLINK_REGEX}\|")


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


def _line_to_row(line: str, default_level: int) -> types_.TableRow:
    """Parse a markdown table line.

    Args:
        line: The line to process.
        default_level: The level to use if the row doesn't have one.

    Returns:
        The parsed row.

    Raises:
        NavigationTableParseError: if no match is found for the line.
    """
    match = _ROW_PATTERN.match(line)

    if match is None:
        raise NavigationTableParseError(f"Invalid table row, {line=!r}")

    level = int(match.group(1)) if match.group(1) is not None else default_level
    path: types_.TablePath = (match.group(2),)
    navlink_title = match.group(3)
    navlink_link = match.group(4)

    # Row is marked as hidden if it doesn't have a level
    return types_.TableRow(
        level=level,
        path=path,
        navlink=types_.Navlink(
            title=navlink_title, link=navlink_link or None, hidden=match.group(1) is None
        ),
    )


def _check_table_row_write_permission(
    table_row: types_.TableRow, discourse: Discourse
) -> types_.TableRow:
    """Check that the user has write permissions to the topic linked in the table row.

    Args:
        table_row: The table row to check.
        discourse: API to the Discourse server.

    Returns:
        The table row.

    Raises:
        PagePermissionError: The user does not have write permission for the linked topic.
        ServerError: The interaction with discourse failed.
    """
    if table_row.navlink.link is None:
        return table_row

    url = table_row.navlink.link
    try:
        if discourse.check_topic_write_permission(url=url):
            return table_row
    except DiscourseError as exc:
        raise ServerError(f"failed to retrieve {url}") from exc

    raise PagePermissionError(f"missing write permission for page, {url=}")


def from_page(page: str, discourse: Discourse) -> typing.Iterator[types_.TableRow]:
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
        discourse: API to the Discourse server.

    Returns:
        The parsed rows from the table.
    """
    match = _TABLE_PATTERN.match(page)

    if match is None:
        return iter([])

    table = match.group(0)
    return (
        _check_table_row_write_permission(row, discourse=discourse)
        for row in generate_table_row(table.splitlines())
    )


def generate_table_row(lines: typing.Sequence[str]) -> typing.Iterator[types_.TableRow]:
    """Return an iterator with the TableRows representing the parsed table lines.

    Args:
        lines: list of strings representing the different lines.

    Yields:
        parsed TableRow object, representing the row of the table
    """
    level = 0
    default_level = 1
    path_components: tuple[str, ...] = ()

    for line in lines:
        if not _filter_line(line):
            row = _line_to_row(line, default_level=default_level)

            prefix = path_components[: len(path_components) - (level - row.level) - 1]
            path_components = prefix + (row.path[0].removeprefix("-".join(prefix) + "-"),)
            level = row.level
            # Change the default level to be the last found item level unless it is a group in
            # which case assume the next item should be nested. Used for hidden items which do not
            # have a level of their own.
            default_level = row.level if not row.is_group else row.level + 1

            yield types_.TableRow(row.level, path_components, row.navlink)
