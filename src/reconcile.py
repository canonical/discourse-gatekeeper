# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for calculating required changes based on docs directory and navigation table."""

import typing

from . import types_
from .discourse import Discourse


def _create_page_action(path_info: types_.PathInfo) -> types_.CreatePageAction:
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


def _update_page_action(
    path_info: types_.PathInfo | None, table_row: types_.TableRow | None, discourse: Discourse
) -> types_.UpdatePageAction:
    """Return an update action.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        A page update action.
    """


def _delete_page_action(
    table_row: types_.TableRow, discourse: Discourse
) -> types_.DeletePageAction:
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
