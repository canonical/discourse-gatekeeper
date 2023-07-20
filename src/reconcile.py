# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for calculating required changes based on docs directory and navigation table."""

import itertools
import typing
from pathlib import Path

from . import exceptions
from . import index as index_module
from . import types_
from .clients import Clients
from .constants import DOCUMENTATION_TAG, NAVIGATION_TABLE_START
from .discourse import Discourse


def _local_only(path_info: types_.PathInfo) -> types_.CreateAction:
    """Return a create action based on information about a local documentation file.

    Args:
        path_info: Information about the local documentation file.

    Returns:
        A page create action.
    """
    return types_.CreateAction(
        level=path_info.level,
        path=path_info.table_path,
        navlink_title=path_info.navlink_title,
        content=path_info.local_path.read_text() if path_info.local_path.is_file() else None,
        navlink_hidden=path_info.navlink_hidden,
    )


def _get_server_content(table_row: types_.TableRow, discourse: Discourse) -> str:
    """Retrieve the content from the server.

    Args:
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        The content on the server.

    Raises:
        ServerError: Retrieving the page contents from the server failed.
        ReconcilliationError: The URL is missing from the navlink.
    """
    if table_row.navlink.link is None:
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {table_row=!r}"
        )

    try:
        return discourse.retrieve_topic(url=table_row.navlink.link).strip()
    except exceptions.DiscourseError as exc:
        raise exceptions.ServerError(
            f"failed to retrieve contents of page, url={table_row.navlink.link}"
        ) from exc


def _local_and_server_validation(
    path_info: types_.PathInfo,
    table_row: types_.TableRow,
) -> None:
    """Input checks before execution.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.

    Raises:
        ReconcilliationError:
            If the table path or level do not match for the path info and table row.
    """
    if path_info.level != table_row.level:
        raise exceptions.ReconcilliationError(
            f"internal error, level mismatch, {path_info=!r}, {table_row=!r}"
        )
    if path_info.table_path != table_row.path:
        raise exceptions.ReconcilliationError(
            f"internal error, table path mismatch, {path_info=!r}, {table_row=!r}"
        )


def _local_and_server_dir_local_group_server(
    path_info: types_.PathInfo, table_row: types_.TableRow
) -> tuple[types_.UpdateAction | types_.NoopAction, ...]:
    """Handle the case where the item is a directory locally and a grouping on the server.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.

    Returns:
        The action to execute against the server.

    """
    if table_row.navlink.title == path_info.navlink_title:
        return (
            types_.NoopAction(
                level=path_info.level,
                path=path_info.table_path,
                navlink=table_row.navlink,
                content=None,
            ),
        )
    return (
        types_.UpdateAction(
            level=path_info.level,
            path=path_info.table_path,
            navlink_change=types_.NavlinkChange(
                old=table_row.navlink,
                new=types_.Navlink(
                    title=path_info.navlink_title, link=table_row.navlink.link, hidden=False
                ),
            ),
            content_change=None,
        ),
    )


def _local_and_server_dir_local_page_server(
    path_info: types_.PathInfo, table_row: types_.TableRow, clients: Clients
) -> tuple[types_.CreateAction | types_.DeleteAction, ...]:
    """Handle the case where the item is a file locally and a grouping on the server.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        clients: The clients to interact with things like discourse and the repository.

    Returns:
        The action to execute against the server.

    Raises:
        ReconcilliationError:
            - If certain edge cases occur that are not expected, such as table_row.navlink.link for
              a page on the server.
    """
    # This is an edge case that can't actually occur because table_row.is_group is based on
    # whether the navlink link is None so this case would have been caught in the local
    # directory and server group case, here for defensive programming if definition of is_group
    # is buggy or changed
    if table_row.navlink.link is None:  # pragma: no cover
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {path_info=!r}, {table_row=!r}"
        )
    return (
        types_.DeleteAction(
            level=path_info.level,
            path=path_info.table_path,
            navlink=table_row.navlink,
            content=clients.discourse.retrieve_topic(url=table_row.navlink.link),
        ),
        types_.CreateAction(
            level=path_info.level,
            path=path_info.table_path,
            navlink_title=path_info.navlink_title,
            content=None,
            navlink_hidden=False,
        ),
    )


