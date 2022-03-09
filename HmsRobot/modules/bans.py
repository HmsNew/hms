import html
import random

from time import sleep
from telegram import (
    ParseMode,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters, CommandHandler, run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_html
from typing import Optional, List
from telegram import TelegramError

import HmsRobot.modules.sql.users_sql as sql
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.filters import CustomFilters
from HmsRobot import (
    DEV_USERS,
    LOGGER,
    OWNER_ID,
    DRAGONS,
    DEMONS,
    TIGERS,
    WOLVES,
    dispatcher,
)
from HmsRobot.modules.helper_funcs.chat_status import (
    user_admin_no_reply,
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    is_user_in_chat,
    user_admin,
    user_can_ban,
    can_delete,
    dev_plus,
)
from HmsRobot.modules.helper_funcs.extraction import extract_user_and_text
from HmsRobot.modules.helper_funcs.string_handling import extract_time
from HmsRobot.modules.log_channel import gloggable, loggable



@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot = context.bot
    args = context.args
    reason = ""
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("قناه {} تم حظره بنجاح من {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
        else:
            message.reply_text("فشل في حظر القناة")
        return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("⚠️ لم يتم العثور على المستخدم.")
        return log_message
    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "لم يتم العثور على المستخدم":
            raise
        message.reply_text("لا يمكن العثور على هذا الشخص.")
        return log_message
    if user_id == bot.id:
        message.reply_text("أوه نعم ، أحظر نفسي ، مستجد!")
        return log_message

    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        if user_id == OWNER_ID:
            message.reply_text("تحاول أن تضعني ضد الملك ، أليس كذلك؟")
        elif user_id in DEV_USERS:
            message.reply_text("لا يمكنني التصرف ضد أميرنا.")
        elif user_id in DRAGONS:
            message.reply_text(
                "محاربة هذا الإمبراطور هنا ستعرض حياة المستخدم للخطر."
            )
        elif user_id in DEMONS:
            message.reply_text(
                "أحضر أمرًا من الكابتن لمحاربة خادم قاتل."
            )
        elif user_id in TIGERS:
            message.reply_text(
                "أحضر أمرًا من الجندي لمحاربة خادم لانسر."
            )
        elif user_id in WOLVES:
            message.reply_text("وصول المتداول جعلهم يحظرون مناعة!")
        else:
            message.reply_text("⚠️ لا يمكن حظر المشرف.")
        return log_message
    if message.text.startswith("/s"):
        silent = True
        if not can_delete(chat, context.bot.id):
            return ""
    else:
        silent = False
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#{'S' if silent else ''}BANNED\n"
        f"<b>مشرف:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += "<b>السبب:</b> {}".format(reason)

    try:
        chat.ban_member(user_id)

        if silent:
            if message.reply_to_message:
                message.reply_to_message.delete()
            message.delete()
            return log

        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        reply = (
            f"{mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] تم يباشا حظرتلك امو خالص ولا تزعل نفسك 😹💔."
        )
        if reason:
            reply += f"\nالسبب: {html.escape(reason)}"

        bot.sendMessage(
            chat.id,
            reply,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🔄  الغاء الحظر ؟ 🖤", callback_data=f"unbanb_unban={user_id}"
                        ),
                        InlineKeyboardButton(text="🗑️ حذف 🖤", callback_data="unbanb_del"),
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            if silent:
                return log
            message.reply_text("محظور!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في حظر المستخدم %s في الدردشه %s (%s) بسبب %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("أوم ... هذا لم ينجح ...")

    return log_message


@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("⚠️ لم يتم العثور على المستخدم.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "لم يتم العثور على المستخدم":
            raise
        message.reply_text("لا يمكنني العثور على هذا المستخدم.")
        return log_message
    if user_id == bot.id:
        message.reply_text("لن احظر نفسي ، هل أنت مجنون؟")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("لا أشعر بالرغبة في ذلك.")
        return log_message

    if not reason:
        message.reply_text("لم تحدد وقتًا لحظر هذا المستخدم من أجله!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>مشرف:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}\n"
        f"<b>وقت:</b> {time_val}"
    )
    if reason:
        log += "\nالسبب: {}".format(reason)

    try:
        chat.ban_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker

        reply_msg = (
            f"{mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] محظور مؤقتا"
            f" for (`{time_val}`)."
        )

        if reason:
            reply_msg += f"\nالسبب: `{html.escape(reason)}`"

        bot.sendMessage(
            chat.id,
            reply_msg,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🔄  الغاء الحظر ؟ 🖤", callback_data=f"unbanb_unban={user_id}"
                        ),
                        InlineKeyboardButton(text="🗑️ حذف 🖤", callback_data="unbanb_del"),
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text(
                f"{mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] محظور ل {time_val}.", quote=False
            )
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في حظر المستخدم %s في الدردشه %s (%s) بسبب %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("اللعنة ، لا يمكنني حظر هذا المستخدم 🙂🖤.")

    return log_message


@connection_status
@bot_admin
@can_restrict
@user_admin_no_reply
@user_can_ban
@loggable
def unbanb_btn(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    if query.data != "unbanb_del":
        splitter = query.data.split("=")
        query_match = splitter[0]
        if query_match == "unbanb_unban":
            user_id = splitter[1]
            if not is_user_admin(chat, int(user.id)):
                bot.answer_callback_query(
                    query.id,
                    text="⚠️ ليس لديك حقوق كافية لإعادة صوت الأشخاص",
                    show_alert=True,
                )
                return ""
            log_message = ""
            try:
                member = chat.get_member(user_id)
            except BadRequest:
                pass
            chat.unban_member(user_id)
            query.message.edit_text(
                f"{member.user.first_name} [{member.user.id}] تم الغاء الحظر يا بهظ يا كبير 😂❤️."
            )
            bot.answer_callback_query(query.id, text="غير محظور!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNBANNED\n"
                f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>مستخدم:</b> {mention_html(member.user.id, member.user.first_name)}"
            )

    else:
        if not is_user_admin(chat, int(user.id)):
            bot.answer_callback_query(
                query.id,
                text="⚠️ ليس لديك حقوق كافية لحذف هذه الرسالة.",
                show_alert=True,
            )
            return ""
        query.message.delete()
        bot.answer_callback_query(query.id, text="حذف!")
        return ""

    
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def punch(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("⚠️ لم يتم العثور على المستخدم")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "لم يتم العثور على المستخدم":
            raise

        message.reply_text("⚠️ لا يمكنني العثور على هذا المستخدم.")
        return log_message
    if user_id == bot.id:
        message.reply_text("نعم ، لن أفعل ذلك.")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("أتمنى حقًا أن أتمكن من لكم هذا المستخدم ....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"{mention_html(member.user.id, html.escape(member.user.first_name))} [<code>{member.user.id}</code>] تم الطرد بنجاح لاجلك انت وبس يا سيد الناس 🥺😹.",
            parse_mode=ParseMode.HTML
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>مشرف:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>مستخدم:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            log += f"\n<b>السبب:</b> {reason}"

        return log

    else:
        message.reply_text("⚠️ اللعنة ، لا يمكنني طرد هذا المستخدم 🖤🙂.")

    return log_message



@bot_admin
@can_restrict
def punchme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("أتمنى لو أستطيع ... لكنك مسؤول.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text(
            "لكمات خارج المجموعة !!",
        )
    else:
        update.effective_message.reply_text("Huh? I can't :")


@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("القناه {} تم رفعه بنجاح من {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
        else:
            message.reply_text("فشل إلغاء حظر القناة")
        return

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("⚠️ لم يتم العثور على المستخدم.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "لم يتم العثور على المستخدم":
            raise
        message.reply_text("لا يمكنني العثور على هذا المستخدم.")
        return log_message
    if user_id == bot.id:
        message.reply_text("كيف يمكنني رفع الحظر عن نفسي إذا لم أكن هنا ...؟")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text(f"⚠️ لم يتم العثور على المستخدم.")
        return log_message

    chat.unban_member(user_id)
    message.reply_text(
        f"{member.user.first_name} [{member.user.id}] تم الغاء الحظر 🖤."
    )

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>مشرف:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>السبب:</b> {reason}"

    return log


@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in DRAGONS or user.id not in TIGERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("أعط معرف دردشة صالحًا.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("ألا أنت بالفعل في الدردشة ؟؟")
        return

    chat.unban_member(user.id)
    message.reply_text(f"نعم ، لقد تم إلغاء حظر المستخدم.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )

    return log


@bot_admin
@can_restrict
@loggable
def banme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    chat = update.effective_chat
    user = update.effective_user
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("⚠️ لا يمكنني حظر المشرف حبيب قلبي 🥺❤️.")
        return

    res = update.effective_chat.ban_member(user_id)
    if res:
        update.effective_message.reply_text("نعم انت على حق! GTFO ..")
        return (
            "<b>{}:</b>"
            "\n#BANME"
            "\n<b>مستخدم:</b> {}"
            "\n<b>ID:</b> <code>{}</code>".format(
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
                user_id,
            )
        )

    else:
        update.effective_message.reply_text("Huh? I can't :")


@dev_plus
def snipe(update: Update, context: CallbackContext):
    args = context.args
    bot = context.bot
    try:
        chat_id = str(args[0])
        del args[0]
    except TypeError:
        update.effective_message.reply_text("من فضلك أعطني محادثة لصدى صدى لها!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("تعذر الإرسال إلى المجموعة %s", str(chat_id))
            update.effective_message.reply_text(
                "تعذر إرسال الرسالة. ربما لست جزءًا من تلك المجموعة؟"
            )


__help__ = """
*User Commands:*

❂ /kickme*:* ركل المستخدم الذي أصدر الأمر

*Admins only:*

❂ /ban <userhandle>*:* يحظر مستخدم. (عبر التعامل أو الرد)
❂ /sban <userhandle>*:* حظر مستخدم بصمت. يحذف الأمر ، تم الرد على الرسالة ولا يرد. (عبر التعامل أو الرد)
❂ /tban <userhandle> x(m/h/d)*:* يحظر مستخدمًا لمدة x مرة. (عن طريق التعامل أو الرد). م = دقائق ، ع = ساعات ، د = أيام.
❂ /unban <userhandle>*:* يقوم بفك حظر مستخدم. (عبر التعامل أو الرد)
❂ /kick <userhandle>*:* يطرد مستخدمًا من المجموعة (عبر التعامل أو الرد)
❂ /mute <userhandle>*:* يسكت المستخدم. يمكن أيضًا استخدامها كرد ، كتم صوت الرد للمستخدم.
❂ /tmute <userhandle> x(m/h/d)*:* كتم صوت المستخدم لوقت x. (عن طريق التعامل أو الرد). م = دقائق ، ع = ساعات ، د = أيام.
❂ /unmute <userhandle>*:* يعيد كتم صوت المستخدم. يمكن أيضًا استخدامها كرد ، كتم صوت الرد للمستخدم.
❂ /zombies*:* عمليات البحث عن الحسابات المحذوفة
❂ /zombies clean*:* يزيل الحسابات المحذوفة من المجموعة.
❂ /snipe <chatid> <string>*:* اجعلني أرسل رسالة إلى دردشة معينة.
"""


__mod_name__ = "Bans+Mutes"

BAN_HANDLER = CommandHandler(["ban", "sban"], ban, run_async=True)
TEMPBAN_HANDLER = CommandHandler(["tban"], temp_ban, run_async=True)
KICK_HANDLER = CommandHandler(["kick", "punch"], punch, run_async=True)
UNBAN_HANDLER = CommandHandler("unban", unban, run_async=True)
ROAR_HANDLER = CommandHandler("roar", selfunban, run_async=True)
UNBAN_BUTTON_HANDLER = CallbackQueryHandler(unbanb_btn, pattern=r"unbanb_")
KICKME_HANDLER = DisableAbleCommandHandler(["kickme", "punchme"], punchme, filters=Filters.chat_type.groups, run_async=True)
SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=CustomFilters.sudo_filter, run_async=True)
BANME_HANDLER = CommandHandler("banme", banme, run_async=True)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(UNBAN_BUTTON_HANDLER)
dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANME_HANDLER)

__handlers__ = [
    BAN_HANDLER,
    TEMPBAN_HANDLER,
    KICK_HANDLER,
    UNBAN_HANDLER,
    ROAR_HANDLER,
    KICKME_HANDLER,
    UNBAN_BUTTON_HANDLER,
    SNIPE_HANDLER,
    BANME_HANDLER,
]
