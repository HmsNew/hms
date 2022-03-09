import html
import time
from datetime import datetime
from io import BytesIO

from telegram import ParseMode, Update
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import mention_html

import HmsRobot.modules.sql.global_bans_sql as sql
from HmsRobot.modules.sql.users_sql import get_user_com_chats
from HmsRobot import (
    DEV_USERS,
    EVENT_LOGS,
    OWNER_ID,
    STRICT_GBAN,
    DRAGONS,
    SUPPORT_CHAT,
    SPAMWATCH_SUPPORT_CHAT,
    DEMONS,
    TIGERS,
    WOLVES,
    sw,
    dispatcher,
)
from HmsRobot.modules.helper_funcs.chat_status import (
    is_user_admin,
    support_plus,
    user_admin,
)
from HmsRobot.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from HmsRobot.modules.helper_funcs.misc import send_to_list

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "يجب أن تكون داعياً للمستخدم ليقوم بطرده من مجموعة أساسية",
    "Chat_admin_required",
    "يمكن لمنشئ المجموعة الأساسية فقط طرد مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
    "لا يمكن إزالة مالك الدردشة",
}

UNGBAN_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "الطريقة متاحة لمحادثات المجموعات الفائقة والقناة فقط",
    "ليس في الدردشة",
    "Channel_private",
    "Chat_admin_required",
    "Peer_id_invalid",
    "لم يتم العثور على المستخدم",
}


