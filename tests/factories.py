# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Factories for generating test data."""

# The factory definitions don't need public methods
# pylint: disable=too-few-public-methods

from pathlib import Path
from typing import Generic, TypeVar

import factory

from src import types_

from . import types

T = TypeVar("T")


class BaseMetaFactory(Generic[T], factory.base.FactoryMetaClass):
    """Used for type hints of factories."""

    # No need for docstring because it is used for type hints
    def __call__(cls, *args, **kwargs) -> T:  # noqa: N805
        """Used for type hints of factories."""  # noqa: DCO020
        return super().__call__(*args, **kwargs)  # noqa: DCO030


# The attributes of these classes are generators for the attributes of the meta class
# mypy incorrectly believes the factories don't support metaclass
class PathInfoFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.PathInfo]  # type: ignore[misc]
):
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


class ActionReportFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.ActionReport]  # type: ignore[misc]
):
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


class CreateActionFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.CreateAction]  # type: ignore[misc]
):
    """Generate CreateActions."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.CreateAction
        abstract = False

    level = factory.Sequence(lambda n: n)
    path = factory.Sequence(lambda n: f"path {n}")
    navlink_title = factory.Sequence(lambda n: f"title {n}")
    content = factory.Sequence(lambda n: f"content {n}")


class NavlinkFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.Navlink]  # type: ignore[misc]
):
    """Generate Navlink."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.Navlink
        abstract = False

    title = factory.Sequence(lambda n: f"navlink-title-{n}")
    link = factory.Sequence(lambda n: f"navlink-{n}")


class NoopActionFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.NoopAction]  # type: ignore[misc]
):
    """Generate NoopActions."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.NoopAction
        abstract = False

    level = factory.Sequence(lambda n: n)
    path = factory.Sequence(lambda n: f"path {n}")
    navlink = factory.SubFactory(NavlinkFactory)
    content = factory.Sequence(lambda n: f"content {n}")


class NavlinkChangeFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.NavlinkChange]  # type: ignore[misc]
):
    """Generate NavlinkChange."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.NavlinkChange
        abstract = False

    old = factory.SubFactory(NavlinkFactory)
    new = factory.SubFactory(NavlinkFactory)


class ContentChangeFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.ContentChange]  # type: ignore[misc]
):
    """Generate ContentChange."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.ContentChange
        abstract = False

    base = factory.Sequence(lambda n: f"base {n}")
    server = factory.Sequence(lambda n: f"server {n}")
    local = factory.Sequence(lambda n: f"local {n}")


class UpdateActionFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.UpdateAction]  # type: ignore[misc]
):
    """Generate UpdateActions."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.UpdateAction
        abstract = False

    level = factory.Sequence(lambda n: n)
    path = factory.Sequence(lambda n: f"path {n}")
    navlink_change = factory.SubFactory(NavlinkChangeFactory)
    content_change = factory.SubFactory(ContentChangeFactory)


class DeleteActionFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.DeleteAction]  # type: ignore[misc]
):
    """Generate DeleteActions."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.DeleteAction
        abstract = False

    level = factory.Sequence(lambda n: n)
    path = factory.Sequence(lambda n: f"path {n}")
    navlink = factory.SubFactory(NavlinkFactory)
    content = factory.Sequence(lambda n: f"content {n}")


class ContentPageFactory(
    factory.Factory, metaclass=BaseMetaFactory[types.DiscoursePageMeta]  # type: ignore[misc]
):
    """Generate discourse content page."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types.DiscoursePageMeta
        abstract = False

    title = factory.Sequence(lambda n: f"Content title {n}")
    content = factory.Sequence(lambda n: f"Content {n}")


class UserInputDiscourseFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.UserInputsDiscourse]  # type: ignore[misc]
):
    """Generate user input tuple."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.UserInputsDiscourse
        abstract = False

    hostname = factory.Sequence(lambda n: f"discourse/{n}")
    category_id = factory.Sequence(lambda n: f"{n}")
    api_username = factory.Sequence(lambda n: f"discourse-test-user-{n}")
    api_key = factory.Sequence(lambda n: f"discourse-test-key-{n}")


class UserInputsFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.UserInputs]  # type: ignore[misc]
):
    """Generate user input tuple."""  # noqa: DCO060

    class Meta:
        """Configuration for factory."""  # noqa: DCO060

        model = types_.UserInputs
        abstract = False

    discourse = factory.SubFactory(UserInputDiscourseFactory)
    github_access_token = factory.Sequence(lambda n: f"test-token-{n}")
    commit_sha = factory.Sequence(lambda n: f"commit-sha-{n}")
    dry_run = False
    delete_pages = False


class TableRowFactory(
    factory.Factory, metaclass=BaseMetaFactory[types_.TableRow]  # type: ignore[misc]
):
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
    navlink = factory.SubFactory(NavlinkFactory)
