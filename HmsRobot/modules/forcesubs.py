import logging
import time

from pyrogram import filters
from pyrogram.errors.exceptions.bad_request_400 import (
    ChatAdminRequired,
    PeerIdInvalid,
    UsernameNotOccupied,
    UserNotParticipant,
)
from pyrogram.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup

from HmsRobot import DRAGONS as SUDO_USERS
from HmsRobot import pbot
from HmsRobot.modules.sql import forceSubscribe_sql as sql

logging.basicConfig(level=logging.INFO)

static_data_filter = filters.create(
    lambda _, __, query: query.data == "onUnMuteRequest"
)


@pbot.on_callback_query(static_data_filter)
def _onUnMuteRequest(client, cb):
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id
    chat_db = sql.fs_settings(chat_id)
    if chat_db:
        channel = chat_db.channel
        chat_member = client.get_chat_member(chat_id, user_id)
        if chat_member.restricted_by:
            if chat_member.restricted_by.id == (client.get_me()).id:
                try:
                    client.get_chat_member(channel, user_id)
                    client.unban_chat_member(chat_id, user_id)
                    cb.message.delete()
                    # if cb.message.reply_to_message.from_user.id == user_id:
                    # cb.message.delete()
                except UserNotParticipant:
                    client.answer_callback_query(
                        cb.id,
                        text=f"❗ انضم الينا @{channel} القناة واضغط 'Unmute Me' زر.",
                        show_alert=True,
                    )
            else:
                client.answer_callback_query(
                    cb.id,
                    text="❗ لقد تم كتم صوتك بواسطة المشرفين لسبب آخر.",
                    show_alert=True,
                )
        else:
            if (not client.get_chat_member(chat_id, (client.get_me()).id).status == "administrator"
            ):
                client.send_message(
                    chat_id,
                    f"❗ **{cb.from_user.mention} يحاول إلغاء كتم الصوت بنفسه ولكن لا يمكنني إلغاء كتمه لأنني لست مشرفًا في هذه الدردشة ، أضفني كمسؤول مرة أخرى.**\n__#Leaving this chat...__",
                )

            else:
                client.answer_callback_query(
                    cb.id,
                    text="❗ تحذير! لا تضغط على الزر عندما يمكنك التحدث.",
                    show_alert=True,
                )


@pbot.on_message(filters.text & ~filters.private & ~filters.edited, group=1)
def _check_member(client, message):
    chat_id = message.chat.id
    chat_db = sql.fs_settings(chat_id)
    if chat_db:
        user_id = message.from_user.id
        if (not client.get_chat_member(chat_id, user_id).status in ("administrator", "creator")
            and not user_id in SUDO_USERS
        ):
            channel = chat_db.channel
            try:
                client.get_chat_member(channel, user_id)
            except UserNotParticipant:
                try:
                    sent_message = message.reply_text(
                        "أهلا بك {} 🙏 \n **أنت لم تنضم إلى @{} القناة حتى الان**👷 \n \nيرجى الانضمام [Our Channel](https://t.me/{}) واضغط علي **UNMUTE ME** زر. \n \n ".format(
                            message.from_user.mention, channel, channel
                        ),
                        disable_web_page_preview=True,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "الانضمام إلى القناة",
                                        url="https://t.me/{}".format(channel),
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        "قم بإلغاء الكتم عني", callback_data="onUnMuteRequest"
                                    )
                                ],
                            ]
                        ),
                    )
                    client.restrict_chat_member(
                        chat_id, user_id, ChatPermissions(can_send_messages=False)
                    )
                except ChatAdminRequired:
                    sent_message.edit(
                        "😕 **نيورك ليس المشرف هنا..**\n__أعطني حظر الأذونات وأعد المحاولة.. \n#Ending FSub...__"
                    )

            except ChatAdminRequired:
                client.send_message(
                    chat_id,
                    text=f"😕 **أنا لست مشرفًا على @{channel} قناة.**\n__أعطني المسؤول عن تلك القناة وأعد المحاولة.\n#Ending FSub...__",
                )


