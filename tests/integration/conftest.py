# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for integration tests."""

# pylint: disable=redefined-outer-name

import asyncio
import re
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
from ops.model import ActiveStatus
from pytest_operator.plugin import OpsTest

from src.discourse import Discourse

from . import types


@pytest.fixture(scope="module")
def discourse_hostname():
    """Get the hostname for discourse."""
    return "discourse"


@pytest.fixture(scope="module", name="model")
def model_module_scope_fixture(ops_test: OpsTest) -> Model:
    """Get current valid model created for integraion testing with module scope."""
    assert ops_test.model
    return ops_test.model


async def create_discourse_account(
    ops_test: OpsTest, unit: str, email: str, admin: bool
) -> types.Credentials:
    """
    Create an account on discourse.

    Assume that the model already contains a discourse unit.

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
    assert isinstance(username, str)

    return types.Credentials(email=email, username=username, password=password)


def create_user_api_key(
    discourse_hostname: str, main_api_key: str, user_credentials: types.Credentials
) -> str:
    """
    Create an API key for a user.

    Args:
        discourse_hostname: The hostname that discourse is running under.
        main_api_key: The system main API key for the discourse server.
        user_credentials: The crednetials of the user to create an API key for.

    Returns:
        The API key for the user.

    """
    headers = {"Api-Key": main_api_key, "Api-Username": "system"}
    data = {"key[description]": "Test key", "key[username]": user_credentials.username}
    response = requests.post(
        f"http://{discourse_hostname}/admin/api/keys", headers=headers, data=data, timeout=60
    )
    assert (
        response.status_code == 200
    ), f"API creation failed, {user_credentials.username=}, {response.content=}"

    return response.json()["key"]["key"]


@pytest_asyncio.fixture(scope="module")
async def discourse(model: Model, discourse_hostname: str):
    """Deploy discourse."""
    postgres_charm_name = "postgresql-k8s"
    redis_charm_name = "redis-k8s"
    discourse_charm_name = "discourse-k8s"
    await asyncio.gather(
        model.deploy(postgres_charm_name),
        model.deploy(redis_charm_name),
    )
    # Using permissive throttle level to speed up tests
    discourse_app = await model.deploy(
        # discourse_charm_name,
        "/home/yanks/Documents/canonical/discourse-k8s-operator/discourse-k8s_ubuntu-20.04-amd64.charm",
        resources={"discourse-image": "discourse:test"},
        config={"external_hostname": discourse_hostname, "throttle_level": "permissive"},
    )

    await model.wait_for_idle()

    await model.relate(discourse_charm_name, f"{postgres_charm_name}:db-admin")
    await model.relate(discourse_charm_name, redis_charm_name)

    # mypy seems to have trouble with this line;
    # "error: Cannot determine type of "name"  [has-type]"
    await model.wait_for_idle(status=ActiveStatus.name)  # type: ignore

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


# Making this depend on discourse_admin_credentials to ensure an admin user gets created
@pytest.mark.usefixtures("discourse_admin_credentials")
@pytest_asyncio.fixture(scope="module")
async def discourse_user_credentials(ops_test: OpsTest, discourse_unit_name: str):
    """Get the user credentials for discourse."""
    return await create_discourse_account(
        ops_test=ops_test, unit=discourse_unit_name, email="user@foo.internal", admin=False
    )


# Making this depend on discourse_admin_credentials to ensure an admin user gets created
@pytest.mark.usefixtures("discourse_admin_credentials")
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
async def discourse_main_api_key(model: Model, discourse: Application, discourse_unit_name: str):
    """Get the user global api key for discourse."""
    test_user_email = "testing@admin.com"
    test_user_password = "testingtesting"
    discourse_unit: Unit = discourse.units[0]
    action: Action = await discourse_unit.run_action(
        "add-admin-user", email=test_user_email, password=test_user_password
    )
    await action.wait()
    status: FullStatus = await model.get_status()
    app_status = typing.cast(ApplicationStatus, status.applications[discourse.name])
    unit_status = typing.cast(UnitStatus, app_status.units[discourse_unit_name])
    unit_ip = typing.cast(str, unit_status.address)
    discourse_url = f"http://{unit_ip}:3000"

    with requests.session() as sess:
        res = sess.get(f"{discourse_url}/session/csrf", headers={"Accept": "application/json"})
        csrf = res.json()["csrf"]
        res = sess.post(
            f"{discourse_url}/session",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "login": test_user_email,
                "password": test_user_password,
                "second_factor_method": "1",
                "timezone": "Asia/Hong_Kong",
            },
        )
        res = sess.post(
            f"{discourse_url}/admin/api/keys",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
            json={"key": {"description": "admin-api-key", "username": None}},
        )

        return res.json()["key"]["key"]


@pytest_asyncio.fixture(scope="module")
async def discourse_user_api_key(
    discourse_main_api_key: str,
    discourse_user_credentials: types.Credentials,
    discourse_hostname: str,
):
    """Get the user api key for discourse."""
    return create_user_api_key(
        discourse_hostname=discourse_hostname,
        main_api_key=discourse_main_api_key,
        user_credentials=discourse_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_alternate_user_api_key(
    discourse_main_api_key: str,
    discourse_alternate_user_credentials: types.Credentials,
    discourse_hostname: str,
):
    """Get the alternate user api key for discourse."""
    return create_user_api_key(
        discourse_hostname=discourse_hostname,
        main_api_key=discourse_main_api_key,
        user_credentials=discourse_alternate_user_credentials,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_client(discourse_main_api_key, discourse_hostname: str):
    """Create the category for topics."""
    return pydiscourse.DiscourseClient(
        host=f"http://{discourse_hostname}",
        api_username="system",
        api_key=discourse_main_api_key,
    )


@pytest_asyncio.fixture(scope="module")
async def discourse_category_id(discourse_client: pydiscourse.DiscourseClient):
    """Create the category for topics."""
    category = discourse_client.create_category(name="docs", color="FFFFFF")
    return category["category"]["id"]


@pytest_asyncio.fixture(scope="module")
async def discourse_api(
    discourse_user_credentials: types.Credentials,
    discourse_hostname: str,
    discourse_user_api_key: str,
    discourse_category_id: int,
):
    """Create discourse instance."""
    return Discourse(
        base_path=f"http://{discourse_hostname}",
        api_username=discourse_user_credentials.username,
        api_key=discourse_user_api_key,
        category_id=discourse_category_id,
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def discourse_enable_tags(
    discourse_main_api_key,
    discourse_hostname: str,
):
    """Enable tags on discourse."""
    headers = {"Api-Key": discourse_main_api_key, "Api-Username": "system"}
    data = {"tagging_enabled": "true"}
    response = requests.put(
        f"http://{discourse_hostname}/admin/site_settings/tagging_enabled",
        headers=headers,
        data=data,
        timeout=60,
    )
    assert response.status_code == 200, f"Enabling tagging failed, {response.content=}"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def discourse_remove_rate_limits(discourse_main_api_key, discourse_hostname: str):
    """Disables rate limits on discourse."""
    headers = {"Api-Key": discourse_main_api_key, "Api-Username": "system"}

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
            f"http://{discourse_hostname}/admin/site_settings/{setting}",
            headers=headers,
            data={setting: value},
            timeout=60,
        )
        assert (
            response.status_code == 200
        ), f"Setting {setting} to {value} failed, {response.content=}"
