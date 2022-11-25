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
) -> types_.ActionReport:
    """Execute a create action.

    Args:
        action: The create action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.

    Returns:
        A report on the outcome of executing the action.
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


def _noop(action: types_.NoopAction) -> types_.ActionReport:
    """Execute a noop action.

    Args:
        action: The noop action details.

    Returns:
        A report on the outcome of executing the action.
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
) -> types_.ActionReport:
    """Execute an update action.

    Args:
        action: The update action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if the new content for a page is None.
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
) -> types_.ActionReport:
    """Execute a delete action.

    Args:
        action: The delete action details.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: If the link for a page to delete is None.
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
        # Edge case that should not be possible
        if action.navlink.link is None:  # pragma: no cover
            raise exceptions.ActionError(
                f"internal error, url None for page to delete, {action=!r}"
            )
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
) -> types_.ActionReport:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if an action that is not handled is passed to the function.
    """
    match action.action:
        case types_.Action.CREATE:
            # To help mypy (same for the rest of the asserts), it is ok if the assert does not run
            assert isinstance(action, types_.CreateAction)  # nosec
            report = _create(action=action, discourse=discourse, draft_mode=draft_mode)
        case types_.Action.NOOP:
            assert isinstance(action, types_.NoopAction)  # nosec
            report = _noop(action=action)
        case types_.Action.UPDATE:
            assert isinstance(action, types_.UpdateAction)  # nosec
            report = _update(action=action, discourse=discourse, draft_mode=draft_mode)
        case types_.Action.DELETE:
            assert isinstance(action, types_.DeleteAction)  # nosec
            report = _delete(
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

    logging.info("report: %s", report)
    return report


def _run_index(
    action: types_.AnyIndexAction, discourse: Discourse, draft_mode: bool
) -> types_.ActionReport:
    """Take the index action against the server.

    Args:
        action: The actions to take.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if an action that is not handled is passed to the function.
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
            try:
                # To help mypy (same for the rest of the asserts), it is ok if the assert does not
                # run
                assert isinstance(action, types_.CreateIndexAction)  # nosec
                url = discourse.create_topic(title=action.title, content=action.content)
                return types_.ActionReport(
                    table_row=None, url=url, result=types_.ActionResult.SUCCESS, reason=None
                )
            except exceptions.DiscourseError as exc:
                return types_.ActionReport(
                    table_row=None, url=None, result=types_.ActionResult.FAIL, reason=str(exc)
                )
        case types_.Action.NOOP:
            assert isinstance(action, types_.NoopIndexAction)  # nosec
            return types_.ActionReport(
                table_row=None, url=action.url, result=types_.ActionResult.SUCCESS, reason=None
            )
        case types_.Action.UPDATE:
            try:
                assert isinstance(action, types_.UpdateIndexAction)  # nosec
                discourse.update_topic(url=action.url, content=action.content_change.new)
                return types_.ActionReport(
                    table_row=None, url=action.url, result=types_.ActionResult.SUCCESS, reason=None
                )
            except exceptions.DiscourseError as exc:
                assert isinstance(action, types_.UpdateIndexAction)  # nosec
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
        The reports of taking all the requested action and the index action report.
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
