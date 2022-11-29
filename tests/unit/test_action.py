# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for action."""

# Need access to protected functions for testing
# pylint: disable=protected-access

import logging
import types
from unittest import mock

import pytest

from src import action, discourse, exceptions
from src import types_ as src_types


@pytest.mark.parametrize(
    "draft_mode",
    [pytest.param(True, id="draft mode enabled"), pytest.param(False, id="draft mode disabled")],
)
def test__create_directory(draft_mode: bool, caplog: pytest.LogCaptureFixture):
    """
    arrange: given create action for a directory, draft mode and mocked discourse
    act: when action is passed to _create with draft_mode
    assert: then no topic is created, the action is logged and a skip report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    create_action = src_types.CreateAction(
        type_=src_types.ActionType.CREATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_title=(navlink_title := "title 1"),
        content=None,
    )

    returned_report = action._create(
        action=create_action, discourse=mocked_discourse, draft_mode=draft_mode
    )

    assert str(create_action) in caplog.text
    assert f"draft mode: {draft_mode}" in caplog.text
    mocked_discourse.create_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link is None
    assert returned_report.url is None
    assert (
        returned_report.result == src_types.ActionResult.SKIP
        if draft_mode
        else src_types.ActionResult.SUCCESS
    )
    assert returned_report.reason == (action.DRAFT_MODE_REASON if draft_mode else None)


def test__create_file_draft_mode(caplog: pytest.LogCaptureFixture):
    """
    arrange: given create action for a file and mocked discourse
    act: when action is passed to _create with draft_mode True
    assert: then no topic is created, the action is logged and a skip report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    create_action = src_types.CreateAction(
        type_=src_types.ActionType.CREATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_title=(navlink_title := "title 1"),
        content="content 1",
    )

    returned_report = action._create(
        action=create_action, discourse=mocked_discourse, draft_mode=True
    )

    assert str(create_action) in caplog.text
    assert f"draft mode: {True}" in caplog.text
    mocked_discourse.create_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link == action.DRAFT_NAVLINK_LINK
    assert returned_report.url == action.DRAFT_NAVLINK_LINK
    assert returned_report.result == src_types.ActionResult.SKIP
    assert returned_report.reason == action.DRAFT_MODE_REASON


