import os
from HmsRobot.modules.sql.night_mode_sql import (
    add_nightmode,
    rmnightmode,
    get_all_chat_id,
    is_nightmode_indb,
)
from telethon.tl.types import ChatBannedRights
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from telethon import functions
from HmsRobot.events import register
from HmsRobot import telethn as tbot, OWNER_ID
from telethon import Button, custom, events

hehes = ChatBannedRights(
    until_date=None,
    send_messages=True,
    send_media=True,
    send_stickers=True,
    send_gifs=True,
    send_games=True,
    send_inline=True,
    send_polls=True,
    invite_users=True,
    pin_messages=True,
    change_info=True,
)

openhehe = ChatBannedRights(
    until_date=None,
    send_messages=False,
    send_media=False,
    send_stickers=False,
    send_gifs=False,
    send_games=False,
    send_inline=False,
    send_polls=False,
    invite_users=True,
    pin_messages=True,
    change_info=True,
)

from telethon.tl.types import (
    ChannelParticipantsAdmins,
    ChatAdminRights,
    MessageEntityMentionName,
    MessageMediaPhoto,
)

from telethon.tl.functions.channels import (
    EditAdminRequest,
    EditBannedRequest,
    EditPhotoRequest,
)

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

async def can_change_info(message):
    result = await tbot(
        functions.channels.GetParticipantRequest(
            channel=message.chat_id,
            user_id=message.sender_id,
        )
    )
    p = result.participant
    return isinstance(p, types.ChannelParticipantCreator) or (
        isinstance(p, types.ChannelParticipantAdmin) and p.admin_rights.change_info
    )

@register(pattern="^/(nightmode|Nightmode|NightMode|kontolmode|KONTOLMODE) ?(.*)")
async def profanity(event):
    if event.fwd_from:
        return
    if event.is_private:
        return
    input = event.pattern_match.group(2)
    if not event.sender_id == OWNER_ID:
        if not await is_register_admin(event.input_chat, event.sender_id):
           await event.reply("يمكن للمسؤولين فقط تنفيذ هذا الأمر!")
           return
        else:
          if not await can_change_info(message=event):
            await event.reply("تفتقد الحقوق التالية لاستخدام هذا الأمر: CanChangeinfo")
            return
    if not input:
        if is_nightmode_indb(str(event.chat_id)):
                await event.reply(
                    "تم تمكين NightMode حاليًا لهذه الدردشة"
                )
                return
        await event.reply(
            "NightMode معطل حاليًا لهذه الدردشة"
        )
        return
    if "on" in input:
        if event.is_group:
            if is_nightmode_indb(str(event.chat_id)):
                    await event.reply(
                        "الوضع الليلي قيد التشغيل بالفعل لهذه الدردشة"
                    )
                    return
            add_nightmode(str(event.chat_id))
            await event.reply("تم تشغيل الوضع الليلي لهذه الدردشة.")
    if "off" in input:
        if event.is_group:
            if not is_nightmode_indb(str(event.chat_id)):
                    await event.reply(
                        "الوضع الليلي متوقف بالفعل لهذه الدردشة"
                    )
                    return
        rmnightmode(str(event.chat_id))
        await event.reply("الوضع الليلي معطل!")
    if not "off" in input and not "on" in input:
        await event.reply("يرجى تحديد تشغيل أو إيقاف تشغيل!")
        return


async def job_close():
    chats = get_all_chat_id()
    if len(chats) == 0:
        return
    for pro in chats:
        try:
            await tbot.send_message(
              int(pro.chat_id), "12:00 صباحًا ، ستغلق المجموعة حتى الساعة 6 صباحًا. بدأ الوضع الليلي! \n**بواسطه @hms_1bot**"
            )
            await tbot(
            functions.messages.EditChatDefaultBannedRightsRequest(
                peer=int(pro.chat_id), banned_rights=hehes
            )
            )
        except Exception as e:
            logger.info(f"تعذر إغلاق المجموعة {chat} - {e}")

#Run everyday at 12am
scheduler = AsyncIOScheduler(timezone="Africa/Cairo")
scheduler.add_job(job_close, trigger="cron", hour=23, minute=59)
scheduler.start()

async def job_open():
    chats = get_all_chat_id()
    if len(chats) == 0:
        return
    for pro in chats:
        try:
            await tbot.send_message(
              int(pro.chat_id), "06:00 صباحًا ، سيتم افتتاح المجموعة.\n**بواسطه @hms_1bot**"
            )
            await tbot(
            functions.messages.EditChatDefaultBannedRightsRequest(
                peer=int(pro.chat_id), banned_rights=openhehe
            )
        )
        except Exception as e:
            logger.info(f"تعذر فتح المجموعة {pro.chat_id} - {e}")

# Run everyday at 06
scheduler = AsyncIOScheduler(timezone="Africa/Cairo")
scheduler.add_job(job_open, trigger="cron", hour=5, minute=58)
scheduler.start()
