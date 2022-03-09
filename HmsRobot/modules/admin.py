import html

from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html
from telethon import events
from telethon.tl import functions, types
from telethon import events
from telethon.errors import *
from telethon.tl import *
from telethon import *

from HmsRobot import DRAGONS, dispatcher, telethn as bot
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_pin,
    can_promote,
    connection_status,
    user_admin,
    ADMIN_CACHE,
)

from HmsRobot.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from HmsRobot.modules.log_channel import loggable
from HmsRobot.modules.helper_funcs.alternate import send_message

async def is_register_admin(chat, user):
    if isinstance(chat, (types.InputPeerChannel, types.InputChannel)):
        return isinstance(
            (
                await bot(functions.channels.GetParticipantRequest(chat, user))
            ).participant,
            (types.ChannelParticipantAdmin, types.ChannelParticipantCreator),
        )
    if isinstance(chat, types.InputPeerUser):
        return True
    
async def can_promote_users(message):
    result = await bot(
        functions.channels.GetParticipantRequest(
            channel=message.chat_id,
            user_id=message.sender_id,
        )
    )
    p = result.participant
    return isinstance(p, types.ChannelParticipantCreator) or (
        isinstance(p, types.ChannelParticipantAdmin) and p.admin_rights.ban_users
    )

async def can_ban_users(message):
    result = await bot(
        functions.channels.GetParticipantRequest(
            channel=message.chat_id,
            user_id=message.sender_id,
        )
    )
    p = result.participant
    return isinstance(p, types.ChannelParticipantCreator) or (
        isinstance(p, types.ChannelParticipantAdmin) and p.admin_rights.ban_users
    )

    

@bot.on(events.NewMessage(pattern="/users$"))
async def get_users(show):
    if not show.is_group:
        return
    if show.is_group:
        if not await is_register_admin(show.input_chat, show.sender_id):
            return
    info = await bot.get_entity(show.chat_id)
    title = info.title if info.title else "this chat"
    mentions = "Users in {}: \n".format(title)
    async for user in bot.iter_participants(show.chat_id):
        if not user.deleted:
            mentions += f"\n[{user.first_name}](tg://user?id={user.id}) {user.id}"
        else:
            mentions += f"\nحساب محذوف {user.id}"
    file = open("userslist.txt", "w+")
    file.write(mentions)
    file.close()
    await bot.send_file(
        show.chat_id,
        "userslist.txt",
        caption="Users in {}".format(title),
        reply_to=show.id,
    )
    os.remove("userslist.txt")