def _local_and_server_file_local_page_server(
    path_info: types_.PathInfo,
    table_row: types_.TableRow,
    clients: Clients,
    base_path: Path,
) -> tuple[
    types_.UpdateAction | types_.NoopAction | types_.CreateAction | types_.DeleteAction, ...
]:
    """Handle the case where the item is a file locally and a page on the server.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        clients: The clients to interact with things like discourse and the repository.
        base_path: The base path of the repository.

    Returns:
        The action to execute against the server.

    Raises:
        ReconcilliationError:
            - If there was a problem retrieving content from GitHub.
            - If the expected tag does not exist on the server.
    """
    local_content = path_info.local_path.read_text(encoding="utf-8").strip()
    server_content = _get_server_content(table_row=table_row, discourse=clients.discourse)

    if (
        server_content == local_content
        and table_row.navlink.title == path_info.navlink_title
        and table_row.navlink.hidden == path_info.navlink_hidden
    ):
        return (
            types_.NoopAction(
                level=path_info.level,
                path=path_info.table_path,
                navlink=table_row.navlink,
                content=local_content,
            ),
        )

    try:
        path = str(path_info.local_path.relative_to(base_path))
        base_content = clients.repository.get_file_content_from_tag(
            path=path, tag_name=DOCUMENTATION_TAG
        )
    except exceptions.RepositoryFileNotFoundError:
        base_content = None
    except exceptions.RepositoryTagNotFoundError as exc:
        raise exceptions.ReconcilliationError(
            f"Tag {DOCUMENTATION_TAG} not defined on the repository, please tag the "
            "commit with the content matching discourse with the tag "
            f"{DOCUMENTATION_TAG!r}"
        ) from exc
    except exceptions.RepositoryClientError as exc:
        raise exceptions.ReconcilliationError(
            f"Unable to retrieve content for path from tag, {path}, "
            f"tag_name={DOCUMENTATION_TAG}"
        ) from exc
    return (
        types_.UpdateAction(
            level=path_info.level,
            path=path_info.table_path,
            navlink_change=types_.NavlinkChange(
                old=table_row.navlink,
                new=types_.Navlink(
                    title=path_info.navlink_title,
                    link=table_row.navlink.link,
                    hidden=path_info.navlink_hidden,
                ),
            ),
            content_change=types_.ContentChange(
                base=base_content, server=server_content, local=local_content
            ),
        ),
    )


def _local_and_server(
    path_info: types_.PathInfo,
    table_row: types_.TableRow,
    clients: Clients,
    base_path: Path,
) -> tuple[
    types_.UpdateAction | types_.NoopAction | types_.CreateAction | types_.DeleteAction, ...
]:
    """Compare the local and server content and return an appropriate action.

    Cases:
        1. The action relates to a directory locally and grouping on the server and
            1.1. the navlink title has not change: noop or
            1.2. the navling title has changed: update action.
        2. The action related to a directory locally and a page on the server: delete the page on
            the server and create the directory.
        3. The action related to a file locally and a group on the server: create the page on the
            server.
        4. The action relates to a file locally and a page on the server and
            4.1. the content and navlink title has not changed: noop or
            4.2. the content and/ or the navlink have changed: update action.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        clients: The clients to interact with things like discourse and the repository.
        base_path: The base path of the repository.

    Returns:
        The action to execute against the server.

    """
    _local_and_server_validation(path_info=path_info, table_row=table_row)

    # Is a directory locally and a grouping on the server
    if path_info.local_path.is_dir() and table_row.is_group:
        return _local_and_server_dir_local_group_server(path_info=path_info, table_row=table_row)

    # Is a directory locally and a page on the server
    if path_info.local_path.is_dir():
        return _local_and_server_dir_local_page_server(
            path_info=path_info, table_row=table_row, clients=clients
        )

    # Is a file locally and a grouping on the server, only need to create the page since the
    # grouping is automatically removed from the navigation table since the directory has been
    # removed locally
    if table_row.is_group:
        return (
            types_.CreateAction(
                level=path_info.level,
                path=path_info.table_path,
                navlink_title=path_info.navlink_title,
                content=path_info.local_path.read_text(),
                navlink_hidden=path_info.navlink_hidden,
            ),
        )

    # Is a file locally and page on the server
    return _local_and_server_file_local_page_server(
        path_info=path_info,
        table_row=table_row,
        clients=clients,
        base_path=base_path,
    )


def _server_only(table_row: types_.TableRow, discourse: Discourse) -> types_.DeleteAction:
    """Return a delete action based on a navigation table entry.

    Args:
        table_row: A row from the navigation table.
        discourse: A client to the documentation server.

    Returns:
        A page delete action.

    Raises:
        ReconcilliationError: if the link for a page is None.
        ServerError: Retrieving the page contents from the server failed.
    """
    # Group case
    if table_row.is_group:
        return types_.DeleteAction(
            level=table_row.level,
            path=table_row.path,
            navlink=table_row.navlink,
            content=None,
        )

    # This is an edge case that can't actually occur because table_row.is_group is based on
    # whether the navlink link is None so this case would have been caught in the group case
    if table_row.navlink.link is None:  # pragma: no cover
        raise exceptions.ReconcilliationError(
            f"internal error, expecting link on table row, {table_row=!r}"
        )
    try:
        content = discourse.retrieve_topic(url=table_row.navlink.link)
    except exceptions.DiscourseError as exc:
        raise exceptions.ServerError(
            f"failed to retrieve contents of page, url={table_row.navlink.link}"
        ) from exc
    return types_.DeleteAction(
        level=table_row.level, path=table_row.path, navlink=table_row.navlink, content=content
    )


