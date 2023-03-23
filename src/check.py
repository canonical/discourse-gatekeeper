# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for running checks."""

from typing import Iterable, Iterator, NamedTuple, TypeGuard

from .content import conflicts as content_conflicts
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

    action_conflcits = content_conflicts(
        base=action.content_change.base,
        theirs=action.content_change.old,
        ours=action.content_change.new,
    )
    if action_conflcits is None:
        return None

    return Problem(path=action.path, description=action_conflcits)


def conflicts(actions: Iterable[AnyAction]) -> Iterator[Problem]:
    """Check whether actions have any content conflicts.

    Args:
        actions: The actions to check.

    Yields:
        A problem for each action with a conflict
    """
    update_actions = filter(_is_update_action, actions)
    yield from filter(None, (_update_action_problem(action) for action in update_actions))
