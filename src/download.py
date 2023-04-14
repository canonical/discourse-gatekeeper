# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for downloading docs folder from charmhub."""

from .constants import DOCUMENTATION_FOLDER_NAME
from .index import contents_from_page
from .index import get as get_index
from .migration import run as migrate_contents
from .navigation_table import from_page as navigation_table_from_page
from .reconcile import Clients


def download_from_discourse(clients: Clients) -> None:
    base_path = clients.repository.base_path
    metadata = clients.repository.metadata

    index = get_index(metadata=metadata, base_path=base_path, server_client=clients.discourse)
    server_content = (
        index.server.content if index.server is not None and index.server.content else ""
    )
    index_content = contents_from_page(server_content)
    table_rows = navigation_table_from_page(page=server_content, discourse=clients.discourse)
    migrate_contents(
        table_rows=table_rows,
        index_content=index_content,
        discourse=clients.discourse,
        docs_path=base_path / DOCUMENTATION_FOLDER_NAME,
    )
