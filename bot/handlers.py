from __future__ import annotations

from contextlib import suppress

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from core.database import (
    add_warning,
    get_stats,
    mark_banned,
    remove_warning,
    set_threshold,
)

router = Router()

BAN_AFTER = 3


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "toxiguard на страже.\n"
        "команды — /stats, /warn, /unwarn, /top_toxic, /settings."
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    data = await get_stats(message.chat.id)
    await message.answer(f"токсичных сообщений — {data['total']}")


@router.message(Command("warn"))
async def cmd_warn(message: Message) -> None:
    if not message.reply_to_message:
        await message.answer("ответь на сообщение нарушителя")
        return

    target = message.reply_to_message.from_user
    if target is None:
        return

    count = await add_warning(message.chat.id, target.id)
    await message.answer(f"⚠️ {target.full_name} получил варн — итого {count}")

    if count >= BAN_AFTER:
        with suppress(TelegramAPIError):
            await message.chat.ban(target.id)
        await mark_banned(message.chat.id, target.id)
        await message.answer(f"🚪 {target.full_name} удалён из чата")


@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message) -> None:
    if not message.reply_to_message:
        await message.answer("ответь на сообщение нарушителя")
        return

    target = message.reply_to_message.from_user
    if target is None:
        return

    count = await remove_warning(message.chat.id, target.id)
    await message.answer(f"варн снят — осталось {count}")


@router.message(Command("top_toxic"))
async def cmd_top_toxic(message: Message) -> None:
    data = await get_stats(message.chat.id)
    top = data["top_offenders"]

    if not top:
        await message.answer("тишина и покой")
        return

    lines = [
        f"{i}. {u['username'] or u['user_id']} — {u['count']}"
        for i, u in enumerate(top, start=1)
    ]
    await message.answer("\n".join(lines))


@router.message(Command("settings"))
async def cmd_settings(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("укажи порог — /settings 0.7")
        return

    try:
        threshold = float(command.args)
    except ValueError:
        await message.answer("это не число")
        return

    if not 0.0 <= threshold <= 1.0:
        await message.answer("число должно быть от 0 до 1")
        return

    await set_threshold(message.chat.id, threshold)
    await message.answer(f"порог установлен — {threshold:.2f}")
