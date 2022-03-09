from datetime import datetime
from functools import wraps
from telegram.ext import CallbackContext
from HmsRobot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import ParseMode, Update
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, JobQueue, run_async
    from telegram.utils.helpers import escape_markdown

    from HmsRobot import EVENT_LOGS, LOGGER, dispatcher
    from HmsRobot.modules.helper_funcs.chat_status import user_admin
    from HmsRobot.modules.sql import log_channel_sql as sql

    def loggable(func):
        @wraps(func)
        def log_action(
            update: Update,
            context: CallbackContext,
            job_queue: JobQueue = None,
            *args,
            **kwargs,
        ):
            if not job_queue:
                result = func(update, context, *args, **kwargs)
            else:
                result = func(update, context, job_queue, *args, **kwargs)

            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += f"\n<b>Event Stamp</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(context, log_chat, chat.id, result)

            return result

        return log_action

    def gloggable(func):
        @wraps(func)
        def glog_action(update: Update, context: CallbackContext, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += "\n<b>Event Stamp</b>: <code>{}</code>".format(
                    datetime.utcnow().strftime(datetime_fmt)
                )

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = str(EVENT_LOGS)
                if log_chat:
                    send_log(context, log_chat, chat.id, result)

            return result

        return glog_action

    def send_log(
        context: CallbackContext, log_chat_id: str, orig_chat_id: str, result: str
    ):
        bot = context.bot
        try:
            bot.send_message(
                log_chat_id,
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as excp:
            if excp.message == "لم يتم العثور على الدردشة":
                bot.send_message(
                    orig_chat_id, "تم حذف قناة السجل هذه - عدم ضبطها."
                )
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("تعذر التحليل")

                bot.send_message(
                    log_chat_id,
                    result
                    + "\n\nتم تعطيل التنسيق بسبب خطأ غير متوقع.",
                )

    @user_admin
    def logging(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                f"تحتوي هذه المجموعة على كل السجلات التي تم إرسالها إليها:"
                f" {escape_markdown(log_channel_info.title)} (`{log_channel}`)",
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            message.reply_text("لم يتم تعيين قناة تسجيل لهذه المجموعة!")

    @user_admin
    def setlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            message.reply_text(
                "الآن ، قم بإعادة توجيه ملف /setlog للمجموعة التي تريد ربط هذه القناة بها!"
            )

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "لم يتم العثور على رسالة للحذف":
                    pass
                else:
                    LOGGER.exception(
                        "خطأ في حذف الرسالة في قناة السجل. يجب أن تعمل على أي حال."
                    )

            try:
                bot.send_message(
                    message.forward_from_chat.id,
                    f"تم تعيين هذه القناة كقناة تسجيل لـ {chat.title or chat.first_name}.",
                )
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot ليس عضوا في قناة الدردشة":
                    bot.send_message(chat.id, "تم تعيين قناة السجل بنجاح!")
                else:
                    LOGGER.exception("خطأ في تحديد قناة السجل.")

            bot.send_message(chat.id, "تم تعيين قناة السجل بنجاح!")

        else:
            message.reply_text(
                "الخطوات لتعيين قناة السجل هي:\n"
                " - إضافة بوت إلى القناة المطلوبة\n"
                " - إرسال /setlog للقناة\n"
                " - إعادة توجيه /setlog الي المجموعه\n"
            )

    @user_admin
    def unsetlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(
                log_channel, f"تم إلغاء ربط القناة من {chat.title}"
            )
            message.reply_text("تم إلغاء تعيين قناة السجل.")

        else:
            message.reply_text("لم يتم تعيين قناة سجل حتى الآن!")

    def __stats__():
        return f"× {sql.num_logchannels()} تعيين قنوات السجل."

    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return f"تحتوي هذه المجموعة على كل السجلات التي تم إرسالها إليها: {escape_markdown(log_channel_info.title)} (`{log_channel}`)"
        return "لم يتم تعيين قناة تسجيل لهذه المجموعة!"


    __help__ = """
──「 Log channel 」──

❂ /logchannel*:* الحصول على معلومات قناة السجل
❂ /setlog*:* ضبط قناة السجل.
❂ /unsetlog*:* قم بفك قناة السجل.

*يتم ضبط قناة السجل بواسطة*:

➩ إضافة الروبوت إلى القناة المطلوبة (كمسؤول!)
➩ إرسال /setlog في القناة
➩ إحالة ال /setlog للمجموعة
"""

    __mod_name__ = "Logger Ch​"

    LOG_HANDLER = CommandHandler("logchannel", logging, run_async=True)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog, run_async=True)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog, run_async=True)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func

    def gloggable(func):
        return func
