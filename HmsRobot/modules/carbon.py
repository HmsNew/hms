from platform import python_version as y
from telegram import __version__ as o
from pyrogram import __version__ as z
from telethon import __version__ as s
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters
from HmsRobot import pbot
from HmsRobot.utils.errors import capture_err
from HmsRobot.utils.functions import make_carbon


@pbot.on_message(filters.command("carbon"))
@capture_err
async def carbon_func(_, message):
    if not message.reply_to_message:
        return await message.reply_text("`الرد على رسالة نصية لجعل الكربون.`")
    if not message.reply_to_message.text:
        return await message.reply_text("`الرد على رسالة نصية لجعل الكربون.`")
    m = await message.reply_text("`تحضير الكربون`")
    carbon = await make_carbon(message.reply_to_message.text)
    await m.edit("`تحميل`")
    await pbot.send_photo(message.chat.id, carbon)
    await m.delete()
    carbon.close()


MEMEK = "https://telegra.ph/file/f67dd5909bbff96ff17bd.jpg"

@pbot.on_message(filters.command("repo"))
async def repo(_, message):
    await message.reply_photo(
        photo=MEMEK,
        caption=f"""✨ **Hey I'm HmsRobot** 

**#الملكه 🖤 : [My Queen](https://t.me/hms_01)**
**#بايثون 🖤 :** `{y()}`
**#المكتبه 🖤 :** `{o}`
**#تيليثون 🖤 :** `{s}`
**#بايروجرام 🖤 :** `{z}`

**إنشاء الخاصة بك مع انقر فوق الزر أدناه.**
""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "HmS", url="https://t.me/hms_01"), 
                    InlineKeyboardButton(
                        "Support", url="https://t.me/dd3mhms")
                ]
            ]
        )
    )
