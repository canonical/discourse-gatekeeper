# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Types for uploading docs to charmhub."""

import dataclasses
import typing
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse


class Metadata(typing.NamedTuple):
    """Information within metadata file. Refer to: https://juju.is/docs/sdk/metadata-yaml.

    Only name and docs are the fields of interest for the scope of this module.

    Attrs:
        name: Name of the charm.
        docs: A link to a documentation cover page on Discourse.
    """

    name: str
    docs: str | None


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
        name: The name of the charm.
    """

    server: Page | None
    local: IndexFile
    name: str


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
            f"| {self.level} | {self.path} | "
            f"[{self.navlink.title}]({urlparse(self.navlink.link or '').path}) |"
        )


TableRowLookup = dict[tuple[Level, TablePath], TableRow]


@dataclasses.dataclass
class CreateAction:
    """Represents a page to be created.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_title: The title of the navlink.
        content: The documentation content, is None for directories.
    """

    level: Level
    path: TablePath
    navlink_title: NavlinkTitle
    content: Content | None


@dataclasses.dataclass
class CreateIndexAction:
    """Represents an index page to be created.

    Attrs:
        title: The title of the index page.
        content: The content including the navigation table.
    """

    title: NavlinkTitle
    content: Content


@dataclasses.dataclass
class NoopAction:
    """Represents a page with no required changes.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The navling title and link for the page.
        content: The documentation content of the page.
    """

    level: Level
    path: TablePath
    navlink: Navlink
    content: Content | None


@dataclasses.dataclass
class NoopIndexAction:
    """Represents an index page with no required changes.

    Attrs:
        content: The content including the navigation table.
        url: The URL to the index page.
    """

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
class UpdateAction:
    """Represents a page to be updated.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink_change: The changeto the navlink.
        content_change: The change to the documentation content.
    """

    level: Level
    path: TablePath
    navlink_change: NavlinkChange
    content_change: ContentChange | None


@dataclasses.dataclass
class UpdateIndexAction:
    """Represents an index page to be updated.

    Attrs:
        content_change: The change to the content including the navigation table.
        url: The URL to the index page.
    """

    content_change: IndexContentChange
    url: Url


@dataclasses.dataclass
class DeleteAction:
    """Represents a page to be deleted.

    Attrs:
        level: The number of parents, is 1 if there is no parent.
        path: The a unique string identifying the navigation table row.
        navlink: The link to the page
        content: The documentation content.
    """

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


@dataclasses.dataclass
class MigrationDocument:
    """Represents a document to be migrated.

    Attrs:
        path: The full document path to be written to.
    """

    path: Path


@dataclasses.dataclass
class GitkeepFile(MigrationDocument):
    """Represents an empty directory from the index table."""


@dataclasses.dataclass
class DocumentFile(MigrationDocument):
    """Represents a document to be migrated from the index table.

    Attrs:
        link: Link to content to read from.
    """

    link: str
