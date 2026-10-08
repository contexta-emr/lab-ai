"""Make localhost inside the test container behave like a developer's machine.

The console's JavaScript calls http://localhost:8000 - NEXT_PUBLIC_API_URL is
compiled into the page - and inside a separate container localhost is that
container. This forwards ports 3000 and 8000 to the compose services, so the
browser sees exactly the origins a developer's browser sees, CORS included.
Rewriting URLs instead would change the page's origin and test a CORS setup
nobody runs.

Started by conftest.py; not meant to be run by hand.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

ROUTES = {3000: ("web", 3000), 8000: ("api", 8000)}


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except ConnectionError:
        pass
    finally:
        writer.close()


def _handler(
    target: tuple[str, int],
) -> Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]:
    async def handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter) -> None:
        try:
            upstream_r, upstream_w = await asyncio.open_connection(*target)
        except OSError:
            client_w.close()
            return
        await asyncio.gather(_pipe(client_r, upstream_w), _pipe(upstream_r, client_w))

    return handle


async def main() -> None:
    servers = [
        await asyncio.start_server(_handler(target), "127.0.0.1", port)
        for port, target in ROUTES.items()
    ]
    await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
    asyncio.run(main())
