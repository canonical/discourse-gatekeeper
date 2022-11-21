# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for calculating required changes based on docs directory and navigation table."""

import typing

from . import exceptions, types_
from .discourse import Discourse


def _local_only(path_info: types_.PathInfo) -> types_.CreatePageAction:
    """Return a create action based on information about a local documentation file.

    Args:
        path_info: Information about the local documentation file.

    Returns:
        A page create action.
    """
    return types_.CreatePageAction(
        action=types_.PageAction.CREATE,
        level=path_info.level,
        path=path_info.table_path,
        navlink_title=path_info.navlink_title,
        content=path_info.local_path.read_text() if path_info.local_path.is_file() else None,
    )


def _local_and_server(
    path_info: types_.PathInfo, table_row: types_.TableRow, discourse: Discourse
) -> (
    types_.UpdatePageAction
    | types_.NoopPageAction
    | types_.CreatePageAction
    | types_.DeletePageAction
):
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
            return types_.NoopPageAction(
                action=types_.PageAction.NOOP,
                level=path_info.level,
                path=path_info.table_path,
                navlink=table_row.navlink,
                content=None,
            )
        return types_.UpdatePageAction(
            action=types_.PageAction.UPDATE,
            level=path_info.level,
            path=path_info.table_path,
            navlink_change=types_.NavlinkChange(
                old=table_row.navlink,
                new=types_.Navlink(title=path_info.navlink_title, link=table_row.navlink.link),
            ),
            content_change=types_.ContentChange(old=None, new=None),
        )

    if path_info.local_path.is_dir():
        if table_row.navlink.link is None:
            raise exceptions.ReconcilliationError(
                f"internal error, expecting link on table row, {path_info=!r}, {table_row=!r}"
            )
        return types_.DeletePageAction(
            action=types_.PageAction.DELETE,
            level=path_info.level,
            path=path_info.table_path,
            navlink=table_row.navlink,
            content=discourse.retrieve_topic(url=table_row.navlink.link),
        )

    if table_row.is_group:
        return types_.CreatePageAction(
            action=types_.PageAction.CREATE,
            level=path_info.level,
            path=path_info.table_path,
            navlink_title=path_info.navlink_title,
            content=path_info.local_path.read_text(),
        )

    local_content = path_info.local_path.read_text(encoding="utf-8")
    if table_row.navlink.link is None:
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {path_info=!r}, {table_row=!r}"
        )
    server_content = discourse.retrieve_topic(url=table_row.navlink.link)

    if server_content == local_content and table_row.navlink.title == path_info.navlink_title:
        return types_.NoopPageAction(
            action=types_.PageAction.NOOP,
            level=path_info.level,
            path=path_info.table_path,
            navlink=table_row.navlink,
            content=local_content,
        )
    return types_.UpdatePageAction(
        action=types_.PageAction.UPDATE,
        level=path_info.level,
        path=path_info.table_path,
        navlink_change=types_.NavlinkChange(
            old=table_row.navlink,
            new=types_.Navlink(title=path_info.navlink_title, link=table_row.navlink.link),
        ),
        content_change=types_.ContentChange(old=server_content, new=local_content),
    )


def _server_only(table_row: types_.TableRow, discourse: Discourse) -> types_.DeletePageAction:
    """Return a delete action based on a navigation table entry.

    Args:
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        A page delete action.
    """


def _calculate_action(
    path_info: types_.PathInfo | None, table_row: types_.TableRow | None, discourse: Discourse
) -> types_.BasePageAction:
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


def run(
    path_infos: typing.Iterator[types_.PathInfo],
    table_rows: typing.Iterator[types_.TableRow],
    discourse: Discourse,
) -> typing.Iterator[types_.BasePageAction]:
    """Reconcile differences between the docs directory and documentation server.

    Args:
        path_infos: Information about the local documentation files.
        table_rows: Rows from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        The actions required to reconcile differences between the documentation server and local
        files.
    """
