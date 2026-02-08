import asyncio

from dishka import make_async_container

from app.di import AppProvider
from bot import start_bot


async def main() -> None:
    container = make_async_container(AppProvider())

    await start_bot(app_container=container)


if __name__ == "__main__":
    asyncio.run(main())
