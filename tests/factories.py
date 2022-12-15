# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Factories for generating test data."""

# The factory definitions don't need public methods
# pylint: disable=too-few-public-methods

from pathlib import Path

import factory

from src import types_


class PathInfoFactory(factory.Factory):
    """Generate PathInfos."""

    class Meta:
        """Configuration for factory."""

        model = types_.PathInfo
        abstract = False

    local_path = factory.Sequence(lambda n: Path(f"dir{n}"))
    level = factory.Sequence(lambda n: n)
    table_path = factory.Sequence(lambda n: f"path {n}")
    navlink_title = factory.Sequence(lambda n: f"title {n}")
    alphabetical_rank = factory.Sequence(lambda n: n)
