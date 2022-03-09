from HmsRobot import dispatcher, LOGGER
from HmsRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    is_bot_admin,
    is_user_ban_protected,
    is_user_in_chat,
)
from HmsRobot.modules.helper_funcs.extraction import extract_user_and_text
from HmsRobot.modules.helper_funcs.filters import CustomFilters
from telegram import Update, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler

RBAN_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "تحتاج إلى أن تكون داعياً لمستخدم لكمة من مجموعة أساسية",
    "Chat_admin_required",
    "فقط منشئ المجموعة الأساسية يمكنه أن يثقب مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
}

RUNBAN_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "تحتاج إلى أن تكون داعياً لمستخدم لكمة من مجموعة أساسية",
    "Chat_admin_required",
    "فقط منشئ المجموعة الأساسية يمكنه أن يثقب مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
}

RKICK_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "تحتاج إلى أن تكون داعياً لمستخدم لكمة من مجموعة أساسية",
    "Chat_admin_required",
    "فقط منشئ المجموعة الأساسية يمكنه أن يثقب مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
}

RMUTE_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "تحتاج إلى أن تكون داعياً لمستخدم لكمة من مجموعة أساسية",
    "Chat_admin_required",
    "فقط منشئ المجموعة الأساسية يمكنه أن يثقب مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
}

RUNMUTE_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "Peer_id_invalid",
    "تم إلغاء تنشيط الدردشة الجماعية",
    "تحتاج إلى أن تكون داعياً لمستخدم لكمة من مجموعة أساسية",
    "Chat_admin_required",
    "فقط منشئ المجموعة الأساسية يمكنه أن يثقب مسؤولي المجموعة",
    "Channel_private",
    "ليس في الدردشة",
}


