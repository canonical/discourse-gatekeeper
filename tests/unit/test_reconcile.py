# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for reconcile module."""

# Need access to protected functions for testing
# pylint: disable=protected-access

from pathlib import Path
from unittest import mock

import pytest

from src import discourse, exceptions, reconcile, types_


def test__local_only_file(tmp_path: Path):
    """
    arrange: given path info with a file
    act: when _local_only is called with the path info
    assert: then a create action with the file content is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path, level=1, table_path="table path 1", navlink_title="title 1"
    )

    returned_action = reconcile._local_only(path_info=path_info)

    assert returned_action.type_ == types_.ActionType.CREATE
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content == content


def test__local_only_directory(tmp_path: Path):
    """
    arrange: given path info with a directory
    act: when _local_only is called with the path info
    assert: then a create action for the directory is returned.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = types_.PathInfo(
        local_path=path, level=1, table_path="table path 1", navlink_title="title 1"
    )

    returned_action = reconcile._local_only(path_info=path_info)

    assert returned_action.type_ == types_.ActionType.CREATE
    assert returned_action.level == path_info.level
    assert returned_action.path == path_info.table_path
    assert returned_action.navlink_title == path_info.navlink_title
    assert returned_action.content is None


@pytest.mark.parametrize(
    "path_info_level, table_row_level, path_info_table_path, table_row_path",
    [
        pytest.param(1, 2, "table path 1", "table path 1", id="level mismatch"),
        pytest.param(1, 1, "table path 1", "table path 2", id="table path mismatch"),
        pytest.param(1, 2, "table path 1", "table path 2", id="level and table path mismatch"),
    ],
)
def test__local_and_server_error(
    path_info_level: int,
    table_row_level: int,
    path_info_table_path: str,
    table_row_path: str,
    tmp_path: Path,
):
    """
    arrange: given path info and table row where either level or table path or both do not match
    act: when _local_and_server is called with the path info and table row
    assert: ReconcilliationError is raised.
    """
    (path := tmp_path / "file1.md").touch()
    path_info = types_.PathInfo(
        local_path=path,
        level=path_info_level,
        table_path=path_info_table_path,
        navlink_title=(navlink_title := "title 1"),
    )
    navlink = types_.Navlink(title=navlink_title, link="link 1")
    table_row = types_.TableRow(level=table_row_level, path=table_row_path, navlink=navlink)
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)

    with pytest.raises(exceptions.ReconcilliationError):
        reconcile._local_and_server(
            path_info=path_info, table_row=table_row, discourse=mock_discourse
        )


