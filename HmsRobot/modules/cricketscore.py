# credits  @BPython

import urllib.request

from bs4 import BeautifulSoup
from telethon import events
from HmsRobot import telethn as tbot
from telethon.tl import functions, types
from telethon.tl.types import *


async def is_register_admin(chat, user):
    if isinstance(chat, (types.InputPeerChannel, types.InputChannel)):
        return isinstance(
            (
                await tbot(functions.channels.GetParticipantRequest(chat, user))
            ).participant,
            (types.ChannelParticipantAdmin, types.ChannelParticipantCreator),
        )
    if isinstance(chat, types.InputPeerUser):
        return True


@tbot.on(events.NewMessage(pattern="/cs$"))
async def _(event):
    if event.fwd_from:
        return
    if event.is_group:
     if not (await is_register_admin(event.input_chat, event.message.sender_id)):
       await event.reply("🚨 تحتاج Admin Pewer .. لا يمكنك استخدام هذا الأمر .. ولكن يمكنك استخدامها في بلدي مساء")
       return

    score_page = "http://static.cricinfo.com/rss/livescores.xml"
    page = urllib.request.urlopen(score_page)
    soup = BeautifulSoup(page, "html.parser")
    result = soup.find_all("description")
    Sed = ""
    for match in result:
        Sed += match.get_text() + "\n\n"
    await event.reply(
        f"<b><u>تم جمع معلومات المباراة بنجاح</b></u>\n\n\n<code>{Sed}</code>",
        parse_mode="HTML",
    )


__help__ = """
*نتيجة الكركيت المباشرة*
 ❂ /cs*:* أحدث النتائج الحية من cricinfo
"""

__mod_name__ = "Cricket"
