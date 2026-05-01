from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv

from bot.handlers import router
from bot.middleware import ToxicityMiddleware
from core.analyzer import warmup
from core.database import init_db


COMMANDS = [
    BotCommand(command="stats", description="сводка по чату"),
    BotCommand(command="warn", description="выдать варн (ответом)"),
    BotCommand(command="unwarn", description="снять варн (ответом)"),
    BotCommand(command="mute", description="заглушить (ответом, /mute 1h)"),
    BotCommand(command="unmute", description="вернуть голос (ответом)"),
    BotCommand(command="top", description="топ нарушителей"),
    BotCommand(command="threshold", description="порог чувствительности"),
]


def _configure_logging() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("aiogram").setLevel(logging.WARNING)


async def main() -> None:
    load_dotenv()
    _configure_logging()

    await init_db()
    warmup()

    bot = Bot(
        token=os.environ["BOT_TOKEN"],
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.outer_middleware(ToxicityMiddleware())
    dp.include_router(router)

    try:
        await bot.set_my_commands(COMMANDS)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
