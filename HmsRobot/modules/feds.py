import ast
import csv
import json
import os
import re
import time
import uuid
from io import BytesIO

import HmsRobot.modules.sql.feds_sql as sql
from HmsRobot import (
    EVENT_LOGS,
    LOGGER,
    SUPPORT_CHAT,
    OWNER_ID,
    DRAGONS,
    TIGERS,
    WOLVES,
    dispatcher,
)
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.alternate import send_message
from HmsRobot.modules.helper_funcs.chat_status import is_user_admin
from HmsRobot.modules.helper_funcs.extraction import (
    extract_unt_fedban,
    extract_user,
    extract_user_fban,
)
from HmsRobot.modules.helper_funcs.string_handling import markdown_parser
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    Update,
)
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    run_async,
)
from telegram.utils.helpers import mention_html, mention_markdown

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
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
    "ليس لديك حقوق لإرسال رسالة",
}

UNFBAN_ERRORS = {
    "المستخدم هو المسؤول عن الدردشة",
    "لم يتم العثور على الدردشة",
    "لا توجد حقوق كافية لتقييد / إلغاء تقييد عضو الدردشة",
    "User_not_participant",
    "الطريقة متاحة لمحادثات المجموعات الفائقة والقناة فقط",
    "ليس في الدردشة",
    "Channel_private",
    "Chat_admin_required",
    "ليس لديك حقوق لإرسال رسالة",
}


def new_fed(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text(
            "لا يمكن إنشاء الاتحادات إلا من خلال مراسلتي بشكل خاص.",
        )
        return
    if len(message.text) == 1:
        send_message(
            update.effective_message,
            "الرجاء كتابة اسم الاتحاد!",
        )
        return
    fednam = message.text.split(None, 1)[1]
    if not fednam == "":
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        # Currently only for creator
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text(
                f"لا يمكن أن تتحد! الرجاء التواصل @{SUPPORT_CHAT} إذا استمرت المشكلة.",
            )
            return

        update.effective_message.reply_text(
            "*لقد نجحت في إنشاء اتحاد جديد!*"
            "\nName: `{}`"
            "\nID: `{}`"
            "\n\nاستخدم الأمر أدناه للانضمام إلى الاتحاد:"
            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            bot.send_message(
                EVENT_LOGS,
                "الاتحاد الجديد: <b>{}</b>\nID: <pre>{}</pre>".format(fed_name, fed_id),
                parse_mode=ParseMode.HTML,
            )
        except:
            LOGGER.warning("لا يمكن إرسال رسالة إلى EVENT_LOGS")
    else:
        update.effective_message.reply_text(
            "الرجاء كتابة اسم الاتحاد",
        )


def del_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        update.effective_message.reply_text(
            "لا يمكن حذف الاتحادات إلا من خلال مراسلتي بشكل خاص.",
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo is False:
            update.effective_message.reply_text("هذا الاتحاد غير موجود.")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("يمكن فقط لأصحاب الاتحاد القيام بذلك!")
            return
    else:
        update.effective_message.reply_text("ما الذي يجب علي حذفه؟")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن فقط لأصحاب الاتحاد القيام بذلك!")
        return

    update.effective_message.reply_text(
        "هل أنت متأكد أنك تريد حذف الاتحاد الخاص بك؟ لا يمكن التراجع عن هذا ، ستفقد قائمة الحظر بالكامل ، و '{}' سوف تضيع بشكل دائم.".format(
            getinfo["fname"],
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ حذف الاتحاد ⚠️",
                        callback_data="rmfed_{}".format(fed_id),
                    ),
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="rmfed_cancel")],
            ],
        ),
    )


def rename_fed(update, context):
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 2)

    if len(args) < 3:
        return msg.reply_text("usage: /renamefed <fed_id> <newname>")

    fed_id, newname = args[1], args[2]
    verify_fed = sql.get_fed_info(fed_id)

    if not verify_fed:
        return msg.reply_text("هذا التغذية غير موجود في قاعدة البيانات الخاصة بي!")

    if is_user_fed_owner(fed_id, user.id):
        sql.rename_fed(fed_id, user.id, newname)
        msg.reply_text(f"تم بنجاح إعادة تسمية اسم التغذية الخاصة بك إلى {newname}!")
    else:
        msg.reply_text("يمكن لمالك الاتحاد فقط القيام بذلك!")


