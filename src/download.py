# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for downloading docs folder from charmhub."""

import shutil

from git import GitCommandError

from .constants import DOCUMENTATION_FOLDER_NAME
from .index import get as get_index
from .migration import run as migrate_contents
from .navigation_table import from_page as navigation_table_from_page
from .reconcile import Clients


def download_from_discourse(clients: Clients) -> None:
    """Download docs folder locally from Discourse.

    Args:
        clients: Clients object
    """
    base_path = clients.repository.base_path
    metadata = clients.repository.metadata

    index = get_index(metadata=metadata, base_path=base_path, server_client=clients.discourse)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    # index_content = contents_from_page(server_content)
    # TODO: I'm not sure about this bit above. We should talk about this  # pylint: disable=W0511
    index_content = server_content
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    migrate_contents(
        table_rows=table_rows,
        index_content=index_content,
        discourse=clients.discourse,
        docs_path=base_path / DOCUMENTATION_FOLDER_NAME,
    )


def recreate_docs(clients: Clients, base: str) -> bool:
    """Recreate the docs folder and checks whether the docs folder is aligned with base branch/tag.

    Args:
        clients: Clients object containing Repository and Discourse API clients
        base: branch or tag to be compared to

    Returns:
        boolean representing whether any differences have occurred
    """
    clients.repository.switch(base)

    try:
        clients.repository.pull()
    except GitCommandError:
        # The branch is either detached or there is no remote branch. In these cases there is no
        # reason for pulling anything
        pass

    # Remove docs folder and recreate content from discourse
    docs_path = clients.repository.base_path / DOCUMENTATION_FOLDER_NAME

    if docs_path.exists():
        shutil.rmtree(docs_path)

    download_from_discourse(clients)

    return clients.repository.is_dirty()
