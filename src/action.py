# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for taking the required actions to match the server state with the local state."""

import logging
import typing
from enum import Enum

from . import content, exceptions, reconcile, types_
from .discourse import Discourse

DRY_RUN_NAVLINK_LINK = "<not created due to dry run>"
DRY_RUN_REASON = "dry run"
BASE_MISSING_REASON = "no base for the content to be automatically merged"
FAIL_NAVLINK_LINK = "<not created due to error>"
NOT_DELETE_REASON = "delete_topics is false"


def _absolute_url(
    action: types_.AnyAction, url: types_.Url | None, discourse: Discourse
) -> types_.Url | None:
    """Get the absolute URL.

    Args:
        url: The url to convert.
        discourse: A client to the documentation server.

    Returns:
        The converted url or None if the url is None.
    """
    if (
        isinstance(
            action,
            (
                types_.CreatePageAction,
                types_.UpdatePageAction,
                types_.NoopPageAction,
                types_.DeletePageAction,
            ),
        )
        and url is not None
    ):
        return discourse.absolute_url(url=url)
    return url


def _log_content_change(base: str, new: str) -> None:
    """Log the difference between the base and new content, if any.

    Args:
        base: The previous content.
        new: The current content.
    """
    old = f"{base}\n" if not base.endswith("\n") else base
    new = f"{new}\n" if not new.endswith("\n") else new
    if new != old:
        logging.info("content change:\n%s", content.diff(old, new))


def _create(
    action: types_.CreateAction, discourse: Discourse, dry_run: bool, name: str
) -> types_.ActionReport:
    """Execute a create action.

    Args:
        action: The create action details.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.
        name: The charm name to prefix to the created pages title.

    Returns:
        A report on the outcome of executing the action.
    """
    logging.info("dry run: %s, action: %s", dry_run, action)

    # Handle the directory/ group case, no server interactions are required
    if isinstance(action, types_.CreateGroupAction):
        url = None
        result = types_.ActionResult.SKIP if dry_run else types_.ActionResult.SUCCESS
        reason = DRY_RUN_REASON if dry_run else None
    elif isinstance(action, types_.CreateExternalRefAction):
        url = action.navlink_value
        result = types_.ActionResult.SKIP if dry_run else types_.ActionResult.SUCCESS
        reason = DRY_RUN_REASON if dry_run else None
    # Handle the file/ page case when dry run is enabled, no server interactions are required
    elif dry_run:
        url = DRY_RUN_NAVLINK_LINK
        result = types_.ActionResult.SKIP
        reason = DRY_RUN_REASON
    # Handle the file/ page case where a new page needs to be created on the server
    elif isinstance(action, types_.CreatePageAction):
        try:
            url = discourse.create_topic(
                title=f"{name} docs: {action.navlink_title}", content=action.content
            )
            result = types_.ActionResult.SUCCESS
            reason = None
        except exceptions.DiscourseError as exc:
            url = FAIL_NAVLINK_LINK
            result = types_.ActionResult.FAIL
            reason = str(exc)
    # This should not occur since all the create action types have been implemented
    else:  # pragma: no cover
        raise NotImplementedError(f"internal error: {action} has not been implemented")

    table_row = types_.TableRow(
        level=action.level,
        path=action.path,
        navlink=types_.Navlink(title=action.navlink_title, link=url, hidden=action.navlink_hidden),
    )
    return types_.ActionReport(table_row=table_row, location=url, result=result, reason=reason)


def _noop(action: types_.NoopAction, discourse: Discourse) -> types_.ActionReport:
    """Execute a noop action.

    Args:
        action: The noop action details.
        discourse: A client to the documentation server.

    Returns:
        A report on the outcome of executing the action.
    """
    logging.info("action: %s", action)

    table_row = types_.TableRow(level=action.level, path=action.path, navlink=action.navlink)
    return types_.ActionReport(
        table_row=table_row,
        location=_absolute_url(action=action, url=table_row.navlink.link, discourse=discourse),
        result=types_.ActionResult.SUCCESS,
        reason=None,
    )


class UpdateCase(str, Enum):
    """The possible cases for the update action.

    Attrs:
        DRY_RUN: Do not make any changes.
        CONTENT_CHANGE: The content has been changed.
        BASE_MISSING: The base content is not available.
        DEFAULT: No other specific case applies.
    """

    DRY_RUN = "dry-run"
    CONTENT_CHANGE = "content-change"
    BASE_MISSING = "base-missing"
    DEFAULT = "default"


