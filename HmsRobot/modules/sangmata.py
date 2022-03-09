from telethon.errors.rpcerrorlist import YouBlockedUserError
from HmsRobot import telethn as tbot
from HmsRobot.events import register
from HmsRobot import ubot2 as ubot
from asyncio.exceptions import TimeoutError


@register(pattern="^/sg ?(.*)")
async def lastname(steal):
    steal.pattern_match.group(1)
    puki = await steal.reply("```استرجاع معلومات المستخدم هذه..```")
    if steal.fwd_from:
        return
    if not steal.reply_to_msg_id:
        await puki.edit("```الرجاء الرد على رسالة المستخدم.```")
        return
    message = await steal.get_reply_message()
    chat = "@SangMataInfo_bot"
    user_id = message.sender.id
    id = f"/search_id {user_id}"
    if message.sender.bot:
        await puki.edit("```الرد على رسالة المستخدم الحقيقي.```")
        return
    await puki.edit("```أرجو الإنتظار...```")
    try:
        async with ubot.conversation(chat) as conv:
            try:
                msg = await conv.send_message(id)
                r = await conv.get_response()
                response = await conv.get_response()
            except YouBlockedUserError:
                await steal.reply(
                    "```خطأ ، أبلغ في @dd3mhms```"
                )
                return
            if r.text.startswith("Name"):
                respond = await conv.get_response()
                await puki.edit(f"`{r.message}`")
                await ubot.delete_messages(
                    conv.chat_id, [msg.id, r.id, response.id, respond.id]
                ) 
                return
            if response.text.startswith("لا أتذكر") or r.text.startswith(
                "لا أتذكر"
            ):
                await puki.edit("```لا يمكنني العثور على معلومات هذا المستخدم ، هذا المستخدم لم يغير اسمه من قبل.```")
                await ubot.delete_messages(
                    conv.chat_id, [msg.id, r.id, response.id]
                )
                return
            else:
                respond = await conv.get_response()
                await puki.edit(f"```{response.message}```")
            await ubot.delete_messages(
                conv.chat_id, [msg.id, r.id, response.id, respond.id]
            )
    except TimeoutError:
        return await puki.edit("`أنا مريض ، آسف...`")



@register(pattern="^/quotly ?(.*)")
async def quotess(qotli):
    if qotli.fwd_from:
        return
    if not qotli.reply_to_msg_id:
        return await qotli.reply("```الرجاء الرد على الرسالة```")
    reply_message = await qotli.get_reply_message()
    if not reply_message.text:
        return await qotli.reply("```الرجاء الرد على الرسالة```")
    chat = "@QuotLyBot"
    if reply_message.sender.bot:
        return await qotli.reply("```الرجاء الرد على الرسالة```")
    await qotli.reply("```معالجة الملصق ، من فضلك انتظر```")
    try:
        async with ubot.conversation(chat) as conv:
            try:
                response = await conv.get_response()
                msg = await ubot.forward_messages(chat, reply_message)
                response = await response
                """ - لا إشعار البريد العشوائي - """
                await ubot.send_read_acknowledge(conv.chat_id)
            except YouBlockedUserError:
                return await qotli.edit("```من فضلك لا تحجب @QuotLyBot قم بإلغاء الحظر ثم حاول مرة أخرى```")
            if response.text.startswith("Hi!"):
                await qotli.edit("```الرجاء تعطيل إعادة توجيه إعدادات الخصوصية الخاصة بك```")
            else:
                await qotli.delete()
                await tbot.send_message(qotli.chat_id, response.message)
                await tbot.send_read_acknowledge(qotli.chat_id)
                """ - تنظيف الدردشة بعد الانتهاء - """
                await ubot.delete_messages(conv.chat_id,
                                              [msg.id, response.id])
    except TimeoutError:
        await qotli.edit()
