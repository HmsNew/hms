import html
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot import dispatcher, DRAGONS
from HmsRobot.modules.helper_funcs.extraction import extract_user
from telegram.ext import CallbackContext, CallbackQueryHandler
import HmsRobot.modules.sql.approve_sql as sql
from HmsRobot.modules.helper_funcs.chat_status import user_admin
from HmsRobot.modules.log_channel import loggable
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.utils.helpers import mention_html
from telegram.error import BadRequest


@loggable
@user_admin
def approve(update, context):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "لا أعرف من الذي تتحدث عنه ، ستحتاج إلى تحديد مستخدم!",
        )
        return ""
    try:
        member = chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status in ("administrator", "creator"):
        message.reply_text(
            "المستخدم هو المسؤول بالفعل - لا تنطبق عليهم بالفعل عمليات التأمين وقوائم الحظر ومكافحة الغمر.",
        )
        return ""
    if sql.is_approved(message.chat_id, user_id):
        message.reply_text(
            f"[{member.user['first_name']}](tg://user?id={member.user['id']}) تمت الموافقة عليه بالفعل في {chat_title}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ""
    sql.approve(message.chat_id, user_id)
    message.reply_text(
        f"[{member.user['first_name']}](tg://user?id={member.user['id']}) تمت الموافقة عليه في {chat_title}! They will now be ignored by automated admin actions like locks, blocklists, and antiflood.",
        parse_mode=ParseMode.MARKDOWN,
    )
    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#APPROVED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    return log_message


@loggable
@user_admin
def disapprove(update, context):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "لا أعرف من الذي تتحدث عنه ، ستحتاج إلى تحديد مستخدم!",
        )
        return ""
    try:
        member = chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status in ("administrator", "creator"):
        message.reply_text("هذا المستخدم مسؤول ، ولا يمكن رفضه.")
        return ""
    if not sql.is_approved(message.chat_id, user_id):
        message.reply_text(f"{member.user['first_name']} لم تتم الموافقة بعد!")
        return ""
    sql.disapprove(message.chat_id, user_id)
    message.reply_text(
        f"{member.user['first_name']} لم يعد معتمدًا في {chat_title}.",
    )
    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNAPPROVED\n"
        f"<b>مشرف:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>مستخدم:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    return log_message


@user_admin
def approved(update, context):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    msg = "تمت الموافقة على المستخدمين التالية أسماؤهم.\n"
    approved_users = sql.list_approved(message.chat_id)
    for i in approved_users:
        member = chat.get_member(int(i.user_id))
        msg += f"- `{i.user_id}`: {member.user['first_name']}\n"
    if msg.endswith("approved.\n"):
        message.reply_text(f"لم تتم الموافقة على مستخدمين في {chat_title}.")
        return ""
    message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@user_admin
def approval(update, context):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id = extract_user(message, args)
    member = chat.get_member(int(user_id))
    if not user_id:
        message.reply_text(
            "لا أعرف من الذي تتحدث عنه ، ستحتاج إلى تحديد مستخدم!",
        )
        return ""
    if sql.is_approved(message.chat_id, user_id):
        message.reply_text(
            f"{member.user['first_name']} هو مستخدم معتمد. لن يتم تطبيق الأقفال ومقاومة الفيضان وقوائم الحظر عليهم.",
        )
    else:
        message.reply_text(
            f"{member.user['first_name']} ليس مستخدمًا معتمدًا. يتأثرون بالأوامر العادية.",
        )


def unapproveall(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in DRAGONS:
        update.effective_message.reply_text(
            "يمكن لمالك الدردشة فقط إلغاء الموافقة على جميع المستخدمين مرة واحدة.",
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Unapprove all users",
                        callback_data="unapproveall_user",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Cancel",
                        callback_data="unapproveall_cancel",
                    ),
                ],
            ],
        )
        update.effective_message.reply_text(
            f"هل أنت متأكد من رغبتك في عدم الموافقة على جميع المستخدمين في {chat.title}? لا يمكن التراجع عن هذا الإجراء.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


def unapproveall_btn(update: Update, context: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == "unapproveall_user":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            approved_users = sql.list_approved(chat.id)
            users = [int(i.user_id) for i in approved_users]
            for user_id in users:
                sql.disapprove(chat.id, user_id)
            message.edit_text("تم بنجاح عدم الموافقة على جميع المستخدمين في هذه الدردشة.")
            return

        if member.status == "administrator":
            query.answer("يمكن لمالك الدردشة فقط القيام بذلك.")

        if member.status == "member":
            query.answer("يجب أن تكون مشرفًا للقيام بذلك.")
    elif query.data == "unapproveall_cancel":
        if member.status == "creator" or query.from_user.id in DRAGONS:
            message.edit_text("تم إلغاء إزالة جميع المستخدمين المعتمدين.")
            return ""
        if member.status == "administrator":
            query.answer("يمكن لمالك الدردشة فقط القيام بذلك.")
        if member.status == "member":
            query.answer("يجب أن تكون مشرفًا للقيام بذلك.")


__help__ = """
في بعض الأحيان ، قد تثق في عدم قيام المستخدم بإرسال محتوى غير مرغوب فيه.
ربما لا يكون ذلك كافيًا لجعلهم مسؤولين ، لكنك قد تكون موافقًا على عدم تطبيق الأقفال والقوائم السوداء ومكافحة الغمر عليهم.

هذا هو الغرض من الموافقات - الموافقة على المستخدمين الجديرين بالثقة للسماح لهم بالإرسال

*Admin commands:*
❂ /approval*:* تحقق من حالة موافقة المستخدم في هذه الدردشة.
❂ /approve*:* موافقة المستخدم. لن يتم تطبيق الأقفال والقوائم السوداء ومقاومة الفيضان عليهم بعد الآن.
❂ /unapprove*:* عدم الموافقة على المستخدم. سيخضعون الآن للأقفال والقوائم السوداء ومقاومة الفيضان مرة أخرى.
❂ /approved*:* قائمة بجميع المستخدمين المعتمدين.
❂ /unapproveall*:* Unapprove *ALL* المستخدمين في الدردشة. هذا لا يمكن التراجع عنها.
"""

APPROVE = DisableAbleCommandHandler("approve", approve, run_async=True)
DISAPPROVE = DisableAbleCommandHandler("unapprove", disapprove, run_async=True)
APPROVED = DisableAbleCommandHandler("approved", approved, run_async=True)
APPROVAL = DisableAbleCommandHandler("approval", approval, run_async=True)
UNAPPROVEALL = DisableAbleCommandHandler("unapproveall", unapproveall, run_async=True)
UNAPPROVEALL_BTN = CallbackQueryHandler(
    unapproveall_btn, pattern=r"unapproveall_.*", run_async=True
)

dispatcher.add_handler(APPROVE)
dispatcher.add_handler(DISAPPROVE)
dispatcher.add_handler(APPROVED)
dispatcher.add_handler(APPROVAL)
dispatcher.add_handler(UNAPPROVEALL)
dispatcher.add_handler(UNAPPROVEALL_BTN)

__mod_name__ = "ApprovalS"
__command_list__ = ["approve", "unapprove", "approved", "approval"]
__handlers__ = [APPROVE, DISAPPROVE, APPROVED, APPROVAL]