def fed_chat(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text(
            "يجب أن تكون مسؤولاً لتنفيذ هذا الأمر",
        )
        return

    if not fed_id:
        update.effective_message.reply_text("هذه المجموعة ليست في أي اتحاد!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "هذه المجموعة هي جزء من الاتحاد التالي:"
    text += "\n{} (ID: <code>{}</code>)".format(info["fname"], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in DRAGONS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text(
                        "يمكن لمبدعي المجموعة فقط استخدام هذا الأمر!",
                    )
                    return
    if fed_id:
        message.reply_text("لا يمكنك الانضمام إلى اتحادين من دردشة واحدة")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            message.reply_text("الرجاء إدخال معرف اتحاد صالح")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            message.reply_text(
                f"فشل في الانضمام إلى الاتحاد! الرجاء التواصل @{SUPPORT_CHAT} هل يجب أن تستمر هذه المشكلة!",
            )
            return

        get_fedlog = sql.get_fed_log(args[0])
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "دردشة *{}* انضم إلى الاتحاد *{}*".format(
                        chat.title,
                        getfed["fname"],
                    ),
                    parse_mode="markdown",
                )

        message.reply_text(
            "انضمت هذه المجموعة إلى الاتحاد: {}!".format(getfed["fname"]),
        )


def leave_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالجماعة وليس برئيس الوزراء!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in "creator" or user.id in DRAGONS:
        if sql.chat_leave_fed(chat.id) is True:
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    bot.send_message(
                        get_fedlog,
                        "محادثه *{}* غادر الاتحاد *{}*".format(
                            chat.title,
                            fed_info["fname"],
                        ),
                        parse_mode="markdown",
                    )
            send_message(
                update.effective_message,
                "هذه المجموعة غادرت الاتحاد {}!".format(fed_info["fname"]),
            )
        else:
            update.effective_message.reply_text(
                "كيف يمكنك ترك اتحاد لم تنضم إليه قط ؟!",
            )
    else:
        update.effective_message.reply_text("يمكن لمبدعي المجموعة فقط استخدام هذا الأمر!")


def user_join_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in DRAGONS:
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("لا أستطيع استخراج المستخدم من هذه الرسالة")
            return
        else:
            LOGGER.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = ast.literal_eval(info["fusers"])["owner"]
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text(
                "أنت تعلم أن المستخدم هو صاحب الاتحاد ، أليس كذلك؟ حق؟",
            )
            return
        if getuser:
            update.effective_message.reply_text(
                "لا يمكنني ترقية المستخدمين الذين هم بالفعل مديرو اتحاد! يمكنك إزالتها إذا كنت تريد!",
            )
            return
        if user_id == bot.id:
            update.effective_message.reply_text(
                "أنا بالفعل مدير اتحاد في جميع الاتحادات!",
            )
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("تمت ترقيته بنجاح!")
        else:
            update.effective_message.reply_text("فشل الترقية!")
    else:
        update.effective_message.reply_text("يمكن فقط لأصحاب الاتحاد القيام بذلك!")


def user_demote_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("لا أستطيع استخراج المستخدم من هذه الرسالة")
            return
        else:
            LOGGER.warning("error")

        if user_id == bot.id:
            update.effective_message.reply_text(
                "الشيء الذي تحاول خفض رتبتي منه سيفشل في العمل بدوني! فقط أقول.",
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) is False:
            update.effective_message.reply_text(
                "لا يمكنني تخفيض رتب الأشخاص الذين ليسوا مدراء اتحاد!",
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res is True:
            update.effective_message.reply_text("انزلت من مدير بنك الاحتياطي الفيدرالي!")
        else:
            update.effective_message.reply_text("فشل التخفيض!")
    else:
        update.effective_message.reply_text("يمكن فقط لأصحاب الاتحاد القيام بذلك!")
        return


def fed_info(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if args:
        fed_id = args[0]
        info = sql.get_fed_info(fed_id)
    else:
        if chat.type == "private":
            send_message(
                update.effective_message,
                "يجب أن تزودني بفيد للتحقق من fedinfo في مساءي.",
            )
            return
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            send_message(
                update.effective_message,
                "هذه المجموعة ليست في أي اتحاد!",
            )
            return
        info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("فقط مسؤول الاتحاد يمكنه فعل ذلك!")
        return

    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ معلومات الاتحاد:</b>"
    text += "\nايدي: <code>{}</code>".format(fed_id)
    text += "\nاسم: {}".format(info["fname"])
    text += "\nالمنشئ: {}".format(mention_html(owner.id, owner_name))
    text += "\nجميع المدراء: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nإجمالي المستخدمين المحظورين: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nعدد المجموعات في هذا الاتحاد: <code>{}</code>".format(
        len(getfchat),
    )

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_admin(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("هذه المجموعة ليست في أي اتحاد!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن فقط لمسؤولي الاتحاد القيام بذلك!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = "<b>الاتحاد الادارية {}:</b>\n\n".format(info["fname"])
    text += "👑 Owner:\n"
    owner = bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 لا يوجد مشرفون في هذا الاتحاد"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = bot.get_chat(x)
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def fed_ban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن فقط لمسؤولي الاتحاد القيام بذلك!")
        return

    message = update.effective_message

    user_id, reason = extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("لا يبدو أنك تشير إلى مستخدم")
        return

    if user_id == bot.id:
        message.reply_text(
            "ما هو أكثر تسلية من ركل منشئ المجموعة؟ التضحية بالنفس.",
        )
        return

    if is_user_fed_owner(fed_id, user_id) is True:
        message.reply_text("لماذا جربت الاتحاد فبان؟")
        return

    if is_user_fed_admin(fed_id, user_id) is True:
        message.reply_text("إنه مدير اتحاد ، لا يمكنني منعه.")
        return

    if user_id == OWNER_ID:
        message.reply_text("مستوى الكارثة لا يمكن إطعامه ممنوع!")
        return

    if int(user_id) in DRAGONS:
        message.reply_text("لا يمكن إطعام التنين محظور!")
        return

    if int(user_id) in TIGERS:
        message.reply_text("لا يمكن إطعام النمور محظورة!")
        return

    if int(user_id) in WOLVES:
        message.reply_text("لا يمكن إطعام الذئاب محظورة!")
        return

    if user_id in [777000, 1087968824]:
        message.reply_text("مجنون! لا يمكنك مهاجمة تقنية Telegram الأصلية!")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        if len(str(user_id)) != 9:
            send_message(update.effective_message, "هذا ليس مستخدمًا!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        send_message(update.effective_message, "هذا ليس مستخدمًا!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    if fban:
        fed_name = info["fname"]
        # https://t.me/OnePunchSupport/41606 // https://t.me/OnePunchSupport/41619
        # starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
        # send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

        # if reason == "":
        #    reason = "No reason given."

        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            message.reply_text("فشل تحديث سبب fedban!")
            return
        x = sql.fban_user(
            fed_id,
            fban_user_id,
            fban_user_name,
            fban_user_lname,
            fban_user_uname,
            reason,
            int(time.time()),
        )
        if not x:
            message.reply_text(
                f"فشل في المنع من الاتحاد! إذا استمرت هذه المشكلة ، اتصل @{SUPPORT_CHAT}.",
            )
            return

        fed_chats = sql.all_fed_chats(fed_id)
        # Will send to current chat
        bot.send_message(
            chat.id,
            "<b>تم تحديث سبب FedBan</b>"
            "\n<b>الاتحاد:</b> {}"
            "\n<b>الاتحاد الادارية:</b> {}"
            "\n<b>مستخدم:</b> {}"
            "\n<b>ايدي المستخدم:</b> <code>{}</code>"
            "\n<b>السبب:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
        # Send message to owner if fednotif is enabled
        if getfednotif:
            bot.send_message(
                info["owner"],
                "<b>تم تحديث سبب FedBan</b>"
                "\n<b>الاتحاد:</b> {}"
                "\n<b>الاتحاد الادارية:</b> {}"
                "\n<b>مستخدم:</b> {}"
                "\n<b>ايدي المستخدم:</b> <code>{}</code>"
                "\n<b>السبب:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
        # If fedlog is set, then send message, except fedlog is current chat
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if int(get_fedlog) != int(chat.id):
                bot.send_message(
                    get_fedlog,
                    "<b>تم تحديث سبب FedBan</b>"
                    "\n<b>الاتحاد:</b> {}"
                    "\n<b>الاتحاد الادارية:</b> {}"
                    "\n<b>مستخدم:</b> {}"
                    "\n<b>ايدي المستخدم:</b> <code>{}</code>"
                    "\n<b>السبب:</b> {}".format(
                        fed_name,
                        mention_html(user.id, user.first_name),
                        user_target,
                        fban_user_id,
                        reason,
                    ),
                    parse_mode="HTML",
                )
        for fedschat in fed_chats:
            try:
                # Do not spam all fed chats
                """
				bot.send_message(chat, "<b>تم تحديث سبب FedBan</b>" \
							 "\n<b>الاتحاد:</b> {}" \
							 "\n<b>الاتحاد الادارية:</b> {}" \
							 "\n<b>مستخدم:</b> {}" \
							 "\n<b>ايدي المستخدم:</b> <code>{}</code>" \
							 "\n<b>السبب:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
                bot.kick_chat_member(fedschat, fban_user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    try:
                        dispatcher.bot.getChat(fedschat)
                    except Unauthorized:
                        sql.chat_leave_fed(fedschat)
                        LOGGER.info(
                            "دردشة {} لقد ترك التغذية {} لأنني تعرضت للركل".format(
                                fedschat,
                                info["fname"],
                            ),
                        )
                        continue
                elif excp.message == "User_id_invalid":
                    break
                else:
                    LOGGER.warning(
                        "تعذر fban on {} لأن: {}".format(chat, excp.message),
                    )
            except TelegramError:
                pass
        # Also do not spam all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>تم تحديث سبب FedBan</b>" \
							 "\n<b>الاتحاد:</b> {}" \
							 "\n<b>الاتحاد الادارية:</b> {}" \
							 "\n<b>مستخدم:</b> {}" \
							 "\n<b>ايدي المستخدم:</b> <code>{}</code>" \
							 "\n<b>السبب:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "دردشه {} يتغذى الجاني {} لأنني تعرضت للركل".format(
                                        fedschat,
                                        info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "تعذر تشغيل fban {} لان: {}".format(
                                    fedschat,
                                    excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
        # send_message(update.effective_message, "Fedban Reason has been updated.")
        return

    fed_name = info["fname"]

    # starting = "Starting a federation ban for {} in the Federation <b>{}</b>.".format(
    #    user_target, fed_name)
    # update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    # if reason == "":
    #    reason = "No reason given."

    x = sql.fban_user(
        fed_id,
        fban_user_id,
        fban_user_name,
        fban_user_lname,
        fban_user_uname,
        reason,
        int(time.time()),
    )
    if not x:
        message.reply_text(
            f"فشل في المنع من الاتحاد! إذا استمرت هذه المشكلة ، اتصل @{SUPPORT_CHAT}.",
        )
        return

    fed_chats = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>جديد FedBan</b>"
        "\n<b>الاتحاد:</b> {}"
        "\n<b>الاتحاد الادارية:</b> {}"
        "\n<b>مستخدم:</b> {}"
        "\n<b>ايدي المستخدم:</b> <code>{}</code>"
        "\n<b>السبب:</b> {}".format(
            fed_name,
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
            reason,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>جديد FedBan</b>"
            "\n<b>الاتحاد:</b> {}"
            "\n<b>الاتحاد الادارية:</b> {}"
            "\n<b>مستخدم:</b> {}"
            "\n<b>ايدي المستخدم:</b> <code>{}</code>"
            "\n<b>السبب:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>جديد FedBan</b>"
                "\n<b>الاتحاد:</b> {}"
                "\n<b>الاتحاد الادارية:</b> {}"
                "\n<b>مستخدم:</b> {}"
                "\n<b>ايدي المستخدم:</b> <code>{}</code>"
                "\n<b>السبب:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
    chats_in_fed = 0
    for fedschat in fed_chats:
        chats_in_fed += 1
        try:
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>تم تحديث سبب FedBan</b>" \
							"\n<b>الاتحاد:</b> {}" \
							"\n<b>الاتحاد الادارية:</b> {}" \
							"\n<b>مستخدم:</b> {}" \
							"\n<b>ايدي المستخدم:</b> <code>{}</code>" \
							"\n<b>السبب:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
            bot.kick_chat_member(fedschat, fban_user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "تعذر fban on {} لان: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

        # Also do not spamming all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>تم تحديث سبب FedBan</b>" \
							 "\n<b>الاتحاد:</b> {}" \
							 "\n<b>الاتحاد الادارية:</b> {}" \
							 "\n<b>مستخدم:</b> {}" \
							 "\n<b>ايدي المستخدم:</b> <code>{}</code>" \
							 "\n<b>السبب:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "دردشه {} يتغذى الجاني {} لأنني تعرضت للركل".format(
                                        fedschat,
                                        info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "تعذر تشغيل fban {} لان: {}".format(
                                    fedschat,
                                    excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
    # if chats_in_fed == 0:
    #    send_message(update.effective_message, "Fedban affected 0 chats. ")
    # elif chats_in_fed > 0:
    #    send_message(update.effective_message,
    #                 "Fedban affected {} chats. ".format(chats_in_fed))


def unfban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن فقط لمسؤولي الاتحاد القيام بذلك!")
        return

    user_id = extract_user_fban(message, args)
    if not user_id:
        message.reply_text("لا يبدو أنك تشير إلى مستخدم.")
        return

    try:
        user_chat = bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        if len(str(user_id)) != 9:
            send_message(update.effective_message, "هذا ليس مستخدمًا!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        message.reply_text("هذا ليس مستخدمًا!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
    if fban is False:
        message.reply_text("هذا المستخدم غير ممنوع!")
        return

    banner = update.effective_user

    # message.reply_text("I'll give {} another chance in this federation".format(user_chat.first_name))

    chat_list = sql.all_fed_chats(fed_id)
    # Will send to current chat
    bot.send_message(
        chat.id,
        "<b>Un-FedBan</b>"
        "\n<b>الاتحاد:</b> {}"
        "\n<b>الاتحاد الادارية:</b> {}"
        "\n<b>مستخدم:</b> {}"
        "\n<b>ايدي المستخدم:</b> <code>{}</code>".format(
            info["fname"],
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        bot.send_message(
            info["owner"],
            "<b>Un-FedBan</b>"
            "\n<b>الاتحاد:</b> {}"
            "\n<b>الاتحاد الادارية:</b> {}"
            "\n<b>مستخدم:</b> {}"
            "\n<b>ايدي المستخدم:</b> <code>{}</code>".format(
                info["fname"],
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            bot.send_message(
                get_fedlog,
                "<b>Un-FedBan</b>"
                "\n<b>الاتحاد:</b> {}"
                "\n<b>الاتحاد الادارية:</b> {}"
                "\n<b>مستخدم:</b> {}"
                "\n<b>ايدي المستخدم:</b> <code>{}</code>".format(
                    info["fname"],
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                ),
                parse_mode="HTML",
            )
    unfbanned_in_chats = 0
    for fedchats in chat_list:
        unfbanned_in_chats += 1
        try:
            member = bot.get_chat_member(fedchats, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(fedchats, user_id)
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Un-FedBan</b>" \
						 "\n<b>الاتحاد:</b> {}" \
						 "\n<b>الاتحاد الادارية:</b> {}" \
						 "\n<b>مستخدم:</b> {}" \
						 "\n<b>ايدي المستخدم:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Could not fban on {} because: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

    try:
        x = sql.un_fban_user(fed_id, user_id)
        if not x:
            send_message(
                update.effective_message,
                "فشل إلغاء fban ، قد يكون هذا المستخدم غير محجوب بالفعل!",
            )
            return
    except:
        pass

    # UnFban for fed subscriber
    subscriber = list(sql.get_subscriber(fed_id))
    if len(subscriber) != 0:
        for fedsid in subscriber:
            all_fedschat = sql.all_fed_chats(fedsid)
            for fedschat in all_fedschat:
                try:
                    bot.unban_chat_member(fedchats, user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.getChat(fedschat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedschat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            LOGGER.info(
                                "دردشه {} يتغذى الجاني {} لأنني تعرضت للركل".format(
                                    fedschat,
                                    info["fname"],
                                ),
                            )
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        LOGGER.warning(
                            "تعذر تشغيل fban {} لان: {}".format(
                                fedschat,
                                excp.message,
                            ),
                        )
                except TelegramError:
                    pass

    if unfbanned_in_chats == 0:
        send_message(
            update.effective_message,
            "تم إلغاء حظر هذا الشخص في 0 دردشة.",
        )
    if unfbanned_in_chats > 0:
        send_message(
            update.effective_message,
            "تم إلغاء حظر هذا الشخص في محادثات {}.".format(unfbanned_in_chats),
        )
    # Also do not spamming all fed admins
    """
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport is False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Un-FedBan</b>" \
			 "\n<b>الاتحاد:</b> {}" \
			 "\n<b>الاتحاد الادارية:</b> {}" \
			 "\n<b>مستخدم:</b> {}" \
			 "\n<b>ايدي المستخدم:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												 mention_html(user_chat.id, user_chat.first_name),
															  user_chat.id),
			html=True)
	"""


def set_frules(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("هذه المجموعة ليست في أي اتحاد!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("فقط مدراء التغذية يمكنهم القيام بذلك!")
        return

    if len(args) >= 1:
        msg = update.effective_message
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(
                txt,
                entities=msg.parse_entities(),
                offset=offset,
            )
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text(
                f"قف! حدث خطأ أثناء تحديد قواعد الاتحاد! إذا كنت تتساءل لماذا يرجى طرحها في @{SUPPORT_CHAT}!",
            )
            return

        rules = sql.get_fed_info(fed_id)["frules"]
        getfed = sql.get_fed_info(fed_id)
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                bot.send_message(
                    get_fedlog,
                    "*{}* قام بتحديث قواعد الاتحاد من أجل التغذية *{}*".format(
                        user.first_name,
                        getfed["fname"],
                    ),
                    parse_mode="markdown",
                )
        update.effective_message.reply_text(f"تم تغيير القواعد إلى :\n{rules}!")
    else:
        update.effective_message.reply_text("يرجى كتابة القواعد لإعداد هذا!")


def get_frules(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("هذه المجموعة ليست في أي اتحاد!")
        return

    rules = sql.get_frules(fed_id)
    text = "*القواعد في هذا تغذية:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def fed_broadcast(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    if args:
        chat = update.effective_chat
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        if is_user_fed_owner(fed_id, user.id) is False:
            update.effective_message.reply_text("يمكن فقط لأصحاب الاتحاد القيام بذلك!")
            return
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text = text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            title = "*بث جديد من الاحتياطي الفيدرالي {}*\n".format(fedinfo["fname"])
            try:
                bot.sendMessage(chat, title + text, parse_mode="markdown")
            except TelegramError:
                try:
                    dispatcher.bot.getChat(chat)
                except Unauthorized:
                    failed += 1
                    sql.chat_leave_fed(chat)
                    LOGGER.info(
                        "دردشه {} لقد ترك التغذية {} لأنني تعرضت للكم".format(
                            chat,
                            fedinfo["fname"],
                        ),
                    )
                    continue
                failed += 1
                LOGGER.warning("تعذر إرسال البث إلى {}".format(str(chat)))

        send_text = "اكتمل بث الاتحاد"
        if failed >= 1:
            send_text += "{} فشلت المجموعة في تلقي الرسالة ، ربما لأنها غادرت الاتحاد.".format(
                failed,
            )
        update.effective_message.reply_text(send_text)


def fed_ban_list(update: Update, context: CallbackContext):
    bot, args, chat_data = context.bot, context.args, context.chat_data
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن لمالكي الاتحاد فقط القيام بذلك!")
        return

    user = update.effective_user
    chat = update.effective_chat
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        update.effective_message.reply_text(
            "قائمة الممنوعات من الاتحاد {} فارغ".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    if args:
        if args[0] == "json":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y",
                        time.localtime(cek.get("value")),
                    )
                    update.effective_message.reply_text(
                        "يمكنك نسخ بياناتك احتياطيًا مرة واحدة كل 30 دقيقة!\nيمكنك نسخ البيانات احتياطيًا مرة أخرى في `{}`".format(
                            waktu,
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {
                    "user_id": users,
                    "first_name": getuserinfo["first_name"],
                    "last_name": getuserinfo["last_name"],
                    "user_name": getuserinfo["user_name"],
                    "reason": getuserinfo["reason"],
                }
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "saitama_fbanned_users.json"
                update.effective_message.reply_document(
                    document=output,
                    filename="saitama_fbanned_users.json",
                    caption="المجموع {} تم حظر المستخدم من قبل الاتحاد {}.".format(
                        len(getfban),
                        info["fname"],
                    ),
                )
            return
        if args[0] == "csv":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y",
                        time.localtime(cek.get("value")),
                    )
                    update.effective_message.reply_text(
                        "يمكنك نسخ البيانات احتياطيًا مرة واحدة كل 30 دقيقة!\nيمكنك نسخ البيانات احتياطيًا مرة أخرى في `{}`".format(
                            waktu,
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in DRAGONS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += (
                    "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                        user_id=users,
                        first_name=getuserinfo["first_name"],
                        last_name=getuserinfo["last_name"],
                        user_name=getuserinfo["user_name"],
                        reason=getuserinfo["reason"],
                    )
                )
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "saitama_fbanned_users.csv"
                update.effective_message.reply_document(
                    document=output,
                    filename="saitama_fbanned_users.csv",
                    caption="المجموع {} تم حظر المستخدم من قبل الاتحاد {}.".format(
                        len(getfban),
                        info["fname"],
                    ),
                )
            return

    text = "<b>{} تم حظر المستخدمين من الاتحاد {}:</b>\n".format(
        len(getfban),
        info["fname"],
    )
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo is False:
            text = "لا يوجد مستخدمون ممنوعون من الاتحاد {}".format(
                info["fname"],
            )
            break
        user_name = getuserinfo["first_name"]
        if getuserinfo["last_name"]:
            user_name += " " + getuserinfo["last_name"]
        text += " • {} (<code>{}</code>)\n".format(
            mention_html(users, user_name),
            users,
        )

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y",
                    time.localtime(cek.get("value")),
                )
                update.effective_message.reply_text(
                    "يمكنك نسخ البيانات احتياطيًا مرة واحدة كل 30 دقيقة!\nيمكنك نسخ البيانات احتياطيًا مرة أخرى في `{}`".format(
                        waktu,
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fbanlist.txt",
                caption="فيما يلي قائمة بالمستخدمين المحظورين حاليًا في الاتحاد {}.".format(
                    info["fname"],
                ),
            )


def fed_notif(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            msg.reply_text(
                "الإبلاغ عن الاتحاد احتياطيًا! كل مستخدم fban / إلغاء الحظر سيتم إخطارك عبر PM.",
            )
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            msg.reply_text(
                "اتحاد التقارير توقف! كل مستخدم fban / إلغاء الحظر لن يتم إخطارك عبر PM.",
            )
        else:
            msg.reply_text("Please enter `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        msg.reply_text(
            "تفضيلات تقرير الاتحاد الحالي الخاص بك: `{}`".format(getreport),
            parse_mode="markdown",
        )


def fed_chats(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن فقط لمسؤولي الاتحاد القيام بذلك!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        update.effective_message.reply_text(
            "لا يوجد مستخدمون ممنوعون من الاتحاد {}".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    text = "<b>انضم دردشة جديدة إلى الاتحاد {}:</b>\n".format(info["fname"])
    for chats in getlist:
        try:
            chat_name = dispatcher.bot.getChat(chats).title
        except Unauthorized:
            sql.chat_leave_fed(chats)
            LOGGER.info(
                "دردشه {} لقد ترك التغذية {} لأنني تعرضت للركل".format(
                    chats,
                    info["fname"],
                ),
            )
            continue
        text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fedchats.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fedchats.txt",
                caption="فيما يلي قائمة بجميع الدردشات التي انضمت إلى الاتحاد {}.".format(
                    info["fname"],
                ),
            )


def fed_import_bans(update: Update, context: CallbackContext):
    bot, chat_data = context.bot, context.chat_data
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)
    getfed = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "هذه المجموعة ليست جزءًا من أي اتحاد!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("يمكن لمالكي الاتحاد فقط القيام بذلك!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y",
                    time.localtime(cek.get("value")),
                )
                update.effective_message.reply_text(
                    "يمكنك الحصول على البيانات الخاصة بك مرة واحدة كل 30 دقيقة!\nيمكنك الحصول على البيانات مرة أخرى في `{}`".format(
                        waktu,
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in DRAGONS:
                put_chat(chat.id, new_jam, chat_data)
        # if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
        # 	msg.reply_text("This file is too big!")
        # 	return
        success = 0
        failed = 0
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text(
                "حاول تنزيل الملف وإعادة تحميله ، يبدو أن هذا الملف معطل!",
            )
            return
        fileformat = msg.reply_to_message.document.file_name.split(".")[-1]
        if fileformat == "json":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError as err:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data["user_id"])  # Make sure it int
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in DRAGONS:
                        failed += 1
                        continue
                    if int(import_userid) in TIGERS:
                        failed += 1
                        continue
                    if int(import_userid) in WOLVES:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            text = "تم استيراد الكتل بنجاح. {} الناس ممنوعون.".format(
                success,
            )
            if failed >= 1:
                text += " {} فشل الاستيراد.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Fed *{}* استورد البيانات بنجاح. {} محظور.".format(
                        getfed["fname"],
                        success,
                    )
                    if failed >= 1:
                        teks += " {} Failed to import.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        elif fileformat == "csv":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            file_info.download(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
            )
            with open(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
                "r",
                encoding="utf8",
            ) as csvFile:
                reader = csv.reader(csvFile)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in DRAGONS:
                        failed += 1
                        continue
                    if int(import_userid) in TIGERS:
                        failed += 1
                        continue
                    if int(import_userid) in WOLVES:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                    # t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
                    # t.start()
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            csvFile.close()
            os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
            text = "تم استيراد الملفات بنجاح. {} الناس المحظورة.".format(success)
            if failed >= 1:
                text += " {} فشل الاستيراد.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Fed *{}* استورد البيانات بنجاح. {} محظور.".format(
                        getfed["fname"],
                        success,
                    )
                    if failed >= 1:
                        teks += " {} فشل الاستيراد.".format(failed)
                    bot.send_message(get_fedlog, teks, parse_mode="markdown")
        else:
            send_message(update.effective_message, "This file is not supported.")
            return
        send_message(update.effective_message, text)


def del_fed_button(update: Update, context: CallbackContext):
    query = update.callback_query
    userid = query.message.chat.id
    fed_id = query.data.split("_")[1]

    if fed_id == "cancel":
        query.message.edit_text("تم إلغاء حذف الاتحاد")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
        delete = sql.del_fed(fed_id)
        if delete:
            query.message.edit_text(
                "لقد قمت بإزالة الاتحاد الخاص بك! الآن كل المجموعات المرتبطة بـ `{}` ليس لديك اتحاد.".format(
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )


def fed_stat_user(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args:
        if args[0].isdigit():
            user_id = args[0]
        else:
            user_id = extract_user(msg, args)
    else:
        user_id = extract_user(msg, args)

    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
            if fbantime:
                fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
            else:
                fbantime = "Unavaiable"
            if user_name is False:
                send_message(
                    update.effective_message,
                    "Fed {} لم يتم العثور على!".format(fed_id),
                    parse_mode="markdown",
                )
                return
            if user_name == "" or user_name is None:
                user_name = "He/she"
            if not reason:
                send_message(
                    update.effective_message,
                    "{} غير محظور في هذا الاتحاد!".format(user_name),
                )
            else:
                teks = "{} المحظورة في هذا الاتحاد بسبب:\n`{}`\n*محظور في:* `{}`".format(
                    user_name,
                    reason,
                    fbantime,
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
            return
        user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
        if user_name == "":
            try:
                user_name = bot.get_chat(user_id).first_name
            except BadRequest:
                user_name = "He/she"
            if user_name == "" or user_name is None:
                user_name = "He/she"
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} غير محظور في أي اتحاد!".format(user_name),
            )
            return
        teks = "{} تم حظره في هذا الاتحاد:\n".format(user_name)
        for x in fbanlist:
            teks += "- `{}`: {}\n".format(x[0], x[1][:20])
        teks += "\nإذا كنت تريد معرفة المزيد حول أسباب Fedban على وجه التحديد ، فاستخدم /fbanstat <FedID>"
        send_message(update.effective_message, teks, parse_mode="markdown")

    elif not msg.reply_to_message and not args:
        user_id = msg.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = msg.from_user.first_name
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} غير محظور في أي اتحاد!".format(user_name),
            )
        else:
            teks = "{} تم حظره في هذا الاتحاد:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nإذا كنت تريد معرفة المزيد حول أسباب Fedban على وجه التحديد ، فاستخدم /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            send_message(update.effective_message, "Fed {} لم يتم العثور على!".format(fed_id))
            return
        name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
        if fbantime:
            fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
        else:
            fbantime = "Unavaiable"
        if not name:
            name = msg.from_user.first_name
        if not reason:
            send_message(
                update.effective_message,
                "{} غير محظور في هذا الاتحاد".format(name),
            )
            return
        send_message(
            update.effective_message,
            "{} المحظورة في هذا الاتحاد بسبب:\n`{}`\n*محظور في:* `{}`".format(
                name,
                reason,
                fbantime,
            ),
            parse_mode="markdown",
        )


def set_fed_log(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "هذا الاتحاد غير موجود!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "يمكن لمنشئ الاتحاد فقط تعيين سجلات الاتحاد.",
            )
            return
        setlog = sql.set_fed_log(args[0], chat.id)
        if setlog:
            send_message(
                update.effective_message,
                "Federation log `{}` تم تعيينه على {}".format(
                    fedinfo["fname"],
                    chat.title,
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "أنت لم تقدم المعرف الفيدرالي الخاص بك!",
        )


def unset_fed_log(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "هذا الاتحاد غير موجود!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "يمكن لمنشئ الاتحاد فقط تعيين سجلات الاتحاد.",
            )
            return
        setlog = sql.set_fed_log(args[0], None)
        if setlog:
            send_message(
                update.effective_message,
                "Federation log `{}` تم إبطالها في {}".format(
                    fedinfo["fname"],
                    chat.title,
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "أنت لم تقدم المعرف الفيدرالي الخاص بك!",
        )


def subs_feds(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "هذه المجموعة ليست في أي اتحاد!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "يمكن لمالك التغذية فقط القيام بذلك!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message,
                "الرجاء إدخال معرف اتحاد صالح.",
            )
            return
        subfed = sql.subs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federation `{}` اشترك الاتحاد `{}`. في كل مرة يوجد فيها Fedban من هذا الاتحاد ، سيقوم هذا الاتحاد أيضًا بحظر هذا المستخدم.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federation `{}` اشترك الاتحاد `{}`".format(
                            fedinfo["fname"],
                            getfed["fname"],
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federation `{}` اشترك بالفعل في الاتحاد `{}`.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "أنت لم تقدم المعرف الفيدرالي الخاص بك!",
        )


def unsubs_feds(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "هذه المجموعة ليست في أي اتحاد!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "يمكن لمالك التغذية فقط القيام بذلك!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message,
                "الرجاء إدخال معرف اتحاد صالح.",
            )
            return
        subfed = sql.unsubs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federation `{}` تغذية إلغاء الاشتراك الآن `{}`.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    bot.send_message(
                        get_fedlog,
                        "Federation `{}` لديه إلغاء الاشتراك تغذية `{}`.".format(
                            fedinfo["fname"],
                            getfed["fname"],
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federation `{}` لا تشترك `{}`.".format(
                    fedinfo["fname"],
                    getfed["fname"],
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "أنت لم تقدم المعرف الفيدرالي الخاص بك!",
        )


def get_myfedsubs(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        send_message(
            update.effective_message,
            "هذا الأمر خاص بالمجموعة وليس في شات البوت!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "هذه المجموعة ليست في أي اتحاد!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "يمكن لمالك التغذية فقط القيام بذلك!")
        return

    try:
        getmy = sql.get_mysubs(fed_id)
    except:
        getmy = []

    if len(getmy) == 0:
        send_message(
            update.effective_message,
            "Federation `{}` لا يشترك في أي اتحاد.".format(
                fedinfo["fname"],
            ),
            parse_mode="markdown",
        )
        return
    listfed = "Federation `{}` هو الاشتراك في الاتحاد:\n".format(
        fedinfo["fname"],
    )
    for x in getmy:
        listfed += "- `{}`\n".format(x)
    listfed += (
        "\nللحصول على معلومات التغذية `/fedinfo <fedid>`. لإلغاء الاشتراك `/unsubfed <fedid>`."
    )
    send_message(update.effective_message, listfed, parse_mode="markdown")


def get_myfeds_list(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    fedowner = sql.get_user_owner_fed_full(user.id)
    if fedowner:
        text = "*أنت صاحب الفدرالية:\n*"
        for f in fedowner:
            text += "- `{}`: *{}*\n".format(f["fed_id"], f["fed"]["fname"])
    else:
        text = "*ليس لديك أي فدائيين!*"
    send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins is False:
        return False
    return bool(int(user_id) in fed_admins or int(user_id) == OWNER_ID)


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql is False:
        return False
    getfedowner = ast.literal_eval(getsql["fusers"])
    if getfedowner is None or getfedowner is False:
        return False
    getfedowner = getfedowner["owner"]
    return bool(str(user_id) == getfedowner or int(user_id) == OWNER_ID)


# There's no handler for this yet, but updating for v12 in case its used
def welcome_fed(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text(
            "هذا المستخدم ممنوع في الاتحاد الحالي! سأقوم بإزالته.",
        )
        bot.kick_chat_member(chat.id, user.id)
        return True
    return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "× {} المستخدمين المحظورين عبر {} Federations".format(
        len(all_fbanned),
        len(all_feds),
    )


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]

        if int(info["owner"]) == user_id:
            text = "مالك الاتحاد: <b>{}</b>.".format(infoname)
        elif is_user_fed_admin(fed_id, user_id):
            text = "ادارة الاتحاد: <b>{}</b>.".format(infoname)

        elif fban:
            text = "حظر الاتحاد: <b>Yes</b>"
            text += "\n<b>السبب:</b> {}".format(fbanreason)
        else:
            text = "حظر الاتحاد: <b>No</b>"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    if value is False:
        status = False
    else:
        status = True
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        value = chat_data[chat_id]["federation"]
        return value
    except KeyError:
        return {"status": False, "value": False}


def fed_owner_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """*👑 Fed Owner Only:*
❂ /newfed <fed_name>*:* ينشئ اتحادًا ، واحدًا مسموحًا به لكل مستخدم
❂ /renamefed <fed_id> <new_fed_name>*:* يعيد تسمية معرف التغذية إلى اسم جديد
❂ /delfed <fed_id>*:* حذف اتحاد وأية معلومات متعلقة به. لن تلغي المستخدمين المحظورين
❂ /fpromote <user>*:* يعيّن المستخدم كمسؤول اتحاد. يُمكّن جميع الأوامر للمستخدم تحت مسؤولي الاحتياطي الفيدرالي
❂ /fdemote <user>*:* يسقط المستخدم من اتحاد الإدارة إلى مستخدم عادي
❂ /subfed <fed_id>*:* للاشتراك في معرّف تغذية معين ، سيحدث الحظر أيضًا في نظام التغذية التلقائية الخاص بك
❂ /unsubfed <fed_id>*:* إلغاء الاشتراك في معرف تغذية معين
❂ /setfedlog <fed_id>*:* يعيّن المجموعة كقاعدة تقرير سجل التغذية الفدرالية للاتحاد
❂ /unsetfedlog <fed_id>*:* تمت إزالة المجموعة كقاعدة تقرير سجل التغذية للاتحاد
❂ /fbroadcast <message>*:* يبث رسائل لجميع المجموعات التي انضمت إلى ملفك
❂ /fedsubs*:* يظهر التغذية الفيدرالية التي اشتركت فيها مجموعتك `(broken rn)`""",
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_admin_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """*🔱 Fed Admins:*
❂ /fban <user> <reason>*:* الفيدرالي يحظر المستخدم
❂ /unfban <user> <reason>*:* إزالة مستخدم من حظر فيدرالي
❂ /fedinfo <fed_id>*:* معلومات عن الاتحاد المحدد
❂ /joinfed <fed_id>*:* انضم إلى الدردشة الحالية إلى الاتحاد. يمكن فقط لأصحاب الدردشة القيام بذلك. يمكن أن تكون كل محادثة في اتحاد واحد فقط
❂ /leavefed <fed_id>*:* اترك الاتحاد معين. يمكن فقط لأصحاب الدردشة القيام بذلك
❂ /setfrules <rules>*:* ترتيب قواعد الاتحاد
❂ /fedadmins*:* إظهار مسؤول الاتحاد
❂ /fbanlist*:* يعرض جميع المستخدمين الذين وقعوا ضحية في الاتحاد في هذا الوقت
❂ /fedchats*:* احصل على جميع الدردشات المتصلة في الاتحاد
❂ /chatfed *:* رؤية الاتحاد في الدردشة الحالية\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_user_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        """*🎩 Any user:*

❂ /fbanstat*:* يظهر إذا كنت أنت / أو المستخدم الذي ترد عليه أو تم حظر اسم المستخدم الخاص به في مكان ما أم لا
❂ /fednotif <on/off>*:* إعدادات الاتحاد ليست في PM عندما يكون هناك مستخدمون ممنوعون / غير محظور
❂ /frules*:* انظر لوائح الاتحاد\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


__mod_name__ = "Federations"


NEW_FED_HANDLER = CommandHandler("newfed", new_fed, run_async=True)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, run_async=True)
RENAME_FED = CommandHandler("renamefed", rename_fed, run_async=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, run_async=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, run_async=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, run_async=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, run_async=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, run_async=True)
BAN_FED_HANDLER = DisableAbleCommandHandler("fban", fed_ban, run_async=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, run_async=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, run_async=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, run_async=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, run_async=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, run_async=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, run_async=True)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, run_async=True)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, run_async=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, run_async=True)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, run_async=True)
FEDSTAT_USER = DisableAbleCommandHandler(
    ["fedstat", "fbanstat"], fed_stat_user, run_async=True
)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, run_async=True)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, run_async=True)
SUBS_FED = CommandHandler("subfed", subs_feds, run_async=True)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, run_async=True)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, run_async=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list, run_async=True)
DELETEBTN_FED_HANDLER = CallbackQueryHandler(
    del_fed_button, pattern=r"rmfed_", run_async=True
)
FED_OWNER_HELP_HANDLER = CommandHandler("fedownerhelp", fed_owner_help, run_async=True)
FED_ADMIN_HELP_HANDLER = CommandHandler("fedadminhelp", fed_admin_help, run_async=True)
FED_USER_HELP_HANDLER = CommandHandler("feduserhelp", fed_user_help, run_async=True)

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(RENAME_FED)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
# dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(FEDSTAT_USER)
dispatcher.add_handler(SET_FED_LOG)
dispatcher.add_handler(UNSET_FED_LOG)
dispatcher.add_handler(SUBS_FED)
dispatcher.add_handler(UNSUBS_FED)
dispatcher.add_handler(MY_SUB_FED)
dispatcher.add_handler(MY_FEDS_LIST)
dispatcher.add_handler(DELETEBTN_FED_HANDLER)
dispatcher.add_handler(FED_OWNER_HELP_HANDLER)
dispatcher.add_handler(FED_ADMIN_HELP_HANDLER)
dispatcher.add_handler(FED_USER_HELP_HANDLER)
