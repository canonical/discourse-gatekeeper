# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for check."""

import logging
from typing import NamedTuple, cast
from unittest.mock import MagicMock

import pytest
from git.repo import Repo

from src import check, constants, types_

from .. import factories
from .helpers import assert_substrings_in_string


def _track_paths_with_diff_parameters():
    """Generate parameters for the track_paths_with_diff test.

    Returns:
        The tests.
    """
    return [
        pytest.param((), (), (), id="empty"),
        pytest.param(
            (factories.UpdateActionFactory(content_change=None),), (), (), id="single None"
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=(base_1 := "base 1"), local=base_1, server=base_1
                    )
                ),
            ),
            (),
            (),
            id="single no diff",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local=(local_1 := "local 1"), server=local_1
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (check.format_path(path_1),),
            (),
            id="single base local diff",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base=(base_1 := "base 1"), local=base_1, server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (),
            (check.format_path(path_1),),
            id="single local server diff",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (check.format_path(path_1),),
            (check.format_path(path_1),),
            id="single all diff",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 2", local="local 2", server="server 2"
                    ),
                    path=(path_2 := ("path 2",)),
                ),
            ),
            (check.format_path(path_1), check.format_path(path_2)),
            (check.format_path(path_1), check.format_path(path_2)),
            id="multiple all diff",
        ),
    ]


@pytest.mark.parametrize(
    "actions, expected_base_local_diffs, expected_local_server_diffs",
    _track_paths_with_diff_parameters(),
)
def test_track_paths_with_diff(
    actions: tuple[types_.UpdateAction, ...],
    expected_base_local_diffs: tuple[str, ...],
    expected_local_server_diffs: tuple[str, ...],
):
    """
    arrange: given actions
    act: when the actions and passed to TrackPathsWithDiff sequentually
    assert: then the TrackPathsWithDiff has the expected base_local_diffs and local_server_diffs.
    """
    track_paths_with_diff = check.TrackPathsWithDiff()
    for action in actions:
        track_paths_with_diff.process(action)

    assert tuple(track_paths_with_diff.base_local_diffs) == expected_base_local_diffs
    assert tuple(track_paths_with_diff.local_server_diffs) == expected_local_server_diffs


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
        pytest.param((), True, (), id="empty"),
        pytest.param((factories.CreateActionFactory(),), True, (), id="single create"),
        pytest.param((factories.NoopActionFactory(),), True, (), id="single noop"),
        pytest.param((factories.DeleteActionFactory(),), True, (), id="single delete"),
        pytest.param(
            (factories.UpdateActionFactory(content_change=None),),
            True,
            (),
            id="single update no content",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="a")
                ),
            ),
            True,
            (),
            id="single update no base content same",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="b")
                ),
            ),
            True,
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
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
                    content_change=types_.ContentChange(base="a", server="a", local="a")
                ),
            ),
            True,
            (),
            id="single update no conflict",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
            ),
            True,
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
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
            True,
            (),
            id="multiple actions no problems",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
                factories.NoopActionFactory(),
            ),
            True,
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions single problem first",
        ),
        pytest.param(
            (
                factories.NoopActionFactory(),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", server="y", local="z")
                ),
            ),
            True,
            (
                ExpectedProblem(
                    path="/".join(action_2.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions single problem second",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", server="y", local="z")
                ),
            ),
            True,
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_1.content_change)[1:]),
                    ),
                ),
                ExpectedProblem(
                    path="/".join(action_2.path),
                    description_contents=(
                        "conflict",
                        *(cast(tuple, action_2.content_change)[1:]),
                    ),
                ),
            ),
            id="multiple actions multiple problems",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="b")
                ),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", server="x", local="y")
                ),
            ),
            False,
            (
                ExpectedProblem(
                    path="/".join(action_1.path),
                    description_contents=(
                        "detected",
                        "unmerged",
                        "community contributions",
                        constants.DISCOURSE_AHEAD_TAG,
                        "/".join(action_1.path),
                        "/".join(action_2.path),
                    ),
                ),
            ),
            id=(
                "multiple actions one has base and local other has local and server diff, tag not "
                "applied"
            ),
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="b")
                ),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", server="x", local="y")
                ),
            ),
            True,
            (),
            id=(
                "multiple actions one has base and local other has local and server diff, tag "
                "applied"
            ),
        ),
    ]


@pytest.mark.parametrize(
    "actions, is_tagged, expected_problems",
    _test_conflicts_parameters(),
)
def test_conflicts(
    actions: tuple[types_.AnyAction, ...],
    is_tagged: bool,
    git_repo: Repo,
    expected_problems: tuple[ExpectedProblem],
    caplog: pytest.LogCaptureFixture,
    mocked_clients,
):
    """
    arrange: given actions
    act: when conflicts is called with the actions
    assert: then the expected problems are yielded.
    """
    caplog.set_level(logging.INFO)
    if is_tagged:
        mocked_clients.repository.tag_commit(
            tag_name=constants.DISCOURSE_AHEAD_TAG, commit_sha=git_repo.head.commit.hexsha
        )

    user_inputs = factories.UserInputsFactory(commit_sha=git_repo.head.commit.hexsha)
    returned_problems = tuple(
        check.conflicts(
            actions=actions,
            repository=mocked_clients.repository,
            user_inputs=user_inputs,
        )
    )

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
                str(returned_problem),
            ),
            caplog.text,
        )
