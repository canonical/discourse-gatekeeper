# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Types for uploading docs to charmhub."""

import dataclasses
import typing
from enum import Enum
from pathlib import Path


class Page(typing.NamedTuple):
    """Information about a documentation page.

    Atrs:
        url: The link to the page.
        content: The documentation text of the page.
    """

    url: str | None
    content: str

    @property
    def is_created(self) -> bool:
        """Whether the page has already been created."""
        return self.url is not None


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


PathInfoLookup = dict[tuple[Level, TablePath], PathInfo]


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

    @property
    def is_group(self) -> bool:
        """Whether the row is a group of pages."""
        return self.navlink.link is None


TableRowLookup = dict[tuple[Level, TablePath], TableRow]


Content = str


class Action(str, Enum):
    """The possible actions to take for a page.

    Attrs:
        CREATE: create a new page.
        NOOP: no action required.
        UPDATE: change aspects of an existing page.
        DELETE: remove an existing page.
    """

    CREATE = "create"
    NOOP = "noop"
    UPDATE = "update"
    DELETE = "delete"


@dataclasses.dataclass
class BaseAction:
    """Represents an action on a page.

    Attrs:
        action: The action to execute on the page.
    """

    action: Action


@dataclasses.dataclass
class CreateAction(BaseAction):
    """Represents a page to be created.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_title: The title of the navlink.
        content: The documentation content, is None for directories.
    """

    action: typing.Literal[Action.CREATE]

    level: Level
    path: TablePath
    navlink_title: NavlinkTitle
    content: Content | None


class NavlinkChange(typing.NamedTuple):
    """Represents a change to the navlink.

    Attrs:
        old: The previous navlink.
        new: The new navlink.
    """

    old: Navlink
    new: Navlink


class ContentChange(typing.NamedTuple):
    """Represents a change to the content.

    Attrs:
        old: The previous content.
        new: The new content.
    """

    old: Content | None
    new: Content | None


@dataclasses.dataclass
class NoopAction(BaseAction):
    """Represents a page with no required changes.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The navling title and link for the page.
        content: The documentation content of the page.
    """

    action: typing.Literal[Action.NOOP]

    level: Level
    path: TablePath
    navlink: Navlink
    content: Content | None


@dataclasses.dataclass
class UpdateAction(BaseAction):
    """Represents a page to be updated.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_change: The changeto the navlink.
        content_change: The change to the documentation content.
    """

    action: typing.Literal[Action.UPDATE]

    level: Level
    path: TablePath
    navlink_change: NavlinkChange
    content_change: ContentChange


@dataclasses.dataclass
class DeleteAction(BaseAction):
    """Represents a page to be deleted.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The title link to the page
        content: The documentation content.
    """

    action: typing.Literal[Action.DELETE]

    level: Level
    path: TablePath
    navlink: Navlink
    content: Content | None


AnyAction = CreateAction | NoopAction | UpdateAction | DeleteAction
