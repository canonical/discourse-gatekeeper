# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for taking the required actions to match the server state with the local state."""

import logging
import typing

from . import types_, exceptions
from .discourse import Discourse


DRAFT_NAVLINK_LINK = "<not created due to draft mode>"


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
    logging.info("draft mode: %s, action: %s", draft_mode, action)

    if action.content is None:
        url = None
    elif draft_mode:
        url = DRAFT_NAVLINK_LINK
    else:
        url = discourse.create_topic(title=action.navlink_title, content=action.content)

    return types_.TableRow(
        level=action.level,
        path=action.path,
        navlink=types_.Navlink(title=action.navlink_title, link=url),
    )


def _noop(action: types_.NoopAction) -> types_.TableRow:
    """Execute a noop action.

    Args:
        action: The noop action details.
    """
    logging.info("action: %s", action)

    return types_.TableRow(level=action.level, path=action.path, navlink=action.navlink)


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
    logging.info("draft mode: %s, action: %s", draft_mode, action)

    if (
        not draft_mode
        and action.navlink_change.new.link is not None
        and action.content_change.new != action.content_change.old
    ):
        if action.content_change.new is None:
            raise exceptions.ActionError(
                f"internal error, new content for page is None, {action=!r}"
            )
        discourse.update_topic(
            url=action.navlink_change.new.link, content=action.content_change.new
        )

    return types_.TableRow(level=action.level, path=action.path, navlink=action.navlink_change.new)


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


def _run_one(
    action: types_.AnyAction,
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
    index: types_.Index,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> None:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        index: Information about the index.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        The table rows for the navigation table.
    """
