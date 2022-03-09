import html
import re

from telegram import ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import HmsRobot.modules.sql.blacklist_sql as sql
from HmsRobot import dispatcher, LOGGER
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from HmsRobot.modules.helper_funcs.extraction import extract_text
from HmsRobot.modules.helper_funcs.misc import split_message
from HmsRobot.modules.log_channel import loggable
from HmsRobot.modules.warns import warn
from HmsRobot.modules.helper_funcs.string_handling import extract_time
from HmsRobot.modules.connection import connected
from HmsRobot.modules.sql.approve_sql import is_approved
from HmsRobot.modules.helper_funcs.alternate import send_message, typing_action

BLACKLIST_GROUP = 11


@user_admin
@typing_action
def blacklist(update, context):
    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if chat.type == "private":
            return
        chat_id = update.effective_chat.id
        chat_name = chat.title

    filter_list = "الكلمات المحظوره 🔞 في القائمة السوداء الحالية بتنسيق <b>{}</b>:\n".format(chat_name)

    all_blacklisted = sql.get_chat_blacklist(chat_id)

    if len(args) > 0 and args[0].lower() == "copy":
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    # for trigger in all_blacklisted:
    #     filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if filter_list == "الكلمات المحظوره 🔞 في القائمة السوداء الحالية بتنسيق <b>{}</b>:\n".format(
            html.escape(chat_name),
        ):
            send_message(
                update.effective_message,
                "لا توجد كلمات في القائمة السوداء <b>{}</b>!".format(html.escape(chat_name)),
                parse_mode=ParseMode.HTML,
            )
            return
        send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@user_admin
