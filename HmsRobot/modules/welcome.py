import html
import random
import re
import time
from functools import partial
from io import BytesIO
import HmsRobot.modules.sql.welcome_sql as sql
from HmsRobot import (
    DEV_USERS,
    OWNER_ID,
    DRAGONS,
    DEMONS,
    WOLVES,
    sw,
    LOGGER,
    dispatcher,
)
from HmsRobot.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from HmsRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from HmsRobot.modules.helper_funcs.msg_types import get_welcome_type
from HmsRobot.modules.helper_funcs.handlers import MessageHandlerChecker
from HmsRobot.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from HmsRobot.modules.log_channel import loggable
from HmsRobot.modules.sql.global_bans_sql import is_user_gbanned
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

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

VERIFIED_USER_WAITLIST = {}
CAPTCHA_ANS_DICT = {}

from multicolorcaptcha import CaptchaGenerator

# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = None
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_chat.send_message(
                markdown_parser(
                    (
                        backup_message
                        + "\nNote: الرسالة دي فيها عنوان url بايظ في الزراير. لازم تحديث."
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

        elif excp.message == "معندكش حقوق لإرسال رسالة":
            return
        elif excp.message == "لم يتم العثور على الرسالة التي تم الرد عليها":
            msg = update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                quote=False,
            )

        elif excp.message == "بروتوكول URL غير مدعوم":
            msg = update.effective_chat.send_message(
                markdown_parser(
                    (
                        backup_message
                        + "\nNote: تحتوي الرسالة الحالية على أزرار تستخدم بروتوكولات URL غير المدعومة بواسطة telegram. يرجى تحديث."
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

        elif excp.message == "مضيف عنوان url خاطئ":
            msg = update.effective_chat.send_message(
                markdown_parser(
                    (
                        backup_message
                        + "\nNote: الرسالة الحالية بها بعض عناوين url سيئة. يرجى تحديث."
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("لا يمكن التحليل! حصلت على أخطاء مضيف url غير صالحة")
        else:
            msg = update.effective_chat.send_message(
                markdown_parser(
                    (
                        backup_message
                        + "\nNote: حدث خطأ أثناء إرسال الرسالة المخصصة. يرجى تحديث."
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

            LOGGER.exception()
    return msg

@loggable
def new_member(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if sw is not None:
            sw_ban = sw.get_ban(new_mem.id)
            if sw_ban:
                return

        reply = update.message.message_id
        cleanserv = sql.clean_service(chat.id)
        # Clean service welcome
        if cleanserv:
            try:
                dispatcher.bot.delete_message(chat.id, update.message.message_id)
            except BadRequest:
                pass
            reply = False

        if should_welc:

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    f"اهلا بك في {html.escape(chat.title)} ملكي حبيبي", reply_to_message_id=reply
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"ملكي و حبيبي وصل اهو 🔥❤️"
                )
                continue

            # Welcome Devs
            if new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "قوم اقف يبني انت وهوا ! الأمير وصل اهو! 🌚🔥",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Sudos
            if new_mem.id in DRAGONS:
                update.effective_message.reply_text(
                    "اوعااا! الإمبراطور وصل اهو! كلو يضرب تعظيم سلام! 😂❤️",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Support
            if new_mem.id in DEMONS:
                update.effective_message.reply_text(
                    "هاه! واحد مع الكابتن وصل اهو! وسع للاشباح 😂❤️",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome WOLVES
            if new_mem.id in WOLVES:
                update.effective_message.reply_text(
                    "هييح عم الناس وصل اهو اصحو يبشر 😄🤍!", reply_to_message_id=reply
                )
                continue

            buttons = sql.get_welc_buttons(chat.id)
            keyb = build_keyboard(buttons)

            if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                media_wel = True

            first_name = (
                new_mem.first_name or "PersonWithNoName"
            )  # edge case of empty name - occurs for some bugs.

            if MessageHandlerChecker.check_user(update.effective_user.id):
                return

            if cust_welcome:
                if "%%%" in cust_welcome:
                    split = cust_welcome.split("%%%")
                    text = random.choice(split) if all(split) else cust_welcome
                else:
                    text = cust_welcome

                if cust_welcome == sql.DEFAULT_WELCOME_MESSAGES:
                    cust_welcome = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )

                if new_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {new_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_member_count()
                mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                if new_mem.username:
                    username = "@" + escape_markdown(new_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    text, VALID_WELCOME_FORMATTERS
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(new_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=new_mem.id,
                )

            else:
                res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name)
                )
                keyb = []

            backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                first=escape_markdown(first_name)
            )
            keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
            reply = None

        # User exceptions from welcomemutes
        if (
            is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id))
            or human_checks
        ):
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id and should_mute:
            if welc_mutes == "soft":
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_add_web_page_previews=False,
                    ),
                    until_date=(int(time.time() + 24 * 60 * 60)),
                )
            if welc_mutes == "strong":
                welcome_bool = False
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                            }
                        }
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                            }
                        }
                    )
                new_join_mem = (
                    f"[{escape_markdown(new_mem.first_name)}](tg://user?id={user.id})"
                )
                message = msg.reply_text(
                    f"{new_join_mem}, دوس علي الزرار عشان نتاكد انك انسان مش بوت يروحي ❤️.\nمعاك 120 ثانية.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            {
                                InlineKeyboardButton(
                                    text="ايوا  انا بني ادم 🙂😂.",
                                    callback_data=f"user_join_({new_mem.id})",
                                )
                            }
                        ]
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    ),
                )
                job_queue.run_once(
                    partial(check_not_bot, new_mem, chat.id, message.message_id),
                    120,
                    name="welcomemute",
                )
            if welc_mutes == "captcha":
                btn = []
                # Captcha image size number (2 -> 640x360)
                CAPCTHA_SIZE_NUM = 2
                # Create Captcha Generator object of specified size
                generator = CaptchaGenerator(CAPCTHA_SIZE_NUM)

                # Generate a captcha image
                captcha = generator.gen_captcha_image(difficult_level=3)
                # Get information
                image = captcha["image"]
                characters = captcha["characters"]
                # print(characters)
                fileobj = BytesIO()
                fileobj.name = f"captcha_{new_mem.id}.png"
                image.save(fp=fileobj)
                fileobj.seek(0)
                CAPTCHA_ANS_DICT[(chat.id, new_mem.id)] = int(characters)
                welcome_bool = False
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                                "captcha_correct": characters,
                            }
                        }
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                                "captcha_correct": characters,
                            }
                        }
                    )

                nums = [random.randint(1000, 9999) for _ in range(7)]
                nums.append(characters)
                random.shuffle(nums)
                to_append = []
                # print(nums)
                for a in nums:
                    to_append.append(
                        InlineKeyboardButton(
                            text=str(a),
                            callback_data=f"user_captchajoin_({chat.id},{new_mem.id})_({a})",
                        )
                    )
                    if len(to_append) > 2:
                        btn.append(to_append)
                        to_append = []
                if to_append:
                    btn.append(to_append)

                message = msg.reply_photo(
                    fileobj,
                    caption=f"Welcome [{escape_markdown(new_mem.first_name)}](tg://user?id={user.id}). حل اللغز يا اذكي اخواتك عشان افتحلك الشات 😹💔!",
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    ),
                )

        if welcome_bool:
            if media_wel:
                if ENUM_FUNC_MAP[welc_type] == dispatcher.bot.send_sticker:
                    sent = ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                    )
                else:
                    sent = ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        caption=res,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                        parse_mode="markdown",
                    )
            else:
                sent = send(update, res, keyboard, backup_message)
            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if welcome_log:
            return welcome_log

        if user.id == new_mem.id:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#USER_JOINED\n"
                f"<b>User</b>: {mention_html(user.id, user.first_name)}\n"
                f"<b>ID</b>: <code>{user.id}</code>"
            )
        elif new_mem.is_bot:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#BOT_ADDED\n"
                f"<b>Bot</b>: {mention_html(new_mem.id, new_mem.first_name)}\n"
                f"<b>ID</b>: <code>{new_mem.id}</code>"
            )
        else:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#USER_ADDED\n"
                f"<b>User</b>: {mention_html(new_mem.id, new_mem.first_name)}\n"
                f"<b>ID</b>: <code>{new_mem.id}</code>"
            )
        return welcome_log