def _calculate_action(
    path_info: types_.PathInfo | None,
    table_row: types_.TableRow | None,
    clients: Clients,
    base_path: Path,
) -> tuple[types_.AnyAction, ...]:
    """Calculate the required action for a page.

    Args:
        path_info: Information about the local documentation file.
        table_row: A row from the navigation table.
        clients: The clients to interact with things like discourse and the repository.
        base_path: The base path of the repository.

    Returns:
        The action to take for the page.

    Raises:
        ReconcilliationError: if both path_info and table_row are None.
    """
    if path_info is table_row is None:
        raise exceptions.ReconcilliationError(
            "internal error, both path info and table row are None"
        )
    if path_info is not None and table_row is None:
        return (_local_only(path_info=path_info),)
    if path_info is None and table_row is not None:
        return (_server_only(table_row=table_row, discourse=clients.discourse),)
    if path_info is not None and table_row is not None:
        return _local_and_server(
            path_info=path_info, table_row=table_row, clients=clients, base_path=base_path
        )

    # Something weird has happened since all cases should already be covered
    raise exceptions.ReconcilliationError("internal error")  # pragma: no cover


def run(
    sorted_path_infos: typing.Iterable[types_.PathInfo],
    table_rows: typing.Iterable[types_.TableRow],
    clients: Clients,
    base_path: Path,
) -> typing.Iterator[types_.AnyAction]:
    """Reconcile differences between the docs directory and documentation server.

    Preserves the order of path_infos although does not for items only in table_rows.

    This function needs to match files and directories locally to items on the navigation table on
    the server knowing that there may be cases that are not matched. The navigation table relies on
    the order that items are displayed to figure out the hierarchy/ page grouping (this is not a
    design choice of this action but how the documentation is interpreted by charmhub). Assume the
    `path_infos` have been sorted to ensure that the hierarchy will be calculated correctly by the
    server when the new navigation table is generated.

    Items only in table_rows won't have their order preserved. Those items are the items that are
    only on the server, i.e., those keys will just result in delete actions which have no effect on
    the navigation table that is generated and hence ordering for them doesn't matter.

    Args:
        base_path: The base path of the repository.
        sorted_path_infos: Information about the local documentation files.
        table_rows: Rows from the navigation table.
        clients: The clients to interact with things like discourse and the repository.

    Returns:
        The actions required to reconcile differences between the documentation server and local
        files.
    """
    path_info_lookup: types_.PathInfoLookup = {
        path_info.table_path: path_info for path_info in sorted_path_infos
    }
    table_row_lookup: types_.TableRowLookup = {
        table_row.path: table_row for table_row in table_rows
    }

    sorted_path_info_keys = path_info_lookup.keys()
    sorted_remaining_table_row_keys = sorted(table_row_lookup.keys() - sorted_path_info_keys)
    keys = itertools.chain(sorted_path_info_keys, sorted_remaining_table_row_keys)
    return itertools.chain.from_iterable(
        _calculate_action(path_info_lookup.get(key), table_row_lookup.get(key), clients, base_path)
        for key in keys
    )


def index_page(
    index: types_.Index,
    table_rows: typing.Iterable[types_.TableRow],
) -> types_.AnyIndexAction:
    """Reconcile differences for the index page.

    Args:
        index: Information about the index on the server and locally.
        table_rows: The current navigation table rows based on local files.

    Returns:
        The action to take for the index page.
    """
    table_contents = "\n".join(table_row.to_markdown() for table_row in table_rows)
    local_content = (
        f"{index_module.get_content_for_server(index.local)}{NAVIGATION_TABLE_START}\n"
        f"{table_contents}\n".strip()
    )

    if index.server is None:
        return types_.CreateIndexAction(content=local_content, title=index.local.title)

    server_content = index.server.content.strip()
    if local_content != server_content:
        return types_.UpdateIndexAction(
            content_change=types_.IndexContentChange(old=server_content, new=local_content),
            url=index.server.url,
        )
    return types_.NoopIndexAction(content=local_content, url=index.server.url)
