from __future__ import annotations

import re
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message, User

from bot.permissions import can_restrict, is_admin
from bot.utils import mention
from core import redis as _redis
from core.config import settings
from core.database import (
    add_warning,
    get_stats,
    get_threshold,
    remove_warning,
    reset_warnings,
    set_threshold,
)

router = Router()

MUTED_PERMS = ChatPermissions(can_send_messages=False)

_DURATION_RE = re.compile(r"(?:^|\s)(\d+)\s*([smhd])\b", re.IGNORECASE)
_DURATION_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def _parse_duration(raw: str) -> timedelta | None:
    m = _DURATION_RE.search(raw)
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2).lower()
    if value <= 0:
        return None
    parsed = timedelta(**{_DURATION_UNITS[unit]: value})
    if parsed > settings.max_mute_duration:
        return None
    return parsed


async def _admins_only(message: Message) -> bool:
    if await is_admin(message):
        return True
    with suppress(TelegramAPIError):
        await message.reply("только для админов")
    return False


async def _target(message: Message, command: CommandObject | None = None) -> User | None:
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if target is None or target.is_bot:
            await message.reply("это бот, его не трону")
            return None
        return target

    username = None
    if command and command.args:
        for p in command.args.split():
            if p.startswith("@"):
                username = p
                break
    if not username:
        await message.reply("ответь на сообщение или укажи @юзернейм")
        return None

    user_id = await _redis.resolve_username(username)
    if user_id is None:
        await message.reply("не знаю такого пользователя — нужно чтобы он написал в чат")
        return None

    try:
        member = await message.chat.get_member(user_id)
    except TelegramAPIError:
        await message.reply("не нашёл такого пользователя")
        return None
    if member.user.is_bot:
        await message.reply("это бот, его не трону")
        return None
    return member.user


async def _mute(message: Message, user: User, duration: timedelta, suffix: str) -> bool:
    until = datetime.now(UTC) + duration
    try:
        await message.chat.restrict(user.id, permissions=MUTED_PERMS, until_date=until)
    except TelegramAPIError:
        return False
    await message.answer(f"🤐 {mention(user)} — {suffix}")
    return True


@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "✨ <b>toxiguard</b> на страже\n" "/stats /warn /unwarn /mute /unmute /top /threshold"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not await _admins_only(message):
        return
    data = await get_stats(message.chat.id)
    thr = await get_threshold(message.chat.id)
    by_cat = data.get("by_category") or {}
    cat_line = " · ".join(f"{k} {v}" for k, v in by_cat.items()) or "—"
    await message.answer(
        f"📊 инцидентов: <b>{data['total']}</b>\n"
        f"по типам: {cat_line}\n"
        f"порог: <b>{thr:.2f}</b>"
    )


@router.message(Command("warn"))
async def cmd_warn(message: Message, command: CommandObject) -> None:
    if not await _admins_only(message):
        return
    target = await _target(message, command)
    if target is None:
        return
    count = await add_warning(message.chat.id, target.id)
    await message.answer(f"⚠️ {mention(target)} · {count}/{settings.mute_after}")
    if count >= settings.mute_after:
        if not await can_restrict(message.chat):
            await message.answer("⚠️ бот не может ограничивать участников")
            return
        if not await _mute(message, target, settings.mute_duration, "час тишины"):
            await message.answer("⚠️ не хватает прав")


@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message, command: CommandObject) -> None:
    if not await _admins_only(message):
        return
    target = await _target(message, command)
    if target is None:
        return
    count = await remove_warning(message.chat.id, target.id)
    await message.answer(f"✅ снято · осталось {count}")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if not await _admins_only(message):
        return
    target = await _target(message, command)
    if target is None:
        return

    duration = settings.mute_duration
    label = "1h"
    if command.args:
        parsed = _parse_duration(command.args)
        if parsed is None:
            await message.answer("формат: 30m, 2h, 1d (макс 366d)")
            return
        duration = parsed
        m = _DURATION_RE.search(command.args)
        label = m.group(0).strip() if m else "1h"
    if not await can_restrict(message.chat):
        await message.answer("⚠️ бот не может ограничивать участников")
        return
    if not await _mute(message, target, duration, label):
        await message.answer("⚠️ не хватает прав")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, command: CommandObject) -> None:
    if not await _admins_only(message):
        return
    target = await _target(message, command)
    if target is None:
        return
    if not await can_restrict(message.chat):
        await message.answer("⚠️ бот не может ограничивать участников")
        return
    try:
        await message.chat.restrict(target.id, permissions=ChatPermissions(can_send_messages=True))
    except TelegramAPIError:
        await message.answer("⚠️ не хватает прав")
        return
    await reset_warnings(message.chat.id, target.id)
    await message.answer(f"✨ {mention(target)} снова с нами")


@router.message(Command("top", "top_toxic"))
async def cmd_top(message: Message) -> None:
    if not await _admins_only(message):
        return
    data = await get_stats(message.chat.id)
    top = data["top_offenders"]
    if not top:
        await message.answer("🌿 тишина и покой")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = [
        f"{medals[i] if i < 3 else f'{i + 1}.'} "
        f"{('@' + u['username']) if u['username'] else 'аноним'} · {u['count']}"
        for i, u in enumerate(top)
    ]
    await message.answer("\n".join(lines))


@router.message(Command("threshold", "settings"))
async def cmd_threshold(message: Message, command: CommandObject) -> None:
    if not await _admins_only(message):
        return

    if not command.args:
        thr = await get_threshold(message.chat.id)
        await message.answer(f"порог: <b>{thr:.2f}</b>\nизменить: <code>/threshold 0.7</code>")
        return

    try:
        value = float(command.args.replace(",", "."))
    except ValueError:
        await message.answer("это не число")
        return
    if not 0.0 <= value <= 1.0:
        await message.answer("от 0 до 1")
        return

    await set_threshold(message.chat.id, value)
    await message.answer(f"✅ порог: <b>{value:.2f}</b>")
