# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for uploading docs to charmhub."""

import logging
from pathlib import Path

from .action import DRAFT_NAVLINK_LINK, FAIL_NAVLINK_LINK
from .action import run_all as run_all_actions
from .discourse import Discourse
from .docs_directory import read as read_docs_directory
from .index import get as get_index
from .navigation_table import from_page as navigation_table_from_page
from .reconcile import run as run_reconcile


def run(
    base_path: Path,
    discourse: Discourse,
    draft_mode: bool,
    delete_pages: bool,
) -> dict[str, str]:
    """Upload the documentation to charmhub.

    Args:
        base_path: The base path to look for the metadata file in.
        discourse: A client to the documentation server.
        draft_mode: If enabled, only log the action that would be taken.
        delete_pages: Whether to delete pages that are no longer needed.

    Returns:
        All the URLs that had an action with the result of that action.

    """
    index = get_index(base_path=base_path, server_client=discourse)
    logging.info("index=%s", index)
    path_infos = list(read_docs_directory(docs_path=base_path / "docs"))
    logging.info("path_infos=%s", path_infos)
    server_content = (index.server.content or "") if index.server is not None else ""
    logging.info("server_content=%s", server_content)
    table_rows = list(navigation_table_from_page(page=server_content))
    logging.info("table_rows=%s", table_rows)
    actions = run_reconcile(path_infos=path_infos, table_rows=table_rows, discourse=discourse)
    reports = run_all_actions(
        actions=actions,
        index=index,
        discourse=discourse,
        draft_mode=draft_mode,
        delete_pages=delete_pages,
    )
    return {
        report.url: report.result
        for report in reports
        if report.url is not None
        and report.url != DRAFT_NAVLINK_LINK
        and report.url != FAIL_NAVLINK_LINK
    }
