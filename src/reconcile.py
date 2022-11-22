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
    """Return an update or noop action depending on if the content or navlink title has changed.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        A page update or noop action.

    Raises:
        ReconcilliationError: if the table path or level do not match for the path info and table
            row.
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
) -> types_.AnyAction:
    """Calculate the required action for a page.

    The action is based on a path in the docs directory and a navigation table entry:
        1. If both path_info and tabke_row are None, raise an error.
        2. If path_info is not None and table_row is None, return a create action.
        2. If table_row is not None and path_info is None, return a delete action.
        2. If both table_row and path_info are not None, return an update action.

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
        return _local_only(path_info=path_info)
    if path_info is None and table_row is not None:
        return _server_only(table_row=table_row, discourse=discourse)
    if path_info is not None and table_row is not None:
        return _local_and_server(path_info=path_info, table_row=table_row, discourse=discourse)

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
        path_info_lookup.keys(), (table_row_lookup.keys() - path_info_lookup.keys())
    )
    return (
        _calculate_action(path_info_lookup.get(key), table_row_lookup.get(key), discourse)
        for key in keys
    )
