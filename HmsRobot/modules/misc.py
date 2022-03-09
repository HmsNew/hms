import time
import os
import re
import codecs
from typing import List
from random import randint
from HmsRobot.modules.helper_funcs.chat_status import user_admin
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot import (
    dispatcher,
    WALL_API,
)
import requests as r
import wikipedia
from requests import get, post
from telegram import (
    Chat,
    ChatAction,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Message,
    MessageEntity,
    TelegramError,
)
from telegram.error import BadRequest
from telegram.ext.dispatcher import run_async
from telegram.ext import CallbackContext, Filters, CommandHandler
from HmsRobot import StartTime
from HmsRobot.modules.helper_funcs.chat_status import sudo_plus
from HmsRobot.modules.helper_funcs.alternate import send_action, typing_action

MARKDOWN_HELP = f"""
Markdown هي أداة تنسيق قوية للغاية تدعمها Telegram {dispatcher.bot.first_name} لديه بعض التحسينات ، للتأكد من ذلك \
يتم تحليل الرسائل المحفوظة بشكل صحيح ، وللسماح لك بإنشاء أزرار.

❂ <code>_italic_</code>: سيؤدي التفاف النص بـ "_" إلى إنتاج نص مائل
❂ <code>*bold*</code>: سيؤدي التفاف النص بـ "*" إلى إنتاج نص غامق
❂ <code>`code`</code>: التفاف النص بـ  سينتج نصًا أحادي المسافة ، يُعرف أيضًا باسم "التعليمات البرمجية"
❂ <code>[sometext](someURL)</code>: سيؤدي هذا إلى إنشاء ارتباط - ستظهر الرسالة فقط <code>sometext</code>, \
والضغط عليها سيفتح الصفحة في <code>someURL</code>.
<b>مثال:</b><code>[test](example.com)</code>

❂ <code>[buttontext](buttonurl:someURL)</code>: هذا تحسين خاص للسماح للمستخدمين بالحصول على برقية \
أزرار في تخفيض السعر. <code>buttontext</code> سيكون ما يتم عرضه على الزر ، و <code>someurl</code> \
سيكون عنوان url الذي تم فتحه.
<b>مثال:</b> <code>[This is a button](buttonurl:example.com)</code>

إذا كنت تريد عدة أزرار على نفس الخط ، فاستخدم:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
سيؤدي هذا إلى إنشاء زرين على سطر واحد ، بدلاً من زر واحد في كل سطر.

ضع في اعتبارك أن رسالتك <b>MUST</b> تحتوي على بعض النصوص بخلاف مجرد زر!
"""


@user_admin
def echo(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if message.reply_to_message:
        message.reply_to_message.reply_text(
            args[1], parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    else:
        message.reply_text(
            args[1], quote=False, parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    message.delete()


def markdown_help_sender(update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "حاول إعادة توجيه الرسالة التالية إليّ ، وسترى ، واستخدم #test!"
    )
    update.effective_message.reply_text(
        "/save test This is a markdown test. _italics_, *bold*, code, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)"
    )


def markdown_help(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        update.effective_message.reply_text(
            "تواصل معي في شات البوت",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Markdown help",
                            url=f"t.me/{context.bot.username}?start=markdownhelp",
                        )
                    ]
                ]
            ),
        )
        return
    markdown_help_sender(update)


def wiki(update: Update, context: CallbackContext):
    kueri = re.split(pattern="wiki", string=update.effective_message.text)
    wikipedia.set_lang("en")
    if len(str(kueri[1])) == 0:
        update.effective_message.reply_text("أدخل الكلمات الرئيسية!")
    else:
        try:
            pertama = update.effective_message.reply_text("🔄 جار التحميل...")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🔧 مزيد من المعلومات...",
                            url=wikipedia.page(kueri).url,
                        )
                    ]
                ]
            )
            context.bot.editMessageText(
                chat_id=update.effective_chat.id,
                message_id=pertama.message_id,
                text=wikipedia.summary(kueri, sentences=10),
                reply_markup=keyboard,
            )
        except wikipedia.PageError as e:
            update.effective_message.reply_text(f"⚠ خطا: {e}")
        except BadRequest as et:
            update.effective_message.reply_text(f"⚠ خطا: {et}")
        except wikipedia.exceptions.DisambiguationError as eet:
            update.effective_message.reply_text(
                f"⚠ خطا\n هناك الكثير من الاستعلام! عبّر عنها أكثر!\nنتيجة الاستعلام المحتملة:\n{eet}"
            )


@send_action(ChatAction.UPLOAD_PHOTO)
def wall(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    msg_id = update.effective_message.message_id
    args = context.args
    query = " ".join(args)
    if not query:
        msg.reply_text("الرجاء إدخال استعلام!")
        return
    caption = query
    term = query.replace(" ", "%20")
    json_rep = r.get(
        f"https://wall.alphacoders.com/api2.0/get.php?auth={WALL_API}&method=search&term={term}"
    ).json()
    if not json_rep.get("نجاح"):
        msg.reply_text("حدث خطأ!")

    else:
        wallpapers = json_rep.get("wallpapers")
        if not wallpapers:
            msg.reply_text("لم يتم العثور على نتائج! حدد بحثك.")
            return
        index = randint(0, len(wallpapers) - 1)  # Choose random index
        wallpaper = wallpapers[index]
        wallpaper = wallpaper.get("url_image")
        wallpaper = wallpaper.replace("\\", "")
        context.bot.send_photo(
            chat_id,
            photo=wallpaper,
            caption="Preview",
            reply_to_message_id=msg_id,
            timeout=60,
        )
        context.bot.send_document(
            chat_id,
            document=wallpaper,
            filename="wallpaper",
            caption=caption,
            reply_to_message_id=msg_id,
            timeout=60,
        )


__help__ = """
*Available commands:*

❂ /markdownhelp*:* ملخص سريع لكيفية عمل تخفيض السعر في telegram - لا يمكن استدعاؤه إلا في المحادثات الخاصة
❂ /paste*:* يحفظ الرد على nekobin.com والرد مع عنوان url
❂ /react*:* يتفاعل مع تفاعل عشوائي
❂ /ud <word>*:* اكتب الكلمة أو التعبير الذي تريد البحث عنه
❂ /reverse*:* يقوم ببحث عكسي عن الصورة للوسائط التي تم الرد عليها.
❂ /wiki <query>*:* ويكيبيديا استفسارك
❂ /wall <query>*:* احصل على خلفية من wall.alphacoders.com
❂ /cash*:* محول العملات
 مثال:
 `!cash 1 USD INR`  
      _OR_
 `!cash 1 usd inr`
 Output: `1.0 USD = 75.505 INR`

"""

ECHO_HANDLER = DisableAbleCommandHandler(
    "echo", echo, filters=Filters.chat_type.groups, run_async=True)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, run_async=True)
WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
WALLPAPER_HANDLER = DisableAbleCommandHandler("wall", wall, run_async=True)

dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(WIKI_HANDLER)
dispatcher.add_handler(WALLPAPER_HANDLER)

__mod_name__ = "Extras"
__command_list__ = ["id", "echo", "wiki", "wall"]
__handlers__ = [
    ECHO_HANDLER,
    MD_HELP_HANDLER,
    WIKI_HANDLER,
    WALLPAPER_HANDLER,
]
