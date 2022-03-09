import re, ast
from io import BytesIO
import random
from typing import Optional

import HmsRobot.modules.sql.notes_sql as sql
from HmsRobot import LOGGER, JOIN_LOGGER, SUPPORT_CHAT, dispatcher, DRAGONS
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.handlers import MessageHandlerChecker
from HmsRobot.modules.helper_funcs.chat_status import user_admin, connection_status
from HmsRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from HmsRobot.modules.helper_funcs.msg_types import get_note_type
from HmsRobot.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
)
from telegram import (
    MAX_MESSAGE_LENGTH,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    InlineKeyboardButton,
)
from telegram.error import BadRequest
from telegram.utils.helpers import escape_markdown, mention_markdown
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    Filters,
    MessageHandler,
)

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}


# Do not async
def get(update, context, notename, show_none=True, no_format=False):
    bot = context.bot
    chat_id = update.effective_message.chat.id
    note_chat_id = update.effective_chat.id
    note = sql.get_note(note_chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        if MessageHandlerChecker.check_user(update.effective_user.id):
            return
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id
        if note.is_reply:
            if JOIN_LOGGER:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=JOIN_LOGGER,
                        message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "لم يتم العثور على رسالة لإعادة التوجيه":
                        message.reply_text(
                            "يبدو أن هذه الرسالة قد ضاعت - سأزيلها "
                            "من قائمة الملاحظات الخاصة بك.",
                        )
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "لم يتم العثور على رسالة لإعادة التوجيه":
                        message.reply_text(
                            "يبدو أن المُرسِل الأصلي لهذه الملاحظة قد تم حذفه"
                            "رسالتهم - آسف! احصل على مسؤول الروبوت الخاص بك لبدء استخدام ملف"
                            "تفريغ الرسائل لتجنب ذلك. سأزيل هذه الملاحظة من"
                            "ملاحظاتك المحفوظة.",
                        )
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
        else:
            VALID_NOTE_FORMATTERS = [
                "first",
                "last",
                "fullname",
                "username",
                "id",
                "chatname",
                "mention",
            ]
            valid_format = escape_invalid_curly_brackets(
                note.value,
                VALID_NOTE_FORMATTERS,
            )
            if valid_format:
                if not no_format:
                    if "%%%" in valid_format:
                        split = valid_format.split("%%%")
                        if all(split):
                            text = random.choice(split)
                        else:
                            text = valid_format
                    else:
                        text = valid_format
                else:
                    text = valid_format
                text = text.format(
                    first=escape_markdown(message.from_user.first_name),
                    last=escape_markdown(
                        message.from_user.last_name or message.from_user.first_name,
                    ),
                    fullname=escape_markdown(
                        " ".join(
                            [message.from_user.first_name, message.from_user.last_name]
                            if message.from_user.last_name
                            else [message.from_user.first_name],
                        ),
                    ),
                    username="@" + message.from_user.username
                    if message.from_user.username
                    else mention_markdown(
                        message.from_user.id,
                        message.from_user.first_name,
                    ),
                    mention=mention_markdown(
                        message.from_user.id,
                        message.from_user.first_name,
                    ),
                    chatname=escape_markdown(
                        message.chat.title
                        if message.chat.type != "private"
                        else message.from_user.first_name,
                    ),
                    id=message.from_user.id,
                )
            else:
                text = ""

            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(note_chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
                else:
                    ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        caption=text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        reply_markup=keyboard,
                    )

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text(
                        "يبدو أنك حاولت ذكر شخص لم أره من قبل. إذا كنت حقا"
                        "أريد أن أذكرهم ، وأرسل إحدى رسائلهم إليّ ، وسأكون قادرًا"
                        "لتمييزهم!",
                    )
                elif FILE_MATCHER.match(note.value):
                    message.reply_text(
                        "كانت هذه الملاحظة ملفًا مستوردًا بشكل غير صحيح من روبوت آخر - لا يمكنني استخدام"
                        "هو - هي. إذا كنت حقًا في حاجة إليه ، فسيتعين عليك حفظه مرة أخرى. في"
                        "في غضون ذلك ، سأزيله من قائمة ملاحظاتك.",
                    )
                    sql.rm_note(note_chat_id, notename)
                else:
                    message.reply_text(
                        "تعذر إرسال هذه الملاحظة حيث تم تنسيقها بشكل غير صحيح. اسأل في"
                        f"@{SUPPORT_CHAT} إذا لم تستطع معرفة السبب!",
                    )
                    LOGGER.exception(
                        "تعذر تحليل الرسالة #%s in chat %s",
                        notename,
                        str(note_chat_id),
                    )
                    LOGGER.warning("كانت الرسالة: %s", str(note.value))
        return
    if show_none:
        message.reply_text("هذه الملاحظة غير موجودة")


@connection_status
def cmd_get(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(update, context, args[0].lower(), show_none=True, no_format=True)
    elif len(args) >= 1:
        get(update, context, args[0].lower(), show_none=True)
    else:
        update.effective_message.reply_text("Get rekt")


@connection_status
def hash_get(update: Update, context: CallbackContext):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:].lower()
    get(update, context, no_hash, show_none=False)


@connection_status
def slash_get(update: Update, context: CallbackContext):
    message, chat_id = update.effective_message.text, update.effective_chat.id
    no_slash = message[1:]
    note_list = sql.get_all_chat_notes(chat_id)

    try:
        noteid = note_list[int(no_slash) - 1]
        note_name = str(noteid).strip(">").split()[1]
        get(update, context, note_name, show_none=False)
    except IndexError:
        update.effective_message.reply_text("Wrong Note ID 😾")


@user_admin
@connection_status
def save(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)
    note_name = note_name.lower()
    if data_type is None:
        msg.reply_text("يا صاح ، ليس هناك ملاحظة")
        return

    sql.add_note_to_db(
        chat_id,
        note_name,
        text,
        data_type,
        buttons=buttons,
        file=content,
    )

    msg.reply_text(
        f"ياس! مضاف `{note_name}`.\nاحصل عليه مع /get `{note_name}`, or `#{note_name}`",
        parse_mode=ParseMode.MARKDOWN,
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text(
                "يبدو أنك تحاول حفظ رسالة من الروبوت. لسوء الحظ،"
                "لا تستطيع برامج الروبوت إعادة توجيه رسائل الروبوت ، لذا لا يمكنني حفظ الرسالة بالضبط."
                "\nسأحفظ كل النص الذي أستطيعه ، ولكن إذا كنت تريد المزيد ، فسيتعين عليك ذلك"
                "قم بإعادة توجيه الرسالة بنفسك ، ثم احفظها.",
            )
        else:
            msg.reply_text(
                "يتم إعاقة برامج الروبوت نوعًا ما عن طريق التلغرام ، مما يجعل من الصعب على الروبوتات القيام بذلك"
                "تتفاعل مع برامج الروبوت الأخرى ، لذا لا يمكنني حفظ هذه الرسالة"
                "كما أفعل عادةً - هل تمانع في إعادة توجيهه و"
                "ثم حفظ تلك الرسالة الجديدة؟ شكرا!",
            )
        return


@user_admin
@connection_status
def clear(update: Update, context: CallbackContext):
    args = context.args
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0].lower()

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("تمت إزالة الملاحظة بنجاح.")
        else:
            update.effective_message.reply_text("هذه ليست ملاحظة في قاعدة بياناتي!")


def clearall(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in DRAGONS:
        update.effective_message.reply_text(
            "يمكن لمالك الدردشة فقط مسح جميع الملاحظات دفعة واحدة.",
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="احذف كافة الملاحظات",
                        callback_data="notes_rmall",
                    ),
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="notes_cancel")],
            ],
        )
        update.effective_message.reply_text(
            f"هل أنت متأكد من رغبتك في مسح كافة الملاحظات بتنسيق {chat.title}? لا يمكن التراجع عن هذا الإجراء.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


def clearall_btn(update: Update, context: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == "notes_rmall":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            note_list = sql.get_all_chat_notes(chat.id)
            try:
                for notename in note_list:
                    note = notename.name.lower()
                    sql.rm_note(chat.id, note)
                message.edit_text("تم حذف كافة الملاحظات.")
            except BadRequest:
                return

        if member.status == "administrator":
            query.answer("يمكن لمالك الدردشة فقط القيام بذلك.")

        if member.status == "member":
            query.answer("يجب أن تكون مشرفًا للقيام بذلك.")
    elif query.data == "notes_cancel":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            message.edit_text("تم إلغاء مسح جميع الأوراق النقدية.")
            return
        if member.status == "administrator":
            query.answer("يمكن لمالك الدردشة فقط القيام بذلك.")
        if member.status == "member":
            query.answer("يجب أن تكون مشرفًا للقيام بذلك.")


@connection_status
def list_notes(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)
    notes = len(note_list) + 1
    msg = "احصل على ملاحظات `/notenumber` or `#notename` \n\n  *ID*    *Note* \n"
    for note_id, note in zip(range(1, notes), note_list):
        if note_id < 10:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        else:
            note_name = f"`{note_id}.`  `#{(note.name.lower())}`\n"
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if not note_list:
        try:
            update.effective_message.reply_text("لا توجد ملاحظات في هذه الدردشة!")
        except BadRequest:
            update.effective_message.reply_text("لا توجد ملاحظات في هذه الدردشة!", quote=False)

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)
        matchsticker = STICKER_MATCHER.match(notedata)
        matchbtn = BUTTON_MATCHER.match(notedata)
        matchfile = MYFILE_MATCHER.match(notedata)
        matchphoto = MYPHOTO_MATCHER.match(notedata)
        matchaudio = MYAUDIO_MATCHER.match(notedata)
        matchvoice = MYVOICE_MATCHER.match(notedata)
        matchvideo = MYVIDEO_MATCHER.match(notedata)
        matchvn = MYVIDEONOTE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end() :].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        elif matchsticker:
            content = notedata[matchsticker.end() :].strip()
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.STICKER,
                    file=content,
                )
        elif matchbtn:
            parse = notedata[matchbtn.end() :].strip()
            notedata = parse.split("<###button###>")[0]
            buttons = parse.split("<###button###>")[1]
            buttons = ast.literal_eval(buttons)
            if buttons:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.BUTTON_TEXT,
                    buttons=buttons,
                )
        elif matchfile:
            file = notedata[matchfile.end() :].strip()
            file = file.split("<###TYPESPLIT###>")
            notedata = file[1]
            content = file[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.DOCUMENT,
                    file=content,
                )
        elif matchphoto:
            photo = notedata[matchphoto.end() :].strip()
            photo = photo.split("<###TYPESPLIT###>")
            notedata = photo[1]
            content = photo[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.PHOTO,
                    file=content,
                )
        elif matchaudio:
            audio = notedata[matchaudio.end() :].strip()
            audio = audio.split("<###TYPESPLIT###>")
            notedata = audio[1]
            content = audio[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.AUDIO,
                    file=content,
                )
        elif matchvoice:
            voice = notedata[matchvoice.end() :].strip()
            voice = voice.split("<###TYPESPLIT###>")
            notedata = voice[1]
            content = voice[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VOICE,
                    file=content,
                )
        elif matchvideo:
            video = notedata[matchvideo.end() :].strip()
            video = video.split("<###TYPESPLIT###>")
            notedata = video[1]
            content = video[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO,
                    file=content,
                )
        elif matchvn:
            video_note = notedata[matchvn.end() :].strip()
            video_note = video_note.split("<###TYPESPLIT###>")
            notedata = video_note[1]
            content = video_note[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO_NOTE,
                    file=content,
                )
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="فشل استيراد هذه الملفات / الصور بسبب إنشائها"
                "من بوت آخر. هذا أحد قيود Telegram API ، ولا يمكن"
                "قد تم تحاشيه. آسف للإزعاج!",
            )


