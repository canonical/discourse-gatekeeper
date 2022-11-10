# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Types for uploading docs to charmhub."""


import typing


class Page(typing.NamedTuple):
    """Information about a documentation page.

    Atrs:
        url: The link to the page.
        content: The documentation text of the page.
    """

    url: str
    content: str
