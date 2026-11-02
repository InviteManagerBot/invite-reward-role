"""HTTP endpoint that receives InviteCount invite alerts.

InviteCount sends one POST request per alert, with a JSON body and your server's
webhook secret as the raw value of the ``Authorization`` header (no HMAC, no
timestamp). Example body::

    {
      "user": {"username": "john", "id": "987654321098765432", "avatar": "a1b2c3...",
               "discriminator": "0", "bot": false},
      "invites": 50,
      "guild_id": "123456789012345678",
      "type": "reached"
    }

``/alert-invites webhook test`` sends the same body with ``"invites": -1``.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiohttp import web

log = logging.getLogger(__name__)

# The body is tiny; anything bigger is not from InviteCount.
MAX_BODY_SIZE = 16 * 1024


@dataclass(frozen=True, slots=True)
class InviteAlert:
    guild_id: int
    user_id: int
    username: str
    invites: int
    is_bot: bool

    @property
    def is_test(self) -> bool:
        """``/alert-invites webhook test`` sends ``invites = -1``."""
        return self.invites < 0


class PayloadError(ValueError):
    """The body is not a valid InviteCount alert."""


def verify_authorization(header: str | None, secret: str) -> bool:
    """True when the ``Authorization`` header is exactly the webhook secret.

    ``hmac.compare_digest`` takes the same time whatever the first wrong
    character is, so the secret cannot be guessed by timing the responses.
    """
    if not header or not secret:
        return False
    return hmac.compare_digest(header.strip().encode(), secret.encode())


def _snowflake(value: object, field: str) -> int:
    # Discord IDs are sent as strings (they do not fit in a JavaScript number).
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise PayloadError(f"{field} must be a string ID")
    try:
        number = int(value)
    except ValueError:
        raise PayloadError(f"{field} must be a numeric ID") from None
    if number <= 0:
        raise PayloadError(f"{field} must be positive")
    return number


def parse_alert(data: object) -> InviteAlert:
    """Validate the JSON body and return an :class:`InviteAlert`."""
    if not isinstance(data, dict):
        raise PayloadError("body must be a JSON object")
    if data.get("type") != "reached":
        raise PayloadError(f"unsupported alert type: {data.get('type')!r}")

    user = data.get("user")
    if not isinstance(user, dict):
        raise PayloadError("user must be an object")

    invites = data.get("invites")
    if isinstance(invites, bool) or not isinstance(invites, int):
        raise PayloadError("invites must be an integer")

    return InviteAlert(
        guild_id=_snowflake(data.get("guild_id"), "guild_id"),
        user_id=_snowflake(user.get("id"), "user.id"),
        username=str(user.get("username", "")),
        invites=invites,
        is_bot=bool(user.get("bot", False)),
    )


AlertHandler = Callable[[InviteAlert], Awaitable[None]]


def create_app(secret: str, handler: AlertHandler, *, path: str = "/webhook") -> web.Application:
    """Build the aiohttp application. ``handler`` runs in the background so
    InviteCount gets its answer at once (it gives up after 5 seconds)."""
    if not secret:
        raise ValueError("a webhook secret is required")

    tasks: set[asyncio.Task[None]] = set()

    async def receive(request: web.Request) -> web.Response:
        if not verify_authorization(request.headers.get("Authorization"), secret):
            log.warning("Rejected a webhook request with a wrong secret from %s", request.remote)
            return web.json_response({"error": "unauthorized"}, status=401)

        try:
            alert = parse_alert(await request.json())
        except web.HTTPRequestEntityTooLarge:
            return web.json_response({"error": "body too large"}, status=413)
        except ValueError as exc:  # JSONDecodeError and PayloadError are both ValueErrors
            log.warning("Rejected an invalid webhook body: %s", exc)
            return web.json_response({"error": "invalid body"}, status=400)

        # Keep a reference so the task is not garbage collected mid-way.
        task = asyncio.create_task(handler(alert))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return web.json_response({"ok": True})

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    app = web.Application(client_max_size=MAX_BODY_SIZE)
    app.router.add_post(path, receive)
    app.router.add_get("/health", health)
    return app
