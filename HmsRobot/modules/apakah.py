import random
from HmsRobot.events import register
from HmsRobot import telethn

APAKAH_STRING = ["Iya", 
                 "لا", 
                 "يمكن", 
                 "على الاغلب لا", 
                 "يمكن ان تكون", 
                 "على الاغلب لا",
                 "غير ممكن",
                 "YNTKTS",
                 "كسر جوزة الطيب والدك",
                 "Apa iya?",
                 "فقط اسأل والدتك pler"
                 ]


@register(pattern="^/apakah ?(.*)")
async def apakah(event):
    quew = event.pattern_match.group(1)
    if not quew:
        await event.reply('أعطني سؤالا 😐')
        return
    await event.reply(random.choice(APAKAH_STRING))
