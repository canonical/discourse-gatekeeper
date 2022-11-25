# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for taking the required actions to match the server state with the local state."""

import logging
import typing

from . import exceptions, reconcile, types_
from .discourse import Discourse

DRAFT_NAVLINK_LINK = "<not created due to draft mode>"
FAIL_NAVLINK_LINK = "<not created due to error>"
DRAFT_MODE_REASON = "draft mode"
NOT_DELETE_REASON = "delete_topics is false"


def _create(
    action: types_.CreateAction, discourse: Discourse, draft_mode: bool
) -> types_.ActionResult:
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
        result = types_.ActionResult.SKIP if draft_mode else types_.ActionResult.SUCCESS
        reason = DRAFT_MODE_REASON if draft_mode else None
    elif draft_mode:
        url = DRAFT_NAVLINK_LINK
        result = types_.ActionResult.SKIP
        reason = DRAFT_MODE_REASON
    else:
        try:
            url = discourse.create_topic(title=action.navlink_title, content=action.content)
            result = types_.ActionResult.SUCCESS
            reason = None
        except exceptions.DiscourseError as exc:
            url = FAIL_NAVLINK_LINK
            result = types_.ActionResult.FAIL
            reason = str(exc)

    table_row = types_.TableRow(
        level=action.level,
        path=action.path,
        navlink=types_.Navlink(title=action.navlink_title, link=url),
    )
    return types_.ActionReport(table_row=table_row, url=url, result=result, reason=reason)


def _noop(action: types_.NoopAction) -> types_.ActionResult:
    """Execute a noop action.

    Args:
        action: The noop action details.
    """
    logging.info("action: %s", action)

    table_row = types_.TableRow(level=action.level, path=action.path, navlink=action.navlink)
    return types_.ActionReport(
        table_row=table_row,
        url=table_row.navlink.link,
        result=types_.ActionResult.SUCCESS,
        reason=None,
    )


def _update(
    action: types_.UpdateAction, discourse: Discourse, draft_mode: bool
) -> types_.ActionResult:
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

        try:
            discourse.update_topic(
                url=action.navlink_change.new.link, content=action.content_change.new
            )
            url = action.navlink_change.new.link
            result = types_.ActionResult.SUCCESS
            reason = None
        except exceptions.DiscourseError as exc:
            url = action.navlink_change.new.link
            result = types_.ActionResult.FAIL
            reason = str(exc)
    else:
        if action.navlink_change.new.link is not None:
            url = DRAFT_NAVLINK_LINK if draft_mode else action.navlink_change.new.link
        else:
            # URL for directory should always be None
            url = None
        result = types_.ActionResult.SKIP if draft_mode else types_.ActionResult.SUCCESS
        reason = DRAFT_MODE_REASON if draft_mode else None

    table_row = types_.TableRow(
        level=action.level, path=action.path, navlink=action.navlink_change.new
    )
    return types_.ActionReport(table_row=table_row, url=url, result=result, reason=reason)


def _delete(
    action: types_.DeleteAction, discourse: Discourse, draft_mode: bool, delete_pages: bool
) -> types_.ActionResult:
    """Execute a delete action.

    Args:
        action: The delete action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.
    """
    logging.info("draft mode: %s, delete pages: %s, action: %s", draft_mode, delete_pages, action)

    is_group = action.navlink.link is None
    if draft_mode:
        return types_.ActionReport(
            table_row=None,
            url=action.navlink.link,
            result=types_.ActionResult.SKIP,
            reason=DRAFT_MODE_REASON,
        )
    if not delete_pages and not is_group:
        return types_.ActionReport(
            table_row=None,
            url=action.navlink.link,
            result=types_.ActionResult.SKIP,
            reason=NOT_DELETE_REASON,
        )
    if is_group:
        return types_.ActionReport(
            table_row=None,
            url=action.navlink.link,
            result=types_.ActionResult.SUCCESS,
            reason=None,
        )

    try:
        discourse.delete_topic(url=action.navlink.link)
        return types_.ActionReport(
            table_row=None,
            url=action.navlink.link,
            result=types_.ActionResult.SUCCESS,
            reason=None,
        )
    except exceptions.DiscourseError as exc:
        return types_.ActionReport(
            table_row=None,
            url=action.navlink.link,
            result=types_.ActionResult.FAIL,
            reason=str(exc),
        )


