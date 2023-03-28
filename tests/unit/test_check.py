# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for check."""

import logging
from typing import NamedTuple, cast

import pytest

from src import check, types_

from .. import factories
from .helpers import assert_substrings_in_string


class ExpectedProblem(NamedTuple):
    """
    Attrs:
        path: The expected path.
        description_contents: The expected contents of the description

    """

    path: str
    description_contents: tuple[str, ...]


def _test_conflicts_parameters():
    """Generate parameters for the test_conflicts test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), id="empty"),
        pytest.param((factories.CreateActionFactory(),), (), id="single create"),
        pytest.param((factories.NoopActionFactory(),), (), id="single noop"),
        pytest.param((factories.DeleteActionFactory(),), (), id="single delete"),
        pytest.param(
            (factories.UpdateActionFactory(content_change=None),),
            (),
            id="single update no content",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, old="a", new="a")
                ),
            ),
            (),
            id="single update no base content same",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, old="a", new="b")
                ),
            ),
            (
                ExpectedProblem(
                    path=action_1.path,
                    description_contents=(
                        "cannot",
                        "execute",
                        "branch",
                        "discourse",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="single update no base content different",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", old="a", new="a")
                ),
            ),
            (),
            id="single update no conflict",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", old="b", new="c")
                ),
            ),
            (
                ExpectedProblem(
                    path=action_1.path,
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="single update conflict",
        ),
        pytest.param(
            (factories.NoopActionFactory(), factories.NoopActionFactory()),
            (),
            id="multiple no problems",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", old="b", new="c")
                ),
                factories.NoopActionFactory(),
            ),
            (
                ExpectedProblem(
                    path=action_1.path,
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple single problem first",
        ),
        pytest.param(
            (
                factories.NoopActionFactory(),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", old="y", new="z")
                ),
            ),
            (
                ExpectedProblem(
                    path=action_2.path,
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple single problem second",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", old="b", new="c")
                ),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", old="y", new="z")
                ),
            ),
            (
                ExpectedProblem(
                    path=action_1.path,
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
                ExpectedProblem(
                    path=action_2.path,
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple multiple problems",
        ),
    ]


@pytest.mark.parametrize(
    "actions, expected_problems",
    _test_conflicts_parameters(),
)
def test_conflicts(
    actions: tuple[types_.AnyAction, ...],
    expected_problems: tuple[ExpectedProblem],
    caplog: pytest.LogCaptureFixture,
):
    """
    arrange: given actions
    act: when conflicts is called with the actions
    assert: then the expected problems are yielded.
    """
    caplog.set_level(logging.INFO)

    returned_problems = tuple(check.conflicts(actions=actions))

    assert len(returned_problems) == len(expected_problems)
    for returned_problem, expected_problem in zip(returned_problems, expected_problems):
        assert returned_problem.path == expected_problem.path
        assert_substrings_in_string(
            expected_problem.description_contents, returned_problem.description
        )
        assert_substrings_in_string(
            (
                "problem",
                "preventing",
                "execution",
                "UpdateAction",
                str(returned_problem),
            ),
            caplog.text,
        )