def test__local_and_server_file_same(tmp_path: Path):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the same content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then a noop action is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = content
    navlink = types_.Navlink(title=navlink_title, link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.NOOP
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink == navlink  # type: ignore
    assert returned_action.content == content  # type: ignore
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


def test__local_and_server_file_content_change(tmp_path: Path):
    """
    arrange: given path info with a file and table row with no changes and discourse client that
        returns the different content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(local_content := "content 1", encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = (server_content := "content 2")
    navlink = types_.Navlink(title=navlink_title, link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.UPDATE
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == navlink  # type: ignore
    assert returned_action.content_change.old == server_content  # type: ignore
    assert returned_action.content_change.new == local_content  # type: ignore
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


def test__local_and_server_file_navlink_title_change(tmp_path: Path):
    """
    arrange: given path info with a file and table row with different navlink title and discourse
        client that returns the same content as in the file
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(local_navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = content
    navlink = types_.Navlink(title="title 2", link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.UPDATE
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == types_.Navlink(  # type: ignore
        title=local_navlink_title, link=navlink_link
    )
    assert returned_action.content_change.old == content  # type: ignore
    assert returned_action.content_change.new == content  # type: ignore
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


def test__local_and_server_directory_same(tmp_path: Path):
    """
    arrange: given path info with a directory and table row with no changes
    act: when _local_and_server is called with the path info and table row
    assert: then a noop action is returned.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    navlink = types_.Navlink(title=navlink_title, link=None)
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.NOOP
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink == navlink  # type: ignore
    assert returned_action.content is None  # type: ignore
    mock_discourse.retrieve_topic.assert_not_called()


def test__local_and_server_directory_navlink_title_changed(tmp_path: Path):
    """
    arrange: given path info with a directory and table row with different navlink title
    act: when _local_and_server is called with the path info and table row
    assert: then an update action is returned.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(local_navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    navlink = types_.Navlink(title="title 2", link=None)
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.UPDATE
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_change.old == navlink  # type: ignore
    assert returned_action.navlink_change.new == types_.Navlink(  # type: ignore
        title=local_navlink_title, link=None
    )
    assert returned_action.content_change is None  # type: ignore
    mock_discourse.retrieve_topic.assert_not_called()


def test__local_and_server_directory_to_file(tmp_path: Path):
    """
    arrange: given path info with a file and table row with a group
    act: when _local_and_server is called with the path info and table row
    assert: then a create action is returned.
    """
    (path := tmp_path / "file1.md").touch()
    path.write_text(content := "content 1", encoding="utf-8")
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    navlink = types_.Navlink(title=navlink_title, link=None)
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    (returned_action,) = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == types_.ActionType.CREATE
    assert returned_action.level == level
    assert returned_action.path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_action.navlink_title == navlink_title  # type: ignore
    assert returned_action.content == content  # type: ignore
    mock_discourse.retrieve_topic.assert_not_called()


def test__local_and_server_file_to_directory(tmp_path: Path):
    """
    arrange: given path info with a directory and table row with a file
    act: when _local_and_server is called with the path info and table row
    assert: then a delete and create action is returned.
    """
    (path := tmp_path / "dir1").mkdir()
    path_info = types_.PathInfo(
        local_path=path,
        level=(level := 1),
        table_path=(table_path := "table path 1"),
        navlink_title=(navlink_title := "title 1"),
    )
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = (content := "content 1")
    navlink = types_.Navlink(title=navlink_title, link=(navlink_link := "link 1"))
    table_row = types_.TableRow(level=level, path=table_path, navlink=navlink)

    returned_actions = reconcile._local_and_server(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert len(returned_actions) == 2
    assert returned_actions[0].type_ == types_.ActionType.DELETE
    assert returned_actions[0].level == level
    assert returned_actions[0].path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_actions[0].navlink == navlink  # type: ignore
    assert returned_actions[0].content == content  # type: ignore
    assert returned_actions[1].type_ == types_.ActionType.CREATE
    assert returned_actions[1].level == level
    assert returned_actions[1].path == table_path
    # mypy has difficulty with determining which action is returned
    assert returned_actions[1].navlink_title == navlink_title  # type: ignore
    assert returned_actions[1].content is None  # type: ignore
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink_link)


def test__server_only_file():
    """
    arrange: given table row with a file
    act: when _server_only is called with the table row
    assert: then a delete action with the file content is returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    mock_discourse.retrieve_topic.return_value = (content := "content 1")
    navlink = types_.Navlink(title="title 1", link="link 1")
    table_row = types_.TableRow(level=1, path="path 1", navlink=navlink)

    returned_action = reconcile._server_only(table_row=table_row, discourse=mock_discourse)

    assert returned_action.type_ == types_.ActionType.DELETE
    assert returned_action.level == table_row.level
    assert returned_action.path == table_row.path
    assert returned_action.navlink == table_row.navlink
    assert returned_action.content == content
    mock_discourse.retrieve_topic.assert_called_once_with(url=navlink.link)


def test__server_only_directory():
    """
    arrange: given table row with a directory
    act: when _server_only is called with the table row
    assert: then a delete action for the directory is returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    navlink = types_.Navlink(title="title 1", link=None)
    table_row = types_.TableRow(level=1, path="path 1", navlink=navlink)

    returned_action = reconcile._server_only(table_row=table_row, discourse=mock_discourse)

    assert returned_action.type_ == types_.ActionType.DELETE
    assert returned_action.level == table_row.level
    assert returned_action.path == table_row.path
    assert returned_action.navlink == table_row.navlink
    assert returned_action.content is None
    mock_discourse.retrieve_topic.assert_not_called()


def test__calculate_action_error():
    """
    arrange: given path info and table row that are None
    act: when _calculate_action is called with the path info and table row
    assert: then ReconcilliationError is raised.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)

    with pytest.raises(exceptions.ReconcilliationError):
        reconcile._calculate_action(path_info=None, table_row=None, discourse=mock_discourse)


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
    "path_info, table_row, expected_action",
    [
        pytest.param(
            types_.PathInfo(
                local_path=Path("dir1"), level=1, table_path="path 1", navlink_title="title 1"
            ),
            None,
            types_.ActionType.CREATE,
            id="path info defined table row None",
        ),
        pytest.param(
            types_.PathInfo(
                local_path=Path("dir1"),
                level=1,
                table_path=(path := "path 1"),
                navlink_title=(title := "title 1"),
            ),
            types_.TableRow(level=1, path=path, navlink=types_.Navlink(title=title, link=None)),
            types_.ActionType.NOOP,
            id="path info defined table row defined",
        ),
        pytest.param(
            None,
            types_.TableRow(
                level=1, path="path 1", navlink=types_.Navlink(title="title 1", link=None)
            ),
            types_.ActionType.DELETE,
            id="path info None table row defined",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test__calculate_action(
    path_info: types_.PathInfo | None,
    table_row: types_.TableRow | None,
    expected_action: types_.ActionType,
    tmp_path: Path,
):
    """
    arrange: given path info and table row for a directory and grouping
    act: when _calculate_action is called with the path info and table row
    assert: then the expected action is returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    if path_info is not None:
        path_info = path_info_mkdir(path_info=path_info, base_dir=tmp_path)

    (returned_action,) = reconcile._calculate_action(
        path_info=path_info, table_row=table_row, discourse=mock_discourse
    )

    assert returned_action.type_ == expected_action


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "path_infos, table_rows, expected_actions",
    [
        pytest.param((), (), (), id="empty path infos empty table rows"),
        pytest.param(
            (
                types_.PathInfo(
                    local_path=Path("dir1"), level=1, table_path="path 1", navlink_title="title 1"
                ),
            ),
            (),
            (types_.ActionType.CREATE,),
            id="single path info empty table rows",
        ),
        pytest.param(
            (
                types_.PathInfo(
                    local_path=Path("dir1"), level=1, table_path="path 1", navlink_title="title 1"
                ),
                types_.PathInfo(
                    local_path=Path("dir2"), level=2, table_path="path 2", navlink_title="title 2"
                ),
            ),
            (),
            (types_.ActionType.CREATE, types_.ActionType.CREATE),
            id="multiple path infos empty table rows",
        ),
        pytest.param(
            (),
            (
                types_.TableRow(
                    level=1, path="path 1", navlink=types_.Navlink(title="title 1", link=None)
                ),
            ),
            (types_.ActionType.DELETE,),
            id="empty path infos single table row",
        ),
        pytest.param(
            (),
            (
                types_.TableRow(
                    level=1, path="path 1", navlink=types_.Navlink(title="title 1", link=None)
                ),
                types_.TableRow(
                    level=2, path="path 2", navlink=types_.Navlink(title="title 2", link=None)
                ),
            ),
            (types_.ActionType.DELETE, types_.ActionType.DELETE),
            id="empty path infos multiple table rows",
        ),
        pytest.param(
            (
                types_.PathInfo(
                    local_path=Path("dir1"),
                    level=(level := 1),
                    table_path=(path := "path 1"),
                    navlink_title=(title := "title 1"),
                ),
            ),
            (
                types_.TableRow(
                    level=level, path=path, navlink=types_.Navlink(title=title, link=None)
                ),
            ),
            (types_.ActionType.NOOP,),
            id="single path info single table row match",
        ),
        pytest.param(
            (
                types_.PathInfo(
                    local_path=Path("dir1"),
                    level=1,
                    table_path=(path := "path 1"),
                    navlink_title=(title := "title 1"),
                ),
            ),
            (types_.TableRow(level=2, path=path, navlink=types_.Navlink(title=title, link=None)),),
            (types_.ActionType.CREATE, types_.ActionType.DELETE),
            id="single path info single table row level mismatch",
        ),
        pytest.param(
            (
                types_.PathInfo(
                    local_path=Path("dir1"),
                    level=(level := 1),
                    table_path="path 1",
                    navlink_title=(title := "title 1"),
                ),
            ),
            (
                types_.TableRow(
                    level=level, path="path 2", navlink=types_.Navlink(title=title, link=None)
                ),
            ),
            (types_.ActionType.CREATE, types_.ActionType.DELETE),
            id="single path info single table row path mismatch",
        ),
    ],
)
# pylint: enable=undefined-variable,unused-variable
def test_run(
    path_infos: tuple[types_.PathInfo, ...],
    table_rows: tuple[types_.TableRow, ...],
    expected_actions: tuple[types_.ActionType, ...],
    tmp_path: Path,
):
    """
    arrange: given path infos and table rows
    act: when run is called with the path infos and table rows
    assert: then the expected actions are returned.
    """
    mock_discourse = mock.MagicMock(spec=discourse.Discourse)
    path_infos = tuple(path_info_mkdir(path_info, base_dir=tmp_path) for path_info in path_infos)

    returned_actions = reconcile.run(
        path_infos=path_infos, table_rows=table_rows, discourse=mock_discourse
    )

    assert tuple(returned_action.type_ for returned_action in returned_actions) == expected_actions


# Pylint diesn't understand how the walrus operator works
# pylint: disable=undefined-variable,unused-variable
@pytest.mark.parametrize(
    "index, table_rows, expected_action",
    [
        pytest.param(
            types_.Index(
                server=None, local=types_.IndexFile(title=(local_title := "title 1"), content=None)
            ),
            (),
            types_.CreateIndexAction(
                type_=types_.ActionType.CREATE,
                title=local_title,
                content=f"{reconcile.NAVIGATION_TABLE_START}\n\n",
            ),
            id="empty local only empty rows",
        ),
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(
                    title=(local_title := "title 1"), content=(local_content := "content 1")
                ),
            ),
            (),
            types_.CreateIndexAction(
                type_=types_.ActionType.CREATE,
                title=local_title,
                content=f"{local_content}{reconcile.NAVIGATION_TABLE_START}\n\n",
            ),
            id="local only empty rows",
        ),
        pytest.param(
            types_.Index(
                server=None,
                local=types_.IndexFile(
                    title=(local_title := "title 1"), content=(local_content := "content 1")
                ),
            ),
            (
                table_row := types_.TableRow(
                    level=1,
                    path="path 1",
                    navlink=types_.Navlink(title="navlink title 1", link=None),
                ),
            ),
            types_.CreateIndexAction(
                type_=types_.ActionType.CREATE,
                title=local_title,
                content=(
                    f"{local_content}{reconcile.NAVIGATION_TABLE_START}\n"
                    f"{table_row.to_markdown()}\n"
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
            ),
            (
                table_row_1 := types_.TableRow(
                    level=1,
                    path="path 1",
                    navlink=types_.Navlink(title="navlink title 1", link=None),
                ),
                table_row_2 := types_.TableRow(
                    level=2,
                    path="path 2",
                    navlink=types_.Navlink(title="navlink title 2", link=None),
                ),
            ),
            types_.CreateIndexAction(
                type_=types_.ActionType.CREATE,
                title=local_title,
                content=(
                    f"{local_content}{reconcile.NAVIGATION_TABLE_START}\n"
                    f"{table_row_1.to_markdown()}\n{table_row_2.to_markdown()}\n"
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
                        server_content := f"{local_content}{reconcile.NAVIGATION_TABLE_START}\n\n"
                    ),
                ),
            ),
            (),
            types_.NoopIndexAction(
                type_=types_.ActionType.NOOP,
                content=server_content,
                url=url,
            ),
            id="local server same empty rows",
        ),
        pytest.param(
            types_.Index(
                local=types_.IndexFile(title="title 1", content=(local_content := "content 1")),
                server=types_.Page(url=(url := "url 1"), content=(server_content := "content 2")),
            ),
            (),
            types_.UpdateIndexAction(
                type_=types_.ActionType.UPDATE,
                content_change=types_.IndexContentChange(
                    old=server_content,
                    new=f"{local_content}{reconcile.NAVIGATION_TABLE_START}\n\n",
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