def check_not_bot(member, chat_id, message_id, context):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop((chat_id, member.id))
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except:
            pass

        try:
            bot.edit_message_text(
                "*kicks user*\nانضم تاني للجروب و حاول تحل اللغز يا حبي 🌚❤️",
                chat_id=chat_id,
                message_id=message_id,
            )
        except:
            pass


def left_member(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    reply = update.message.message_id
    cleanserv = sql.clean_service(chat.id)
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False

    if should_goodbye:

        left_mem = update.effective_message.left_chat_member
        if left_mem:

            # Thingy for spamwatched users
            if sw is not None:
                sw_ban = sw.get_ban(left_mem.id)
                if sw_ban:
                    return

            # Dont say goodbyes to gbanned users
            if is_user_gbanned(left_mem.id):
                return

            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "الاه الدمعه هتفر من عيني كده تمشي 🙂 :(", reply_to_message_id=reply
                )
                return

            # Give the devs a special goodbye
            if left_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "طب بالسلامه انت بقا ابو تقل دم امك مبحبوش ابدا البني ادم دا 😂💔",
                    reply_to_message_id=reply,
                )
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type not in [sql.Types.TEXT, sql.Types.BUTTON_TEXT]:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = (
                left_mem.first_name or "PersonWithNoName"
            )  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE_MESSAGES:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                if left_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_member_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_mem.id,
                )
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                    first=first_name
                )
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(
                update,
                res,
                keyboard,
                random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )


