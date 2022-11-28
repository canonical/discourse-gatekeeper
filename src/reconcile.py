# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for calculating required changes based on docs directory and navigation table."""

import itertools
import typing

from . import exceptions, types_
from .discourse import Discourse


def _local_only(path_info: types_.PathInfo) -> types_.CreateAction:
    """Return a create action based on information about a local documentation file.

    Args:
        path_info: Information about the local documentation file.

    Returns:
        A page create action.
    """
    return types_.CreateAction(
        action=types_.Action.CREATE,
        level=path_info.level,
        path=path_info.table_path,
        navlink_title=path_info.navlink_title,
        content=path_info.local_path.read_text() if path_info.local_path.is_file() else None,
    )


def _local_and_server(
    path_info: types_.PathInfo, table_row: types_.TableRow, discourse: Discourse
) -> (types_.UpdateAction | types_.NoopAction | types_.CreateAction | types_.DeleteAction):
    """Compare the local and server content and return an appropriate action.

    Cases:
        1. The action relates to a directory locally and grouping on the server and
            1.1. the navlink title has not change: noop or
            1.2. the navling title has changed: update action.
        2. The action related to a directory locally and a page on the server: delete the page on
            the server and create the directory.
        3. The action related to a file locally and a group on the server: create the page on the
            server.
        4. The action relates to a file locally and a page on the server and
            4.1. the content and navlink title has not changed: noop or
            4.2. the content and/ or the navlink have changed: update action.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        The action to execute against the server.

    Raises:
        ReconcilliationError: if the table path or level do not match for the path info and table
            row.
        ReconcilliationError: if certain edge cases occur that are not expected, such as
            table_row.navlink.link for a page on the server.
    """
    if path_info.level != table_row.level:
        raise exceptions.ReconcilliationError(
            f"internal error, level mismatch, {path_info=!r}, {table_row=!r}"
        )
    if path_info.table_path != table_row.path:
        raise exceptions.ReconcilliationError(
            f"internal error, table path mismatch, {path_info=!r}, {table_row=!r}"
        )

    # Is a directory locally and a grouping on the server
    if path_info.local_path.is_dir() and table_row.is_group:
        if table_row.navlink.title == path_info.navlink_title:
            return types_.NoopAction(
                action=types_.Action.NOOP,
                level=path_info.level,
                path=path_info.table_path,
                navlink=table_row.navlink,
                content=None,
            )
        return types_.UpdateAction(
            action=types_.Action.UPDATE,
            level=path_info.level,
            path=path_info.table_path,
            navlink_change=types_.NavlinkChange(
                old=table_row.navlink,
                new=types_.Navlink(title=path_info.navlink_title, link=table_row.navlink.link),
            ),
            content_change=types_.ContentChange(old=None, new=None),
        )

    # Is a directory locally and a page on the server
    if path_info.local_path.is_dir():
        # This is an edge case that can't actually occur because table_row.is_group is based on
        # whether the navlink link is None so this case would have been caught in the local
        # directory and server group case
        if table_row.navlink.link is None:  # pragma: no cover
            raise exceptions.ReconcilliationError(
                f"internal error, expecting link on table row, {path_info=!r}, {table_row=!r}"
            )
        return types_.DeleteAction(
            action=types_.Action.DELETE,
            level=path_info.level,
            path=path_info.table_path,
            navlink=table_row.navlink,
            content=discourse.retrieve_topic(url=table_row.navlink.link),
        )

    # Is a page locally and a grouping on the server
    if table_row.is_group:
        return types_.CreateAction(
            action=types_.Action.CREATE,
            level=path_info.level,
            path=path_info.table_path,
            navlink_title=path_info.navlink_title,
            content=path_info.local_path.read_text(),
        )

    # Is a page locally and on the server
    local_content = path_info.local_path.read_text(encoding="utf-8")
    # This is an edge case that can't actually occur because table_row.is_group is based on
    # whether the navlink link is None so this case would have been caught in the local
    # page and server group case
    if table_row.navlink.link is None:  # pragma: no cover
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {path_info=!r}, {table_row=!r}"
        )
    server_content = discourse.retrieve_topic(url=table_row.navlink.link)

    if server_content == local_content and table_row.navlink.title == path_info.navlink_title:
        return types_.NoopAction(
            action=types_.Action.NOOP,
            level=path_info.level,
            path=path_info.table_path,
            navlink=table_row.navlink,
            content=local_content,
        )
    return types_.UpdateAction(
        action=types_.Action.UPDATE,
        level=path_info.level,
        path=path_info.table_path,
        navlink_change=types_.NavlinkChange(
            old=table_row.navlink,
            new=types_.Navlink(title=path_info.navlink_title, link=table_row.navlink.link),
        ),
        content_change=types_.ContentChange(old=server_content, new=local_content),
    )


