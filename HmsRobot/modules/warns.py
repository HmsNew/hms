import html
import re
from typing import Optional

import telegram
from HmsRobot import TIGERS, WOLVES, dispatcher
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    is_user_admin,
    user_admin,
    user_can_ban,
    user_admin_no_reply,
    can_delete,
)
from HmsRobot.modules.helper_funcs.extraction import (
    extract_text,
    extract_user,
    extract_user_and_text,
)
from HmsRobot.modules.helper_funcs.filters import CustomFilters
from HmsRobot.modules.helper_funcs.misc import split_message
from HmsRobot.modules.helper_funcs.string_handling import split_quotes
from HmsRobot.modules.log_channel import loggable
from HmsRobot.modules.sql import warns_sql as sql
from telegram import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    User,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    DispatcherHandlerStop,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html
from HmsRobot.modules.sql.approve_sql import is_approved

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>مرشحات التحذير الحالية في هذه الدردشة:</b>\n"


# Not async
def warn(user: User,
         chat: Chat,
         reason: str,
         message: Message,
         warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        # message.reply_text("Damn admins, They are too far to be One Punched!")
        return

    if user.id in TIGERS:
        if warner:
            message.reply_text("لا يمكن تحذيرهم لانهم مميزين 🙂.")
        else:
            message.reply_text(
                "أطلق المميز مرشح تحذير تلقائي!\n لا يمكنني تحذير المميزين لكن يجب عليهم تجنب إساءة استخدام هذا."
            )
        return

    if user.id in WOLVES:
        if warner:
            message.reply_text("كوارث الذئاب محصنة.")
        else:
            message.reply_text(
                "تسبب Wolf Disaster في تشغيل مرشح تحذير تلقائي!\nلا يمكنني تحذير الذئاب ولكن يجب عليهم تجنب إساءة استخدام هذا."
            )
        return

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "مرشح التحذير الآلي."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # punch
            chat.unban_member(user.id)
            reply = (
                f"{mention_html(user.id, user.first_name)} [<code>{user.id}</code>] لقد تم طرده")

        else:  # ban
            chat.kick_member(user.id)
            reply = (
                f"{mention_html(user.id, user.first_name)} [<code>{user.id}</code>] لقد تم حظره")

        for warn_reason in reasons:
            reply += f"\n - {html.escape(warn_reason)}"

        # message.bot.send_sticker(chat.id, BAN_STICKER)  #Neyork sticker
        keyboard = None
        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN_BAN\n"
                      f"<b>مشرف:</b> {warner_tag}\n"
                      f"<b>مستخدم:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>السبب:</b> {reason}\n"
                      f"<b>العد:</b> <code>{num_warns}/{limit}</code>")

    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "❌ إزالة ؟! 🖤", callback_data="rm_warn({})".format(user.id))
        ]])

        reply = (
            f"{mention_html(user.id, user.first_name)} [<code>{user.id}</code>]"
            f" تم تحذير المستخدم بنجاح !🖤 ({num_warns} of {limit}).")
        if reason:
            reply += f"\nالسبب: {html.escape(reason)}"

        log_reason = (f"<b>{html.escape(chat.title)}:</b>\n"
                      f"#WARN\n"
                      f"<b>مشرف:</b> {warner_tag}\n"
                      f"<b>مستخدم:</b> {mention_html(user.id, user.first_name)}\n"
                      f"<b>السبب:</b> {reason}\n"
                      f"<b>العد:</b> <code>{num_warns}/{limit}</code>")

    try:
        message.reply_text(
            reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text(
                reply,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                quote=False)
        else:
            raise
    return log_reason



@user_admin_no_reply
# @user_can_ban
@bot_admin
@loggable
def button(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        res = sql.remove_warn(user_id, chat.id)
        if res:
            user_member = chat.get_member(user_id)
            update.effective_message.edit_text(
                f"{mention_html(user_member.user.id, user_member.user.first_name)} [<code>{user_member.user.id}</code>] تحذير إزالتها.",
                parse_mode=ParseMode.HTML,
            )
            user_member = chat.get_member(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNWARN\n"
                f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
            )
        else:
            update.effective_message.edit_text(
                "المستخدم ليس لديه أي تحذيرات.", parse_mode=ParseMode.HTML
            )

    return ""


@user_admin
@can_restrict
# @user_can_ban
@loggable
def warn_user(update: Update, context: CallbackContext) -> str:
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    warner: Optional[User] = update.effective_user

    user_id, reason = extract_user_and_text(message, args)
    if message.text.startswith("/d") and message.reply_to_message:
        message.reply_to_message.delete()
    if user_id:
        if (
            message.reply_to_message
            and message.reply_to_message.from_user.id == user_id
        ):
            return warn(
                message.reply_to_message.from_user,
                chat,
                reason,
                message.reply_to_message,
                warner,
            )
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("باين أن المعرف المستخدم غير صالح بالنسبة لي حاول بالايدي او باليوزر تاني 🙂.")
    return ""


@user_admin
# @user_can_ban
@bot_admin
@loggable
def reset_warns(update: Update, context: CallbackContext) -> str:
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("تمت إعادة تعيين التحذيرات!")
        warned = chat.get_member(user_id).user
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESETWARNS\n"
            f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>مستخدم:</b> {mention_html(warned.id, warned.first_name)}"
        )
    else:
        message.reply_text("⚠️ حدد طيب عاوز تحذر مين اعمل ريب علي حد او هات يوزر او ايدي اي حاجه متتعبنيش 🙂😂!")
    return ""


def warns(update: Update, context: CallbackContext):
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = (
                f"هذا المستخدم لديه {num_warns}/{limit} يحذر ، للأسباب التالية:"
            )
            for reason in reasons:
                text += f"\n {reason}"

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                f"المستخدم لديه {num_warns}/{limit} يحذر ، ولكن لا توجد أسباب للتحزير ."
            )
    else:
        update.effective_message.reply_text("هذا المستخدم ليس لديه أي تحذيرات بمعني نضيف اباشا معندوش اي سوابق ولا معاه مخدرات حتي 😂💔!")