@typing_action
def add_blacklist(update, context):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(context.bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(
            {trigger.strip() for trigger in text.split("\n") if trigger.strip()},
        )
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat_id, trigger.lower())

        if len(to_blacklist) == 1:
            send_message(
                update.effective_message,
                "القائمة السوداء المضافة <code>{}</code> في الدردشه: <b>{}</b>!".format(
                    html.escape(to_blacklist[0]),
                    html.escape(chat_name),
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            send_message(
                update.effective_message,
                "تمت إضافة مشغل القائمة السوداء: <code>{}</code> في <b>{}</b>!".format(
                    len(to_blacklist),
                    html.escape(chat_name),
                ),
                parse_mode=ParseMode.HTML,
            )

    else:
        send_message(
            update.effective_message,
            "أخبرني ما هي الكلمات التي ترغب في إضافتها إلى القائمة السوداء.",
        )


@user_admin
@typing_action
def unblacklist(update, context):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(context.bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            {trigger.strip() for trigger in text.split("\n") if trigger.strip()},
        )
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                send_message(
                    update.effective_message,
                    "إزالة <code>{}</code> من القائمة السوداء في <b>{}</b>!".format(
                        html.escape(to_unblacklist[0]),
                        html.escape(chat_name),
                    ),
                    parse_mode=ParseMode.HTML,
                )
            else:
                send_message(
                    update.effective_message,
                    "هذا ليس مشغل القائمة السوداء!",
                )

        elif successful == len(to_unblacklist):
            send_message(
                update.effective_message,
                "ازاله <code>{}</code> من القائمة السوداء في <b>{}</b>!".format(
                    successful,
                    html.escape(chat_name),
                ),
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            send_message(
                update.effective_message,
                "لا يوجد أي من هذه المشغلات لذا لا يمكن إزالتها.",
                parse_mode=ParseMode.HTML,
            )

        else:
            send_message(
                update.effective_message,
                "إزالة <code>{}</code> من القائمة السوداء. {} لا يوجد, "
                "لذلك لم يتم إزالتها.".format(
                    successful,
                    len(to_unblacklist) - successful,
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        send_message(
            update.effective_message,
            "أخبرني ما هي الكلمات التي تريد إزالتها من القائمة السوداء!",
        )


@loggable
@user_admin
@typing_action
def blacklist_mode(update, context):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "لا يمكن استخدام هذا الأمر إلا في المجموعة وليس في PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() in ["off", "nothing", "no"]:
            settypeblacklist = "do nothing"
            sql.set_blacklist_strength(chat_id, 0, "0")
        elif args[0].lower() in ["del", "delete"]:
            settypeblacklist = "حذف الرسالة من القائمة السوداء"
            sql.set_blacklist_strength(chat_id, 1, "0")
        elif args[0].lower() == "warn":
            settypeblacklist = "حذر المرسل"
            sql.set_blacklist_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeblacklist = "كتم صوت المرسل"
            sql.set_blacklist_strength(chat_id, 3, "0")
        elif args[0].lower() == "kick":
            settypeblacklist = "ركل المرسل"
            sql.set_blacklist_strength(chat_id, 4, "0")
        elif args[0].lower() == "ban":
            settypeblacklist = "حظر المرسل"
            sql.set_blacklist_strength(chat_id, 5, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """يبدو أنك حاولت تعيين قيمة زمنية للقائمة السوداء لكنك لم تحدد الوقت ؛ يحاول، `/blacklistmode tban <timevalue>`.

    أمثلة على قيمة الوقت: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """قيمة الوقت غير صحيحة!
    مثال على قيمة الوقت: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "حظر مؤقت ل {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 6, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """يبدو أنك حاولت تعيين قيمة زمنية للقائمة السوداء لكنك لم تحدد الوقت ؛ يحاول، `/blacklistmode tmute <timevalue>`.

    أمثلة على قيمة الوقت: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """قيمة الوقت غير صحيحة!
    مثال على قيمة الوقت: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "كتم الصوت مؤقتًا لـ {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 7, str(args[1]))
        else:
            send_message(
                update.effective_message,
                "أنا أفهم فقط: off/del/warn/ban/kick/mute/tban/tmute!",
            )
            return ""
        if conn:
            text = "وضع القائمة السوداء المتغير: `{}` in *{}*!".format(
                settypeblacklist,
                chat_name,
            )
        else:
            text = "وضع القائمة السوداء المتغير: `{}`!".format(settypeblacklist)
        send_message(update.effective_message, text, parse_mode="markdown")
        return (
            "<b>{}:</b>\n"
            "<b>مشرف:</b> {}\n"
            "تم تغيير وضع القائمة السوداء. إرادة {}.".format(
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
                settypeblacklist,
            )
        )
    getmode, getvalue = sql.get_blacklist_setting(chat.id)
    if getmode == 0:
        settypeblacklist = "do nothing"
    elif getmode == 1:
        settypeblacklist = "delete"
    elif getmode == 2:
        settypeblacklist = "warn"
    elif getmode == 3:
        settypeblacklist = "mute"
    elif getmode == 4:
        settypeblacklist = "kick"
    elif getmode == 5:
        settypeblacklist = "ban"
    elif getmode == 6:
        settypeblacklist = "حظر مؤقت ل {}".format(getvalue)
    elif getmode == 7:
        settypeblacklist = "كتم الصوت مؤقتًا لـ {}".format(getvalue)
    if conn:
        text = "وضع القائمة السوداء الحالية: *{}* in *{}*.".format(
            settypeblacklist,
            chat_name,
        )
    else:
        text = "وضع القائمة السوداء الحالية: *{}*.".format(settypeblacklist)
    send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def findall(p, s):
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)


@user_not_admin
def del_blacklist(update, context):
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    bot = context.bot
    to_match = extract_text(message)
    if not to_match:
        return
    if is_approved(chat.id, user.id):
        return
    getmode, value = sql.get_blacklist_setting(chat.id)

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                if getmode == 0:
                    return
                if getmode == 1:
                    try:
                        message.delete()
                    except BadRequest:
                        pass
                elif getmode == 2:
                    try:
                        message.delete()
                    except BadRequest:
                        pass
                    warn(
                        update.effective_user,
                        chat,
                        ("استخدام الزناد المدرج في القائمة السوداء: {}".format(trigger)),
                        message,
                        update.effective_user,
                    )
                    return
                elif getmode == 3:
                    message.delete()
                    bot.restrict_chat_member(
                        chat.id,
                        update.effective_user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    bot.sendMessage(
                        chat.id,
                        f"كتم الصوت {user.first_name} لاستخدام الكلمة المدرجة في القائمة السوداء: {trigger}!",
                    )
                    return
                elif getmode == 4:
                    message.delete()
                    res = chat.unban_member(update.effective_user.id)
                    if res:
                        bot.sendMessage(
                            chat.id,
                            f"مطرود {user.first_name} لاستخدام الكلمة المدرجة في القائمة السوداء: {trigger}!",
                        )
                    return
                elif getmode == 5:
                    message.delete()
                    chat.kick_member(user.id)
                    bot.sendMessage(
                        chat.id,
                        f"محظور {user.first_name} لاستخدام الكلمة المدرجة في القائمة السوداء: {trigger}",
                    )
                    return
                elif getmode == 6:
                    message.delete()
                    bantime = extract_time(message, value)
                    chat.kick_member(user.id, until_date=bantime)
                    bot.sendMessage(
                        chat.id,
                        f"محظور {user.first_name} until '{value}' لاستخدام الكلمة المدرجة في القائمة السوداء: {trigger}!",
                    )
                    return
                elif getmode == 7:
                    message.delete()
                    mutetime = extract_time(message, value)
                    bot.restrict_chat_member(
                        chat.id,
                        user.id,
                        until_date=mutetime,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    bot.sendMessage(
                        chat.id,
                        f"تم كتمك  {user.first_name} until '{value}' لاستخدامك كلمات محظوره 🔞 في القائمة السوداء: {trigger}!",
                    )
                    return
            except BadRequest as excp:
                if excp.message != "لم يتم العثور على رسالة للحذف":
                    LOGGER.exception("خطأ أثناء حذف رسالة القائمة السوداء.")
            break


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get("blacklist", {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "هناك {} الكلمات المحظوره 🔞 في القائمة السوداء.".format(blacklisted)


def __stats__():
    return "× {} مشغلات القائمة السوداء ، عبر {} دردشات.".format(
        sql.num_blacklist_filters(),
        sql.num_blacklist_filter_chats(),
    )


__mod_name__ = "Blacklist"

__help__ = """

تُستخدم القوائم السوداء لمنع قول محفزات معينة في المجموعة. في أي وقت يذكر المشغل ، سيتم حذف الرسالة على الفور. السرد الجيد في بعض الأحيان هو إقران هذا مع مرشحات التحذير!

*NOTE*: لا تؤثر القوائم السوداء على مسؤولي المجموعة.

❂ /blacklist*:* عرض الكلمات المحظوره 🔞 في القائمة السوداء الحالية.

Admin only:
❂ /addblacklist <triggers>*:* إضافة مشغل إلى القائمة السوداء. يعتبر كل سطر مشغلًا واحدًا ، لذا فإن استخدام سطور مختلفة سيسمح لك بإضافة عدة مشغلات.
❂ /unblacklist <triggers>*:* إزالة المشغلات من القائمة السوداء. ينطبق منطق السطر الجديد نفسه هنا ، لذا يمكنك إزالة عدة مشغلات مرة واحدة.
❂ /blacklistmode <off/del/warn/ban/kick/mute/tban/tmute>*:* إجراء يتم تنفيذه عندما يرسل شخص ما كلمات مدرجة في القائمة السوداء.

يستخدم ملصق القائمة السوداء لإيقاف بعض الملصقات. عندما يتم إرسال ملصق ، سيتم حذف الرسالة على الفور.
*NOTE:* لا تؤثر ملصقات القائمة السوداء على مسؤول المجموعة
❂ /blsticker*:* انظر الملصق الحالي في القائمة السوداء
*Only admin:*
❂ /addblsticker <sticker link>*:* أضف مشغل الملصق إلى القائمة السوداء. يمكن إضافتها عبر ملصق الرد
❂ /unblsticker <sticker link>*:* إزالة المشغلات من القائمة السوداء. ينطبق نفس منطق السطر الجديد هنا ، بحيث يمكنك حذف عدة مشغلات في وقت واحد
❂ /rmblsticker <sticker link>*:* كما ورد أعلاه
❂ /blstickermode <delete/ban/tban/mute/tmute>*:* يُنشئ إجراءً افتراضيًا بشأن ما يجب فعله إذا استخدم المستخدمون الملصقات المدرجة في القائمة السوداء
Note:
❂ <sticker link> يمكن ان يكون `https://t.me/addstickers/<sticker>` أو فقط `<sticker>` أو الرد على رسالة الملصق

"""
BLACKLIST_HANDLER = DisableAbleCommandHandler(
    "blacklist",
    blacklist,
    pass_args=True,
    admin_ok=True,
    run_async=True,
)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, run_async=True)
UNBLACKLIST_HANDLER = CommandHandler("unblacklist", unblacklist, run_async=True)
BLACKLISTMODE_HANDLER = CommandHandler(
    "blacklistmode", blacklist_mode, pass_args=True, run_async=True
)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo)
    & Filters.chat_type.groups,
    del_blacklist,
    allow_edit=True,
    run_async=True,
)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLISTMODE_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

__handlers__ = [
    BLACKLIST_HANDLER,
    ADD_BLACKLIST_HANDLER,
    UNBLACKLIST_HANDLER,
    BLACKLISTMODE_HANDLER,
    (BLACKLIST_DEL_HANDLER, BLACKLIST_GROUP),
]
