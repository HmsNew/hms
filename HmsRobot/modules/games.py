import html
import random
import time

from telegram import ParseMode, Update, ChatPermissions
from telegram.ext import CallbackContext, run_async
from telegram.error import BadRequest

import HmsRobot.modules.game_strings as game_strings
from HmsRobot import dispatcher
from HmsRobot.modules.disable import DisableAbleCommandHandler
from HmsRobot.modules.helper_funcs.chat_status import (is_user_admin)
from HmsRobot.modules.helper_funcs.extraction import extract_user


@run_async
def twet(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(game_strings.TWET_STRINGS))


@run_async
def saraha(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(game_strings.SARAHA_STRINGS))


@run_async
def tord(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(game_strings.TORD_STRINGS))

@run_async
def wyr(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(game_strings.WYR_STRINGS))


__help__ = """
❂ /twet *:* لعبه تويت اساله و تسليه و فيها قدها و احكام 💘
❂ /saraha *:* لعبه صراحه اساله صريحه و تسليه و احكام 🤍
  """

TWET_HANDLER = DisableAbleCommandHandler("twet", twet)
SARAHA_HANDLER = DisableAbleCommandHandler("saraha", saraha)
TORD_HANDLER = DisableAbleCommandHandler("tord", tord)
WYR_HANDLER = DisableAbleCommandHandler("rather", wyr)

dispatcher.add_handler(TWET_HANDLER)
dispatcher.add_handler(SARAHA_HANDLER)
dispatcher.add_handler(TORD_HANDLER)
dispatcher.add_handler(WYR_HANDLER)

__mod_name__ = "Games"
__command_list__ = [
   "twet", "saraha", "tord", "rather",
]

__handlers__ = [
    TWET_HANDLER, SARAHA_HANDLER, TORD_HANDLER, WYR_HANDLER,
]