def _get_update_case(action: types_.UpdateAction, dry_run: bool) -> UpdateCase:
    """Get the execution case for the update action.

    Args:
        action: The update action details.
        dry_run: If enabled, only log the action that would be taken.

    Returns:
        The named case for the action execution.
    """
    if dry_run:
        return UpdateCase.DRY_RUN
    if (
        not dry_run
        and isinstance(action, types_.UpdatePageAction)
        and action.navlink_change.new.link is not None
        and action.content_change.base is not None
        and action.content_change.local != action.content_change.server
    ):
        return UpdateCase.CONTENT_CHANGE
    if (
        isinstance(action, types_.UpdatePageAction)
        and action.content_change.base is None
        and action.content_change.local != action.content_change.server
    ):
        return UpdateCase.BASE_MISSING
    return UpdateCase.DEFAULT


def _update(
    action: types_.UpdateAction, discourse: Discourse, dry_run: bool
) -> types_.ActionReport:
    """Execute an update action.

    Args:
        action: The update action details.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if the content change or new content for a page is None.
    """
    logging.info("dry run: %s, action: %s", dry_run, action)
    if isinstance(action, types_.UpdatePageAction):
        _log_content_change(
            base=action.content_change.base or action.content_change.server,
            new=action.content_change.local,
        )

    update_case = _get_update_case(action=action, dry_run=dry_run)

    reason: str | None
    match update_case:
        case UpdateCase.DRY_RUN:
            result = types_.ActionResult.SKIP
            reason = DRY_RUN_REASON
        case UpdateCase.CONTENT_CHANGE:
            action = typing.cast(types_.UpdatePageAction, action)
            try:
                content_change = typing.cast(types_.ContentChange, action.content_change)
                merged_content = content.merge(
                    base=typing.cast(str, content_change.base),
                    theirs=content_change.server,
                    ours=content_change.local,
                )
                discourse.update_topic(
                    url=typing.cast(str, action.navlink_change.new.link), content=merged_content
                )
                result = types_.ActionResult.SUCCESS
                reason = None
            except (exceptions.DiscourseError, exceptions.ContentError) as exc:
                result = types_.ActionResult.FAIL
                reason = str(exc)
        case UpdateCase.BASE_MISSING:
            result = types_.ActionResult.FAIL
            reason = BASE_MISSING_REASON
        case _:
            result = types_.ActionResult.SUCCESS
            reason = None

    url = _absolute_url(action=action, url=action.navlink_change.new.link, discourse=discourse)
    table_row = types_.TableRow(
        level=action.level, path=action.path, navlink=action.navlink_change.new
    )
    return types_.ActionReport(table_row=table_row, location=url, result=result, reason=reason)


def _delete(
    action: types_.DeleteAction, discourse: Discourse, dry_run: bool, delete_pages: bool
) -> types_.ActionReport:
    """Execute a delete action.

    Args:
        action: The delete action details.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: If the link for a page to delete is None.
    """
    logging.info("dry run: %s, delete pages: %s, action: %s", dry_run, delete_pages, action)

    # Handle group and external references
    if isinstance(action, (types_.DeleteGroupAction, types_.DeleteExternalRefAction)):
        return types_.ActionReport(
            table_row=None,
            location=None,
            result=types_.ActionResult.SKIP if dry_run else types_.ActionResult.SUCCESS,
            reason=DRY_RUN_REASON if dry_run else None,
        )

    url = _absolute_url(action=action, url=action.navlink.link, discourse=discourse)
    if dry_run:
        return types_.ActionReport(
            table_row=None, location=url, result=types_.ActionResult.SKIP, reason=DRY_RUN_REASON
        )
    if not delete_pages and isinstance(action, types_.DeletePageAction):
        return types_.ActionReport(
            table_row=None, location=url, result=types_.ActionResult.SKIP, reason=NOT_DELETE_REASON
        )

    try:
        # Edge case that should not be possible, here for defensive programming
        if action.navlink.link is None:  # pragma: no cover
            raise exceptions.ActionError(
                f"internal error, url None for page to delete, {action=!r}"
            )

        discourse.delete_topic(url=action.navlink.link)
        return types_.ActionReport(
            table_row=None, location=url, result=types_.ActionResult.SUCCESS, reason=None
        )
    except exceptions.DiscourseError as exc:
        return types_.ActionReport(
            table_row=None, location=url, result=types_.ActionResult.FAIL, reason=str(exc)
        )


