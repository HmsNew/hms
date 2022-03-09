import os
import subprocess
import sys

from contextlib import suppress
from time import sleep

import HmsRobot

from HmsRobot import dispatcher
from HmsRobot.modules.helper_funcs.chat_status import dev_plus
from telegram import TelegramError, Update
from telegram.error import Unauthorized
from telegram.ext import CallbackContext, CommandHandler


@dev_plus
def allow_groups(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        state = "تأمين هو " + "on" if not HmsRobot.ALLOW_CHATS else "off"
        update.effective_message.reply_text(f"الوضع الحالي: {state}")
        return
    if args[0].lower() in ["off", "no"]:
        HmsRobot.ALLOW_CHATS = True
    elif args[0].lower() in ["yes", "on"]:
        HmsRobot.ALLOW_CHATS = False
    else:
        update.effective_message.reply_text("Format: /lockdown Yes/No or Off/On")
        return
    update.effective_message.reply_text("منجز! تم تبديل قيمة التأمين.")


@dev_plus
def leave(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args
    if args:
        chat_id = str(args[0])
        try:
            bot.leave_chat(int(chat_id))
        except TelegramError:
            update.effective_message.reply_text(
                "لم أستطع مغادرة تلك المجموعة (لا أعرف لماذا).",
            )
            return
        with suppress(Unauthorized):
            update.effective_message.reply_text("بيب بوب ، تركت هذا الحساء !.")
    else:
        update.effective_message.reply_text("أرسل معرف دردشة صالحًا")


@dev_plus
def gitpull(update: Update, context: CallbackContext):
    sent_msg = update.effective_message.reply_text(
        "سحب جميع التغييرات من جهاز التحكم عن بُعد ثم محاولة إعادة التشغيل.",
    )
    subprocess.Popen("git pull", stdout=subprocess.PIPE, shell=True)

    sent_msg_text = sent_msg.text + "\n\nتم سحب التغييرات ... أعتقد .. إعادة التشغيل "

    for i in reversed(range(5)):
        sent_msg.edit_text(sent_msg_text + str(i + 1))
        sleep(1)

    sent_msg.edit_text("مستأنف.")

    os.system("restart.bat")
    os.execv("start.bat", sys.argv)


@dev_plus
def restart(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        "بدء مثيل جديد وإغلاق هذا المثال",
    )

    os.system("restart.bat")
    os.execv("start.bat", sys.argv)


LEAVE_HANDLER = CommandHandler("leave", leave, run_async=True)
GITPULL_HANDLER = CommandHandler("gitpull", gitpull, run_async=True)
RESTART_HANDLER = CommandHandler("reboot", restart, run_async=True)
ALLOWGROUPS_HANDLER = CommandHandler("lockdown", allow_groups, run_async=True)

dispatcher.add_handler(ALLOWGROUPS_HANDLER)
dispatcher.add_handler(LEAVE_HANDLER)
dispatcher.add_handler(GITPULL_HANDLER)
dispatcher.add_handler(RESTART_HANDLER)

__mod_name__ = "Dev"
__handlers__ = [LEAVE_HANDLER, GITPULL_HANDLER, RESTART_HANDLER, ALLOWGROUPS_HANDLER]