@support_plus
def gban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "هذا المستخدم هو جزء من الرابطة\nلا يمكنني التصرف ضد بلدنا.",
        )
        return

    if int(user_id) in DRAGONS:
        message.reply_text(
            "أنا أتجسس بعيني الصغيرة .. كارثة! لماذا يا رفاق تنقلبون على بعضكم البعض؟",
        )
        return

    if int(user_id) in DEMONS:
        message.reply_text(
            "أوه ، شخص ما يحاول حظر كارثة شيطانية! *يمسك الفشار*",
        )
        return

    if int(user_id) in TIGERS:
        message.reply_text("هذا نمر! لا يمكن حظرهم!")
        return

    if int(user_id) in WOLVES:
        message.reply_text("هذا ذئب! لا يمكن حظرهم!")
        return

    if user_id == bot.id:
        message.reply_text("أنت آه ... تريدني أن ألكم نفسي؟")
        return

    if user_id in [777000, 1087968824]:
        message.reply_text("مجنون! لا يمكنك مهاجمة تقنية Telegram الأصلية!")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم.")
            return ""
        return

    if user_chat.type != "private":
        message.reply_text("هذا ليس مستخدم!")
        return

    if sql.is_user_gbanned(user_id):

        if not reason:
            message.reply_text(
                "هذا المستخدم ممنوع بالفعل ؛ كنت سأغير السبب ، لكنك لم تعطني واحدًا ...",
            )
            return

        old_reason = sql.update_gban_reason(
            user_id,
            user_chat.username or user_chat.first_name,
            reason,
        )
        if old_reason:
            message.reply_text(
                "هذا المستخدم ممنوع بالفعل ، للسبب التالي:\n"
                "<code>{}</code>\n"
                "لقد ذهبت وقمت بتحديثه مع السبب الجديد الخاص بك!".format(
                    html.escape(old_reason),
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "هذا المستخدم ممنوع بالفعل ، لكن لم يتم تحديد أسباب ؛ لقد ذهبت وقمت بتحديثه!",
            )

        return

    message.reply_text("عليه!")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = "<b>{} ({})</b>\n".format(html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>\n".format(chat.id)

    log_message = (
        f"#GBANNED\n"
        f"<b>نشأت من:</b> <code>{chat_origin}</code>\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم محظور:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>معرف المستخدم المحظور:</b> <code>{user_chat.id}</code>\n"
        f"<b>ختم الحدث:</b> <code>{current_time}</code>"
    )

    if reason:
        if chat.type == chat.SUPERGROUP and chat.username:
            log_message += f'\n<b>سبب:</b> <a href="https://telegram.me/{chat.username}/{message.message_id}">{reason}</a>'
        else:
            log_message += f"\n<b>سبب:</b> <code>{reason}</code>"

    if EVENT_LOGS:
        try:
            log = bot.send_message(EVENT_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                EVENT_LOGS,
                log_message
                + "\n\nتم تعطيل التنسيق بسبب خطأ غير متوقع.",
            )

    else:
        send_to_list(bot, DRAGONS + DEMONS, log_message, html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_user_com_chats(user_id)
    gbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.ban_chat_member(chat_id, user_id)
            gbanned_chats += 1

        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text(f"لا يمكن gban بسبب: {excp.message}")
                if EVENT_LOGS:
                    bot.send_message(
                        EVENT_LOGS,
                        f"لا يمكن gban بسبب {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    send_to_list(
                        bot,
                        DRAGONS + DEMONS,
                        f"لا يمكن gban بسبب: {excp.message}",
                    )
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    if EVENT_LOGS:
        log.edit_text(
            log_message + f"\n<b>الدردشات تتأثر:</b> <code>{gbanned_chats}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(
            bot,
            DRAGONS + DEMONS,
            f"اكتمل Gban! (تم حظر المستخدم في <code>{gbanned_chats}</code> chats)",
            html=True,
        )

    end_time = time.time()
    gban_time = round((end_time - start_time), 2)

    if gban_time > 60:
        gban_time = round((gban_time / 60), 2)
        message.reply_text("تم حظر المستخدم عالميا !🖤", parse_mode=ParseMode.HTML)
    else:
        message.reply_text("تم حظر المستخدم عالميا !🖤", parse_mode=ParseMode.HTML)

    try:
        bot.send_message(
            user_id,
            "#EVENT"
            "لقد تم وضع علامة ضار عليك وعلى هذا النحو تم منعك من أي مجموعات نديرها في المستقبل."
            f"\n<b>السبب:</b> <code>{html.escape(user.reason)}</code>"
            f"</b>استئناف الدردشة:</b> @{SUPPORT_CHAT}",
            parse_mode=ParseMode.HTML,
        )
    except:
        pass  # bot probably blocked by user


@support_plus
def ungban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("هذا ليس مستخدم!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("هذا المستخدم غير ممنوع!")
        return

    message.reply_text(f"سوف اعطيك {user_chat.first_name} فرصة ثانية على الصعيد العالمي.")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = f"<b>{html.escape(chat.title)} ({chat.id})</b>\n"
    else:
        chat_origin = f"<b>{chat.id}</b>\n"

    log_message = (
        f"#UNGBANNED\n"
        f"<b>نشأت من:</b> <code>{chat_origin}</code>\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم غير محظور:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>معرّف مستخدم غير محظور:</b> <code>{user_chat.id}</code>\n"
        f"<b>ختم الحدث:</b> <code>{current_time}</code>"
    )

    if EVENT_LOGS:
        try:
            log = bot.send_message(EVENT_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                EVENT_LOGS,
                log_message
                + "\n\nتم تعطيل التنسيق بسبب خطأ غير متوقع.",
            )
    else:
        send_to_list(bot, DRAGONS + DEMONS, log_message, html=True)

    chats = get_user_com_chats(user_id)
    ungbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(chat_id, user_id)
                ungbanned_chats += 1

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(f"تعذر إلغاء gban بسبب: {excp.message}")
                if EVENT_LOGS:
                    bot.send_message(
                        EVENT_LOGS,
                        f"تعذر إلغاء gban بسبب: {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    bot.send_message(
                        OWNER_ID,
                        f"تعذر إلغاء gban بسبب: {excp.message}",
                    )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    if EVENT_LOGS:
        log.edit_text(
            log_message + f"\n<b>الدردشات تتأثر:</b> {ungbanned_chats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(bot, DRAGONS + DEMONS, "un-gban complete!")

    end_time = time.time()
    ungban_time = round((end_time - start_time), 2)

    if ungban_time > 60:
        ungban_time = round((ungban_time / 60), 2)
        message.reply_text(f"تم إلغاء حظر الشخص. استغرق {ungban_time} min")
    else:
        message.reply_text(f"تم إلغاء حظر الشخص. استغرق {ungban_time} sec")


@support_plus
def gbanlist(update: Update, context: CallbackContext):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "لا يوجد أي مستخدمين gbanned! أنت ألطف مما توقعت ...",
        )
        return

    banfile = "تبا هؤلاء الرجال.\n"
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user["reason"]:
            banfile += f"Reason: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="هنا قائمة المستخدمين gbanned حاليا.",
        )


def check_and_ban(update, user_id, should_message=True):

    if user_id in TIGERS or user_id in WOLVES:
        sw_ban = None
    else:
        try:
            sw_ban = sw.get_ban(int(user_id))
        except:
            sw_ban = None

    if sw_ban:
        update.effective_chat.ban_member(user_id)
        if should_message:
            update.effective_message.reply_text(
                f"<b>إنذار</b>: هذا المستخدم محظور عالميًا.\n"
                f"<code>*يحظر عليهم من هنا*</code>.\n"
                f"<b>مناشدة الدردشة</b>: {SPAMWATCH_SUPPORT_CHAT}\n"
                f"<b>هوية المستخدم</b>: <code>{sw_ban.id}</code>\n"
                f"<b>سبب الحظر</b>: <code>{html.escape(sw_ban.reason)}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    if sql.is_user_gbanned(user_id):
        update.effective_chat.ban_member(user_id)
        if should_message:
            text = (
                f"<b>إنذار</b>: هذا المستخدم محظور عالميًا.\n"
                f"<code>*يحظر عليهم من هنا*</code>.\n"
                f"<b>مناشدة الدردشة</b>: @{SUPPORT_CHAT}\n"
                f"<b>هوية المستخدم</b>: <code>{user_id}</code>"
            )
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += f"\n<b>هوية المستخدم:</b> <code>{html.escape(user.reason)}</code>"
            update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def enforce_gban(update: Update, context: CallbackContext):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    bot = context.bot
    try:
        restrict_permission = update.effective_chat.get_member(
            bot.id,
        ).can_restrict_members
    except Unauthorized:
        return
    if sql.does_chat_gban(update.effective_chat.id) and restrict_permission:
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)
            return

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@user_admin
def gbanstat(update: Update, context: CallbackContext):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "تم تمكين مكافحة البريد العشوائي الآن ✅ "
                "أنا الآن أحمي مجموعتك من التهديدات البعيدة المحتملة!",
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "تم تعطيل Antispan الآن ❌ " "تم تعطيل ميزة Spamwatch الآن ❌",
            )
    else:
        update.effective_message.reply_text(
            "أعطني بعض الحجج لاختيار الإعداد! on/off, yes/no!\n\n"
            "الإعداد الحالي الخاص بك هو: {}\n"
            "عندما يكون هذا صحيحًا ، فإن أي gbans يحدث سيحدث أيضًا في مجموعتك. "
            "عندما يكون خطأ ، لن يتركوك تحت رحمة محتملة"
            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)),
        )