def _run_one(
    action: types_.AnyAction,
    discourse: Discourse,
    name: str,
    dry_run: bool,
    delete_pages: bool,
) -> types_.ActionReport:
    """Take the actions against the server.

    Args:
        action: The details of the action to take.
        discourse: A client to the documentation server.
        name: The charm name to prefix to the created pages title.
        dry_run: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if an action that is not handled is passed to the function.
    """
    match type(action):
        case types_.CreatePageAction | types_.CreateGroupAction | types_.CreateExternalRefAction:
            # To help mypy (same for the rest of the asserts), it is ok if the assert does not run
            assert isinstance(action, types_.CreateAction)  # nosec
            report = _create(action=action, discourse=discourse, dry_run=dry_run, name=name)
        case types_.NoopPageAction | types_.NoopGroupAction | types_.NoopExternalRefAction:
            assert isinstance(action, types_.NoopAction)  # nosec
            report = _noop(action=action, discourse=discourse)
        case types_.UpdatePageAction | types_.UpdateGroupAction | types_.UpdateExternalRefAction:
            assert isinstance(action, types_.UpdateAction)  # nosec
            report = _update(action=action, discourse=discourse, dry_run=dry_run)
        case types_.DeletePageAction | types_.DeleteGroupAction | types_.DeleteExternalRefAction:
            assert isinstance(action, types_.DeleteAction)  # nosec
            report = _delete(
                action=action,
                discourse=discourse,
                dry_run=dry_run,
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
    action: types_.AnyIndexAction, discourse: Discourse, dry_run: bool
) -> types_.ActionReport:
    """Take the index action against the server.

    Args:
        action: The actions to take.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.

    Returns:
        A report on the outcome of executing the action.

    Raises:
        ActionError: if an action that is not handled is passed to the function.
    """
    logging.info("dry run: %s, action: %s", dry_run, action)

    if dry_run:
        report = types_.ActionReport(
            table_row=None,
            location=(
                DRY_RUN_NAVLINK_LINK
                if isinstance(action, types_.CreateIndexAction)
                else action.url
            ),
            result=types_.ActionResult.SKIP,
            reason=DRY_RUN_REASON,
        )
        logging.info("report: %s", report)
        return report

    match type(action):
        case types_.CreateIndexAction:
            try:
                # To help mypy (same for the rest of the asserts), it is ok if the assert does not
                # run
                assert isinstance(action, types_.CreateIndexAction)  # nosec
                url = discourse.create_topic(title=action.title, content=action.content)
                report = types_.ActionReport(
                    table_row=None, location=url, result=types_.ActionResult.SUCCESS, reason=None
                )
            except exceptions.DiscourseError as exc:
                report = types_.ActionReport(
                    table_row=None,
                    location=FAIL_NAVLINK_LINK,
                    result=types_.ActionResult.FAIL,
                    reason=str(exc),
                )
        case types_.NoopIndexAction:
            assert isinstance(action, types_.NoopIndexAction)  # nosec
            report = types_.ActionReport(
                table_row=None,
                location=action.url,
                result=types_.ActionResult.SUCCESS,
                reason=None,
            )
        case types_.UpdateIndexAction:
            try:
                assert isinstance(action, types_.UpdateIndexAction)  # nosec
                _log_content_change(base=action.content_change.old, new=action.content_change.new)
                discourse.update_topic(url=action.url, content=action.content_change.new)
                report = types_.ActionReport(
                    table_row=None,
                    location=action.url,
                    result=types_.ActionResult.SUCCESS,
                    reason=None,
                )
            except exceptions.DiscourseError as exc:
                assert isinstance(action, types_.UpdateIndexAction)  # nosec
                report = types_.ActionReport(
                    table_row=None,
                    location=action.url,
                    result=types_.ActionResult.FAIL,
                    reason=str(exc),
                )
        # Edge case that should not be possible
        case _:  # pragma: no cover
            raise exceptions.ActionError(
                f"internal error, no implementation for action, {action=!r}"
            )

    logging.info("report: %s", report)
    return report


def run_all(
    actions: typing.Iterable[types_.AnyAction],
    index: types_.Index,
    discourse: Discourse,
    dry_run: bool,
    delete_pages: bool,
) -> tuple[str, list[types_.ActionReport]]:
    """Take the actions against the server.

    Args:
        actions: The actions to take.
        index: Information about the index.
        discourse: A client to the documentation server.
        dry_run: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        A 2-element tuple with the index url and the reports of all the requested action.
    """
    action_reports = [
        _run_one(
            action=action,
            discourse=discourse,
            name=index.name,
            dry_run=dry_run,
            delete_pages=delete_pages,
        )
        for action in actions
    ]
    table_rows = (report.table_row for report in action_reports if report.table_row is not None)
    index_action = reconcile.index_page(index=index, table_rows=table_rows, discourse=discourse)
    index_action_report = _run_index(action=index_action, discourse=discourse, dry_run=dry_run)
    action_reports.append(index_action_report)
    return str(index_action_report.location), action_reports
