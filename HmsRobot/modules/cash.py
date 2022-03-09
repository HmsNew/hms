import requests

from telegram import Bot, Update
from telegram.ext import CommandHandler, run_async

from HmsRobot import dispatcher, CASH_API_KEY


def convert(bot: Bot, update: Update):

    args = update.effective_message.text.split(" ", 3)
    if len(args) > 1:

        orig_cur_amount = float(args[1])

        try:
            orig_cur = args[2].upper()
        except IndexError:
            update.effective_message.reply_text(
                "لقد نسيت ذكر رمز العملة."
            )
            return

        try:
            new_cur = args[3].upper()
        except IndexError:
            update.effective_message.reply_text(
                "لقد نسيت ذكر رمز العملة الذي تريد التحويل إليه."
            )
            return

        request_url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={orig_cur}&to_currency={new_cur}&apikey={CASH_API_KEY}"
        response = requests.get(request_url).json()
        try:
            current_rate = float(
                response["سعر صرف العملات الحقيقي"]["5. سعر الصرف"]
            )
        except KeyError:
            update.effective_message.reply_text(f"العملة غير مدعومة.")
            return
        new_cur_amount = round(orig_cur_amount * current_rate, 5)
        update.effective_message.reply_text(
            f"{orig_cur_amount} {orig_cur} = {new_cur_amount} {new_cur}"
        )
    else:
        update.effective_message.reply_text(__help__)


CONVERTER_HANDLER = CommandHandler("cash", convert, run_async=True)

dispatcher.add_handler(CONVERTER_HANDLER)

__command_list__ = ["cash"]
__handlers__ = [CONVERTER_HANDLER]
