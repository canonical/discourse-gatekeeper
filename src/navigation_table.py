# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Class for parsing and rendering a navigation table."""

from pathlib import Path
import typing


class TableRow(typing.NamedTuple):
    """Represents one parsed row of the navigation table.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the row.
        navlink: The relative URL to the documentation page.
        file_path: The path to the file relative to the docs folder.
    """

    level: int
    path: str
    navlink: str
    file_path: Path


class NavigationTable:
    """Parses and can render a navigation table.

    Attrs:
        rows: All the rows of the table.
    """

    rows: list[TableRow]
    table_regex = r"(\|.*Level.*\|.*Path.*\|.*Navlink.*\|[\s\S]*\|)"

    def __init__(self, rows: list[TableRow]) -> None:
        """Construct.

        Recommend the use of one of the from_* methods.

        Args:
            rows: The rows of the table.
        """
