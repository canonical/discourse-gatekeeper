# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Factories for generating test data."""

# The factory definitions don't need public methods
# pylint: disable=too-few-public-methods

from pathlib import Path

import factory

from src import types_

from . import types


# The attributes of these classes are generators for the attributes of the meta class
class PathInfoFactory(factory.Factory):
    # Docstrings have been abbreviated for factories, checking for docstrings on model attributes
    # can be skipped.
    """Generate PathInfos."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.PathInfo
        abstract = False

    local_path = factory.Sequence(lambda n: Path(f"dir{n}"))
    level = factory.Sequence(lambda n: n)
    table_path = factory.Sequence(lambda n: f"path {n}")
    navlink_title = factory.Sequence(lambda n: f"title {n}")
    alphabetical_rank = factory.Sequence(lambda n: n)


class ActionReportFactory(factory.Factory):
    """Generate Action reports."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.ActionReport
        abstract = False

    class Params:
        """Variable factory params for generating different status report.

        Attrs:
            is_success: flag to instantiate successful action result.
            is_skipped: flag to instantiate skipped action result.
            is_failed: flag to instantiate failed action result.
            is_migrate: flag to instantiate migration action result. Generates reconcile action
                reports by default.
        """

        is_success = factory.Trait(result=types_.ActionResult.SUCCESS, reason=None)
        is_skipped = factory.Trait(result=types_.ActionResult.SKIP, reason="skipped")
        is_failed = factory.Trait(result=types_.ActionResult.FAIL, reason="failed")
        is_migrate = factory.Trait(location=factory.Sequence(lambda n: Path(f"path-{n}")))

    table_row = factory.Sequence(
        lambda n: types_.TableRow(
            level=n,
            path=f"path {n}",
            navlink=types_.Navlink(title=f"title {n}", link=f"link {n}"),
        )
    )
    location = factory.Sequence(lambda n: types_.Url(f"link-{n}"))
    result = None
    reason = None


class ContentPageFactory(factory.Factory):
    """Generate discourse content page."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types.DiscoursePageMeta
        abstract = False

    title = factory.Sequence(lambda n: f"Content title {n}")
    content = factory.Sequence(lambda n: f"Content {n}")


class UserInputDiscourseFactory(factory.Factory):
    """Generate user input tuple."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.UserInputsDiscourse
        abstract = False

    hostname = factory.Sequence(lambda n: f"http://discourse/{n}")
    category_id = factory.Sequence(lambda n: n)
    api_username = factory.Sequence(lambda n: f"discourse-test-user-{n}")
    api_key = factory.Sequence(lambda n: f"discourse-test-key-{n}")


class UserInputFactory(factory.Factory):
    """Generate user input tuple."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.UserInputs
        abstract = False

    discourse = factory.SubFactory(UserInputDiscourseFactory)
    github_access_token = factory.Sequence(lambda n: f"test-token-{n}")
    dry_run = False
    delete_pages = False


class TableRowFactory(factory.Factory):
    """Generate table row."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.TableRow
        abstract = False

    class Params:
        """Variable factory params for generating different type of table row.

        Attrs:
            is_group: flag to instantiate a table row representing a group.
            is_document: flag to instantiate a table row representing a document(Default).
        """

        is_group = factory.Trait(
            navlink=factory.Sequence(lambda n: types_.Navlink(f"navlink-title-{n}", link=None))
        )
        is_document = factory.Trait(
            navlink=factory.Sequence(
                lambda n: types_.Navlink(f"navlink-title-{n}", link=f"navlink-{n}")
            )
        )

    level = factory.Sequence(lambda n: n)
    path = factory.Sequence(lambda n: f"path-{n}")
    navlink = factory.Sequence(lambda n: types_.Navlink(f"navlink-title-{n}", link=f"navlink-{n}"))
