"""A limit on request body size, in the app itself.

Caddy has the same limit in production (deploy/Caddyfile), but the dev and
Compose paths have no Caddy in front of them, so the API must hold on its own.

Pure ASGI on purpose: it replaces `receive` and hands `send` to the app
untouched, so every server-sent event of a /chat answer goes straight to the
client. BaseHTTPMiddleware would put its own stream between the two.
"""

import json


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Refuses a large body without reading it. Only a shortcut: Content-Length
        # is the client's claim, and a chunked body doesn't have one.
        if self._declared_size(scope) > self.max_bytes:
            await self._refuse(send)
            return

        # The real limit: the bytes that actually arrive. Reading them first means
        # the app never starts on a body that later turns out too big.
        messages = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break  # the client went away; the app sees that below
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._refuse(send)
                return
            if not message.get("more_body", False):
                break

        # The app reads the same messages, then the real `receive`, so it still
        # hears about a client that disconnects in the middle of an answer.
        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    def _declared_size(scope) -> int:
        for name, value in scope["headers"]:
            if name == b"content-length" and value.isdigit():
                return int(value)
        return 0

    @staticmethod
    async def _refuse(send) -> None:
        body = json.dumps({"kind": "too_large", "message": "The request is too large."}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    # The rest of the body is never read, so the connection can't be reused.
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
