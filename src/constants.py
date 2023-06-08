# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared constants.

The use of this module should be limited to cases where the constant is not better placed in
another module or to resolve circular imports.
"""
DEFAULT_BRANCH = "main"
DOCUMENTATION_TAG = "upload-charm-docs/base-content"
DISCOURSE_AHEAD_TAG = "upload-charm-docs/discourse-ahead-ok"

DOCUMENTATION_FOLDER_NAME = "docs"
DOCUMENTATION_INDEX_FILENAME = "index.md"
NAVIGATION_TABLE_START = """

# Navigation

| Level | Path | Navlink |
| -- | -- | -- |"""