@bot_admin
def rban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message

    if not args:
        message.reply_text("يبدو أنك لا تشير إلى دردشة / مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return
    if not chat_id:
        message.reply_text("لا يبدو أنك تشير إلى محادثة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على الدردشة":
            message.reply_text(
                "لم يتم العثور على الدردشة! تأكد من إدخال معرف دردشة صالح وأنا جزء من تلك الدردشة.",
            )
            return
        raise

    if chat.type == "private":
        message.reply_text("أنا آسف ، لكن هذه محادثة خاصة!")
        return

    if (
        not is_bot_admin(chat, bot.id)
        or not chat.get_member(bot.id).can_restrict_members
    ):
        message.reply_text(
            "لا أستطيع تقييد الناس هناك! تأكد من أنني مسؤول ويمكنني حظر المستخدمين.",
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return
        raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("أتمنى حقًا أن أحظر المشرفين ...")
        return

    if user_id == bot.id:
        message.reply_text("لن احظر نفسي ، هل أنت مجنون؟")
        return

    try:
        chat.ban_member(user_id)
        message.reply_text("ممنوع من الدردشة!")
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text("Banned!", quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في حظر المستخدم %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("اللعنة ، لا يمكنني حظر هذا المستخدم.")


@bot_admin
def runban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message

    if not args:
        message.reply_text("يبدو أنك لا تشير إلى دردشة / مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return
    if not chat_id:
        message.reply_text("لا يبدو أنك تشير إلى محادثة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على الدردشة":
            message.reply_text(
                "لم يتم العثور على الدردشة! تأكد من إدخال معرف دردشة صالح وأنا جزء من تلك الدردشة.",
            )
            return
        raise

    if chat.type == "private":
        message.reply_text("أنا آسف ، لكن هذه محادثة خاصة!")
        return

    if (
        not is_bot_admin(chat, bot.id)
        or not chat.get_member(bot.id).can_restrict_members
    ):
        message.reply_text(
            "لا أستطيع إلغاء تقييد الناس هناك! تأكد من أنني مشرف ويمكنني إلغاء حظر المستخدمين.",
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم هناك")
            return
        raise

    if is_user_in_chat(chat, user_id):
        message.reply_text(
            "لماذا تحاول إلغاء حظر شخص موجود بالفعل في تلك الدردشة عن بعد؟",
        )
        return

    if user_id == bot.id:
        message.reply_text("لن أحظر الحظر بنفسي ، فأنا مسؤول هناك!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("نعم ، يمكن لهذا المستخدم الانضمام إلى تلك الدردشة!")
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text("غير محظور!", quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في إلغاء حظر المستخدم %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("اللعنة ، لا يمكنني إلغاء حظر هذا المستخدم.")


@bot_admin
def rkick(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message

    if not args:
        message.reply_text("يبدو أنك لا تشير إلى دردشة / مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return
    if not chat_id:
        message.reply_text("لا يبدو أنك تشير إلى محادثة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على الدردشة":
            message.reply_text(
                "لم يتم العثور على الدردشة! تأكد من إدخال معرف دردشة صالح وأنا جزء من تلك الدردشة.",
            )
            return
        raise

    if chat.type == "private":
        message.reply_text("أنا آسف ، لكن هذه محادثة خاصة!")
        return

    if (
        not is_bot_admin(chat, bot.id)
        or not chat.get_member(bot.id).can_restrict_members
    ):
        message.reply_text(
            "لا أستطيع تقييد الناس هناك! تأكد من أنني مسؤول ويمكنني ضرب المستخدمين.",
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return
        raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("أتمنى حقًا أن أتمكن من توجيه الضربات إلى المديرين ...")
        return

    if user_id == bot.id:
        message.reply_text("أنا لن ألكم نفسي ، هل أنت مجنون؟")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("لكمات من الدردشة!")
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text("Punched!", quote=False)
        elif excp.message in RKICK_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في اللكم المستخدم %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("اللعنة ، لا يمكنني ضرب هذا المستخدم.")


@bot_admin
def rmute(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message

    if not args:
        message.reply_text("يبدو أنك لا تشير إلى دردشة / مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return
    if not chat_id:
        message.reply_text("لا يبدو أنك تشير إلى محادثة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على الدردشة":
            message.reply_text(
                "لم يتم العثور على الدردشة! تأكد من إدخال معرف دردشة صالح وأنا جزء من تلك الدردشة.",
            )
            return
        raise

    if chat.type == "private":
        message.reply_text("أنا آسف ، لكن هذه محادثة خاصة!")
        return

    if (
        not is_bot_admin(chat, bot.id)
        or not chat.get_member(bot.id).can_restrict_members
    ):
        message.reply_text(
            "لا أستطيع تقييد الناس هناك! تأكد من أنني مسؤول ويمكنني كتم صوت المستخدمين.",
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return
        raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("أتمنى حقًا أن أتمكن من تجاهل المسؤولين ...")
        return

    if user_id == bot.id:
        message.reply_text("لن اكتم نفسي ، هل أنت مجنون؟")
        return

    try:
        bot.restrict_chat_member(
            chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        message.reply_text("كتم الصوت من الدردشة!")
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text("Muted!", quote=False)
        elif excp.message in RMUTE_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ كتم المستخدم %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("حسنًا ، لا يمكنني كتم صوت هذا المستخدم.")


@bot_admin
def runmute(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message

    if not args:
        message.reply_text("يبدو أنك لا تشير إلى دردشة / مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return
    if not chat_id:
        message.reply_text("لا يبدو أنك تشير إلى محادثة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على الدردشة":
            message.reply_text(
                "لم يتم العثور على الدردشة! تأكد من إدخال معرف دردشة صالح وأنا جزء من تلك الدردشة.",
            )
            return
        raise

    if chat.type == "private":
        message.reply_text("أنا آسف ، لكن هذه محادثة خاصة!")
        return

    if (
        not is_bot_admin(chat, bot.id)
        or not chat.get_member(bot.id).can_restrict_members
    ):
        message.reply_text(
            "لا أستطيع إلغاء تقييد الناس هناك! تأكد من أنني مشرف ويمكنني إلغاء حظر المستخدمين.",
        )
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على المستخدم":
            message.reply_text("لا يمكنني العثور على هذا المستخدم هناك")
            return
        raise

    if is_user_in_chat(chat, user_id):
        if (
            member.can_send_messages
            and member.can_send_media_messages
            and member.can_send_other_messages
            and member.can_add_web_page_previews
        ):
            message.reply_text("هذا المستخدم لديه بالفعل الحق في التحدث في تلك الدردشة.")
            return

    if user_id == bot.id:
        message.reply_text("لن أقوم بإلغاء التجاهل بنفسي ، فأنا مشرف هناك!")
        return

    try:
        bot.restrict_chat_member(
            chat.id,
            int(user_id),
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        message.reply_text("نعم ، يمكن لهذا المستخدم التحدث في تلك الدردشة!")
    except BadRequest as excp:
        if excp.message == "لم يتم العثور على رسالة الرد":
            # Do not reply
            message.reply_text("Unmuted!", quote=False)
        elif excp.message in RUNMUTE_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "خطأ في إلغاء صوت المستخدم %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("حسنًا ، لا يمكنني إلغاء كتم صوت هذا المستخدم.")


RBAN_HANDLER = CommandHandler(
    "rban", rban, filters=CustomFilters.sudo_filter, run_async=True
)
RUNBAN_HANDLER = CommandHandler(
    "runban", runban, filters=CustomFilters.sudo_filter, run_async=True
)
RKICK_HANDLER = CommandHandler(
    "rpunch", rkick, filters=CustomFilters.sudo_filter, run_async=True
)
RMUTE_HANDLER = CommandHandler(
    "rmute", rmute, filters=CustomFilters.sudo_filter, run_async=True
)
RUNMUTE_HANDLER = CommandHandler(
    "runmute", runmute, filters=CustomFilters.sudo_filter, run_async=True
)

dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
dispatcher.add_handler(RKICK_HANDLER)
dispatcher.add_handler(RMUTE_HANDLER)
dispatcher.add_handler(RUNMUTE_HANDLER)
