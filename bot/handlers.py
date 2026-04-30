#handlers
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from core.database import get_stats, add_warning, remove_warning, set_threshold

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    data = await get_stats(message.chat.id)
    await message.answer(f"Токсичных {data['total']}")

@router.message(Command("warn"))
async def cmd_warn(message: Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение нарушителя")
        return
    
    target = message.reply_to_message.from_user
    count = await add_warning(message.chat.id, target.id)
    
    await message.answer(
        f"⚠️ {target.full_name} получил варн!\n"
        f"Варнов: {count}"
    )


@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение нарушителя")
        return
    
    target = message.reply_to_message.from_user
    count = await remove_warning(message.chat.id, target.id)

    await message.answer(
        f"✅ Варн снят\n"
        f"Осталось варнов: {count}"
    )

@router.message(Command("top_toxic"))
async def cmd_top_toxic(message: Message):
    data = await get_stats(message.chat.id)
    top = data["top_offenders"]  # это список словарей

    if not top:
        await message.answer("Нарушителей нет")
        return

    toplist = []
    for i, user in enumerate(top, start=1):
        toplist.append(f"{i}. {user['username']} — {user['count']} сообщений")
    
    await message.answer("\n".join(toplist))

@router.message(Command("settings"))
async def cmd_settings(message: Message, command: CommandObject):

    if not command.args:
        await message.answer("⚙️ Укажи порог: /settings 0.7")
        return
    
    try:
        threshold = float(command.args)
    except ValueError:
        await message.answer("❌ Это не число")
        return
    
    if not (0.0 <= threshold <= 1.0):
        await message.answer("❌ Число должно быть от 0.0 до 1.0")
        return

    await set_threshold(message.chat.id, threshold)
    await message.answer(f"✅ Порог установлен: {threshold}")