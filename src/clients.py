# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for Client class."""

import typing
from pathlib import Path

from .discourse import Discourse, create_discourse
from .repository import Client as RepositoryClient
from .repository import create_repository_client
from .types_ import UserInputs


class Clients(typing.NamedTuple):
    """Collection of clients needed during execution.

    Attrs:
        discourse: Discourse client.
        repository: Client for the repository.
    """

    discourse: Discourse
    repository: RepositoryClient


def get_clients(user_inputs: UserInputs, base_path: Path) -> Clients:
    """Return Clients object.

    Args:
        user_inputs: inputs provided via environment
        base_path: path where the git repository is stored

    Returns:
        Clients object embedding both Discourse API and Repository clients
    """
    return Clients(
        discourse=create_discourse(
            hostname=user_inputs.discourse.hostname,
            category_id=user_inputs.discourse.category_id,
            api_username=user_inputs.discourse.api_username,
            api_key=user_inputs.discourse.api_key,
        ),
        repository=create_repository_client(
            access_token=user_inputs.github_access_token, base_path=base_path
        ),
    )
