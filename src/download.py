# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for downloading docs folder from charmhub."""

import shutil

from src.clients import Clients
from src.index import contents_from_page
from src.index import get as get_index
from src.migration import run as migrate_contents
from src.navigation_table import from_page as navigation_table_from_page


def _download_from_discourse(clients: Clients) -> None:
    """Download docs folder locally from Discourse.

    Args:
        clients: Clients object
    """
    charm_path = clients.repository.base_charm_path
    docs_path = clients.repository.docs_path
    metadata = clients.repository.metadata

    index = get_index(metadata=metadata, docs_path=docs_path, server_client=clients.discourse)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    index_content = contents_from_page(server_content)
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    migrate_contents(
        table_rows=table_rows,
        index_content=index_content,
        discourse=clients.discourse,
        docs_path=docs_path,
    )


def recreate_docs(clients: Clients, base: str) -> bool:
    """Recreate the docs folder and checks whether the docs folder is aligned with base branch/tag.

    Args:
        clients: Clients object containing Repository and Discourse API clients
        base: tag to be compared to

    Returns:
        boolean representing whether any differences have occurred
    """
    clients.repository.switch(base)

    # Remove docs folder and recreate content from discourse
    docs_path = clients.repository.docs_path

    if docs_path.exists():
        shutil.rmtree(docs_path)

    _download_from_discourse(clients)

    return clients.repository.is_dirty()
