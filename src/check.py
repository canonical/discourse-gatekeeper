# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for running checks."""

import logging
from collections.abc import Iterable, Iterator
from typing import NamedTuple, TypeGuard

from .content import conflicts as content_conflicts
from .content import diff as content_diff
from .types_ import AnyAction, UpdateAction


class Problem(NamedTuple):
    """Details about a failed check.

    Attrs:
        path: Unique identifier for the file and discourse topic with the problem
        description: A summary of what the problem is and how to resolve it.

    """

    path: str
    description: str


def _is_update_action(action: AnyAction) -> TypeGuard[UpdateAction]:
    """Check whether an action is an UpdateAction.

    Args:
        action: The action to check.

    Returns:
        Whether the action is an UpdateAction.
    """
    return isinstance(action, UpdateAction)


def _update_action_problem(action: UpdateAction) -> Problem | None:
    """Get any problem with an update action.

    Args:
        action: The action to check.

    Returns:
        None if there is no problem or the problem if there is an issue with the action.
    """
    if action.content_change is None:
        return None

    if (
        action.content_change.base is None
        and action.content_change.server == action.content_change.local
    ):
        return None

    if action.content_change.base is None:
        diff = content_diff(action.content_change.server, action.content_change.local)
        problem = Problem(
            path="/".join(action.path),
            description=(
                "cannot execute the update action due to not finding a file on the base branch "
                "and there are differences between the branch and discourse content, please ensure "
                f"that there are no differences and try again. Detected differences:\n{diff}"
            ),
        )
    else:
        action_conflicts = content_conflicts(
            base=action.content_change.base,
            theirs=action.content_change.server,
            ours=action.content_change.local,
        )
        if action_conflicts is None:
            return None
        problem = Problem(
            path="/".join(action.path),
            description=(
                "cannot execute the update action due to conflicting changes on discourse, "
                f"please resolve the conflicts and try again: \n{action_conflicts}"
            ),
        )

    logging.error(
        "there is a problem preventing the execution of an action, action: %s, problem: %s",
        action,
        problem,
    )
    return problem


def conflicts(actions: Iterable[AnyAction]) -> Iterator[Problem]:
    """Check whether actions have any content conflicts.

    Args:
        actions: The actions to check.

    Yields:
        A problem for each action with a conflict
    """
    update_actions = filter(_is_update_action, actions)
    yield from filter(None, (_update_action_problem(action) for action in update_actions))
