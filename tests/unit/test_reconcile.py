# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for reconcile module."""
import typing
from pathlib import Path
from unittest import mock

import pytest

from src import constants, discourse, exceptions, reconcile, types_

from .. import factories
from .helpers import assert_substrings_in_string

# Need access to protected functions for testing, using walrus operator causes too-many-locals
# pylint: disable=protected-access,too-many-locals,too-many-lines


@pytest.mark.parametrize(
    "hidden", [pytest.param(False, id="not hidden"), pytest.param(True, id="hidden")]
)
def test__local_only_file(tmp_path: Path, hidden: bool):
    """
    arrange: given path info with a file
    act: when _local_only is called with the path info
    assert: then a create action with the file content is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path, navlink_hidden=hidden)

    returned_action = reconcile._local_only(path_info=path_info)

    assert isinstance(returned_action, types_.CreateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content == content
    assert returned_action.navlink_hidden == hidden


def test__local_only_directory(tmp_path: Path):
    """
    arrange: given path info with a directory
    act: when _local_only is called with the path info
    assert: then a create action for the directory is returned.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = factories.PathInfoFactory(local_path=path)

    returned_action = reconcile._local_only(path_info=path_info)

    assert isinstance(returned_action, types_.CreateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content is None
    assert returned_action.navlink_hidden is False


@pytest.mark.parametrize(
    "path_info_level, table_row_level, path_info_table_path, table_row_path",
    [
        pytest.param(1, 2, "table path 1", "table path 1", id="level mismatch"),
        pytest.param(1, 1, "table path 1", "table path 2", id="table path mismatch"),
        pytest.param(1, 2, "table path 1", "table path 2", id="level and table path mismatch"),
    ],
)
# The arguments are needed due to parametrisation and use of fixtures
def test__local_and_server_error(  # pylint: disable=too-many-arguments
    path_info_level: int,
    table_row_level: int,
    path_info_table_path: str,
    table_row_path: str,
    tmp_path: Path,
    mocked_clients,
):
    """
    arrange: given path info and table row where either level or table path or both do not match
    act: when _local_and_server is called with the path info and table row
    assert: ReconcilliationError is raised.
    """
    (path := tmp_path / "file1.md").touch()
    path_info = factories.PathInfoFactory(
        local_path=path, level=path_info_level, table_path=path_info_table_path
    )
    navlink = factories.NavlinkFactory(title=path_info.navlink_title, link="link 1")
    table_row = types_.TableRow(level=table_row_level, path=(table_row_path,), navlink=navlink)

    with pytest.raises(exceptions.ReconcilliationError):
        reconcile._local_and_server(
            path_info=path_info,
            table_row=table_row,
            clients=mocked_clients,
            base_path=tmp_path,
        )


def test__get_server_content_missing_link():
    """
    arrange: table row with None link
    act: when _get_server_content is called with table row
    assert: then ReconcilliationError is raised.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = "content 1"
    navlink = factories.NavlinkFactory(title="title 1", link=None)
    table_row = types_.TableRow(level=1, path=("table path 1",), navlink=navlink)

    with pytest.raises(exceptions.ReconcilliationError):
        reconcile._get_server_content(table_row=table_row, discourse=mock_discourse)


def test__get_server_content_server_error():
    """
    arrange: given table row and discourse client that raises an error
    act: when _get_server_content is called with the table row
    assert: then ServerError is raised.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.side_effect = exceptions.DiscourseError
    navlink = factories.NavlinkFactory(title="title 1", link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=1, path=("table path 1",), navlink=navlink)

    with pytest.raises(exceptions.ServerError) as exc_info:
        reconcile._get_server_content(table_row=table_row, discourse=mock_discourse)

    assert navlink_link in str(exc_info.value)


@pytest.mark.parametrize(
    "local_content, server_content",
    [
        pytest.param("content 1", "content 1", id="same"),
        pytest.param(" content 1", "content 1", id="server leading whitespace"),
        pytest.param("\ncontent 1", "content 1", id="server leading whitespace new line"),
        pytest.param("content 1 ", "content 1", id="server trailing whitespace"),
        pytest.param("content 1", " content 1", id="local leading whitespace"),
        pytest.param("content 1", "\ncontent 1", id="local leading whitespace new line"),
        pytest.param("content 1", "content 1 ", id="local trailing whitespace"),
    ],
)
def test__local_and_server_file_same(local_content: str, server_content: str, mocked_clients):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the same content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then a noop action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    (path := tmp_path / "file1.md").touch()
    path.write_text(local_content, encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = server_content
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.NoopAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink == navlink  # type: ignore
    assert returned_action.content == local_content.strip()  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_content_change_repo_error(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the different content as in the file and repository that raises an error
    act: when _local_and_server is called with the path info and table row
    assert: then ReconcilliationError is raised.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text("content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = "content 2"
    mock_get_file.side_effect = exceptions.RepositoryClientError
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    with pytest.raises(exceptions.ReconcilliationError) as exc_info:
        reconcile._local_and_server(
            path_info=path_info,
            table_row=table_row,
            clients=mocked_clients,
            base_path=tmp_path,
        )

    assert_substrings_in_string(
        ("unable", "retrieve", str(relative_path), constants.DOCUMENTATION_TAG),
        str(exc_info.value).lower(),
    )
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_content_change_repo_tag_not_found(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the different content as in the file and repository that raises a tag not found
        error
    act: when _local_and_server is called with the path info and table row
    assert: then ReconcilliationError is raised.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text("content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = "content 2"
    mock_get_file.side_effect = exceptions.RepositoryTagNotFoundError
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    with pytest.raises(exceptions.ReconcilliationError) as exc_info:
        reconcile._local_and_server(
            path_info=path_info,
            table_row=table_row,
            clients=mocked_clients,
            base_path=tmp_path,
        )

    assert_substrings_in_string(
        ("tag", "not", "defined", constants.DOCUMENTATION_TAG), str(exc_info.value).lower()
    )
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_content_change_file_not_in_repo(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the different content as in the file and repository that cannot find the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned with None for the base content.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text(local_content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = (server_content := "content 2")
    mock_get_file.side_effect = exceptions.RepositoryFileNotFoundError
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.UpdateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == navlink  # type: ignore
    assert returned_action.content_change.server == server_content  # type: ignore
    assert returned_action.content_change.local == local_content  # type: ignore
    assert returned_action.content_change.base is None  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_content_change(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the different content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text(local_content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = (server_content := "content 2")
    base_content = "content 3"
    mock_get_file.return_value = base_content
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.UpdateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == navlink  # type: ignore
    assert returned_action.content_change.server == server_content  # type: ignore
    assert returned_action.content_change.local == local_content  # type: ignore
    assert returned_action.content_change.base == base_content  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_navlink_title_change(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with different navlink title and discourse
        client that returns the same content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path, navlink_title="title 1")
    mocked_clients.discourse.retrieve_topic.return_value = content
    mock_get_file.return_value = content
    navlink = factories.NavlinkFactory(title="title 2", link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.UpdateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == factories.NavlinkFactory(  # type: ignore
        title=path_info.navlink_title, link=navlink_link
    )
    assert returned_action.content_change.server == content  # type: ignore
    assert returned_action.content_change.local == content  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_file_navlink_hidden_change(mock_get_file, mocked_clients):
    """
    arrange: given path info with a file and table row with different navlink hidden and discourse
        client that returns the same content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    relative_path = Path("file1.md")
    (path := tmp_path / relative_path).touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(
        local_path=path, navlink_title=(title := "title 1"), navlink_hidden=True
    )
    mocked_clients.discourse.retrieve_topic.return_value = content
    mock_get_file.return_value = content
    navlink = factories.NavlinkFactory(title=title, link=(navlink_link := "link 1"), hidden=False)
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.UpdateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == factories.NavlinkFactory(  # type: ignore
        title=path_info.navlink_title, link=navlink_link, hidden=True
    )
    assert returned_action.content_change.server == content  # type: ignore
    assert returned_action.content_change.local == content  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)
    mock_get_file.assert_called_once_with(
        path=str(relative_path), tag_name=constants.DOCUMENTATION_TAG
    )


@mock.patch("src.repository.Client.get_file_content_from_tag")
def test__local_and_server_directory_same(mock_get_file, mocked_clients):
    """
    arrange: given path info with a directory and table row with no changes
    act: when _local_and_server is called with the path info and table row
    assert: then a noop action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    (path := tmp_path / "dir1").mkdir()
    path_info = factories.PathInfoFactory(local_path=path)
    navlink = factories.NavlinkFactory(title=path_info.navlink_title, link=None)
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.NoopAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink == navlink  # type: ignore
    assert returned_action.content is None  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_not_called()
    mock_get_file.assert_not_called()


def test__local_and_server_directory_navlink_title_changed(mocked_clients):
    """
    arrange: given path info with a directory and table row with different navlink title
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    (path := tmp_path / "dir1").mkdir()
    path_info = factories.PathInfoFactory(local_path=path, navlink_title="title 1")
    navlink = factories.NavlinkFactory(title="title 2", link=None)
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.UpdateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == factories.NavlinkFactory(  # type: ignore
        title=path_info.navlink_title, link=None
    )
    assert returned_action.content_change is None  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_not_called()


@pytest.mark.parametrize(
    "hidden", [pytest.param(False, id="not hidden"), pytest.param(True, id="hidden")]
)
def test__local_and_server_directory_to_file(mocked_clients, hidden: bool):
    """
    arrange: given path info with a file and table row with a group
    act: when _local_and_server is called with the path info and table row
    assert: then a create action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = factories.PathInfoFactory(local_path=path, navlink_hidden=hidden)
    navlink = factories.NavlinkFactory(title=path_info.navlink_title, link=None, hidden=False)
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, types_.CreateAction)
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_title == path_info.navlink_title  # type: ignore
    assert returned_action.navlink_hidden == path_info.navlink_hidden  # type: ignore
    assert returned_action.content == content  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_not_called()


def test__local_and_server_file_to_directory(mocked_clients):
    """
    arrange: given path info with a directory and table row with a file
    act: when _local_and_server is called with the path info and table row
    assert: then a delete and create action is returned.
    """
    tmp_path = mocked_clients.repository.base_path

    (path := tmp_path / "dir1").mkdir()
    path_info = factories.PathInfoFactory(local_path=path)
    mocked_clients.discourse.retrieve_topic.return_value = (content := "content 1")
    navlink = factories.NavlinkFactory(
        title=path_info.navlink_title, link=(navlink_link := "link 1")
    )
    table_row = types_.TableRow(level=path_info.level, path=path_info.table_path, navlink=navlink)

    returned_actions = reconcile._local_and_server(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert len(returned_actions) == 2
    assert isinstance(returned_actions[0], types_.DeleteAction)
    assert returned_actions[0].level == path_info.level
    assert returned_actions[0].path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_actions[0].navlink == navlink  # type: ignore
    assert returned_actions[0].content == content  # type: ignore
    assert isinstance(returned_actions[1], types_.CreateAction)
    assert returned_actions[1].level == path_info.level
    assert returned_actions[1].path == path_info.table_path
    # mypy has difficulty with determining which action is returned
    assert returned_actions[1].navlink_title == path_info.navlink_title  # type: ignore
    assert returned_actions[1].content is None  # type: ignore
    mocked_clients.discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


def test__server_only_file():
    """
    arrange: given table row with a file
    act: when _server_only is called with the table row
    assert: then a delete action with the file content is returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = (content := "content 1")
    navlink = factories.NavlinkFactory(title="title 1", link="link 1")
    table_row = types_.TableRow(level=1, path=("path 1",), navlink=navlink)

    returned_action = reconcile._server_only(table_row=table_row, discourse=mock_discourse)

    assert isinstance(returned_action, types_.DeleteAction)
    assert returned_action.level == table_row.level
    assert returned_action.path == table_row.path
    assert returned_action.navlink == table_row.navlink
    assert returned_action.content == content
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink.link)


def test__server_only_file_discourse_error():
    """
    arrange: given table row with a file and mocked discourse that raises an error
    act: when _server_only is called with the table row
    assert: then ServerError is raised.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.side_effect = exceptions.DiscourseError
    navlink = factories.NavlinkFactory(title="title 1", link=(link := "link 1"))
    table_row = types_.TableRow(level=1, path=("path 1",), navlink=navlink)

    with pytest.raises(exceptions.ServerError) as exc_info:
        reconcile._server_only(table_row=table_row, discourse=mock_discourse)

    assert link in str(exc_info.value)


def test__server_only_directory():
    """
    arrange: given table row with a directory
    act: when _server_only is called with the table row
    assert: then a delete action for the directory is returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    navlink = factories.NavlinkFactory(title="title 1", link=None)
    table_row = types_.TableRow(level=1, path=("path 1",), navlink=navlink)

    returned_action = reconcile._server_only(table_row=table_row, discourse=mock_discourse)

    assert isinstance(returned_action, types_.DeleteAction)
    assert returned_action.level == table_row.level
    assert returned_action.path == table_row.path
    assert returned_action.navlink == table_row.navlink
    assert returned_action.content is None
    mock_discourse.retrieve_topic.assert_not_called()


def test__calculate_action_error(tmp_path: Path, mocked_clients):
    """
    arrange: given path info and table row that are None
    act: when _calculate_action is called with the path info and table row
    assert: then ReconcilliationError is raised.
    """
    with pytest.raises(exceptions.ReconcilliationError):
        reconcile._calculate_action(
            path_info=None,
            table_row=None,
            clients=mocked_clients,
            base_path=tmp_path,
        )


def path_info_mkdir(path_info: types_.PathInfo, base_dir: Path) -> types_.PathInfo:
    """Create the directory and update the path info.

    Args:
        path_info: The path info to update
        base_dir: The directory to create the directory within

    Returns:
        The path info with an updated path to the created directory.
    """
    (path := base_dir / path_info.local_path).mkdir()
    return types_.PathInfo(path, *path_info[1:])


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "path_info, table_row, expected_action_type",
    [
        pytest.param(
            factories.PathInfoFactory(),
            None,
            types_.CreateAction,
            id="path info defined table row None",
        ),
        pytest.param(
            factories.PathInfoFactory(
                level=1, table_path=(path := "path 1"), navlink_title=(title := "title 1")
            ),
            factories.TableRowFactory(
                level=1, path=path, navlink=factories.NavlinkFactory(title=title, link=None)
            ),
            types_.NoopAction,
            id="path info defined table row defined",
        ),
        pytest.param(
            None,
            factories.TableRowFactory(
                level=1, navlink=factories.NavlinkFactory(title=title, link=None)
            ),
            types_.DeleteAction,
            id="path info None table row defined",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test__calculate_action(
    path_info: types_.PathInfo | None,
    table_row: types_.TableRow | None,
    expected_action_type: type[types_.AnyAction],
    tmp_path: Path,
    mocked_clients,
):
    """
    arrange: given path info and table row for a directory and grouping
    act: when _calculate_action is called with the path info and table row
    assert: then the expected action type is returned.
    """
    if path_info is not None:
        path_info = path_info_mkdir(path_info=path_info, base_dir=tmp_path)

    (returned_action,) = reconcile._calculate_action(
        path_info=path_info,
        table_row=table_row,
        clients=mocked_clients,
        base_path=tmp_path,
    )

    assert isinstance(returned_action, expected_action_type)


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "path_infos, table_rows, expected_action_types, expected_level_paths",
    [
        pytest.param((), (), (), (), id="empty path infos empty table rows"),
        pytest.param(
            (path_info_1 := factories.PathInfoFactory(),),
            (),
            (types_.CreateAction,),
            ((path_info_1.level, path_info_1.table_path),),
            id="single path info empty table rows",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(alphabetical_rank=1),
                path_info_2 := factories.PathInfoFactory(alphabetical_rank=2),
            ),
            (),
            (types_.CreateAction, types_.CreateAction),
            (
                (path_info_1.level, path_info_1.table_path),
                (path_info_2.level, path_info_2.table_path),
            ),
            id="multiple path infos empty table rows",
        ),
        pytest.param(
            (
                path_info_1 := factories.PathInfoFactory(alphabetical_rank=2),
                path_info_2 := factories.PathInfoFactory(alphabetical_rank=1),
            ),
            (),
            (types_.CreateAction, types_.CreateAction),
            (
                (path_info_1.level, path_info_1.table_path),
                (path_info_2.level, path_info_2.table_path),
            ),
            id="multiple path infos empty table rows alternate order",
        ),
        pytest.param(
            (),
            (table_row_1 := factories.TableRowFactory(level=1, path=("path 1",), is_group=True),),
            (types_.DeleteAction,),
            ((table_row_1.level, table_row_1.path),),
            id="empty path infos single table row",
        ),
        pytest.param(
            (),
            (
                table_row_1 := factories.TableRowFactory(level=1, path=("path 1",), is_group=True),
                table_row_2 := factories.TableRowFactory(level=2, path=("path 2",), is_group=True),
            ),
            (types_.DeleteAction, types_.DeleteAction),
            ((table_row_1.level, table_row_1.path), (table_row_2.level, table_row_2.path)),
            id="empty path infos multiple table rows",
        ),
        pytest.param(
            (path_info_1 := factories.PathInfoFactory(),),
            (
                factories.TableRowFactory(
                    level=path_info_1.level,
                    path=path_info_1.table_path,
                    navlink=factories.NavlinkFactory(title=path_info_1.navlink_title, link=None),
                ),
            ),
            (types_.NoopAction,),
            ((path_info_1.level, path_info_1.table_path),),
            id="single path info single table row match",
        ),
        pytest.param(
            (path_info_1 := factories.PathInfoFactory(level=1),),
            (
                table_row_1 := factories.TableRowFactory(
                    level=2, path=("group-1",) + path_info_1.table_path, is_group=True
                ),
            ),
            (types_.CreateAction, types_.DeleteAction),
            (
                (path_info_1.level, path_info_1.table_path),
                (table_row_1.level, ("group-1",) + path_info_1.table_path),
            ),
            id="single path info single table row level mismatch",
        ),
        pytest.param(
            (path_info_1 := factories.PathInfoFactory(table_path=("path 1",)),),
            (
                table_row := factories.TableRowFactory(
                    level=path_info_1.level, path=("path 2",), is_group=True
                ),
            ),
            (types_.CreateAction, types_.DeleteAction),
            ((path_info_1.level, path_info_1.table_path), (path_info_1.level, table_row.path)),
            id="single path info single table row path mismatch",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
# The arguments are needed due to parametrisation and use of fixtures
def test_run(  # pylint: disable=too-many-arguments
    path_infos: tuple[types_.PathInfo, ...],
    table_rows: tuple[types_.TableRow, ...],
    expected_action_types: tuple[type[types_.AnyAction], ...],
    expected_level_paths: tuple[tuple[types_.Level, types_.TablePath], ...],
    tmp_path: Path,
    mocked_clients,
):
    """
    arrange: given path infos and table rows
    act: when run is called with the path infos and table rows
    assert: then the expected actions are returned in the expected order.
    """
    path_infos = tuple(path_info_mkdir(path_info, base_dir=tmp_path) for path_info in path_infos)

    returned_actions = list(
        reconcile.run(
            sorted_path_infos=path_infos,
            table_rows=table_rows,
            clients=mocked_clients,
            base_path=tmp_path,
        )
    )

    assert (
        tuple(type(returned_action) for returned_action in returned_actions)
        == expected_action_types
    )
    assert (
        tuple(
            (returned_action.level, returned_action.path) for returned_action in returned_actions
        )
        == expected_level_paths
    )


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "index, table_rows, expected_action",
    [
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(title=(local_title := "title 1"), content=None),
                name="name 1",
            ),
            (),
            types_.CreateIndexAction(
                title=local_title, content=f"{constants.NAVIGATION_TABLE_START.strip()}"
            ),
            id="empty local only empty rows",
        ),
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(
                    title=(local_title := "title 1"), content=(local_content := "content 1")
                ),
                name="name 1",
            ),
            (),
            types_.CreateIndexAction(
                title=local_title, content=f"{local_content}{constants.NAVIGATION_TABLE_START}"
            ),
            id="local only empty rows",
        ),
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(
                    title=(local_title := "title 1"), content=(local_content := "content 1")
                ),
                name="name 1",
            ),
            (table_row := factories.TableRowFactory(level=1),),
            types_.CreateIndexAction(
                title=local_title,
                content=(
                    f"{local_content}{constants.NAVIGATION_TABLE_START}\n"
                    f"{table_row.to_markdown()}"
                ),
            ),
            id="local only single row",
        ),
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(
                    title=(local_title := "title 1"), content=(local_content := "content 1")
                ),
                name="name 1",
            ),
            (
                table_row_1 := factories.TableRowFactory(level=1),
                table_row_2 := factories.TableRowFactory(level=2),
            ),
            types_.CreateIndexAction(
                title=local_title,
                content=(
                    f"{local_content}{constants.NAVIGATION_TABLE_START}\n"
                    f"{table_row_1.to_markdown()}\n{table_row_2.to_markdown()}"
                ),
            ),
            id="local only multiple rows",
        ),
        pytest.param(
            types_.Index(
                local=types_.IndexFile(title="title 1", content=(local_content := "content 1")),
                server=types_.Page(
                    url=(url := "url 1"),
                    content=(
                        server_content := f"{local_content}{constants.NAVIGATION_TABLE_START}"
                    ),
                ),
                name="name 1",
            ),
            (),
            types_.NoopIndexAction(content=server_content, url=url),
            id="local server same empty rows",
        ),
        pytest.param(
            types_.Index(
                local=types_.IndexFile(title="title 1", content=(local_content := "content 1")),
                server=types_.Page(
                    url=(url := "url 1"),
                    content=(
                        server_content := f" {local_content}{constants.NAVIGATION_TABLE_START}"
                    ),
                ),
                name="name 1",
            ),
            (),
            types_.NoopIndexAction(content=server_content[1:], url=url),
            id="local server whitespace different same empty rows",
        ),
        pytest.param(
            types_.Index(
                local=types_.IndexFile(title="title 1", content=(local_content := " content 1")),
                server=types_.Page(
                    url=(url := "url 1"),
                    content=(
                        server_content := f"{local_content.strip()}"
                        f"{constants.NAVIGATION_TABLE_START}"
                    ),
                ),
                name="name 1",
            ),
            (),
            types_.NoopIndexAction(content=server_content, url=url),
            id="local whitespace server different same empty rows",
        ),
        pytest.param(
            types_.Index(
                local=types_.IndexFile(title="title 1", content=(local_content := "content 1")),
                server=types_.Page(url=(url := "url 1"), content=(server_content := "content 2")),
                name="name 1",
            ),
            (),
            types_.UpdateIndexAction(
                content_change=types_.IndexContentChange(
                    old=server_content,
                    new=f"{local_content}{constants.NAVIGATION_TABLE_START}",
                ),
                url=url,
            ),
            id="local server different empty rows",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_index_page(
    index: types_.Index,
    table_rows: tuple[types_.TableRow],
    expected_action: types_.AnyIndexAction,
):
    """
    arrange: given index information and server and local table rows
    act: when index_page is called with the index and server and table rows
    assert: then the expected action is returned.
    """
    returned_action = reconcile.index_page(index=index, table_rows=table_rows)

    assert returned_action == expected_action


@pytest.mark.parametrize(
    "actions, expected_value",
    [
        pytest.param(
            [types_.NoopAction(1, tuple("path"), types_.Navlink("title", None, True), None)],
            True,
            id="Noop action",
        ),
        pytest.param(
            [types_.CreateAction(1, tuple("path"), "title", None, True)], False, id="Create action"
        ),
        pytest.param(
            [types_.DeleteAction(1, tuple("path"), types_.Navlink("title", None, True), None)],
            False,
            id="Delete action",
        ),
        pytest.param(
            [
                types_.UpdateAction(
                    1,
                    tuple("path"),
                    types_.NavlinkChange(
                        types_.Navlink("title", None, True), types_.Navlink("title", None, True)
                    ),
                    types_.ContentChange(None, "one", "two"),
                )
            ],
            False,
            id="Update action with different content",
        ),
        pytest.param(
            [
                types_.UpdateAction(
                    1,
                    tuple("path"),
                    types_.NavlinkChange(
                        types_.Navlink("title", None, True), types_.Navlink("title", None, True)
                    ),
                    types_.ContentChange(None, "same", "same"),
                )
            ],
            True,
            id="Update action with same content",
        ),
    ],
)
def test__is_same_content_actions(
    actions: typing.Iterable[types_.AnyAction], expected_value: bool
):
    """
    arrange: given some mock list of actions and an index with matching local and server content
    act: when is_same_content function is called
    assert: then the correct results is returned.
    """
    index = types_.Index(
        types_.Page("index-url", "index-content"),
        types_.IndexFile("index-title", "index-content"),
        "charm",
    )

    assert reconcile.is_same_content(index, actions) == expected_value


@pytest.mark.parametrize(
    "index, expected_value",
    [
        pytest.param(
            types_.Index(
                types_.Page("index-url", "index-content"),
                types_.IndexFile("index-title", "index-content"),
                "charm",
            ),
            True,
            id="same index",
        ),
        pytest.param(
            types_.Index(
                types_.Page("index-url", "index-content"),
                types_.IndexFile("index-title", "index-content-different"),
                "charm",
            ),
            False,
            id="different index",
        ),
        pytest.param(
            types_.Index(
                None, types_.IndexFile("index-title", "index-content-different"), "charm"
            ),
            False,
            id="missing server content",
        ),
        pytest.param(
            types_.Index(
                types_.Page("index-url", "index-content"),
                types_.IndexFile("index-title", None),
                "charm",
            ),
            False,
            id="missing local content",
        ),
    ],
)
def test__is_same_content_index(index: types_.Index, expected_value: bool):
    """
    arrange: given some mock Index object and an action list that only contains a NoopAction
    act: when is_same_content function is called
    assert: then the correct results is returned.
    """
    actions = [types_.NoopAction(1, tuple("path"), types_.Navlink("title", None, True), None)]

    assert reconcile.is_same_content(index, actions) == expected_value
