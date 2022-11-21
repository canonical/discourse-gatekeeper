# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Types for uploading docs to charmhub."""

import typing
from pathlib import Path


class Page(typing.NamedTuple):
    """Information about a documentation page.

    Atrs:
        url: The link to the page.
        content: The documentation text of the page.
    """

    url: str
    content: str


Level = int
TablePath = str
NavlinkTitle = str


class PathInfo(typing.NamedTuple):
    """Represents a file or directory in the docs directory.

    Attrs:
        local_path: The path to the file on the local disk.
        level: The number of parent directories to the docs folder including the docs folder.
        table_path: The computed table path based on the disk path relative to the docs folder.
        navlink_title: The title of the navlink.
    """

    local_path: Path
    level: Level
    table_path: TablePath
    navlink_title: NavlinkTitle


class Navlink(typing.NamedTuple):
    """Represents navlink of a table row of the navigation table.

    Attrs:
        title: The title of the documentation page.
        link: The relative URL to the documentation page or None if there is no link.
    """

    title: NavlinkTitle
    link: str | None


class TableRow(typing.NamedTuple):
    """Represents one parsed row of the navigation table.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the row.
        navlink: The title and relative URL to the documentation page.
    """

    level: Level
    path: TablePath
    navlink: Navlink