def __stats__():
    return f"× {sql.num_notes()} الملاحظات عبر {sql.num_chats()} محادثات."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"هناك `{len(notes)}` ملاحظات في هذه الدردشة."


__help__ = """
❂ /get <notename>*:* الحصول على الملاحظة بهذا الاسم
❂ #<notename>*:* مثل !get
❂ /notes or !saved*:* قائمة بجميع الملاحظات المحفوظة في هذه الدردشة
❂ /number *:* سوف يسحب ملاحظة هذا الرقم في القائمة
إذا كنت ترغب في استرداد محتويات ملاحظة بدون أي تنسيق ، فاستخدم `/get <notename> noformat`. This can \
تكون مفيدة عند تحديث ملاحظة حالية

*المشرفين فقط:*
❂ /save <notename> <notedata>*:* يحفظ الملاحظات كملاحظة بالاسم لاسم
يمكن إضافة زر إلى ملاحظة باستخدام صيغة ارتباط markdown القياسية - يجب أن يتم إضافة الرابط مسبقًا بامتداد \
`buttonurl:` القسم ، على هذا النحو: `[somelink](buttonurl:example.com)`. يفحص `!markdownhelp` لمزيد من المعلومات
❂ /save <notename>*:* حفظ الرسالة التي تم الرد عليها كملاحظة بالاسم والاسم
 ردود فرق منفصلة حسب `%%%` للحصول على ملاحظات عشوائية
 *مثال:*
 `!save notename
 Reply 1
 %%%
 Reply 2
 %%%
 Reply 3`
❂ /clear <notename>*:* ملاحظة واضحة بهذا الاسم
❂ /removeallnotes*:* يزيل كافة الملاحظات من المجموعة

 *Note:* أسماء الملاحظات غير حساسة لحالة الأحرف ، ويتم تحويلها تلقائيًا إلى أحرف صغيرة قبل حفظها.
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, run_async=True)
HASH_GET_HANDLER = MessageHandler(Filters.regex(r"^#[^\s]+"), hash_get, run_async=True)
SLASH_GET_HANDLER = MessageHandler(Filters.regex(r"^/\d+$"), slash_get, run_async=True)
SAVE_HANDLER = CommandHandler("save", save, run_async=True)
DELETE_HANDLER = CommandHandler("clear", clear, run_async=True)
LIST_HANDLER = DisableAbleCommandHandler(
    ["notes", "saved"], list_notes, admin_ok=True, run_async=True
)
CLEARALL = DisableAbleCommandHandler("removeallnotes", clearall, run_async=True)
CLEARALL_BTN = CallbackQueryHandler(clearall_btn, pattern=r"notes_.*", run_async=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
dispatcher.add_handler(SLASH_GET_HANDLER)
dispatcher.add_handler(CLEARALL)
dispatcher.add_handler(CLEARALL_BTN)
