# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for integration tests."""

# pylint: disable=redefined-outer-name

import asyncio
import secrets
import typing

import pydiscourse
import pytest
import pytest_asyncio
import requests
from juju.action import Action
from juju.application import Application
from juju.client._definitions import ApplicationStatus, FullStatus, UnitStatus
from juju.model import Model
from juju.unit import Unit
from pytest_operator.plugin import OpsTest

from src.discourse import Discourse

from . import types


@pytest.fixture(scope="module", name="model")
def model_fixture(ops_test: OpsTest) -> Model:
    """Get current valid model created for integraion testing with module scope."""
    assert ops_test.model
    return ops_test.model


@pytest_asyncio.fixture(scope="module")
async def discourse(model: Model) -> Application:
    """Deploy discourse."""
    postgres_charm_name = "postgresql-k8s"
    redis_charm_name = "redis-k8s"
    discourse_charm_name = "discourse-k8s"
    await asyncio.gather(
        model.deploy(postgres_charm_name),
        model.deploy(redis_charm_name),
    )
    await model.wait_for_idle(apps=[postgres_charm_name, redis_charm_name], raise_on_error=False)

    discourse_app: Application = await model.deploy(discourse_charm_name, channel="edge")
    await model.relate(discourse_charm_name, f"{postgres_charm_name}:db")
    await model.relate(discourse_charm_name, redis_charm_name)

    # Need to wait for the waiting status to be resolved

    async def get_discourse_status():
        """Get the status of discourse.

        Returns:
            The status of discourse.
        """
        return (await model.get_status())["applications"]["discourse-k8s"].status["status"]

    for _ in range(120):
        if await get_discourse_status() != "waiting":
            break
        await asyncio.sleep(10)
    assert await get_discourse_status() != "waiting", "discourse never stopped waiting"

    status: FullStatus = await model.get_status()
    app_status = typing.cast(ApplicationStatus, status.applications[discourse_app.name])
    unit_status = typing.cast(UnitStatus, app_status.units[f"{discourse_app.name}/0"])
    unit_ip = typing.cast(str, unit_status.address)
    # the redirects will be towards default external_hostname value of application name which
    # the client cannot reach. Hence we need to override it with accessible address.
    await discourse_app.set_config({"external_hostname": f"{unit_ip}:3000"})

    await model.wait_for_idle()

    return discourse_app


@pytest.fixture(scope="module")
def discourse_unit_name(discourse: Application):
    """Get the discourse charm's unit name."""
    return f"{discourse.name}/0"


@pytest_asyncio.fixture(scope="module")
async def discourse_address(model: Model, discourse: Application, discourse_unit_name: str):
    """Get discourse web address."""
    status: FullStatus = await model.get_status()
    app_status = typing.cast(ApplicationStatus, status.applications[discourse.name])
    unit_status = typing.cast(UnitStatus, app_status.units[discourse_unit_name])
    unit_ip = typing.cast(str, unit_status.address)
    return f"http://{unit_ip}:3000"


async def create_discourse_admin_account(discourse: Application, email: str):
    """Create an admin account on discourse.

    Args:
        discourse: The Discourse charm application.
        email: The email address to use to create the account.

    Returns:
        The credentials of the admin user.
    """
    password = secrets.token_urlsafe(16)
    discourse_unit: Unit = discourse.units[0]
    action: Action = await discourse_unit.run_action(
        "add-admin-user", email=email, password=password
    )
    await action.wait()
    return types.Credentials(email=email, username=email.split("@")[0], password=password)


async def create_discourse_admin_api_key(
    discourse_address: str, admin_credentials: types.Credentials
) -> types.APICredentials:
    """Create a discourse admin API key for admin user account.

    Args:
        discourse_address: The discourse web address.
        admin_credentials: The discourse admin user credentials.

    Returns:
        The admin API credentials.
    """
    with requests.session() as sess:
        # Get CSRF token
        res = sess.get(
            f"{discourse_address}/session/csrf", headers={"Accept": "application/json"}, timeout=60
        )
        csrf = res.json()["csrf"]
        # Create session & login
        res = sess.post(
            f"{discourse_address}/session",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "login": admin_credentials.email,
                "password": admin_credentials.password,
                "second_factor_method": "1",
                "timezone": "UTC",
            },
            timeout=60,
        )
        # Create global key
        res = sess.post(
            f"{discourse_address}/admin/api/keys",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
            json={"key": {"description": "admin-api-key", "username": None}},
            timeout=60,
        )

    return types.APICredentials(username=admin_credentials.username, key=res.json()["key"]["key"])


async def create_discourse_account(
    discourse_address: str, email: str, username: str, admin_api_headers: dict[str, str]
) -> types.Credentials:
    """Create an user account on discourse.

    Args:
        discourse_address: The Discourse web address.
        email: The email address to use to create the account.
        username: The username to use to create the account.
        admin_api_headers: Headers with admin API key.

    Returns:
        A newly created discourse user credential.
    """
    password = secrets.token_urlsafe(16)
    # Register user
    requests.post(
        f"{discourse_address}/users.json",
        headers=admin_api_headers,
        json={
            "name": username,
            "email": email,
            "password": password,
            "username": username,
            "active": True,
            "approved": True,
        },
        timeout=60,
    ).raise_for_status()

    return types.Credentials(email=email, username=username, password=password)