def _run_one(
    action: types_.AnyAction,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> types_.ActionResult:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        The table row for the navigation table or None if the action does not require a row.
    """
    match action.action:
        case types_.Action.CREATE:
            # To help mypy (same for the rest of the asserts), it is ok if the assert does not run
            assert isinstance(action, types_.CreateAction)  # nosec
            return _create(action=action, discourse=discourse, draft_mode=draft_mode)
        case types_.Action.NOOP:
            assert isinstance(action, types_.NoopAction)  # nosec
            return _noop(action=action)
        case types_.Action.UPDATE:
            assert isinstance(action, types_.UpdateAction)  # nosec
            return _update(action=action, discourse=discourse, draft_mode=draft_mode)
        case types_.Action.DELETE:
            assert isinstance(action, types_.DeleteAction)  # nosec
            return _delete(
                action=action,
                discourse=discourse,
                draft_mode=draft_mode,
                delete_pages=delete_pages,
            )
        # Edge case that should not be possible
        case _:  # pragma: no cover
            raise exceptions.ActionError(
                f"internal error, no implementation for action, {action=!r}"
            )


def _run_index(
    action: types_.AnyIndexAction, discourse: Discourse, draft_mode: bool
) -> types_.ActionResult:
    """Take the index action against the server.

    Args:
        action: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
    """
    logging.info("draft mode: %s, action: %s", draft_mode, action)

    if draft_mode:
        return types_.ActionReport(
            table_row=None,
            url=DRAFT_NAVLINK_LINK,
            result=types_.ActionResult.SKIP,
            reason=DRAFT_MODE_REASON,
        )

    match action.action:
        case types_.Action.CREATE:
            # To help mypy (same for the rest of the asserts), it is ok if the assert does not run
            assert isinstance(action, types_.CreateIndexAction)  # nosec
            try:
                url = discourse.create_topic(title=action.title, content=action.content)
                return types_.ActionReport(
                    table_row=None, url=url, result=types_.ActionResult.SUCCESS, reason=None
                )
            except exceptions.DiscourseError as exc:
                return types_.ActionReport(
                    table_row=None, url=None, result=types_.ActionResult.FAIL, reason=str(exc)
                )
        case types_.Action.NOOP:
            return types_.ActionReport(
                table_row=None, url=action.url, result=types_.ActionResult.SUCCESS, reason=None
            )
        case types_.Action.UPDATE:
            assert isinstance(action, types_.UpdateIndexAction)  # nosec
            try:
                discourse.update_topic(url=action.url, content=action.content_change.new)
                return types_.ActionReport(
                    table_row=None, url=action.url, result=types_.ActionResult.SUCCESS, reason=None
                )
            except exceptions.DiscourseError as exc:
                return types_.ActionReport(
                    table_row=None,
                    url=action.url,
                    result=types_.ActionResult.FAIL,
                    reason=str(exc),
                )
        # Edge case that should not be possible
        case _:  # pragma: no cover
            raise exceptions.ActionError(
                f"internal error, no implementation for action, {action=!r}"
            )


def run_all(
    actions: typing.Iterable[types_.AnyAction],
    index: types_.Index,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> list[types_.ActionReport]:
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
    action_reports = [
        _run_one(
            action=action,
            discourse=discourse,
            draft_mode=draft_mode,
            delete_pages=delete_pages,
        )
        for action in actions
    ]
    table_rows = (report.table_row for report in action_reports if report.table_row is not None)
    index_action = reconcile.index_page(index=index, table_rows=table_rows)
    index_action_report = _run_index(
        action=index_action, discourse=discourse, draft_mode=draft_mode
    )
    action_reports.append(index_action_report)
    return action_reports
