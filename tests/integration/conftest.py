# Copyright 2022 Canonical Ltd.
# Licensed under the GPLv3, see LICENCE file for details.

"""Fixtures for integration tests."""

import asyncio
import re
import secrets

from ops.model import ActiveStatus, Application
import pydiscourse
import pytest
import pytest_asyncio
from pytest_operator.plugin import OpsTest
import requests

from . import types


@pytest.fixture(scope="module")
def discourse_hostname():
    """Get the hostname for discourse."""
    return "discourse"


async def create_discourse_account(
    ops_test: OpsTest, unit: str, email: str, admin: bool
) -> types.Credentials:
    """
    Create an account on discourse.

    Assume that the model already countains a discourse unit unit.

    Args:
        ops_test: Used for interactions with the model.
        unit: The unit running discourse.
        email: The email address to use on the account.
        admin: Whether to make the account an admin account.

    Returns:
        The credentials for the discourse account.

    """
    password = secrets.token_urlsafe(16)
    # For some reason discourse.units[0] is None so can't use the discourse.units[0].ssh function
    return_code, stdout, stderr = await ops_test.juju(
        "exec",
        "--unit",
        unit,
        "--",
        "cd /srv/discourse/app && ./bin/bundle exec rake admin:create RAILS_ENV=production << "
        f"ANSWERS\n{email}\n{password}\n{password}\n{'Y' if admin else 'n'}\nANSWERS",
    )
    assert (
        return_code == 0
    ), f"discourse account creation failed for email {email}, {stdout=}, {stderr=}"

    username_match = re.search(r"Account created successfully with username (.*?)\n", stdout)
    assert (
        username_match is not None
    ), f"failed to get username for account with email {email}, {stdout=}, {stderr=}"
    username = username_match.group(1)
    assert type(username) == str

    return types.Credentials(email=email, username=username, password=password)


def create_user_api_key(
    discourse_hostname: str, master_api_key: str, user_credentials: types.Credentials
) -> str:
    """
    Create an API key for a user.

    Args:
        discourse_hostname: The hostname that discourse is running under.
        master_api_key: The system master API key for the discourse server.
        user_credentials: The crednetials of the user to create an API key for.

    Returns:
        The API key for the user.

    """
    headers = {"Api-Key": master_api_key, "Api-Username": "system"}
    data = {"key[description]": "Test key", "key[username]": user_credentials.username}
    response = requests.post(
        f"http://{discourse_hostname}/admin/api/keys", headers=headers, data=data
    )
    assert (
        response.status_code == 200
    ), f"API creation failed, {user_credentials.username=}, {response.content=}"

    return response.json()["key"]["key"]


@pytest_asyncio.fixture(scope="module")
async def discourse(ops_test: OpsTest, discourse_hostname: str):
    """Deploy discourse."""
    postgres_charm_name = "postgresql-k8s"
    redis_charm_name = "redis-k8s"
    discourse_charm_name = "discourse-k8s"
    await asyncio.gather(
        ops_test.model.deploy(postgres_charm_name),
        ops_test.model.deploy(redis_charm_name),
    )
    discourse_app = await ops_test.model.deploy(
        discourse_charm_name, config={"external_hostname": discourse_hostname}
    )

    await ops_test.model.wait_for_idle()

    await ops_test.model.relate(discourse_charm_name, f"{postgres_charm_name}:db-admin")
    await ops_test.model.relate(discourse_charm_name, redis_charm_name)

    await ops_test.model.wait_for_idle(status=ActiveStatus.name)

    # Need to wait for the waiting status to be resolved

    async def get_discourse_status():
        """Get the status of discourse."""
        return (await ops_test.model.get_status())["applications"]["discourse-k8s"].status[
            "status"
        ]

    for _ in range(120):
        if await get_discourse_status() != "waiting":
            break
        await asyncio.sleep(10)
    assert await get_discourse_status() != "waiting", "discourse never stopped waiting"

    return discourse_app


@pytest_asyncio.fixture(scope="module")
async def discourse_unit_name(discourse: Application):
    """Get the admin credentials for discourse."""
    return f"{discourse.name}/0"


@pytest_asyncio.fixture(scope="module")
async def discourse_admin_credentials(ops_test: OpsTest, discourse_unit_name: str):
    """Get the admin credentials for discourse."""
    return await create_discourse_account(
        ops_test=ops_test, unit=discourse_unit_name, email="admin@foo.internal", admin=True
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_user_credentials(ops_test: OpsTest, discourse_unit_name: str):
    """Get the user credentials for discourse."""
    return await create_discourse_account(
        ops_test=ops_test, unit=discourse_unit_name, email="user@foo.internal", admin=False
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_alternate_user_credentials(ops_test: OpsTest, discourse_unit_name: str):
    """Get the alternate user credentials for discourse."""
    return await create_discourse_account(
        ops_test=ops_test,
        unit=discourse_unit_name,
        email="alternate_user@foo.internal",
        admin=False,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_master_api_key(ops_test: OpsTest, discourse_unit_name: str):
    """Get the user api key for discourse."""
    return_code, stdout, stderr = await ops_test.juju(
        "exec",
        "--unit",
        discourse_unit_name,
        "--",
        "cd /srv/discourse/app && ./bin/bundle exec rake "
        "api_key:create_master['master API key for testing'] RAILS_ENV=production",
    )
    assert return_code == 0, f"discourse master API key creation failed, {stderr=}"

    return stdout.strip()


@pytest_asyncio.fixture(scope="module")
async def discourse_user_api_key(
    discourse_master_api_key: str,
    discourse_user_credentials: types.Credentials,
    discourse_hostname: str,
):
    """Get the user api key for discourse."""
    return create_user_api_key(
        discourse_hostname=discourse_hostname,
        master_api_key=discourse_master_api_key,
        user_credentials=discourse_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_alternate_user_api_key(
    discourse_master_api_key: str,
    discourse_alternate_user_credentials: types.Credentials,
    discourse_hostname: str,
):
    """Get the alternate user api key for discourse."""
    return create_user_api_key(
        discourse_hostname=discourse_hostname,
        master_api_key=discourse_master_api_key,
        user_credentials=discourse_alternate_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_category(
    discourse_master_api_key,
    discourse_hostname: str,
):
    """Create the category for topics."""
    client = pydiscourse.DiscourseClient(
        host=f"http://{discourse_hostname}",
        api_username="system",
        api_key=discourse_master_api_key,
    )
    category = client.create_category(name="docs", color="FFFFFF")
    return category["category"]["id"]
