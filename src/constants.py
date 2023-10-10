# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared constants.

The use of this module should be limited to cases where the constant is not better placed in
another module or to resolve circular imports.
"""
DEFAULT_BRANCH = "main"
DOCUMENTATION_TAG = "discourse-gatekeeper/base-content"
DISCOURSE_AHEAD_TAG = "discourse-gatekeeper/discourse-ahead-ok"

DOCUMENTATION_FOLDER_NAME = "docs"
DOC_FILE_EXTENSION = ".md"
DOCUMENTATION_INDEX_FILENAME = f"index{DOC_FILE_EXTENSION}"
NAVIGATION_HEADING = "Navigation"
NAVIGATION_TABLE_START = f"""
# {NAVIGATION_HEADING}

| Level | Path | Navlink |
| -- | -- | -- |"""
PATH_CHARS = r"\w-"