def __stats__():
    return f"× {sql.num_gbanned_users()} المستخدمين gbanned."


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)
    text = "Malicious: <b>{}</b>"
    if user_id in [777000, 1087968824]:
        return ""
    if user_id == dispatcher.bot.id:
        return ""
    if int(user_id) in DRAGONS + TIGERS + WOLVES:
        return ""
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>السبب:</b> <code>{html.escape(user.reason)}</code>"
        text += f"\n<b>استئناف الدردشة:</b> @{SUPPORT_CHAT}"
    else:
        text = text.format("???")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"هذه الدردشة تفرض *gbans*: `{sql.does_chat_gban(chat_id)}`."


__help__ = f"""
*المشرفين فقط:*
❂ /antispam <on/off/yes/no>*:* سنقوم بتبديل تقنية مكافحة البريد العشوائي الخاصة بنا أو إعادة إعداداتك الحالية.

Anti-Spam, يستخدمه bot devs لحظر مرسلي البريد العشوائي في جميع المجموعات. هذا يساعد على الحماية \
أنت ومجموعاتك عن طريق إزالة متطفلي البريد العشوائي في أسرع وقت ممكن.
*Note:* يمكن للمستخدمين استئناف gbans أو الإبلاغ عن مرسلي البريد العشوائي على @{SUPPORT_CHAT}

هذا يتكامل أيضا @Spamwatch API لإزالة مرسلي البريد العشوائي قدر الإمكان من غرفة الدردشة الخاصة بك!
*ما هو SpamWatch?*
SpamWatch يحتفظ بقائمة حظر كبيرة محدثة باستمرار من spambots و trolls و bitcoin spamers والشخصيات البغيضة[.](https://telegra.ph/file/f584b643c6f4be0b1de53.jpg)
ساعد باستمرار في حظر مرسلي البريد العشوائي من مجموعتك تلقائيًا لذلك ، لن تقلق بشأن اقتحام مرسلي البريد العشوائي لمجموعتك.
*Note:* يمكن للمستخدمين استئناف حظر الساعات العشوائية على @SpamwatchSupport
"""

GBAN_HANDLER = CommandHandler("gban", gban, run_async=True)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, run_async=True)
GBAN_LIST = CommandHandler("gbanlist", gbanlist, run_async=True)
GBAN_STATUS = CommandHandler(
    "antispam", gbanstat, filters=Filters.chat_type.groups, run_async=True
)
GBAN_ENFORCER = MessageHandler(
    Filters.all & Filters.chat_type.groups, enforce_gban, run_async=True
)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

__mod_name__ = "Anti-Spam"
__handlers__ = [GBAN_HANDLER, UNGBAN_HANDLER, GBAN_LIST, GBAN_STATUS]

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
    __handlers__.append((GBAN_ENFORCER, GBAN_ENFORCE_GROUP))
