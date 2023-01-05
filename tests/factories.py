# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Factories for generating test data."""

# The factory definitions don't need public methods
# pylint: disable=too-few-public-methods

from pathlib import Path

import factory

from src import types_

from . import types


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


class MigrationReportFactory(factory.Factory):
    """Generate Migration reports."""

    class Meta:
        """Configuration for factory."""

        model = types_.MigrationReport
        abstract = False

    class Params:
        """Variable factory params for generating different status report."""

        is_success = factory.Trait(result=types_.ActionResult.SUCCESS, reason=None)
        is_skipped = factory.Trait(result=types_.ActionResult.SKIP, reason="skipped")
        is_failed = factory.Trait(result=types_.ActionResult.FAIL, reason="failed")

    table_row = factory.Sequence(
        lambda n: types_.TableRow(
            level=n,
            path=f"path {n}",
            navlink=types_.Navlink(title=f"title {n}", link=f"link {n}"),
        )
    )
    path = factory.Sequence(lambda n: Path(f"dir{n}"))
    result = None
    reason = None


class ContentPageFactory(factory.Factory):
    """Generate discourse content page."""

    class Meta:
        """Configuration for factory."""

        model = types.DiscoursePageMeta
        abstract = False

    title = factory.Sequence(lambda n: f"Content title {n}")
    content = factory.Sequence(lambda n: f"Content {n}")


class UserInputFactory(factory.Factory):
    """Generate user input tuple."""

    class Meta:
        """Configuration for factory."""

        model = types_.UserInputs
        abstract = False

    # the following token is a test variable for testing.
    github_access_token = "test-token"  # nosec
    dry_run = False
    delete_pages = False