@user_admin
def welcome(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            f"تم وضع الترحيب بنجاح للجروب يا كبير خلصانه 😹: `{pref}`.\n"
            f"*رساله الترحيب (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type in [sql.Types.BUTTON_TEXT, sql.Types.TEXT]:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, random.choice(sql.DEFAULT_WELCOME_MESSAGES))
        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](chat.id, cust_content, caption=welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP[welcome_type](
                    chat.id,
                    cust_content,
                    caption=welcome_m,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text(
                "تمام! هرحب بالأعضاء لما ينضمو خلصانه😌."
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text(
                "خلاص يبا مش مرحب بحد تاني انت حر بشوقك بقا 😔🧑‍🦯."
            )

        else:
            update.effective_message.reply_text(
                "فاهم 'on/yes' or 'off/no' only!"
            )


@user_admin
def goodbye(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            f"تم وضع رساله الوداع فالجروب 🙂🖤: `{pref}`.\n"
            f"*رساله الوداع هيا (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, random.choice(sql.DEFAULT_GOODBYE_MESSAGES))

        elif noformat:
            ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

        else:
            ENUM_FUNC_MAP[goodbye_type](
                chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN
            )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text(
                "فاهم 'on/yes' or 'off/no' only!"
            )


@user_admin
@loggable
def set_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("انت محددتش ارد ب ايه طيب لو سمحت يبا حدد عاوزني ارد بايه")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text("تم وضع رسالة ترحيب مخصوصة لاجلك يعمنا!")

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"يلا اعمل رساله ترحيب يصحبي."
    )


@user_admin
@loggable
def reset_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, None, random.choice(sql.DEFAULT_WELCOME_MESSAGES), sql.Types.TEXT)
    update.effective_message.reply_text(
        "تم إعادة وضع رسالة الترحيب إلى العادي فل عليك!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"لو عاوز ترجع رسالة الترحيب العاديه."
    )


@user_admin
@loggable
def set_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("انت محددتش ارد ب ايه طيب لو سمحت يبا حدد عاوزني ارد بايه")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("تم وضع رسالة وداع مخصوصة لاجلك يسيد الناس!")
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"يلا اعمل رساله وداع يقلبي."
    )


@user_admin
@loggable
def reset_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, random.choice(sql.DEFAULT_GOODBYE_MESSAGES), sql.Types.TEXT)
    update.effective_message.reply_text(
        "تم إعادة وضع رسالة الوداع إلى العادي خلوصه!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"يلا اعمل رساله وداع يقلبي."
    )