def _server_only(table_row: types_.TableRow, discourse: Discourse) -> types_.DeleteAction:
    """Return a delete action based on a navigation table entry.

    Args:
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        A page delete action.

    Raises:
        ReconcilliationError: if the link for a page is None.
    """
    # Group case
    if table_row.is_group:
        return types_.DeleteAction(
            action=types_.Action.DELETE,
            level=table_row.level,
            path=table_row.path,
            navlink=table_row.navlink,
            content=None,
        )

    # This is an edge case that can't actually occur because table_row.is_group is based on
    # whether the navlink link is None so this case would have been caught in the group case
    if table_row.navlink.link is None:  # pragma: no cover
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {table_row=!r}"
        )
    return types_.DeleteAction(
        action=types_.Action.DELETE,
        level=table_row.level,
        path=table_row.path,
        navlink=table_row.navlink,
        content=discourse.retrieve_topic(url=table_row.navlink.link),
    )


def _calculate_action(
    path_info: types_.PathInfo | None, table_row: types_.TableRow | None, discourse: Discourse
) -> tuple[types_.AnyAction, ...]:
    """Calculate the required action for a page.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Raises:
        ReconcilliationError: if both path_info and table_row are None.
    """
    if path_info is None and table_row is None:
        raise exceptions.ReconcilliationError(
            "internal error, both path info and table row are None"
        )
    if path_info is not None and table_row is None:
        return (_local_only(path_info=path_info),)
    if path_info is None and table_row is not None:
        return (_server_only(table_row=table_row, discourse=discourse),)
    if path_info is not None and table_row is not None:
        return (_local_and_server(path_info=path_info, table_row=table_row, discourse=discourse),)

    # Something weird has happened since all cases should already be covered
    raise exceptions.ReconcilliationError("internal error")  # pragma: no cover


def run(
    path_infos: typing.Iterable[types_.PathInfo],
    table_rows: typing.Iterable[types_.TableRow],
    discourse: Discourse,
) -> typing.Iterator[types_.AnyAction]:
    """Reconcile differences between the docs directory and documentation server.

    Preserves the order of path_infos although does not for items only in table_rows.

    Args:
        path_infos: Information about the local documentation files.
        table_rows: Rows from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        The actions required to reconcile differences between the documentation server and local
        files.
    """
    path_info_lookup: types_.PathInfoLookup = {
        (path_info.level, path_info.table_path): path_info for path_info in path_infos
    }
    table_row_lookup: types_.TableRowLookup = {
        (table_row.level, table_row.path): table_row for table_row in table_rows
    }

    # Need to process items only on the server last
    keys = itertools.chain(
        path_info_lookup.keys(), table_row_lookup.keys() - path_info_lookup.keys()
    )
    return itertools.chain.from_iterable(
        _calculate_action(path_info_lookup.get(key), table_row_lookup.get(key), discourse)
        for key in keys
    )


NAVIGATION_TABLE_START = """

# Navigation

| Level | Path | Navlink |
| -- | -- | -- |"""


def index_page(
    index: types_.Index,
    table_rows: typing.Iterable[types_.TableRow],
) -> types_.AnyIndexAction:
    """Reconcile differences for the index page.

    Args:
        index: Information about the index on the server and locally.
        server_table_rows: The current navigation table rows on the server.
        table_rows: The current navigation table rows based on local files.

    Returns:
        The action to take for the index page.
    """
    table_contents = "\n".join(table_row.to_line() for table_row in table_rows)
    local_content = f"{index.local.content or ''}{NAVIGATION_TABLE_START}\n{table_contents}\n"

    if index.server is None:
        return types_.CreateIndexAction(
            action=types_.Action.CREATE, content=local_content, title=index.local.title
        )
    if local_content != index.server.content:
        return types_.UpdateIndexAction(
            action=types_.Action.UPDATE,
            content_change=types_.IndexContentChange(old=index.server.content, new=local_content),
            url=index.server.url,
        )
    return types_.NoopIndexAction(
        action=types_.Action.NOOP, content=local_content, url=index.server.url
    )
