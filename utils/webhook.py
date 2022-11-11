from __future__ import annotations

import json

from typing import TYPE_CHECKING, Callable, Coroutine, Any, TypeVar
from aiohttp import web

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

T = TypeVar("T")
Coro: TypeAlias = Coroutine[Any, Any, T]
EndpointHandler: TypeAlias = Callable[[Any], Coro[Any]]


class WebhookServer:
    """Webhook server that receives hooks from InviteManager"""

    if TYPE_CHECKING:
        _app: web.Application
        _site: web.TCPSite

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        secret: str | None = None,
    ) -> None:
        self._app = web.Application()
        self._secret = secret
        self.host = host
        self.port = port

    @property
    def name(self) -> str:
        return self._site.name

    @property
    def secret(self) -> str | None:
        return self._secret

    def add_endpoint(self, handler: EndpointHandler, *, path: str = "/"):
        async def _handler_wrapper(request: web.Request) -> web.StreamResponse:
            authorization = request.headers.get("Authorization", None)
            if self._secret is not None and authorization != self._secret:
                return web.Response(status=401, text="Unauthorized")

            try:
                data = await request.json()
            except json.JSONDecodeError:
                return web.Response(status=400, text="Bad Request")

            await handler(data)
            return web.Response(status=200, text="OK")

        self._app.router.add_post(
            path=path,
            handler=_handler_wrapper,
        )

    async def start(self) -> None:
        runner = web.AppRunner(self._app)
        await runner.setup()
        self._site = web.TCPSite(runner=runner, host=self.host, port=self.port)
        await self._site.start()

    async def close(self) -> None:
        await self._site.stop()
