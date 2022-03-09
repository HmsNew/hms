import html

from telegram.ext.filters import Filters
from telegram import Update, message, ParseMode
from telegram.ext import CallbackContext

from HmsRobot.modules.helper_funcs.decorators import HmsRobotcmd, HmsRobotmsg
from HmsRobot.modules.helper_funcs.channel_mode import user_admin, AdminPerms
from HmsRobot.modules.sql.antichannel_sql import antichannel_status, disable_antichannel, enable_antichannel

@HmsRobotcmd(command="antich", group=100)
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
def set_antichannel(update: Update, context: CallbackContext):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    if len(args) > 0:
        s = args[0].lower()
        if s in ["yes", "on"]:
            enable_antichannel(chat.id)
            message.reply_html("تمكين antichannel في {}".format(html.escape(chat.title)))
        elif s in ["off", "no"]:
            disable_antichannel(chat.id)
            message.reply_html("تعطيل antichannel في {}".format(html.escape(chat.title)))
        else:
            message.reply_text("حجج غير معترف بها {}".format(s))
        return
    message.reply_html(
        "إعداد Antichannel حاليًا {} في {}".format(antichannel_status(chat.id), html.escape(chat.title)))

@HmsRobotmsg(Filters.chat_type.groups, group=110)
def eliminate_channel(update: Update, context: CallbackContext):
    message = update.effective_message
    chat = update.effective_chat
    bot = context.bot
    if not antichannel_status(chat.id):
        return
    if message.sender_chat and message.sender_chat.type == "channel" and not message.is_automatic_forward:
        message.delete()
        sender_chat = message.sender_chat
        bot.ban_chat_sender_chat(sender_chat_id=sender_chat.id, chat_id=chat.id)
        
__help__ = """
──「 Anti-Channels 」──
    ⚠️ WARNING ⚠️
*إذا كنت تستخدم هذا الوضع ، فستكون النتيجة في المجموعة إلى الأبد ، ولا يمكنك الدردشة باستخدام القناة*
وضع Anti Channel Mode هو وضع لحظر المستخدمين الذين يتحدثون باستخدام القنوات تلقائيًا.
لا يمكن استخدام هذا الأمر إلا بواسطة *Admins*.
❂ /antich <'on'/'yes'> *:* تمكين anti-channel-mode
❂ /antich <'off'/'no'> *:* تعطيل anti-channel-mode
"""

__mod_name__ = "Anti-Channel"