# Dispatcher handler stop - do not async
@user_admin
# @user_can_ban
def add_warn_filter(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text(f"تمت إضافة معالج التحذير لـ '{keyword}'!")
    raise DispatcherHandlerStop


@user_admin
# @user_can_ban
def remove_warn_filter(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    msg: Optional[Message] = update.effective_message

    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("لا توجد عوامل تصفية تحذير نشطة هنا!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("حسنًا ، سأتوقف عن تحذير الناس من ذلك.")
            raise DispatcherHandlerStop

    msg.reply_text(
        "هذا ليس عامل تصفية تحذير حالي - تشغيل /warnlist لجميع عوامل تصفية التحذير النشطة."
    )


def list_warn_filters(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("لا توجد عوامل تصفية تحذير نشطة هنا!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = f" - {html.escape(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if filter_list != CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@loggable
def reply_filter(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    user: Optional[User] = update.effective_user

    if not user:  # Ignore channel
        return

    if user.id == 777000:
        return
    if is_approved(chat.id, user.id):
        return
    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user: Optional[User] = update.effective_user
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@user_admin
# @user_can_ban
@loggable
def set_warn_limit(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("الحد الأدنى للتحذير هو 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("تم تحديث حد التحذير إلى {}".format(args[0]))
                return (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#SET_WARN_LIMIT\n"
                    f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
                    f"تعيين حد التحذير على <code>{args[0]}</code>"
                )
        else:
            msg.reply_text("أعطني رقمًا !")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("حد التحذير الحالي هو {}".format(limit))
    return ""


@user_admin
# @user_can_ban
def set_warn_strength(update: Update, context: CallbackContext):
    args = context.args
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    msg: Optional[Message] = update.effective_message

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("تم الضبط علي ان عدد من التحذيرات سيؤدي إلى الحظر !🖤")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
                f"وقد مكنت من تحذيرات قوية. سيتم ضرب المستخدمين بجدية.!🖤(تم الحظر)"
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text(
                "الكثير من التحذيرات ستؤدي الآن إلى طرد! سيتمكن المستخدمون من الانضمام مرة أخرى بعد ذلك. !🖤"
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
                f"أوقف اللكمات القوية. سأستخدم لكمة عادية على المستخدمين."
            )

        else:
            msg.reply_text("فاهم on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text(
                "تم تعيين التحذيرات حاليًا على *punch* المستخدمين عندما يتجاوزون الحدود.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            msg.reply_text(
                "تم تعيين التحذيرات حاليًا على *Ban* المستخدمين عندما يتجاوزون الحدود.",
                parse_mode=ParseMode.MARKDOWN,
            )
    return ""


def __stats__():
    return (
        f"× {sql.num_warns()} يحذر بشكل عام ، عبر {sql.num_warn_chats()} chats.\n"
        f"× {sql.num_warn_filters()} مرشحات تحذير عبر {sql.num_warn_filter_chats()} chats."
    )


def __import_data__(chat_id, data):
    for user_id, count in data.get("warns", {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return (
        f"هذه الدردشة لها `{num_warn_filters}` مرشحات تحذير. "
        f"تستغرق `{limit}` يحذر قبل أن يحصل المستخدم *{'kicked' if soft_warn else 'banned'}*."
    )

__help__ = """

❂ /warns <المستخدم>: الحصول على رقم المستخدم وسبب تحذيراته.
❂ /warnlist: قائمة بجميع عوامل تصفية التحذير الحالية
❂ /warn <المستخدم>: تحذير المستخدم. بعد 3 تحذيرات ، سيتم حظر المستخدم من المجموعة. يمكن أيضا أن تستخدم كرد.
❂ /dwarn <المستخدم>: تحذير المستخدم وحذف الرسالة. بعد 3 تحذيرات ، سيتم حظر المستخدم من المجموعة. يمكن أيضا أن تستخدم كرد.
❂ /resetwarn <المستخدم>: إعادة تعيين التحذيرات للمستخدم. يمكن أيضا أن تستخدم كرد.
❂ /addwarn <keyword> <رسالة الرد>: تعيين عامل تصفية تحذير على كلمة رئيسية معينة. إذا كنت تريد أن تكون كلمتك الرئيسية جملة ، فقم بتضمينها بعلامات اقتباس ، مثل: /addwarn  very angry هذا مستخدم غاضب.
❂ /nowarn <keyword>: وقف مرشح تحذير
❂ /warnlimit <num>: تعيين حد التحذير
❂ /strongwarn <on/yes/off/no>: في حالة الضبط على تشغيل ، سيؤدي تجاوز حد التحذير إلى حظر. عدا ذلك ، سوف يضرب فقط.
"""

__mod_name__ = "WarnS"

WARN_HANDLER = CommandHandler(["warn", "dwarn"], warn_user, filters=Filters.chat_type.groups, run_async=True)
RESET_WARN_HANDLER = CommandHandler(
    ["resetwarn", "resetwarns"], reset_warns, filters=Filters.chat_type.groups, run_async=True
)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn", run_async=True)
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, filters=Filters.chat_type.groups, run_async=True)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.chat_type.groups, run_async=True)
RM_WARN_HANDLER = CommandHandler(
    ["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.chat_type.groups, run_async=True
)
LIST_WARN_HANDLER = DisableAbleCommandHandler(
    ["warnlist", "warnfilters"], list_warn_filters, filters=Filters.chat_type.groups, admin_ok=True, run_async=True
)
WARN_FILTER_HANDLER = MessageHandler(
    CustomFilters.has_text & Filters.chat_type.groups, reply_filter, run_async=True
)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, filters=Filters.chat_type.groups, run_async=True)
WARN_STRENGTH_HANDLER = CommandHandler(
    "strongwarn", set_warn_strength, filters=Filters.chat_type.groups, run_async=True
)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
