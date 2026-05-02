from __future__ import annotations

import asyncio
import logging
import signal
import sys
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.handlers import router
from bot.middleware import ToxicityMiddleware
from core.analyzer import warmup
from core.config import settings
from core.database import cleanup_events, dispose_engine, init_db

log = logging.getLogger("toxiguard")

COMMANDS = [
    BotCommand(command="stats", description="📊 сводка"),
    BotCommand(command="top", description="🏆 топ нарушителей"),
    BotCommand(command="warn", description="⚠️ выдать варн"),
    BotCommand(command="unwarn", description="✅ снять варн"),
    BotCommand(command="mute", description="🤐 мут (например 1h)"),
    BotCommand(command="unmute", description="✨ снять мут"),
    BotCommand(command="threshold", description="🎚 порог чувствительности"),
]


def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s · %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    for noisy in ("aiogram.event", "aiogram.dispatcher"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            removed = await cleanup_events()
            log.debug("cleanup removed %s events", removed)
        except Exception:
            pass


async def _run() -> None:
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set")

    log.info("starting toxiguard…")
    await init_db()
    warmup()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.outer_middleware(ToxicityMiddleware())
    dp.include_router(router)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    log.info("online as @%s", me.username)

    polling = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    waiter = asyncio.create_task(stop.wait())
    cleanup = asyncio.create_task(_cleanup_loop())
    try:
        await asyncio.wait({polling, waiter}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        log.info("shutting down…")
        with suppress(Exception):
            await dp.stop_polling()
        polling.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await polling
        waiter.cancel()
        cleanup.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await cleanup
        with suppress(Exception):
            await bot.session.close()
        with suppress(Exception):
            await dispose_engine()
        log.info("bye")


def main() -> None:
    _configure_logging()
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