def create_user_api_key(
    discourse_address: str,
    admin_api_headers: dict[str, str],
    user_credentials: types.Credentials,
) -> str:
    """
    Create an API key for a user.

    Args:
        discourse_address: The web address discourse is running under.
        admin_api_headers: Headers with admin API key.
        user_credentials: The crednetials of the user to create an API key for.

    Returns:
        The API key for the user.

    """
    data = {"key": {"description": "Test key", "username": user_credentials.username}}
    response = requests.post(
        f"{discourse_address}/admin/api/keys", headers=admin_api_headers, json=data, timeout=60
    )

    return response.json()["key"]["key"]


@pytest_asyncio.fixture(scope="module")
async def discourse_admin_credentials(discourse: Application) -> types.Credentials:
    """Get the admin credentials for discourse."""
    return await create_discourse_admin_account(discourse=discourse, email="test@admin.internal")


@pytest_asyncio.fixture(scope="module")
async def discourse_admin_api_credentials(
    discourse_address: str, discourse_admin_credentials: types.Credentials
) -> types.APICredentials:
    """Get the admin API credentials for discourse."""
    return await create_discourse_admin_api_key(
        discourse_address=discourse_address, admin_credentials=discourse_admin_credentials
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_admin_api_headers(
    admin_api_credentials: types.APICredentials,
) -> dict[str, str]:
    """Headers with admin api key to access API requiring admin privileges."""
    return {
        "Api-Key": admin_api_credentials.key,
        "Api-Username": admin_api_credentials.username,
    }


@pytest_asyncio.fixture(scope="module")
async def discourse_user_credentials(
    discourse_address: str, discourse_admin_api_headers: dict[str, str]
):
    """Get the user credentials for discourse."""
    return await create_discourse_account(
        discourse_address=discourse_address,
        email="user@test.internal",
        username="test_user",
        admin_api_headers=discourse_admin_api_headers,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_alternate_user_credentials(
    discourse_address: str, discourse_admin_api_headers: dict[str, str]
):
    """Get the alternate user credentials for discourse."""
    return await create_discourse_account(
        discourse_address=discourse_address,
        email="alternate_user@test.internal",
        username="alternate_user",
        admin_api_headers=discourse_admin_api_headers,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_user_api_key(
    discourse_admin_api_headers: dict[str, str],
    discourse_user_credentials: types.Credentials,
    discourse_address: str,
):
    """Get the user api key for discourse."""
    return create_user_api_key(
        discourse_address=discourse_address,
        admin_api_headers=discourse_admin_api_headers,
        user_credentials=discourse_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_alternate_user_api_key(
    discourse_admin_api_headers,
    discourse_alternate_user_credentials: types.Credentials,
    discourse_address: str,
):
    """Get the alternate user api key for discourse."""
    return create_user_api_key(
        discourse_address=discourse_address,
        admin_api_headers=discourse_admin_api_headers,
        user_credentials=discourse_alternate_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_client(
    discourse_admin_api_credentials: types.APICredentials, discourse_address: str
):
    """Create the category for topics."""
    return pydiscourse.DiscourseClient(
        host=discourse_address,
        api_username=discourse_admin_api_credentials.username,
        api_key=discourse_admin_api_credentials.key,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_category_id(discourse_client: pydiscourse.DiscourseClient):
    """Create the category for topics."""
    category = discourse_client.create_category(name="docs", color="FFFFFF")
    return category["category"]["id"]


@pytest_asyncio.fixture(scope="module")
async def discourse_api(
    discourse_user_credentials: types.Credentials,
    discourse_address: str,
    discourse_user_api_key: str,
    discourse_category_id: int,
):
    """Create discourse instance."""
    return Discourse(
        base_path=discourse_address,
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )


@pytest.fixture(scope="module", autouse=True)
def discourse_enable_tags(
    discourse_admin_api_credentials: types.APICredentials,
    discourse_address: str,
):
    """Enable tags on discourse."""
    headers = {
        "Api-Key": discourse_admin_api_credentials.key,
        "Api-Username": discourse_admin_api_credentials.username,
    }
    data = {"tagging_enabled": "true"}
    response = requests.put(
        f"{discourse_address}/admin/site_settings/tagging_enabled",
        headers=headers,
        data=data,
        timeout=60,
    )
    assert response.status_code == 200, f"Enabling tagging failed, {response.content=}"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def discourse_remove_rate_limits(
    discourse_admin_api_headers: dict[str, str], discourse_address: str
):
    """Disables rate limits on discourse."""
    settings = {
        "unique_posts_mins": "0",
        "rate_limit_create_post": "0",
        "rate_limit_new_user_create_topic": "0",
        "rate_limit_new_user_create_post": "0",
        "max_topics_per_day": "1000",
        "max_edits_per_day": "1000",
        "max_topics_in_first_day": "1000",
        "max_post_deletions_per_minute": "1000",
        "max_post_deletions_per_day": "1000",
        "min_post_length": "1",
        "min_first_post_length": "1",
        "body_min_entropy": "0",
        "min_topic_title_length": "1",
        "title_min_entropy": "0",
        "title_prettify": "false",
        "allow_duplicate_topic_titles": "false",
        "min_title_similar_length": "1000000",
        "newuser_max_links": "1000000",
    }
    for setting, value in settings.items():
        response = requests.put(
            f"{discourse_address}/admin/site_settings/{setting}",
            headers=discourse_admin_api_headers,
            data={setting: value},
            timeout=60,
        )
        assert (
            response.status_code == 200
        ), f"Setting {setting} to {value} failed, {response.content=}"
