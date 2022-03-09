import html

from HmsRobot import LOGGER, DRAGONS, TIGERS, WOLVES, dispatcher
from HmsRobot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from HmsRobot.modules.log_channel import loggable
from HmsRobot.modules.sql import reporting_sql as sql
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import mention_html

REPORT_GROUP = 12
REPORT_IMMUNE_USERS = DRAGONS + TIGERS + WOLVES


@user_admin
def report_setting(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "تم تشغيل الإبلاغ! سيتم إعلامك كلما أبلغ أي شخص عن شيء ما.",
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("تم إيقاف الإبلاغ! لن تحصل على أي تقارير.")
        else:
            msg.reply_text(
                f"التقرير الحالي المفضل لديك هو: `{sql.user_should_report(chat.id)}`",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text(
                    f"تم تشغيل إعداد التقارير {chat.title}!\n\nسيتم إخطار المسؤولين الذين قاموا بتشغيل التقارير عندما `/report` "
                    "or @admin يسمى.",
                )

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text(
                    f"Turned off reporting in {chat.title}!\n\nلن يتم إخطار أي مدراء في `/report` or @admin.",
                )
        else:
            msg.reply_text(
                f"إعداد التقرير الحالي هو: `{sql.chat_should_report(chat.id)}`.\n\nلتغيير هذا الإعداد ، جرب هذا الأمر مرة أخرى ، بإحدى الوسائل التالية: yes/no/on/off",
                parse_mode=ParseMode.MARKDOWN,
            )


@user_not_admin
@loggable
def report(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()
        message = update.effective_message

        if not args:
            message.reply_text("أضف سببًا للإبلاغ أولاً.")
            return ""

        if user.id == reported_user.id:
            message.reply_text("آه أجل ، أكيد أكيد ... ماسو كثيرًا؟")
            return ""

        if user.id == bot.id:
            message.reply_text("محاولة جيدة.")
            return ""

        if reported_user.id in REPORT_IMMUNE_USERS:
            message.reply_text("أوه؟ هل تقوم بالإبلاغ عن جمعية مملكة؟")
            return ""

        if chat.username and chat.type == Chat.SUPERGROUP:

            reported = f"{mention_html(user.id, user.first_name)} reported {mention_html(reported_user.id, reported_user.first_name)} للمسؤولين!"

            msg = (
                f"<b>⚠️ ابلاغ: </b>{html.escape(chat.title)}\n"
                f"<b> • ابلاغ بواسطه:</b> {mention_html(user.id, user.first_name)}(<code>{user.id}</code>)\n"
                f"<b> • ابلاغ عن المستخدم:</b> {mention_html(reported_user.id, reported_user.first_name)} (<code>{reported_user.id}</code>)\n"
            )
            link = f'<b> • الرسالة المبلغ عنها:</b> <a href="https://t.me/{chat.username}/{message.reply_to_message.message_id}">click here</a>'
            should_forward = False
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➡ رسالة",
                        url=f"https://t.me/{chat.username}/{message.reply_to_message.message_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⚠ طرد",
                        callback_data=f"report_{chat.id}=kick={reported_user.id}={reported_user.first_name}",
                    ),
                    InlineKeyboardButton(
                        "⛔️ حظر",
                        callback_data=f"report_{chat.id}=banned={reported_user.id}={reported_user.first_name}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❎ حذف رسالة",
                        callback_data=f"report_{chat.id}=delete={reported_user.id}={message.reply_to_message.message_id}",
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reported = (
                f"{mention_html(user.id, user.first_name)} ذكرت "
                f"{mention_html(reported_user.id, reported_user.first_name)} للمسؤولين!"
            )

            msg = f'{mention_html(user.id, user.first_name)} يستدعي المشرفين في "{html.escape(chat_name)}"!'
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    if not chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)
                    if not chat.username:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if chat.username and chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    LOGGER.exception("استثناء أثناء الإبلاغ عن المستخدم")

        message.reply_to_message.reply_text(
            f"{mention_html(user.id, user.first_name)} أبلغت الرسالة إلى المسؤولين.",
            parse_mode=ParseMode.HTML,
        )
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, _):
    return f"تم إعداد هذه الدردشة لإرسال تقارير المستخدم إلى المسؤولين عبر /report and @admin: `{sql.chat_should_report(chat_id)}`"


def __user_settings__(user_id):
    if sql.user_should_report(user_id) is True:
        text = "ستتلقى تقارير من الدردشات التي تديرها."
    else:
        text = "سوف *لن* تتلقى تقارير من الدردشات التي تديرها."
    return text


def buttons(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            bot.unbanChatMember(splitter[0], splitter[2])
            query.aswer("✅ تم الطرد بنجاح")
            return ""
        except Exception as err:
            query.answer("🛑 فشل الطرد")
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
    elif splitter[1] == "banned":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            query.answer("✅  تم الحظر بنجاح")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("🛑 فشل الحظر")
    elif splitter[1] == "delete":
        try:
            bot.deleteMessage(splitter[0], splitter[3])
            query.answer("✅ الرسالة مسحت")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("🛑 فشل حذف الرسالة!")


__help__ = """
❂ /report <السبب>*:* الرد على رسالة لإبلاغ المسؤولين عنها.
❂ @admin*:* الرد على رسالة لإبلاغ المسؤولين عنها.
*NOTE:* لن يتم تشغيل أيٍّ من هذين الخيارين إذا تم استخدامه من قبل المشرفين.

*المشرفون فقط:*
❂ /reports <on/off>*:* تغيير إعداد التقرير ، أو عرض الحالة الحالية.
❂ إذا تم ذلك في الخاص ، فتبديل حالتك.
➢ إذا كنت في مجموعة ، فقم بتبديل حالة تلك المجموعات.
"""

SETTING_HANDLER = CommandHandler("reports", report_setting, run_async=True)
REPORT_HANDLER = CommandHandler(
    "report", report, filters=Filters.chat_type.groups, run_async=True
)
ADMIN_REPORT_HANDLER = MessageHandler(
    Filters.regex(r"(?i)@admin(s)?"), report, run_async=True
)
REPORT_BUTTON_USER_HANDLER = CallbackQueryHandler(
    buttons, pattern=r"report_", run_async=True
)

dispatcher.add_handler(REPORT_BUTTON_USER_HANDLER)
dispatcher.add_handler(SETTING_HANDLER)
dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)

__mod_name__ = "Report"
__handlers__ = [
    (REPORT_HANDLER, REPORT_GROUP),
    (ADMIN_REPORT_HANDLER, REPORT_GROUP),
    (SETTING_HANDLER),
]