@user_admin
@loggable
def welcomemute(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("مش هكتم حد عند الانضمام خلاص!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"تم تبديل كتم صوت الترحيب إلى <b>OFF</b>."
            )
        if args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text(
                "هخلي محدش يبعت وسائط لمدة 24 ساعة."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"تم تبديل كتم صوت الترحيب إلى <b>SOFT</b>."
            )
        if args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text(
                "هبدا من دلوقتي بكتم الاعضاء المنضمين لحد ما يثبتوا أنهم مش بوتات.\nهيكون ليهم 120 ثانية قبل ما اطردهم."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"تم تبديل كتم صوت الترحيب إلى <b>STRONG</b>."
            )
        if args[0].lower() in ["captcha"]:
            sql.set_welcome_mutes(chat.id, "captcha")
            msg.reply_text(
                "هبدا من دلوقتي بكتم الاعضاء المنضمين لحد ما يثبتوا أنهم مش بوتات.\nلازم انهم يحلو اختبار CAPTCHA عشان الغي الكتم ."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"تم تبديل كتم صوت الترحيب إلى <b>CAPTCHA</b>."
            )
        msg.reply_text(
            "لو سمحت اختار `off`/`no`/`soft`/`strong`/`captcha`!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ""
    curr_setting = sql.welcome_mutes(chat.id)
    reply = (
        f"\n أعطني الإعداد!\nاختر واحدًا من: `off`/`no` or `soft`, `strong` or `captcha` only! \n"
        f"الإعداد الحالي: `{curr_setting}`"
    )
    msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    return ""


@user_admin
@loggable
def clean_welcome(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text(
                "لازم أحذف رسائل الترحيب الي بقالها يومين."
            )
        else:
            update.effective_message.reply_text(
                "مش هحذف دلوقتي رسائل الترحيب القديمة!"
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("سأحاول حذف رسائل الترحيب القديمة!")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"تم تبديل مرحبا نظيفا بـ <code>ON</code>."
        )
    if args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("لن أحذف رسائل الترحيب القديمة.")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"تم تبديل مرحبا نظيفا بـ <code>OFF</code>."
        )
    update.effective_message.reply_text("افهم 'on/yes' or 'off/no' only!")
    return ""


@user_admin
def cleanservice(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type == chat.PRIVATE:
        curr = sql.clean_service(chat.id)
        if curr:
            update.effective_message.reply_text(
                "نرحب بالخدمة النظيفة : on", parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.effective_message.reply_text(
                "نرحب بالخدمة النظيفة : off", parse_mode=ParseMode.MARKDOWN
            )

    elif len(args) >= 1:
        var = args[0]
        if var in ("no", "off"):
            sql.set_clean_service(chat.id, False)
            update.effective_message.reply_text("نرحب بالخدمة النظيفة : off")
        elif var in ("yes", "on"):
            sql.set_clean_service(chat.id, True)
            update.effective_message.reply_text("نرحب بالخدمة النظيفة : on")
        else:
            update.effective_message.reply_text(
                "خيار غير صالح", parse_mode=ParseMode.MARKDOWN
            )
    else:
        update.effective_message.reply_text(
            "الاستخدام on/yes or off/no", parse_mode=ParseMode.MARKDOWN
        )


def user_button(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        sql.set_human_checks(user.id, chat.id)
        member_dict = VERIFIED_USER_WAITLIST[(chat.id, user.id)]
        member_dict["status"] = True
        query.answer(text="ايوا يعم! أنت بني ادم اهو اخويا و حبيبي و ابن جهتي 😂 ، فتحتلك الشات ❤️!")
        bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        try:
            bot.deleteMessage(chat.id, message.message_id)
        except:
            pass
        if member_dict["should_welc"]:
            if member_dict["media_wel"]:
                sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                    member_dict["chat_id"],
                    member_dict["cust_content"],
                    caption=member_dict["res"],
                    reply_markup=member_dict["keyboard"],
                    parse_mode="markdown",
                )
            else:
                sent = send(
                    member_dict["update"],
                    member_dict["res"],
                    member_dict["keyboard"],
                    member_dict["backup_message"],
                )

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        query.answer(text="مش مسموحلك تعمل دا!")


def user_captcha_button(update: Update, context: CallbackContext):
    # sourcery no-metrics
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    # print(query.data)
    match = re.match(r"user_captchajoin_\(([\d\-]+),(\d+)\)_\((\d{4})\)", query.data)
    message = update.effective_message
    join_chat = int(match.group(1))
    join_user = int(match.group(2))
    captcha_ans = int(match.group(3))
    join_usr_data = bot.getChat(join_user)

    if join_user == user.id:
        c_captcha_ans = CAPTCHA_ANS_DICT.pop((join_chat, join_user))
        if c_captcha_ans == captcha_ans:
            sql.set_human_checks(user.id, chat.id)
            member_dict = VERIFIED_USER_WAITLIST[(chat.id, user.id)]
            member_dict["status"] = True
            query.answer(text="ايوا يعم! أنت بني ادم اهو اخويا و حبيبي و ابن جهتي 😂 ، فتحتلك الشات ❤️!")
            bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_send_polls=True,
                    can_change_info=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            try:
                bot.deleteMessage(chat.id, message.message_id)
            except:
                pass
            if member_dict["should_welc"]:
                if member_dict["media_wel"]:
                    sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                        member_dict["chat_id"],
                        member_dict["cust_content"],
                        caption=member_dict["res"],
                        reply_markup=member_dict["keyboard"],
                        parse_mode="markdown",
                    )
                else:
                    sent = send(
                        member_dict["update"],
                        member_dict["res"],
                        member_dict["keyboard"],
                        member_dict["backup_message"],
                    )

                prev_welc = sql.get_clean_pref(chat.id)
                if prev_welc:
                    try:
                        bot.delete_message(chat.id, prev_welc)
                    except BadRequest:
                        pass

                    if sent:
                        sql.set_clean_welcome(chat.id, sent.message_id)
        else:
            try:
                bot.deleteMessage(chat.id, message.message_id)
            except:
                pass
            kicked_msg = f"""
            ❌ [{escape_markdown(join_usr_data.first_name)}](tg://user?id={join_user}) طلع حمار و معرفش يحل اختبار  captcha طردتو 😹💔.
            """
            query.answer(text="إجابة خاطئة يا غبي 😹😜")
            res = chat.unban_member(join_user)
            if res:
                bot.sendMessage(
                    chat_id=chat.id, text=kicked_msg, parse_mode=ParseMode.MARKDOWN
                )

    else:
        query.answer(text="مش مسموحلك تعمل دا!")


WELC_HELP_TXT = (
    "يمكن تخصيص رسائل الترحيب / الوداع الخاصة بمجموعتك بعدة طرق. إذا كنت تريد الرسائل"
    " ليتم إنشاؤها بشكل فردي ، مثل رسالة الترحيب الافتراضية ، يمكنك استخدام *these* المتغيرات:\n"
    "  • `{first}`*:* هذا يمثل المستخدم *first* name\n"
    "  • `{last}`*:* هذا يمثل المستخدم *last* name. افتراضات إلى *first name* إذا لم يكن لدى المستخدم "
    "last name.\n"
    "  • `{fullname}`*:* هذا يمثل المستخدم *full* name. افتراضات إلى *first name* إذا لم يكن لدى المستخدم "
    "last name.\n"
    "  • `{username}`*:* هذا يمثل المستخدم *username*. افتراضات إلى a *mention* من المستخدم "
    "الاسم الأول إذا لم يكن له اسم مستخدم.\n"
    "  • `{mention}`*:* هذا ببساطة *mentions* المستخدم - وسمهم باسمهم الأول.\n"
    "  • `{id}`*:* هذا يمثل المستخدم *id*\n"
    "  • `{count}`*:* هذا يمثل المستخدم *رقم عضوية*.\n"
    "  • `{chatname}`*:* هذا يمثل المستخدم *اسم الدردشة الحالي*.\n"
    "\nيجب أن يكون كل متغير محاطًا بـ `{}` ليتم استبداله.\n"
    "تدعم رسائل الترحيب أيضًا ازرار ماركداون ، بحيث يمكنك عمل أي رساله تريدها bold/italic/code/links. "
    "يتم دعم الأزرار أيضًا ، لذا يمكنك جعل ترحيبك يبدو رائعًا مع بعض المقدمة اللطيفة "
    "الازرار.\n"
    f"لإنشاء زر يرتبط بقواعدك ، استخدم هذا: `[Rules](buttonurl://t.me/{dispatcher.bot.username}?start=group_id)`. "
    "ببساطة استبدل `group_id` بمعرف مجموعتك ، والذي يمكن الحصول عليه من خلال /id, وأنت جيد "
    "اذهب. لاحظ أن معرفات المجموعة مسبوقة عادةً بـ a `-` إشارة؛ هذا مطلوب ، لذا من فضلك لا "
    "أزلها.\n"
    "يمكنك حتى تعيين الصور / صور متحركة / مقاطع الفيديو / الرسائل الصوتية كرسالة ترحيب بواسطة "
    "الرد على الوسائط المرغوبة والدعوة `/setwelcome`."
)

WELC_MUTE_HELP_TXT = (
    "يمكنك جعل الروبوت يقوم بكتم صوت الأشخاص الجدد الذين ينضمون إلى مجموعتك وبالتالي منع المتطفلين من إغراق مجموعتك. "
    "الخيارات التالية ممكنة:\n"
    "  ➢ /welcomemute soft*:* يقيد الأعضاء الجدد من إرسال الوسائط لمدة 24 ساعة.\n"
    "  ➢ /welcomemute strong*:* كتم صوت الأعضاء الجدد حتى ينقروا على زر وبالتالي يتحققون من أنهم بشر.\n"
    "  ➢ /welcomemute captcha*:*  كتم صوت الأعضاء الجدد حتى يقوموا بحل رمز التحقق (captcha) وبالتالي التحقق من أنهم بشر.\n"
    "  ➢ /welcomemute off*:* يغلق welcomemute.\n"
    "*Note:* يطرد الوضع القوي المستخدم من الدردشة إذا لم يقم بالتحقق خلال 120 ثانية. يمكنهم دائمًا الانضمام مرة أخرى بالرغم من ذلك"
)


@user_admin
def welcome_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@user_admin
def welcome_mute_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN
    )


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, _):
    welcome_pref = sql.get_welc_pref(chat_id)[0]
    goodbye_pref = sql.get_gdbye_pref(chat_id)[0]
    return (
        "تم تعيين تفضيل الترحيب في هذه الدردشة على `{}`.\n"
        "وداعا هو التفضيل `{}`.".format(welcome_pref, goodbye_pref)
    )


__help__ = """
*المشرفين/AdminS:*
❂ /welcome <on/off>*:* تمكين / تعطيل رسائل الترحيب.
❂ /welcome*:* يعرض إعدادات الترحيب الحالية.
❂ /welcome noformat*:* يعرض إعدادات الترحيب الحالية ، بدون التنسيق - مفيد لإعادة استخدام رسائل الترحيب الخاصة بك!
❂ /goodbye*:* نفس الاستخدام و ضع في البدايه `/welcome`.
❂ /setwelcome <رساله ترحيبك>*:* تعيين رسالة ترحيب مخصصة. إذا يمكنك استخدام الوسائط الفيديو و الصور و الجيف ، قم بالرد علي الوسائط ب.
❂ /setgoodbye <رساله الوداع>*:* تعيين رسالة وداع مخصصة. إذا يمكنك استخدام الوسائط الفيديو و الصور و الجيف ، قم بالرد علي الوسائط ب.
❂ /resetwelcome*:* إعادة التعيين إلى رسالة الترحيب الافتراضية.
❂ /resetgoodbye*:* إعادة التعيين إلى رسالة الوداع الافتراضية.
❂ /cleanwelcome <on/off>*:* على العضو الجديد ، حاول حذف رسالة الترحيب السابقة لتجنب إرسال رسائل غير مرغوب فيها إلى الدردشة.
❂ /welcomemutehelp*:* يعطي معلومات حول كتم الترحيب.
❂ /cleanservice <on/off*:* يحذف البرقيات الترحيبية / رسائل الخدمة اليسرى.
 *مثال:*
انضم المستخدم إلى الدردشة ، وغادر المستخدم الدردشة.
*ترحيب بالماركداون:*
❂ /welcomehelp*:* عرض المزيد من معلومات التنسيق لرسائل الترحيب / الوداع المخصصة.
"""

NEW_MEM_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members, new_member, run_async=True
)
LEFT_MEM_HANDLER = MessageHandler(
    Filters.status_update.left_chat_member, left_member, run_async=True
)
WELC_PREF_HANDLER = CommandHandler(
    "welcome", welcome, filters=Filters.chat_type.groups, run_async=True
)
GOODBYE_PREF_HANDLER = CommandHandler(
    "goodbye", goodbye, filters=Filters.chat_type.groups, run_async=True
)
SET_WELCOME = CommandHandler(
    "setwelcome", set_welcome, filters=Filters.chat_type.groups, run_async=True
)
SET_GOODBYE = CommandHandler(
    "setgoodbye", set_goodbye, filters=Filters.chat_type.groups, run_async=True
)
RESET_WELCOME = CommandHandler(
    "resetwelcome", reset_welcome, filters=Filters.chat_type.groups, run_async=True
)
RESET_GOODBYE = CommandHandler(
    "resetgoodbye", reset_goodbye, filters=Filters.chat_type.groups, run_async=True
)
WELCOMEMUTE_HANDLER = CommandHandler(
    "welcomemute", welcomemute, filters=Filters.chat_type.groups, run_async=True
)
CLEAN_SERVICE_HANDLER = CommandHandler(
    "cleanservice", cleanservice, filters=Filters.chat_type.groups, run_async=True
)
CLEAN_WELCOME = CommandHandler(
    "cleanwelcome", clean_welcome, filters=Filters.chat_type.groups, run_async=True
)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help, run_async=True)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help, run_async=True)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(
    user_button, pattern=r"user_join_", run_async=True
)
CAPTCHA_BUTTON_VERIFY_HANDLER = CallbackQueryHandler(
    user_captcha_button,
    pattern=r"user_captchajoin_\([\d\-]+,\d+\)_\(\d{4}\)",
    run_async=True,
)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WELCOME_MUTE_HELP)
dispatcher.add_handler(CAPTCHA_BUTTON_VERIFY_HANDLER)

__mod_name__ = "Welcome"
__command_list__ = []
__handlers__ = [
    NEW_MEM_HANDLER,
    LEFT_MEM_HANDLER,
    WELC_PREF_HANDLER,
    GOODBYE_PREF_HANDLER,
    SET_WELCOME,
    SET_GOODBYE,
    RESET_WELCOME,
    RESET_GOODBYE,
    CLEAN_WELCOME,
    WELCOME_HELP,
    WELCOMEMUTE_HANDLER,
    CLEAN_SERVICE_HANDLER,
    BUTTON_VERIFY_HANDLER,
    CAPTCHA_BUTTON_VERIFY_HANDLER,
    WELCOME_MUTE_HELP,
]
