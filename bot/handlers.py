from __future__ import annotations

import re
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message, User

from bot.permissions import is_admin
from core.database import (
    add_warning,
    get_stats,
    get_threshold,
    remove_warning,
    reset_warnings,
    set_threshold,
)

router = Router()

MUTE_AFTER = 3
DEFAULT_MUTE = timedelta(hours=1)
MUTED_PERMS = ChatPermissions(can_send_messages=False)
OPEN_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
)

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.IGNORECASE)
_DURATION_UNITS = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def _parse_duration(raw: str) -> Optional[timedelta]:
    m = _DURATION_RE.match(raw)
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2).lower()
    if value <= 0:
        return None
    return timedelta(**{_DURATION_UNITS[unit]: value})


def _mention(user: User) -> str:
    return f"@{user.username}" if user.username else user.full_name


async def _guard(message: Message) -> bool:
    if await is_admin(message):
        return True
    with suppress(TelegramAPIError):
        await message.reply("команда доступна только администраторам")
    return False


async def _replied_user(message: Message) -> Optional[User]:
    if not message.reply_to_message:
        await message.answer("ответь на сообщение пользователя")
        return None
    return message.reply_to_message.from_user


async def _mute(message: Message, user: User, duration: timedelta, reason: str) -> bool:
    until = datetime.now(timezone.utc) + duration
    try:
        await message.chat.restrict(user.id, permissions=MUTED_PERMS, until_date=until)
    except TelegramAPIError:
        return False
    await message.answer(f"{_mention(user)} в тишине — {reason}")
    return True


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "toxiguard на страже.\n"
        "команды для админов — /stats, /warn, /unwarn, /mute, /unmute, /top, /threshold."
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not await _guard(message):
        return
    data = await get_stats(message.chat.id)
    thr = await get_threshold(message.chat.id)
    await message.answer(
        f"инцидентов всего — {data['total']}\n"
        f"порог чувствительности — {thr:.2f}"
    )


@router.message(Command("warn"))
async def cmd_warn(message: Message) -> None:
    if not await _guard(message):
        return
    target = await _replied_user(message)
    if target is None:
        return

    count = await add_warning(message.chat.id, target.id)
    await message.answer(f"⚠️ {_mention(target)} получил варн — итого {count}/{MUTE_AFTER}")

    if count >= MUTE_AFTER:
        await _mute(message, target, DEFAULT_MUTE, "час молчания за повторные нарушения")


@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message) -> None:
    if not await _guard(message):
        return
    target = await _replied_user(message)
    if target is None:
        return

    count = await remove_warning(message.chat.id, target.id)
    await message.answer(f"варн снят — осталось {count}")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if not await _guard(message):
        return
    target = await _replied_user(message)
    if target is None:
        return

    duration = DEFAULT_MUTE
    if command.args:
        parsed = _parse_duration(command.args)
        if parsed is None:
            await message.answer("длительность — например, 30m, 2h, 1d")
            return
        duration = parsed

    ok = await _mute(message, target, duration, f"{command.args or '1h'} по решению админа")
    if not ok:
        await message.answer("не удалось ограничить — проверь права бота")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message) -> None:
    if not await _guard(message):
        return
    target = await _replied_user(message)
    if target is None:
        return

    try:
        await message.chat.restrict(target.id, permissions=OPEN_PERMS)
    except TelegramAPIError:
        await message.answer("не удалось снять ограничения — проверь права бота")
        return

    await reset_warnings(message.chat.id, target.id)
    await message.answer(f"{_mention(target)} снова с нами")


@router.message(Command("top", "top_toxic"))
async def cmd_top(message: Message) -> None:
    if not await _guard(message):
        return
    data = await get_stats(message.chat.id)
    top = data["top_offenders"]

    if not top:
        await message.answer("тишина и покой")
        return

    lines = [
        f"{i}. {('@' + u['username']) if u['username'] else 'аноним'} (id {u['user_id']}) — {u['count']}"
        for i, u in enumerate(top, start=1)
    ]
    await message.answer("\n".join(lines))


@router.message(Command("threshold", "settings"))
async def cmd_threshold(message: Message, command: CommandObject) -> None:
    if not await _guard(message):
        return

    if not command.args:
        thr = await get_threshold(message.chat.id)
        await message.answer(
            f"текущий порог — {thr:.2f}\n"
            f"чтобы изменить — /threshold 0.7"
        )
        return

    try:
        value = float(command.args.replace(",", "."))
    except ValueError:
        await message.answer("это не число")
        return

    if not 0.0 <= value <= 1.0:
        await message.answer("число должно быть от 0 до 1")
        return

    await set_threshold(message.chat.id, value)
    await message.answer(f"порог установлен — {value:.2f}")
