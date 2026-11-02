from __future__ import annotations

import asyncio
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from reward_bot.db import RewardStore
from reward_bot.webhook import InviteAlert, PayloadError, create_app, parse_alert, verify_authorization

SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# Exactly what InviteCount sends (bot/cogs/core/welcomer.py, trigger_webhook_alert).
PAYLOAD = {
    "user": {
        "username": "john",
        "id": "987654321098765432",
        "avatar": "a1b2c3d4e5f6",
        "discriminator": "0",
        "bot": False,
    },
    "invites": 50,
    "guild_id": "123456789012345678",
    "type": "reached",
}


def test_verify_authorization():
    assert verify_authorization(SECRET, SECRET)
    assert verify_authorization(f" {SECRET}\n", SECRET)
    assert not verify_authorization(SECRET[:-1] + "0", SECRET)
    assert not verify_authorization("", SECRET)
    assert not verify_authorization(None, SECRET)
    assert not verify_authorization(SECRET, "")


def test_parse_alert():
    alert = parse_alert(PAYLOAD)
    assert alert == InviteAlert(
        guild_id=123456789012345678, user_id=987654321098765432, username="john", invites=50, is_bot=False
    )
    assert not alert.is_test


def test_parse_test_request():
    assert parse_alert({**PAYLOAD, "invites": -1}).is_test


@pytest.mark.parametrize(
    "body",
    [
        [],
        {**PAYLOAD, "type": "lost"},
        {**PAYLOAD, "invites": "50"},
        {**PAYLOAD, "invites": True},
        {**PAYLOAD, "guild_id": "abc"},
        {**PAYLOAD, "guild_id": None},
        {**PAYLOAD, "user": "john"},
        {**PAYLOAD, "user": {"id": "-5"}},
    ],
)
def test_parse_rejects_invalid(body):
    with pytest.raises(PayloadError):
        parse_alert(body)


def test_roles_earned():
    store = RewardStore(":memory:")
    store.set_reward(1, 10, 5)
    store.set_reward(1, 20, 50)
    store.set_reward(1, 30, 100)
    store.set_reward(2, 40, 1)
    assert sorted(store.roles_earned(1, 50)) == [10, 20]
    store.set_reward(1, 20, 60)  # same role: requirement updated, not duplicated
    assert store.roles_earned(1, 50) == [10]
    assert store.remove_reward(1, 10)
    assert not store.remove_reward(1, 10)
    assert store.list_rewards(1) == [(20, 60), (30, 100)]


def test_endpoint():
    async def scenario():
        received: list[InviteAlert] = []

        async def handler(alert: InviteAlert) -> None:
            received.append(alert)

        async with TestClient(TestServer(create_app(SECRET, handler))) as client:
            ok = await client.post("/webhook", json=PAYLOAD, headers={"Authorization": SECRET})
            wrong = await client.post("/webhook", json=PAYLOAD, headers={"Authorization": "nope"})
            missing = await client.post("/webhook", json=PAYLOAD)
            bad_json = await client.post("/webhook", data="{", headers={"Authorization": SECRET})
            too_big = await client.post(
                "/webhook", data=json.dumps({"x": "a" * 20_000}), headers={"Authorization": SECRET}
            )
            health = await client.get("/health")
            await asyncio.sleep(0)  # let the background handler run
            return [ok.status, wrong.status, missing.status, bad_json.status, too_big.status, health.status], received

    statuses, received = asyncio.run(scenario())
    assert statuses == [200, 401, 401, 400, 413, 200]
    assert [alert.invites for alert in received] == [50]