def test__create_file_fail(caplog: pytest.LogCaptureFixture):
    """
    arrange: given create action for a file and mocked discourse that raises an error
    act: when action is passed to _create with draft_mode False
    assert: then no topic is created, the action is logged and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    create_action = src_types.CreateAction(
        type_=src_types.ActionType.CREATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_title=(navlink_title := "title 1"),
        content=(content := "content 1"),
    )

    returned_report = action._create(
        action=create_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(create_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.create_topic.assert_called_once_with(title=navlink_title, content=content)
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link == action.FAIL_NAVLINK_LINK
    assert returned_report.url == action.FAIL_NAVLINK_LINK
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__create_file(caplog: pytest.LogCaptureFixture):
    """
    arrange: given create action for a file and mocked discourse
    act: when action is passed to _create with draft_mode False
    assert: then no topic is created, the action is logged and a success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")
    create_action = src_types.CreateAction(
        type_=src_types.ActionType.CREATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_title=(navlink_title := "title 1"),
        content=(content := "content 1"),
    )

    returned_report = action._create(
        action=create_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(create_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.create_topic.assert_called_once_with(title=navlink_title, content=content)
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink.title == navlink_title
    assert returned_report.table_row.navlink.link == url
    assert returned_report.url == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "noop_action, expected_table_row",
    [
        pytest.param(
            src_types.NoopAction(
                type_=src_types.ActionType.NOOP,
                level=(level := 1),
                path=(path := "path 1"),
                navlink=(navlink := src_types.Navlink(title="title 1", link=None)),
                content=None,
            ),
            src_types.TableRow(level=level, path=path, navlink=navlink),
            id="directory",
        ),
        pytest.param(
            src_types.NoopAction(
                type_=src_types.ActionType.NOOP,
                level=(level := 1),
                path=(path := "path 1"),
                navlink=(navlink := src_types.Navlink(title="title 1", link="link 1")),
                content="content 1",
            ),
            src_types.TableRow(level=level, path=path, navlink=navlink),
            id="file",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test__noop(
    noop_action: src_types.NoopAction,
    expected_table_row: src_types.TableRow,
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given noop action
    act: when action is passed to _noop
    assert: then the action is logged and a success report is returned.
    """
    caplog.set_level(logging.INFO)

    returned_report = action._noop(action=noop_action)

    assert str(noop_action) in caplog.text
    assert returned_report.table_row == expected_table_row
    assert returned_report.url == expected_table_row.navlink.link
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


@pytest.mark.parametrize(
    "draft_mode",
    [pytest.param(True, id="draft mode enabled"), pytest.param(False, id="draft mode disabled")],
)
def test__update_directory(draft_mode: bool, caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a directory, draft mode and mocked discourse
    act: when action is passed to _update with draft_mode
    assert: then no topic is updated, the action is logged and the expected report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=None),
            new=src_types.Navlink(title="title 2", link=None),
        ),
        content_change=None,
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, draft_mode=draft_mode
    )

    assert str(update_action) in caplog.text
    assert f"draft mode: {draft_mode}" in caplog.text
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.url is None
    assert (
        returned_report.result == src_types.ActionResult.SKIP
        if draft_mode
        else src_types.ActionResult.SUCCESS
    )
    assert returned_report.reason == (action.DRAFT_MODE_REASON if draft_mode else None)


def test__update_file_draft_mode(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file and mocked discourse
    act: when action is passed to _update with draft_mode True
    assert: then no topic is updated, the action is logged and a skip report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link="link 1"),
            new=src_types.Navlink(title="title 2", link="link 2"),
        ),
        content_change=src_types.ContentChange(old="content 1", new="content 2"),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, draft_mode=True
    )

    assert str(update_action) in caplog.text
    assert f"draft mode: {True}" in caplog.text
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.url == action.DRAFT_NAVLINK_LINK
    assert returned_report.result == src_types.ActionResult.SKIP
    assert returned_report.reason == action.DRAFT_MODE_REASON


def test__update_file_navlink_title_change(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where only the navlink title has changed and mocked
        discourse
    act: when action is passed to _update with draft_mode False
    assert: then no topic is updated, the action is logged and the expected table row is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(old=(content := "content 1"), new=content),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(update_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.url == link
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


def test__update_file_navlink_content_change_discourse_error(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where content has changed and mocked discourse that
        raises an error
    act: when action is passed to _update with draft_mode False
    assert: then topic is updated, the action is logged and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.update_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(old="content 1", new="content 2"),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(update_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_called_once_with(
        url=link, content=update_action.content_change.new
    )
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.url == link
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__update_file_navlink_content_change(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update action for a file where content has changed and mocked discourse
    act: when action is passed to _update with draft_mode False
    assert: then topic is updated, the action is logged and success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=(level := 1),
        path=(path := "path 1"),
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=src_types.ContentChange(old="content 1", new="content 2"),
    )

    returned_report = action._update(
        action=update_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(update_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    assert update_action.content_change is not None
    mocked_discourse.update_topic.assert_called_once_with(
        url=link, content=update_action.content_change.new
    )
    assert returned_report.table_row is not None
    assert returned_report.table_row.level == level
    assert returned_report.table_row.path == path
    assert returned_report.table_row.navlink == update_action.navlink_change.new
    assert returned_report.url == link
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


@pytest.mark.parametrize(
    "content_change",
    [
        pytest.param(None, id="None"),
        pytest.param(src_types.ContentChange(old="content 1", new=None), id="new is None"),
    ],
)
def test__update_file_navlink_content_change_error(content_change: src_types.ContentChange | None):
    """
    arrange: given update action for a file where content has changed to None
    act: when action is passed to _update with draft_mode False
    assert: ActionError is raised.
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    update_action = src_types.UpdateAction(
        type_=src_types.ActionType.UPDATE,
        level=1,
        path="path 1",
        navlink_change=src_types.NavlinkChange(
            old=src_types.Navlink(title="title 1", link=(link := "link 1")),
            new=src_types.Navlink(title="title 2", link=link),
        ),
        content_change=content_change,
    )

    with pytest.raises(exceptions.ActionError):
        action._update(action=update_action, discourse=mocked_discourse, draft_mode=False)


@pytest.mark.parametrize(
    "draft_mode, delete_pages, navlink_link, expected_result, expected_reason",
    [
        pytest.param(
            True,
            True,
            "link 1",
            src_types.ActionResult.SKIP,
            action.DRAFT_MODE_REASON,
            id="draft mode enabled",
        ),
        pytest.param(
            False,
            False,
            "link 1",
            src_types.ActionResult.SKIP,
            action.NOT_DELETE_REASON,
            id="delete pages false enabled",
        ),
        pytest.param(False, True, None, src_types.ActionResult.SUCCESS, None, id="directory"),
    ],
)
# Simplifying the test would mean needing to write many more tests instead of parametrize
# pylint: disable=too-many-arguments
def test__delete_not_delete(
    draft_mode: bool,
    delete_pages: bool,
    navlink_link: str | None,
    expected_result: src_types.ActionResult,
    expected_reason: str | None,
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given delete action with given navlink link, draft mode and whether to delete pages
    act: when action is passed to _delete with draft_mode and whether to delete pages
    assert: then no topic is deleted, the action is logged and the expected report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    delete_action = src_types.DeleteAction(
        type_=src_types.ActionType.DELETE,
        level=1,
        path="path 1",
        navlink=src_types.Navlink(title="title 1", link=navlink_link),
        content="content 1",
    )

    returned_report = action._delete(
        action=delete_action,
        discourse=mocked_discourse,
        draft_mode=draft_mode,
        delete_pages=delete_pages,
    )

    assert str(delete_action) in caplog.text
    assert f"draft mode: {draft_mode}" in caplog.text
    assert f"delete pages: {delete_pages}" in caplog.text
    mocked_discourse.delete_topic.assert_not_called()
    assert returned_report.table_row is None
    assert returned_report.url == navlink_link
    assert returned_report.result == expected_result
    assert returned_report.reason == expected_reason


def test__delete_error(caplog: pytest.LogCaptureFixture):
    """
    arrange: given delete action for file
    act: when action is passed to _delete with draft_mode False and whether to delete pages True
    assert: then topic is deleted and the action is logged and a success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.delete_topic.side_effect = (error := exceptions.DiscourseError("fail"))
    delete_action = src_types.DeleteAction(
        type_=src_types.ActionType.DELETE,
        level=1,
        path="path 1",
        navlink=src_types.Navlink(title="title 1", link=(link := "link 1")),
        content="content 1",
    )

    returned_report = action._delete(
        action=delete_action,
        discourse=mocked_discourse,
        draft_mode=False,
        delete_pages=True,
    )

    assert str(delete_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    assert f"delete pages: {True}" in caplog.text
    mocked_discourse.delete_topic.assert_called_once_with(url=link)
    assert returned_report.table_row is None
    assert returned_report.url == link
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__delete(caplog: pytest.LogCaptureFixture):
    """
    arrange: given delete action for file
    act: when action is passed to _delete with draft_mode False and whether to delete pages True
    assert: then topic is deleted and the action is logged and a success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    delete_action = src_types.DeleteAction(
        type_=src_types.ActionType.DELETE,
        level=1,
        path="path 1",
        navlink=src_types.Navlink(title="title 1", link=(link := "link 1")),
        content="content 1",
    )

    returned_report = action._delete(
        action=delete_action,
        discourse=mocked_discourse,
        draft_mode=False,
        delete_pages=True,
    )

    assert str(delete_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    assert f"delete pages: {True}" in caplog.text
    mocked_discourse.delete_topic.assert_called_once_with(url=link)
    assert returned_report.table_row is None
    assert returned_report.url == link
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


@pytest.mark.parametrize(
    "test_action, expected_return_type",
    [
        pytest.param(
            src_types.CreateAction(
                type_=src_types.ActionType.CREATE,
                level=1,
                path="path 1",
                navlink_title="title 1",
                content=None,
            ),
            src_types.TableRow,
            id="create",
        ),
        pytest.param(
            src_types.NoopAction(
                type_=src_types.ActionType.NOOP,
                level=1,
                path="path 1",
                navlink=src_types.Navlink(title="title 1", link=None),
                content=None,
            ),
            src_types.TableRow,
            id="noop",
        ),
        pytest.param(
            src_types.UpdateAction(
                type_=src_types.ActionType.UPDATE,
                level=1,
                path="path 1",
                navlink_change=src_types.NavlinkChange(
                    old=src_types.Navlink(title="title 1", link=None),
                    new=src_types.Navlink(title="title 1", link=None),
                ),
                content_change=None,
            ),
            src_types.TableRow,
            id="update",
        ),
        pytest.param(
            src_types.DeleteAction(
                type_=src_types.ActionType.DELETE,
                level=1,
                path="path 1",
                navlink=src_types.Navlink(title="title 1", link=None),
                content=None,
            ),
            types.NoneType,
            id="delete",
        ),
    ],
)
def test__run_one(test_action: src_types.AnyAction, expected_return_type: type):
    """
    arrange: given action
    act: when _run_one is called with the action
    assert: then the expected report is returned
    """
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    returned_report = action._run_one(
        action=test_action, discourse=mocked_discourse, draft_mode=False, delete_pages=True
    )

    assert isinstance(returned_report.table_row, expected_return_type)


@pytest.mark.parametrize(
    "index_action",
    [
        pytest.param(
            src_types.CreateIndexAction(
                type_=src_types.ActionType.CREATE, title="title 1", content="content 1"
            ),
            id="create",
        ),
        pytest.param(
            src_types.NoopIndexAction(
                type_=src_types.ActionType.NOOP, url="url 1", content="content 1"
            ),
            id="noop",
        ),
        pytest.param(
            src_types.UpdateIndexAction(
                type_=src_types.ActionType.UPDATE,
                url="url 1",
                content_change=src_types.IndexContentChange(old="content 1", new="content 2"),
            ),
            id="update",
        ),
    ],
)
def test__run_index_draft_mode(
    index_action: src_types.AnyIndexAction, caplog: pytest.LogCaptureFixture
):
    """
    arrange: given index action and mocked discourse
    act: when action is passed to _run_index with draft_mode True and mocked discourse
    assert: then the action is logged, no functions are called on mocked discourse and skip report
        is returned
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)

    action_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=True
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {True}" in caplog.text
    mocked_discourse.create_topic.assert_not_called()
    mocked_discourse.update_topic.assert_not_called()
    assert action_report.table_row is None
    assert action_report.url == action.DRAFT_NAVLINK_LINK
    assert action_report.result == src_types.ActionResult.SKIP
    assert action_report.reason == action.DRAFT_MODE_REASON


def test__run_index_create_error(caplog: pytest.LogCaptureFixture):
    """
    arrange: given create index action, draft mode and mocked discourse that raises an error
    act: when action is passed to _run_index and mocked discourse
    assert: then the action is logged, and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    index_action = src_types.CreateIndexAction(
        type_=src_types.ActionType.CREATE,
        title=(title := "title 1"),
        content=(content := "content 1"),
    )

    returned_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.create_topic.assert_called_once_with(title=title, content=content)
    assert returned_report.table_row is None
    assert returned_report.url == action.FAIL_NAVLINK_LINK
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__run_index_create(caplog: pytest.LogCaptureFixture):
    """
    arrange: given create index action and mocked discourse
    act: when action is passed to _run_index with dfraft mode False and mocked discourse
    assert: then the action is logged, the topic is created and a success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")
    index_action = src_types.CreateIndexAction(
        type_=src_types.ActionType.CREATE,
        title=(title := "title 1"),
        content=(content := "content 1"),
    )

    returned_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.create_topic.assert_called_once_with(title=title, content=content)
    assert returned_report.table_row is None
    assert returned_report.url == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


def test__run_index_noop(caplog: pytest.LogCaptureFixture):
    """
    arrange: given noop index action, draft mode and mocked discourse
    act: when action is passed to _run_index with dfraft mode False and mocked discourse
    assert: then the action is logged, no topic is created or updated and a success report is
        returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    index_action = src_types.NoopIndexAction(
        type_=src_types.ActionType.NOOP, url=(url := "url 1"), content="content 1"
    )

    returned_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.create_topic.assert_not_called()
    mocked_discourse.update_topic.assert_not_called()
    assert returned_report.table_row is None
    assert returned_report.url == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


def test__run_index_update_error(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update index action, draft mode and mocked discourse that raises an error
    act: when action is passed to _run_index and mocked discourse
    assert: then the action is logged and a fail report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.update_topic.side_effect = (error := exceptions.DiscourseError("failed"))
    index_action = src_types.UpdateIndexAction(
        type_=src_types.ActionType.UPDATE,
        url=(url := "url 1"),
        content_change=src_types.IndexContentChange(old="content 1", new=(content := "content 2")),
    )

    returned_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.update_topic.assert_called_once_with(url=url, content=content)
    assert returned_report.table_row is None
    assert returned_report.url == url
    assert returned_report.result == src_types.ActionResult.FAIL
    assert returned_report.reason == str(error)


def test__run_index_update(caplog: pytest.LogCaptureFixture):
    """
    arrange: given update index action and mocked discourse
    act: when action is passed to _run_index with dfraft mode False and mocked discourse
    assert: then the action is logged, the topic is updated and a success report is returned.
    """
    caplog.set_level(logging.INFO)
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    index_action = src_types.UpdateIndexAction(
        type_=src_types.ActionType.UPDATE,
        url=(url := "url 1"),
        content_change=src_types.IndexContentChange(old="content 1", new=(content := "content 2")),
    )

    returned_report = action._run_index(
        action=index_action, discourse=mocked_discourse, draft_mode=False
    )

    assert str(index_action) in caplog.text
    assert f"draft mode: {False}" in caplog.text
    mocked_discourse.update_topic.assert_called_once_with(url=url, content=content)
    assert returned_report.table_row is None
    assert returned_report.url == url
    assert returned_report.result == src_types.ActionResult.SUCCESS
    assert returned_report.reason is None


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable,too-many-locals
@pytest.mark.parametrize(
    "actions, expected_reports",
    [
        pytest.param((), [], id="empty"),
        pytest.param(
            (
                src_types.NoopAction(
                    type_=src_types.ActionType.NOOP,
                    level=(level := 1),
                    path=(path := "path 1"),
                    navlink=(
                        navlink := src_types.Navlink(title="title 1", link=(link := "link 1"))
                    ),
                    content="content 1",
                ),
            ),
            [
                src_types.ActionReport(
                    table_row=src_types.TableRow(level=level, path=path, navlink=navlink),
                    url=link,
                    result=src_types.ActionResult.SUCCESS,
                    reason=None,
                )
            ],
            id="single",
        ),
        pytest.param(
            (
                src_types.NoopAction(
                    type_=src_types.ActionType.NOOP,
                    level=(level_1 := 1),
                    path=(path_1 := "path 1"),
                    navlink=(
                        navlink_1 := src_types.Navlink(title="title 1", link=(link_1 := "link 1"))
                    ),
                    content="content 1",
                ),
                src_types.NoopAction(
                    type_=src_types.ActionType.NOOP,
                    level=(level_2 := 2),
                    path=(path_2 := "path 2"),
                    navlink=(
                        navlink_2 := src_types.Navlink(title="title 2", link=(link_2 := "link 2"))
                    ),
                    content="content 2",
                ),
            ),
            [
                src_types.ActionReport(
                    table_row=src_types.TableRow(level=level_1, path=path_1, navlink=navlink_1),
                    url=link_1,
                    result=src_types.ActionResult.SUCCESS,
                    reason=None,
                ),
                src_types.ActionReport(
                    table_row=src_types.TableRow(level=level_2, path=path_2, navlink=navlink_2),
                    url=link_2,
                    result=src_types.ActionResult.SUCCESS,
                    reason=None,
                ),
            ],
            id="multiple",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_run_all(
    actions: tuple[src_types.AnyAction, ...], expected_reports: list[src_types.ActionReport]
):
    """
    arrange: given actions and index
    act: when run_all is called with the actions
    assert: then the expected actions are returned.
    """
    index = src_types.Index(server=None, local=src_types.IndexFile(title="title 1", content=None))
    mocked_discourse = mock.MagicMock(spec=discourse.Discourse)
    mocked_discourse.create_topic.return_value = (url := "url 1")

    returned_reports = action.run_all(
        actions=actions,
        index=index,
        discourse=mocked_discourse,
        draft_mode=False,
        delete_pages=True,
    )

    expected_reports.append(
        src_types.ActionReport(
            table_row=None, url=url, result=src_types.ActionResult.SUCCESS, reason=None
        )
    )
    assert returned_reports == expected_reports


# Need this after the function as locals from parametrize also go to function
# pylint: enable=too-many-locals
