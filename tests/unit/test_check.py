# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for check."""

import logging
from typing import NamedTuple, cast

import pytest

from src import check, constants, repository, types_

from .. import factories
from .helpers import assert_substrings_in_string


def _track_paths_with_diff_parameters():
    """Generate parameters for the track_paths_with_diff test.

    Returns:
        The test parameters, the first item of each element is the action and the second and third
        the expected paths with base and local and base and server diffs, respectively.
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
                        base=(base_1 := "base 1"), local="local 1", server=base_1
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
            id="single base server diff",
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
            (),
            (),
            id="single base diff server local same",
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
                        base=None, local="local 1", server="server 1"
                    ),
                    path=(path_1 := ("path 1",)),
                ),
            ),
            (),
            (),
            id="single all diff base None",
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
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 1", local=(local_1 := "local 1"), server=local_1
                    )
                ),
                factories.UpdateActionFactory(
                    content_change=factories.ContentChangeFactory(
                        base="base 2", local=(local_2 := "local 2"), server=local_2
                    )
                ),
            ),
            (),
            (),
            id="multiple base diff local server same",
        ),
    ]


@pytest.mark.parametrize(
    "actions, expected_base_local_diffs, expected_base_server_diffs",
    _track_paths_with_diff_parameters(),
)
def test_track_paths_with_diff(
    actions: tuple[types_.UpdateAction, ...],
    expected_base_local_diffs: tuple[str, ...],
    expected_base_server_diffs: tuple[str, ...],
):
    """
    arrange: given actions
    act: when the actions and passed to TrackPathsWithDiff sequentually
    assert: then the TrackPathsWithDiff has the expected base_local_diffs and base_server_diffs.
    """
    paths_with_diff = check.get_path_with_diffs(actions)

    assert paths_with_diff.base_local_diffs == expected_base_local_diffs
    assert paths_with_diff.base_server_diffs == expected_base_server_diffs


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
        pytest.param((), False, (), id="empty"),
        pytest.param((factories.CreatePageActionFactory(),), False, (), id="single create"),
        pytest.param((factories.NoopActionFactory(),), False, (), id="single noop"),
        pytest.param((factories.DeleteActionFactory(),), False, (), id="single delete"),
        pytest.param(
            (factories.UpdateActionFactory(content_change=None),),
            False,
            (),
            id="single update no content",
        ),
        pytest.param(
            (
                factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="a")
                ),
            ),
            False,
            (),
            id="single update no base content same",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base=None, server="a", local="b")
                ),
            ),
            False,
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
            False,
            (),
            id="single update no conflict",
        ),
        pytest.param(
            (
                action_1 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="a", server="b", local="c")
                ),
            ),
            False,
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
            False,
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
            False,
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
            False,
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
            False,
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
                    content_change=types_.ContentChange(base="a", server="b", local="a")
                ),
                action_2 := factories.UpdateActionFactory(
                    content_change=types_.ContentChange(base="x", server="x", local="y")
                ),
            ),
            False,
            (
                ExpectedProblem(
                    path="/".join(action_2.path),
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
                    content_change=types_.ContentChange(base="a", server="b", local="a")
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
    expected_problems: tuple[ExpectedProblem],
    caplog: pytest.LogCaptureFixture,
    repository_client: repository.Client,
):
    """
    arrange: given actions
    act: when conflicts is called with the actions
    assert: then the expected problems are yielded.
    """
    caplog.set_level(logging.INFO)
    if is_tagged:
        repository_client.tag_commit(
            tag_name=constants.DISCOURSE_AHEAD_TAG, commit_sha=repository_client.current_commit
        )

    user_inputs = factories.UserInputsFactory(commit_sha=repository_client.current_commit)
    returned_problems = tuple(
        check.conflicts(
            actions=actions,
            repository=repository_client,
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
                returned_problem.path,
                returned_problem.description,
            ),
            caplog.text,
        )