@bot_admin
@user_admin
def set_sticker(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if user_can_changeinfo(chat, user, context.bot.id) is False:
        return msg.reply_text("أنت تفتقد الحقوق لتغيير معلومات الدردشة!")

    if msg.reply_to_message:
        if not msg.reply_to_message.sticker:
            return msg.reply_text(
                "تحتاج إلى الرد على بعض الملصقات لتعيين مجموعة ملصقات الدردشة!"
            )
        stkr = msg.reply_to_message.sticker.set_name
        try:
            context.bot.set_chat_sticker_set(chat.id, stkr)
            msg.reply_text(f"نجح في تعيين ملصقات المجموعة الجديدة في {chat.title}!")
        except BadRequest as excp:
            if excp.message == "Participants_too_few":
                return msg.reply_text(
                    "عذرًا ، نظرًا لقيود التليجرام ، يجب ألا يقل عدد أعضاء الدردشة عن 100 عضو قبل أن يكون لديهم ملصقات جماعية!"
                )
            msg.reply_text(f"خطا! {excp.message}.")
    else:
        msg.reply_text("تحتاج إلى الرد على بعض الملصقات لتعيين مجموعة ملصقات الدردشة!")
       
    
@bot_admin
@user_admin
def setchatpic(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user

    if user_can_changeinfo(chat, user, context.bot.id) is False:
        msg.reply_text("أنت تفتقد الحق في تغيير معلومات المجموعة!")
        return

    if msg.reply_to_message:
        if msg.reply_to_message.photo:
            pic_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            pic_id = msg.reply_to_message.document.file_id
        else:
            msg.reply_text("يمكنك فقط تعيين بعض الصور كصورة دردشة!")
            return
        dlmsg = msg.reply_text("لحظة...")
        tpic = context.bot.get_file(pic_id)
        tpic.download("gpic.png")
        try:
            with open("gpic.png", "rb") as chatp:
                context.bot.set_chat_photo(int(chat.id), photo=chatp)
                msg.reply_text("نجح تعيين chatpic جديد!")
        except BadRequest as excp:
            msg.reply_text(f"خطا! {excp.message}")
        finally:
            dlmsg.delete()
            if os.path.isfile("gpic.png"):
                os.remove("gpic.png")
    else:
        msg.reply_text("قم بالرد على بعض الصور أو الملفات لتعيين صورة دردشة جديدة!")
        
@bot_admin
@user_admin
def rmchatpic(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user

    if user_can_changeinfo(chat, user, context.bot.id) is False:
        msg.reply_text("ليس لديك حقوق كافية لحذف صورة المجموعة")
        return
    try:
        context.bot.delete_chat_photo(int(chat.id))
        msg.reply_text("تم حذف صورة الملف الشخصي للدردشة بنجاح!")
    except BadRequest as excp:
        msg.reply_text(f"خطا! {excp.message}.")
        return
    
@bot_admin
@user_admin
def set_desc(update: Update, context: CallbackContext):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if user_can_changeinfo(chat, user, context.bot.id) is False:
        return msg.reply_text("أنت تفتقد الحقوق لتغيير معلومات الدردشة!")

    tesc = msg.text.split(None, 1)
    if len(tesc) >= 2:
        desc = tesc[1]
    else:
        return msg.reply_text("لن يؤدي تعيين الوصف الفارغ إلى أي شيء!")
    try:
        if len(desc) > 255:
            return msg.reply_text("يجب أن يكون الوصف أقل من 255 حرفًا!")
        context.bot.set_chat_description(chat.id, desc)
        msg.reply_text(f"تم تحديث وصف الدردشة بنجاح في {chat.title}!")
    except BadRequest as excp:
        msg.reply_text(f"خطا! {excp.message}.")        
        
@bot_admin
@user_admin
def setchat_title(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    args = context.args

    if user_can_changeinfo(chat, user, context.bot.id) is False:
        msg.reply_text("ليس لديك حقوق كافية لتغيير معلومات الدردشة!")
        return

    title = " ".join(args)
    if not title:
        msg.reply_text("أدخل بعض النص لتعيين عنوان جديد في الدردشة الخاصة بك!")
        return

    try:
        context.bot.set_chat_title(int(chat.id), str(title))
        msg.reply_text(
            f"تم الضبط بنجاح <b>{title}</b> كعنوان دردشة جديد!",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as excp:
        msg.reply_text(f"خطا! {excp.message}.")
        return
        
        
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def promote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = chat.get_member(user.id)

    if (
        not (promoter.can_promote_members or promoter.status == "creator")
        and user.id not in DRAGONS
    ):
        message.reply_text("ليس لديك الحقوق اللازمة للقيام بذلك!")
        return

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status in ('administrator', 'creator'):
        message.reply_text("كيف أقصد ترقية شخص يعمل كمسؤول بالفعل؟")
        return

    if user_id == bot.id:
        message.reply_text("لا أستطيع الترويج لنفسي! احصل على مسؤول للقيام بذلك من أجلي.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            # can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("لا يمكنني ترقية شخص ليس في المجموعة.")
        else:
            message.reply_text("حدث خطأ أثناء الترقية.")
        return

    bot.sendMessage(
        chat.id,
        f"تمت ترقيته بنجاح <b>{user_member.user.first_name or user_id}</b>!",
        parse_mode=ParseMode.HTML,
    )

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#PROMOTED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message

@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def midpromote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = chat.get_member(user.id)

    if (
        not (promoter.can_promote_members or promoter.status == "creator")
        and user.id not in DRAGONS
    ):
        message.reply_text("ليس لديك الحقوق اللازمة للقيام بذلك!")
        return

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status in ('administrator', 'creator'):
        message.reply_text("كيف أقصد ترقية شخص يعمل كمسؤول بالفعل؟")
        return

    if user_id == bot.id:
        message.reply_text("لا أستطيع الترويج لنفسي! احصل على مسؤول للقيام بذلك من أجلي.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            can_pin_messages=bot_member.can_pin_messages,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("لا يمكنني ترقية شخص ليس في المجموعة.")
        else:
            message.reply_text("حدث خطأ أثناء الترقية.")
        return

    bot.sendMessage(
        chat.id,
        f"تمت ترقيته بنجاح منتصف <b>{user_member.user.first_name or user_id}</b> with low rights!",
        parse_mode=ParseMode.HTML,
    )

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#MIDPROMOTED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message

@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def lowpromote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = chat.get_member(user.id)

    if (
        not (promoter.can_promote_members or promoter.status == "creator")
        and user.id not in DRAGONS
    ):
        message.reply_text("ليس لديك الحقوق اللازمة للقيام بذلك!")
        return

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status in ('administrator', 'creator'):
        message.reply_text("كيف أقصد ترقية شخص يعمل كمسؤول بالفعل؟")
        return

    if user_id == bot.id:
        message.reply_text("لا أستطيع الترويج لنفسي! احصل على مسؤول للقيام بذلك من أجلي.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("لا يمكنني ترقية شخص ليس في المجموعة.")
        else:
            message.reply_text("حدث خطأ أثناء الترقية.")
        return

    bot.sendMessage(
        chat.id,
        f"تمت ترقية منخفضة بنجاح <b>{user_member.user.first_name or user_id}</b> with low rights!",
        parse_mode=ParseMode.HTML,
    )

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#LOWPROMOTED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message


@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def fullpromote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = chat.get_member(user.id)

    if (
        not (promoter.can_promote_members or promoter.status == "creator")
        and user.id not in DRAGONS
    ):
        message.reply_text("ليس لديك الحقوق اللازمة للقيام بذلك!")
        return

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status in ('administrator', 'creator'):
        message.reply_text("كيف أقصد ترقية شخص يعمل كمسؤول بالفعل؟")
        return

    if user_id == bot.id:
        message.reply_text("لا أستطيع الترويج لنفسي! احصل على مسؤول للقيام بذلك من أجلي.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
            can_manage_voice_chats=bot_member.can_manage_voice_chats,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("لا يمكنني ترقية شخص ليس في المجموعة.")
        else:
            message.reply_text("حدث خطأ أثناء الترقية.")
        return

    message.reply_text(
        f"ترقيه كامله بكل الصلاحيات <b>{user_member.user.first_name or user_id}</b>"
        + f" with title <code>{title[:16]}</code>!",
        parse_mode=ParseMode.HTML,
    )

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#FULLPROMOTED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message

@bot.on(events.NewMessage(pattern="/middemote(?: |$)(.*)"))
async def middemote(dmod):
    if dmod.is_group:
        if not await can_promote_users(message=dmod):
            return
    else:
        return

    user = await get_user_from_event(dmod)
    if dmod.is_group:
        if not await is_register_admin(dmod.input_chat, user.id):
            await dmod.reply("**حبيبي ، لا أستطيع تخفيض رتبة غير المشرف**")
            return
    else:
        return

    if user:
        pass
    else:
        return

    # New rights after demotion
    newrights = ChatAdminRights(
        add_admins=False,
        invite_users=True,
        change_info=True,
        ban_users=False,
        delete_messages=True,
        pin_messages=True,
    )
    # Edit Admin Permission
    try:
        await bot(EditAdminRequest(dmod.chat_id, user.id, newrights, "Admin"))
        await dmod.reply("**منتصف التخفيض بنجاح!**")

    # If we catch BadRequestError from Telethon
    # Assume we don't have permission to demote
    except Exception:
        await dmod.reply("**فشل التخفيض.**")
        return

    
@bot.on(events.NewMessage(pattern="/lowdemote(?: |$)(.*)"))
async def lowdemote(dmod):
    if dmod.is_group:
        if not await can_promote_users(message=dmod):
            return
    else:
        return

    user = await get_user_from_event(dmod)
    if dmod.is_group:
        if not await is_register_admin(dmod.input_chat, user.id):
            await dmod.reply("**حبيبي ، لا أستطيع تخفيض رتبة غير المشرف**")
            return
    else:
        return

    if user:
        pass
    else:
        return

    # New rights after demotion
    newrights = ChatAdminRights(
        add_admins=False,
        invite_users=True,
        change_info=False,
        ban_users=False,
        delete_messages=True,
        pin_messages=False,
    )
    # Edit Admin Permission
    try:
        await bot(EditAdminRequest(dmod.chat_id, user.id, newrights, "Admin"))
        await dmod.reply("**خفض الرتبة بنجاح!**")

    # If we catch BadRequestError from Telethon
    # Assume we don't have permission to demote
    except Exception:
        await dmod.reply("**فشل التخفيض.**")
        return

    
@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
def demote(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status == "creator":
        message.reply_text("هذا الشخص هو من أنشأ الدردشة ، كيف سأخفض رتبتي؟")
        return

    if not user_member.status == "administrator":
        message.reply_text("لا يمكن تخفيض ما لم يتم ترقيته!")
        return

    if user_id == bot.id:
        message.reply_text("لا أستطيع أن أخفض مرتبة نفسي! احصل على مسؤول للقيام بذلك من أجلي.")
        return

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_voice_chats=False,
        )
        message.reply_text(
            f"خفض رتبته بنجاح <b>{user_member.user.first_name or user_id}</b>!",
            parse_mode=ParseMode.HTML,
        )

        log_message = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#DEMOTED\n"
            f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>مستخدم:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
        )

        return log_message
    except BadRequest:
        message.reply_text(
            "لا يمكن الخفض. قد لا أكون مسؤولاً ، أو أن حالة المسؤول تم تعيينها بواسطة شخص آخر"
            " مستخدم ، لذلك لا يمكنني العمل عليها!",
        )
        return


@user_admin
def refresh_admin(update, _):
    try:
        ADMIN_CACHE.pop(update.effective_chat.id)
    except KeyError:
        pass

    update.effective_message.reply_text("تم تحديث ذاكرة التخزين المؤقت للمسؤولين!")


@connection_status
@bot_admin
@can_promote
@user_admin
def set_title(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message

    user_id, title = extract_user_and_text(message, args)
    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if not user_id:
        message.reply_text(
            "يبدو أنك لا تشير إلى مستخدم أو أن المعرف المحدد غير صحيح ..",
        )
        return

    if user_member.status == "creator":
        message.reply_text(
            "هذا الشخص أنشأ الدردشة ، كيف يمكنني تعيين عنوان مخصص له؟",
        )
        return

    if user_member.status != "administrator":
        message.reply_text(
            "لا يمكن تعيين عنوان لغير المسؤولين!\nقم بترقيتهم أولاً لتعيين عنوان مخصص!",
        )
        return

    if user_id == bot.id:
        message.reply_text(
            "لا يمكنني تحديد لقبي بنفسي! احصل على الشخص الذي جعلني مشرفًا للقيام بذلك من أجلي.",
        )
        return

    if not title:
        message.reply_text("تعيين عنوان فارغ لا يفعل أي شيء!")
        return

    if len(title) > 16:
        message.reply_text(
            "طول العنوان أطول من 16 حرفًا.\nاختصارها إلى 16 حرفًا.",
        )

    try:
        bot.setChatAdministratorCustomTitle(chat.id, user_id, title)
    except BadRequest:
        message.reply_text(
            "إما أنه لم يتم الترويج لها بواسطتي أو قمت بتعيين نص عنوان يستحيل تعيينه."
        )
        return

    bot.sendMessage(
        chat.id,
        f"تم تعيين العنوان بنجاح لـ <code>{user_member.user.first_name or user_id}</code> "
        f"to <code>{html.escape(title[:16])}</code>!",
        parse_mode=ParseMode.HTML,
    )


@bot_admin
@can_pin
@user_admin
@loggable
def pin(update, context):
    bot, args = context.bot, context.args
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    is_group = chat.type not in ["private", "channel"]

    prev_message = update.effective_message.reply_to_message

    if user_can_pin(chat, user, bot.id) is False:
        message.reply_text("أنت تفتقد الحقوق لتثبيت رسالة!")
        return ""

    if not prev_message:
        message.reply_text("رد على الرسالة التي تريد تثبيتها!")
        return

    is_silent = True
    if len(args) >= 1:
        is_silent = (
            args[0].lower() != "notify"
            or args[0].lower() == "loud"
            or args[0].lower() == "violent"
        )

    if prev_message and is_group:
        try:
            bot.pinChatMessage(
                chat.id, prev_message.message_id, disable_notification=is_silent
            )
        except BadRequest as excp:
            if excp.message != "Chat_not_modified":
                raise
        return (
            "<b>{}:</b>"
            "\n#PINNED"
            "\n<b>مشرف:</b> {}".format(
                html.escape(chat.title), mention_html(user.id, user.first_name)
            )
        )

    return ""


@bot_admin
@can_pin
@user_admin
@loggable
def unpin(update, context):
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user_can_pin(chat, user, bot.id) is False:
        message.reply_text("تفتقد الحقوق اللازمة لإزالة تثبيت رسالة!")
        return ""

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        elif excp.message == "لم يتم العثور على رسالة لإلغاء التثبيت":
            message.reply_text(
                "لا يمكنني رؤية الرسالة المثبتة ، ربما تم إلغاء تثبيتها بالفعل ، أو تثبيت الرسالة القديمة!"
            )
        else:
            raise

    return (
        "<b>{}:</b>"
        "\n#UNPINNED"
        "\n<b>مشرف:</b> {}".format(
            html.escape(chat.title), mention_html(user.id, user.first_name)
        )
    )


@bot_admin
def pinned(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    msg = update.effective_message
    msg_id = update.effective_message.reply_to_message.message_id if update.effective_message.reply_to_message else update.effective_message.message_id

    chat = bot.getChat(chat_id=msg.chat.id)
    if chat.pinned_message:
        pinned_id = chat.pinned_message.message_id
        if msg.chat.username:
            link_chat_id = msg.chat.username
            message_link = (f"https://t.me/{link_chat_id}/{pinned_id}")
        elif (str(msg.chat.id)).startswith("-100"):
            link_chat_id = (str(msg.chat.id)).replace("-100", "")
            message_link = (f"https://t.me/c/{link_chat_id}/{pinned_id}")
            
        msg.reply_text(f'الرسالة المثبتة لـ {html.escape(chat.title)} is <a href="{message_link}">here</a>.', reply_to_message_id=msg_id, parse_mode=ParseMode.HTML, disable_web_page_preview=True,)
    else:
        msg.reply_text(f'لا توجد رسالة مثبتة في {html.escape(chat.title)}!')


@bot_admin
@user_admin
@connection_status
def invite(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat

    if chat.username:
        update.effective_message.reply_text(f"https://t.me/{chat.username}")
    elif chat.type in [chat.SUPERGROUP, chat.CHANNEL]:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text(
                "لا يمكنني الوصول إلى رابط الدعوة ، حاول تغيير أذوناتي!",
            )
    else:
        update.effective_message.reply_text(
            "يمكنني فقط أن أعطيك روابط دعوة للمجموعات الكبرى والقنوات ، آسف!",
        )


@connection_status
def adminlist(update, context):
    chat = update.effective_chat  # type: Optional[Chat] -> unused variable
    user = update.effective_user  # type: Optional[User]
    args = context.args  # -> unused variable
    bot = context.bot

    if update.effective_message.chat.type == "private":
        send_message(update.effective_message, "هذا الأمر يعمل فقط في المجموعات.")
        return

    chat = update.effective_chat
    chat_id = update.effective_chat.id
    chat_name = update.effective_message.chat.title  # -> unused variable

    try:
        msg = update.effective_message.reply_text(
            "إحضار مسؤولي المجموعة...",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        msg = update.effective_message.reply_text(
            "إحضار مسؤولي المجموعة...",
            quote=False,
            parse_mode=ParseMode.HTML,
        )

    administrators = bot.getChatAdministrators(chat_id)
    text = "مشرف في <b>{}</b>:".format(html.escape(update.effective_chat.title))

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title

        if user.first_name == "":
            name = "☠ حساب محذوف"
        else:
            name = "{}".format(
                mention_html(
                    user.id,
                    html.escape(user.first_name + " " + (user.last_name or "")),
                ),
            )

        if user.is_bot:
            administrators.remove(admin)
            continue

        # if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "creator":
            text += "\n 🌏 منشئ:"
            text += "\n<code> • </code>{}\n".format(name)

            if custom_title:
                text += f"<code> ┗━ {html.escape(custom_title)}</code>\n"

    text += "\n🌟 المدراء:"

    custom_admin_list = {}
    normal_admin_list = []

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title

        if user.first_name == "":
            name = "☠ حساب محذوف"
        else:
            name = "{}".format(
                mention_html(
                    user.id,
                    html.escape(user.first_name + " " + (user.last_name or "")),
                ),
            )
        # if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "administrator":
            if custom_title:
                try:
                    custom_admin_list[custom_title].append(name)
                except KeyError:
                    custom_admin_list.update({custom_title: [name]})
            else:
                normal_admin_list.append(name)

    for admin in normal_admin_list:
        text += "\n<code> • </code>{}".format(admin)

    for admin_group in custom_admin_list.copy():
        if len(custom_admin_list[admin_group]) == 1:
            text += "\n<code> • </code>{} | <code>{}</code>".format(
                custom_admin_list[admin_group][0],
                html.escape(admin_group),
            )
            custom_admin_list.pop(admin_group)

    text += "\n"
    for admin_group, value in custom_admin_list.items():
        text += "\n🚨 <code>{}</code>".format(admin_group)
        for admin in value:
            text += "\n<code> • </code>{}".format(admin)
        text += "\n"

    try:
        msg.edit_text(text, parse_mode=ParseMode.HTML)
    except BadRequest:  # if original message is deleted
        return


__help__ = """
*User Commands*:
❂ /admins*:* قائمة المسؤولين في الدردشة
❂ /pinned*:* للحصول على الرسالة المثبتة الحالية.
❂ /rules*:* احصل على قواعد هذه الدردشة.

*أوامر الترقية والتخفيض هي أوامر إدارية فقط*:
❂ /promote (user) (?admin's title)*:* يقوم بترقية المستخدم إلى مسؤول.
❂ /demote (user)*:* ينزل المستخدم من المسؤول.
❂ /lowpromote*:* قم بترقية عضو بحقوق منخفضة
❂ /midpromote*:* قم بترقية عضو بحقوق متوسطة
❂ /fullpromote*:* قم بترقية عضو بأقصى حقوق
❂ /lowdemote*:* خفض رتبة المسؤول إلى أذونات منخفضة
❂ /middemote*:* خفض رتبة المسؤول إلى أذونات متوسطة
 
*أوامر المنظف والتطهير هي للمشرفين فقط*:
❂ /del*:* يحذف الرسالة التي قمت بالرد عليها
❂ /purge*:* يحذف جميع الرسائل بين هذا والرسالة التي تم الرد عليها.
❂ /purge <integer X>*:* يحذف الرسالة التي تم الرد عليها ، والرسائل X التي تتبعها إذا تم الرد على رسالة.
❂ /zombies*:* تحسب عدد الحسابات المحذوفة في مجموعتك
❂ /kickthefools*:* طرد الأعضاء غير النشطين من المجموعة (أسبوع واحد)
  
*أوامر التثبيت وإلغاء التثبيت هي للمشرفين فقط*:
❂ /pin*:* قم بتثبيت الرسالة التي تم الرد عليها بصمت - أضف بصوت عالٍ أو إعلام لإعطاء تنبيهات للمستخدمين.
❂ /unpin*:* إلغاء تثبيت الرسالة المثبتة حاليًا - أضف الكل لإلغاء تثبيت جميع الرسائل المثبتة.
❂ /permapin*:* تثبيت رسالة مخصصة من خلال الروبوت. يمكن أن تحتوي هذه الرسالة على تخفيض السعر والأزرار وجميع الميزات الرائعة الأخرى.
❂ /unpinall*:* إلغاء تثبيت جميع الرسائل المثبتة.
❂ /antichannelpin <yes/no/on/off>*:* لا تدع التلغرام يثبت القنوات المرتبطة تلقائيًا. إذا لم يتم تقديم أي وسيطات ، فسيتم عرض الإعداد الحالي.
❂ /cleanlinked <yes/no/on/off>*:* احذف الرسائل المرسلة من القناة المرتبطة.
  
*سجل القناة هم مشرفون فقط*:
❂ /logchannel*:* الحصول على معلومات قناة السجل
❂ /setlog*:* ضبط قناة السجل.
❂ /unsetlog*:* قم بفك قناة السجل.
*يتم إعداد قناة السجل بواسطة*:
 ➩ إضافة الروبوت إلى القناة المطلوبة (كمسؤول!)
 ➩ إرسال /setlog الدخول في القناة
 ➩ إعادة توجيه / setlog إلى المجموعة
 
*Rules*:
❂ /setrules <your rules here>*:* وضع القواعد لهذه الدردشة.
❂ /clearrules*:* امسح قواعد هذه الدردشة.

*أوامر الآخرين هي للمشرفين فقط*:
❂ /invitelink*:* احصل على رابط الدعوة
❂ /title <title here>*:* يعيّن عنوانًا مخصصًا للمسؤول الذي روّج له الروبوت
❂ /reload*:* فرض تحديث قائمة المسؤولين
❂ /setgtitle <text>*:* تعيين عنوان المجموعة
❂ /setgpic*:* الرد على صورة لتعيينها كصورة جماعية
❂ /setdesc*:* تعيين وصف المجموعة
❂ /setsticker*:* تعيين ملصق المجموعة
"""

SET_DESC_HANDLER = CommandHandler("setdesc", set_desc, filters=Filters.chat_type.groups, run_async=True)
SET_STICKER_HANDLER = CommandHandler("setsticker", set_sticker, filters=Filters.chat_type.groups, run_async=True)
SETCHATPIC_HANDLER = CommandHandler("setgpic", setchatpic, filters=Filters.chat_type.groups, run_async=True)
RMCHATPIC_HANDLER = CommandHandler("delgpic", rmchatpic, filters=Filters.chat_type.groups, run_async=True)
SETCHAT_TITLE_HANDLER = CommandHandler("setgtitle", setchat_title, filters=Filters.chat_type.groups, run_async=True)

ADMINLIST_HANDLER = DisableAbleCommandHandler(["admins", "adminlist"], adminlist, run_async=True)

PIN_HANDLER = CommandHandler("pin", pin, filters=Filters.chat_type.groups, run_async=True)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.chat_type.groups, run_async=True)
PINNED_HANDLER = CommandHandler("pinned", pinned, filters=Filters.chat_type.groups, run_async=True)

INVITE_HANDLER = DisableAbleCommandHandler("invitelink", invite, run_async=True)

PROMOTE_HANDLER = DisableAbleCommandHandler("promote", promote, run_async=True)
FULLPROMOTE_HANDLER = DisableAbleCommandHandler("fullpromote", fullpromote, run_async=True)
LOW_PROMOTE_HANDLER = DisableAbleCommandHandler("lowpromote", lowpromote, run_async=True)
MID_PROMOTE_HANDLER = DisableAbleCommandHandler("midpromote", midpromote, run_async=True)
DEMOTE_HANDLER = DisableAbleCommandHandler("demote", demote, run_async=True)

SET_TITLE_HANDLER = CommandHandler("title", set_title, run_async=True)
ADMIN_REFRESH_HANDLER = CommandHandler("reload", refresh_admin, filters=Filters.chat_type.groups, run_async=True)

dispatcher.add_handler(SET_DESC_HANDLER)
dispatcher.add_handler(SET_STICKER_HANDLER)
dispatcher.add_handler(SETCHATPIC_HANDLER)
dispatcher.add_handler(RMCHATPIC_HANDLER)
dispatcher.add_handler(SETCHAT_TITLE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(PINNED_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(FULLPROMOTE_HANDLER)
dispatcher.add_handler(LOW_PROMOTE_HANDLER)
dispatcher.add_handler(MID_PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(SET_TITLE_HANDLER)
dispatcher.add_handler(ADMIN_REFRESH_HANDLER)

__mod_name__ = "Admins"
__command_list__ = [
    "setdesc"
    "setsticker"
    "setgpic"
    "delgpic"
    "setgtitle"
    "adminlist",
    "admins", 
    "invitelink", 
    "promote", 
    "fullpromote",
    "lowpromote",
    "midpromote",
    "demote", 
    "reload"
]
__handlers__ = [
    SET_DESC_HANDLER,
    SET_STICKER_HANDLER,
    SETCHATPIC_HANDLER,
    RMCHATPIC_HANDLER,
    SETCHAT_TITLE_HANDLER,
    ADMINLIST_HANDLER,
    PIN_HANDLER,
    UNPIN_HANDLER,
    PINNED_HANDLER,
    INVITE_HANDLER,
    PROMOTE_HANDLER,
    FULLPROMOTE_HANDLER,
    LOW_PROMOTE_HANDLER,
    MID_PROMOTE_HANDLER,
    DEMOTE_HANDLER,
    SET_TITLE_HANDLER,
    ADMIN_REFRESH_HANDLER,
]
