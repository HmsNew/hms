from gpytranslate import Translator
from telegram.ext import CommandHandler, CallbackContext
from telegram import (
    Message,
    Chat,
    User,
    ParseMode,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from HmsRobot import dispatcher, pbot
from pyrogram import filters
from HmsRobot.modules.disable import DisableAbleCommandHandler


__help__ = """ 
استخدم هذه الوحدة لترجمة الأشياء!
*أوامر:*
❂ /tl (or /tr): كرد على رسالة ، يترجمها إلى اللغة الإنجليزية.
❂ /tl <lang>: يترجم إلى <lang>
eg: /tl ja: يترجم إلى اليابانية.
❂ /tl <source>//<dest>: يترجم من <source> to <lang>.
eg:  !tl ja//en: يترجم من اليابانية إلى الإنجليزية.
❂ /langs: الحصول على قائمة باللغات المدعومة للترجمة.

يمكنني تحويل النص إلى صوت والصوت إلى نص ..
❂ /tts <lang code>*:* قم بالرد على أي رسالة للحصول على تحويل النص إلى كلام
❂ /stt*:* اكتب ردًا على رسالة صوتية (دعم اللغة الإنجليزية فقط) لاستخراج نص منها.
*رموز اللغة*
`af,am,ar,az,be,bg,bn,bs,ca,ceb,co,cs,cy,da,de,el,en,eo,es,
et,eu,fa,fi,fr,fy,ga,gd,gl,gu,ha,haw,hi,hmn,hr,ht,hu,hy,
id,ig,is,it,iw,ja,jw,ka,kk,km,kn,ko,ku,ky,la,lb,lo,lt,lv,mg,mi,mk,
ml,mn,mr,ms,mt,my,ne,nl,no,ny,pa,pl,ps,pt,ro,ru,sd,si,sk,sl,
sm,sn,so,sq,sr,st,su,sv,sw,ta,te,tg,th,tl,tr,uk,ur,uz,
vi,xh,yi,yo,zh,zh_CN,zh_TW,zu`
"""

__mod_name__ = "Translator"


trans = Translator()


@pbot.on_message(filters.command(["tl", "tr"]))
async def translate(_, message: Message) -> None:
    reply_msg = message.reply_to_message
    if not reply_msg:
        await message.reply_text("رد على رسالة لترجمتها!")
        return
    if reply_msg.caption:
        to_translate = reply_msg.caption
    elif reply_msg.text:
        to_translate = reply_msg.text
    try:
        args = message.text.split()[1].lower()
        if "//" in args:
            source = args.split("//")[0]
            dest = args.split("//")[1]
        else:
            source = await trans.detect(to_translate)
            dest = args
    except IndexError:
        source = await trans.detect(to_translate)
        dest = "en"
    translation = await trans(to_translate, sourcelang=source, targetlang=dest)
    reply = (
        f"<b>ترجمت من {source} to {dest}</b>:\n"
        f"<code>{translation.text}</code>"
    )

    await message.reply_text(reply, parse_mode="html")


def languages(update: Update, context: CallbackContext) -> None:
    update.effective_message.reply_text(
        "انقر فوق الزر أدناه لمشاهدة قائمة رموز اللغات المدعومة.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="رموز اللغة",
                        url="https://telegra.ph/Lang-Codes-03-19-3",
                    ),
                ],
            ],
            disable_web_page_preview=True,
        ),
    )


LANG_HANDLER = DisableAbleCommandHandler("langs", languages, run_async=True)

dispatcher.add_handler(LANG_HANDLER)
