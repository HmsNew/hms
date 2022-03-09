import os
import re
from platform import python_version as kontol
from telethon import events, Button
from telegram import __version__ as telever
from telethon import __version__ as tlhver
from pyrogram import __version__ as pyrover
from HmsRobot.events import register
from HmsRobot import telethn as tbot


PHOTO = "https://telegra.ph/file/f67dd5909bbff96ff17bd.jpg"

@register(pattern=("/alive"))
async def awake(event):
  TEXT = f"**Hi [{event.sender.first_name}](tg://user?id={event.sender.id}), I'm HmsRobot.** \n\n"
  TEXT += "🖤 **أنا أعمل بشكل صحيح** \n\n"
  TEXT += f"🖤 **#الملكه : [ My Queen ♡](https://t.me/hms_01)** \n\n"
  TEXT += f"🖤 **#المكتبة :** `{telever}` \n\n"
  TEXT += f"🖤 **#تيليثون :** `{tlhver}` \n\n"
  TEXT += f"🖤 **#بايروجرام :** `{pyrover}` \n\n"
  TEXT += "**شكرا لإضافتي هنا 🖤**"
  BUTTON = [[Button.url("Update", "https://t.me/botatiiii"), Button.url("Support", "https://t.me/dd3mhms")]]
  await tbot.send_file(event.chat_id, PHOTO, caption=TEXT,  buttons=BUTTON)