@pbot.on_message(filters.command(["forcesubscribe", "fsub"]) & ~filters.private)
def config(client, message):
    user = client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status is "creator" or user.user.id in SUDO_USERS:
        chat_id = message.chat.id
        if len(message.command) > 1:
            input_str = message.command[1]
            input_str = input_str.replace("@", "")
            if input_str.lower() in ("off", "no", "disable"):
                sql.disapprove(chat_id)
                message.reply_text("❌ **تم تعطيل فرض الاشتراك بنجاح.**")
            elif input_str.lower() in ("clear"):
                sent_message = message.reply_text(
                    "**إعادة صوت جميع الأعضاء الذين قمت بكتم صوتهم ...**"
                )
                try:
                    for chat_member in client.get_chat_members(
                        message.chat.id, filter="restricted"
                    ):
                        if chat_member.restricted_by.id == (client.get_me()).id:
                            client.unban_chat_member(chat_id, chat_member.user.id)
                            time.sleep(1)
                    sent_message.edit("✅ **تمت إعادة صوت جميع الأعضاء الذين قمت بكتم صوتهم.**")
                except ChatAdminRequired:
                    sent_message.edit(
                        "😕 **أنا لست مشرفًا في هذه الدردشة.**\n__لا يمكنني إلغاء كتم صوت الأعضاء لأنني لست مسؤولاً في هذه الدردشة ، اجعلني مشرفًا بإذن حظر المستخدم.__"
                    )
            else:
                try:
                    client.get_chat_member(input_str, "me")
                    sql.add_channel(chat_id, input_str)
                    message.reply_text(
                        f"✅ **تم تمكين فرض الاشتراك**\n__تم تمكين فرض الاشتراك ، يجب على جميع أعضاء المجموعة الاشتراك في هذا [channel](https://t.me/{input_str}) من أجل إرسال الرسائل في هذه المجموعة.__",
                        disable_web_page_preview=True,
                    )
                except UserNotParticipant:
                    message.reply_text(
                        f"😕 **ليس مشرفًا في القناة**\n__أنا لست مشرفًا في [channel](https://t.me/{input_str}). أضفني كمسؤول من أجل تمكين ForceSubscribe.__",
                        disable_web_page_preview=True,
                    )
                except (UsernameNotOccupied, PeerIdInvalid):
                    message.reply_text(f"❗ **اسم مستخدم قناة غير صالح.**")
                except Exception as err:
                    message.reply_text(f"❗ **خطأ:** ```{err}```")
        else:
            if sql.fs_settings(chat_id):
                message.reply_text(
                    f"✅ **تم تفعيل فرض الاشتراك في هذه الدردشة.**\n__For this [Channel](https://t.me/{sql.fs_settings(chat_id).channel})__",
                    disable_web_page_preview=True,
                )
            else:
                message.reply_text("❌ **تم تعطيل فرض الاشتراك في هذه الدردشة.**")
    else:
        message.reply_text(
            "❗ **مطلوب منشئ المجموعة**\n__عليك أن تكون منشئ المجموعة للقيام بذلك.__"
        )


__help__ = """
*Force Subscribe:*
❂ يمكن لنيورك كتم صوت الأعضاء غير المشتركين في قناتك حتى يشتركوا فيها
❂ عند التمكين ، سأقوم بكتم صوت الأعضاء غير المشتركين وأظهر لهم زر إلغاء كتم الصوت. عندما ضغطوا على الزر سأعيد صوتهم
❂*Setup*
*Only creator*
❂ أضفني في مجموعتك كمسؤول
❂ أضفني في قناتك كمسؤول
 
*Commmands*
❂ /fsub {channel username} - لتشغيل وإعداد القناة.
  💡افعل هذا أولاً...
❂ /fsub - للحصول على الإعدادات الحالية.
❂ /fsub disable - لغلق الاشتراك..
  💡إذا قمت بتعطيل fsub ، فأنت بحاجة إلى التعيين مرة أخرى للعمل .. /fsub {channel username} 
❂ /fsub clear - لإلغاء كتم صوت جميع الأعضاء الذين كتموا بواسطتي.
*Federation*
كل شيء ممتع ، حتى يبدأ مرسل البريد العشوائي في الدخول إلى مجموعتك ، وعليك حظرها. ثم عليك أن تبدأ في حظر المزيد والمزيد ، وهذا مؤلم.
ولكن بعد ذلك لديك العديد من المجموعات ، ولا تريد أن يكون مرسل البريد العشوائي هذا في إحدى مجموعاتك - كيف يمكنك التعامل؟ هل يجب عليك حظره يدويًا ، في كل مجموعاتك؟\n
*ليس اطول!* مع الاتحاد ، يمكنك جعل الحظر في دردشة واحدة يتداخل مع جميع الدردشات الأخرى.\n
يمكنك حتى تعيين مسؤولي اتحاد ، بحيث يمكن للمسؤول الموثوق به حظر جميع مرسلي البريد العشوائي من الدردشات التي تريد حمايتها.\n
*Commands:*\n
يتم الآن تقسيم الفدراليين إلى 3 أقسام من أجل راحتك.
❂ /fedownerhelp*:* يوفر المساعدة في إنشاء التغذية وأوامر المالك فقط
❂ /fedadminhelp*:* يوفر المساعدة لأوامر إدارة التغذية
❂ /feduserhelp*:* يوفر المساعدة للأوامر التي يمكن لأي شخص استخدامها
"""
__mod_name__ = "F-Sub/Feds"
