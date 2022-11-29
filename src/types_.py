# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Types for uploading docs to charmhub."""

import dataclasses
import typing
from enum import Enum
from pathlib import Path

Content = str
Url = str


class Page(typing.NamedTuple):
    """Information about a documentation page.

    Attrs:
        url: The link to the page.
        content: The documentation text of the page.
    """

    url: Url
    content: Content


NavlinkTitle = str


class IndexFile(typing.NamedTuple):
    """Information about a documentation page.

    Attrs:
        title: The title for the index.
        content: The local content of the index.
    """

    title: NavlinkTitle
    content: Content | None


class Index(typing.NamedTuple):
    """Information about the local and server index page.

    Attrs:
        server: The index page on the server.
        local: The local index file contents.
    """

    server: Page | None
    local: IndexFile


Level = int
TablePath = str


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

    def to_markdown(self) -> str:
        """Convert to a line in the navigation table.

        Returns:
            The line in the navigation table.
        """
        return (
            f"| {self.level} | {self.path} | [{self.navlink.title}]({self.navlink.link or ''}) |"
        )


TableRowLookup = dict[tuple[Level, TablePath], TableRow]


class ActionType(str, Enum):
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
        type_: The type of action to execute on the page.
    """

    type_: ActionType


@dataclasses.dataclass
class CreateAction(BaseAction):
    """Represents a page to be created.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_title: The title of the navlink.
        content: The documentation content, is None for directories.
    """

    type_: typing.Literal[ActionType.CREATE]

    level: Level
    path: TablePath
    navlink_title: NavlinkTitle
    content: Content | None


@dataclasses.dataclass
class CreateIndexAction(BaseAction):
    """Represents an index page to be created.

    Attrs:
        content: The content including the navigation table.
    """

    type_: typing.Literal[ActionType.CREATE]

    title: NavlinkTitle
    content: Content


@dataclasses.dataclass
class NoopAction(BaseAction):
    """Represents a page with no required changes.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The navling title and link for the page.
        content: The documentation content of the page.
    """

    type_: typing.Literal[ActionType.NOOP]

    level: Level
    path: TablePath
    navlink: Navlink
    content: Content | None


@dataclasses.dataclass
class NoopIndexAction(BaseAction):
    """Represents an index page with no required changes.

    Attrs:
        content: The content including the navigation table.
    """

    type_: typing.Literal[ActionType.NOOP]

    content: Content
    url: Url


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


class IndexContentChange(typing.NamedTuple):
    """Represents a change to the content of the index.

    Attrs:
        old: The previous content.
        new: The new content.
    """

    old: Content
    new: Content


@dataclasses.dataclass
class UpdateAction(BaseAction):
    """Represents a page to be updated.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_change: The changeto the navlink.
        content_change: The change to the documentation content.
    """

    type_: typing.Literal[ActionType.UPDATE]

    level: Level
    path: TablePath
    navlink_change: NavlinkChange
    content_change: ContentChange | None


@dataclasses.dataclass
class UpdateIndexAction(BaseAction):
    """Represents an index page to be updated.

    Attrs:
        content_change: The change to the content including the navigation table.
    """

    type_: typing.Literal[ActionType.UPDATE]

    content_change: IndexContentChange
    url: Url


@dataclasses.dataclass
class DeleteAction(BaseAction):
    """Represents a page to be deleted.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The title link to the page
        content: The documentation content.
    """

    type_: typing.Literal[ActionType.DELETE]

    level: Level
    path: TablePath
    navlink: Navlink
    content: Content | None


AnyAction = CreateAction | NoopAction | UpdateAction | DeleteAction
AnyIndexAction = CreateIndexAction | NoopIndexAction | UpdateIndexAction


class ActionResult(str, Enum):
    """Result of taking an action.

    Attrs:
        SUCCESS: The action succeeded.
        SKIP: The action was skipped.
        FAIL: The action failed.
    """

    SUCCESS = "success"
    SKIP = "skip"
    FAIL = "fail"


class ActionReport(typing.NamedTuple):
    """Post execution report for an action.

    Attrs:
        table_row: The navigation table entry, None for delete or index actions.
        url: The URL that the action operated on, None for groups or if a create action was
            skipped.
        result: The action execution result.
        reason: The reason, None for success reports.
    """

    table_row: TableRow | None
    url: Url | None
    result: ActionResult
    reason: str | None
