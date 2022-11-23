# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for taking the required actions to match the server state with the local state."""

import typing

from . import types_
from .discourse import Discourse


def _create(
    action: types_.CreateAction, discourse: Discourse, draft_mode: bool
) -> types_.TableRow:
    """Execute a create action.

    Args:
        action: The create action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.

    Returns:
        The navigation table row to add to the navigation table.
    """


def _noop(action: types_.NoopAction) -> types_.TableRow:
    """Execute a noop action.

    Args:
        action: The noop action details.
    """


def _update(
    action: types_.UpdateAction, discourse: Discourse, draft_mode: bool
) -> types_.TableRow:
    """Execute an update action.

    Args:
        action: The update action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.

    Returns:
        The updated navigation table row to for the navigation table.
    """


def _delete(
    action: types_.DeleteAction, discourse: Discourse, draft_mode: bool, delete_pages: bool
) -> None:
    """Execute a delete action.

    Args:
        action: The delete action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.
    """


def run_one(
    action: types_.AnyAction,
    index_page: types_.Page,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> types_.TableRow | None:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        The table row for the navigation table or None if the action does not require a row.
    """


def run_all(
    actions: typing.Iterable[types_.AnyAction],
    index_page: types_.Page,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> typing.Iterator[types_.TableRow]:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        The table rows for the navigation table.
    """
