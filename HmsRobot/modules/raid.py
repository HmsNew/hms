import html
from typing import Optional
from datetime import timedelta
from HmsRobot import telethn as tbot

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from .log_channel import loggable
from .helper_funcs.anonymous import user_admin, AdminPerms
from .helper_funcs.chat_status import bot_admin, connection_status, user_admin_no_reply
from .helper_funcs.decorators import HmsRobotcmd, HmsRobotcallback
from HmsRobot import pbot, updater

import HmsRobot.modules.sql.welcome_sql as sql

j = updater.job_queue

# store job id in a dict to be able to cancel them later
RUNNING_RAIDS = {}  # {chat_id:job_id, ...}


def get_time(time: str) -> int:
    try:
        return timeparse(time)
    except BaseException:
        return 0


def get_readable_time(time: int) -> str:
    t = f"{timedelta(seconds=time)}".split(":")
    if time == 86400:
        return "1 day"
    return "{} hour(s)".format(t[0]) if time >= 3600 else "{} minutes".format(t[1])


@HmsRobotcmd(command="raid", pass_args=True)
@bot_admin
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def setRaid(update: Update, context: CallbackContext) -> Optional[str]:
    args = context.args
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    if chat.type == "private":
        context.bot.sendMessage(chat.id, "هذا الأمر غير متوفر في PMs.")
        return
    stat, time, acttime = sql.getRaidStatus(chat.id)
    readable_time = get_readable_time(time)
    if len(args) == 0:
        if stat:
            text = 'وضع الغارة حاليا <code>فتح</code>\nهل تريد أن <code>تعطيل</code> raid?'
            keyboard = [[
                InlineKeyboardButton("تعطيل وضع Raid", callback_data="disable_raid={}={}".format(chat.id, time)),
                InlineKeyboardButton("إلغاء الإجراء", callback_data="cancel_raid=1"),
            ]]
        else:
            text = f"وضع الغارة حاليا <code>تعطيل</code>\nهل تريد أن <code>فتح</code> " \
                   f"raid for {readable_time}?"
            keyboard = [[
                InlineKeyboardButton("تمكين وضع Raid", callback_data="enable_raid={}={}".format(chat.id, time)),
                InlineKeyboardButton("إلغاء الإجراء", callback_data="cancel_raid=0"),
            ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    elif args[0] == "off":
        if stat:
            sql.setRaidStatus(chat.id, False, time, acttime)
            j.scheduler.remove_job(RUNNING_RAIDS.pop(chat.id))
            text = "كان وضع الغارة <code>تعطيل</code>, الأعضاء الذين ينضمون لن يتم طردهم بعد الآن."
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#RAID\n"
                f"Disabled\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")

    else:
        args_time = args[0].lower()
        if time := get_time(args_time):
            readable_time = get_readable_time(time)
            if 300 <= time < 86400:
                text = f"وضع الغارة حاليا <code>تعطيل</code>\nهل تريد أن <code>فتح</code> " \
                       f"raid for {readable_time}? "
                keyboard = [[
                    InlineKeyboardButton("تمكين Raid", callback_data="enable_raid={}={}".format(chat.id, time)),
                    InlineKeyboardButton("إلغاء الإجراء", callback_data="cancel_raid=0"),
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            else:
                msg.reply_text("يمكنك فقط ضبط الوقت بين 5 دقائق ويوم واحد", parse_mode=ParseMode.HTML)

        else:
            msg.reply_text("أعطني وقتًا غير معروف ، أعطني شيئًا مثل 5m أو 1h", parse_mode=ParseMode.HTML)


@HmsRobotcallback(pattern="enable_raid=")
@connection_status
@user_admin_no_reply
@loggable
def enable_raid_cb(update: Update, ctx: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("enable_raid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = int(args[1])
    readable_time = get_readable_time(time)
    _, t, acttime = sql.getRaidStatus(chat_id)
    sql.setRaidStatus(chat_id, True, time, acttime)
    update.effective_message.edit_text(f"كان وضع الغارة <code>تمكين</code> for {readable_time}.",
                                       parse_mode=ParseMode.HTML)
    log.info("تم تمكين وضع الغارة في {} من أجل {}".format(chat_id, readable_time))
    try:
        oldRaid = RUNNING_RAIDS.pop(int(chat_id))
        j.scheduler.remove_job(oldRaid)  # check if there was an old job
    except KeyError:
        pass

    def disable_raid(_):
        sql.setRaidStatus(chat_id, False, t, acttime)
        log.info("تعطيل وضع الغارة في {}".format(chat_id))
        ctx.bot.send_message(chat_id, "تم تعطيل وضع Raid تلقائيًا!")

    raid = j.run_once(disable_raid, time)
    RUNNING_RAIDS[int(chat_id)] = raid.job.id
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RAID\n"
        f"Enabled for {readable_time}\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
    )


@HmsRobotcallback(pattern="disable_raid=")
@connection_status
@user_admin_no_reply
@loggable
def disable_raid_cb(update: Update, _: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("disable_raid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = args[1]
    _, _, acttime = sql.getRaidStatus(chat_id)
    sql.setRaidStatus(chat_id, False, time, acttime)
    j.scheduler.remove_job(RUNNING_RAIDS.pop(int(chat_id)))
    update.effective_message.edit_text(
        'كان وضع الغارة <code>تعطيل</code>, لن يتم طرد الأعضاء المنضمين حديثًا.',
        parse_mode=ParseMode.HTML,
    )
    logmsg = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RAID\n"
        f"Disabled\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
    )
    return logmsg


@HmsRobotcallback(pattern="cancel_raid=")
@connection_status
@user_admin_no_reply
def disable_raid_cb(update: Update, _: CallbackContext):
    args = update.callback_query.data.split("=")
    what = args[0]
    update.effective_message.edit_text(
        f"تم إلغاء الإجراء ، وسيظل وضع Raid <code>{'تمكين' if what == 1 else 'تعطيل'}</code>.",
        parse_mode=ParseMode.HTML)


@HmsRobotcmd(command="raidtime")
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def raidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, time, acttime = sql.getRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"تم ضبط وضع Raid حاليًا على {get_readable_time(time)}\nعند التبديل ، سيستمر وضع الغارة "
            f"for {get_readable_time(time)} ثم إيقاف تلقائيا",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"تم ضبط وضع Raid حاليًا على {readable_time}\nعند التبديل ، سيستمر وضع الغارة لمدة " \
                   f"{readable_time} ثم إيقاف تلقائيا"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setRaidStatus(chat.id, what, time, acttime)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#RAID\n"
                    f"اضبط وقت وضع Raid على {readable_time}\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("يمكنك فقط ضبط الوقت بين 5 دقائق ويوم واحد", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("أعطني وقتًا غير معروف ، أعطني شيئًا مثل 5m أو 1h", parse_mode=ParseMode.HTML)


@HmsRobotcmd(command="raidactiontime", pass_args=True)
@connection_status
@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def raidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, t, time = sql.getRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"تم تعيين وقت عمل الغارة حاليًا على {get_readable_time(time)}\nعند تبديل الأعضاء "
            f"سيتم حظر الانضمام مؤقتًا لـ {get_readable_time(time)}",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"تم تعيين وقت عمل الغارة حاليًا على {get_readable_time(time)}\nعند تبديل الأعضاء" \
                   f" سيتم حظر الانضمام مؤقتًا لـ {readable_time}"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setRaidStatus(chat.id, what, t, time)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#RAID\n"
                    f"اضبط وقت عمل وضع Raid على {readable_time}\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("يمكنك فقط ضبط الوقت بين 5 دقائق ويوم واحد", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("أعطني وقتًا غير معروف ، أعطني شيئًا مثل 5m أو 1h", parse_mode=ParseMode.HTML)




def get_help(chat):
    return gs(chat, "raid_help")


__mod_name__ = "AntiRaid"
