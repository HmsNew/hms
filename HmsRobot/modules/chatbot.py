# AI Chat (C) 2020-2021 by @InukaAsith

import emoji
import re
import aiohttp
from googletrans import Translator as google_translator
from pyrogram import filters
from aiohttp import ClientSession
from HmsRobot import BOT_USERNAME as bu
from HmsRobot import BOT_ID, pbot, arq
from HmsRobot.ex_plugins.chatbot import add_chat, get_session, remove_chat
from HmsRobot.utils.pluginhelper import admins_only, edit_or_reply

url = "https://acobot-brainshop-ai-v1.p.rapidapi.com/get"

translator = google_translator()


async def lunaQuery(query: str, user_id: int):
    luna = await arq.luna(query, user_id)
    return luna.result


def extract_emojis(s):
    return "".join(c for c in s if c in emoji.UNICODE_EMOJI)


async def fetch(url):
    try:
        async with aiohttp.Timeout(10.0):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    try:
                        data = await resp.json()
                    except:
                        data = await resp.text()
            return data
    except:
        print("AI response Timeout")
        return


ewe_chats = []
en_chats = []


@pbot.on_message(filters.command(["chatbot", f"chatbot@{bu}"]) & ~filters.edited & ~filters.bot & ~filters.private)
@admins_only
async def hmm(_, message):
    global ewe_chats
    if len(message.command) != 2:
        await message.reply_text("I only recognize /chatbot on and /chatbot off only")
        message.continue_propagation()
    status = message.text.split(None, 1)[1]
    chat_id = message.chat.id
    if status == "ON" or status == "on" or status == "On":
        lel = await edit_or_reply(message, "`معالجة...`")
        lol = add_chat(int(message.chat.id))
        if not lol:
            await lel.edit("تم تنشيط الذكاء الاصطناعي في نيورك بالفعل في هذه الدردشة")
            return
        await lel.edit(f"تم تنشيط الذكاء الاصتناعي لبوت نيورك المنشط بواسطة {message.from_user.mention()} للمستخدمين في {message.chat.title}")

    elif status == "OFF" or status == "off" or status == "Off":
        lel = await edit_or_reply(message, "`معالجة...`")
        Escobar = remove_chat(int(message.chat.id))
        if not Escobar:
            await lel.edit("نيورك لم يتم تنشيطي في هذه الدردشة")
            return
        await lel.edit(f"تم إلغاء تنشيط الذكاء الاصطناعي في نيورك بواسطة {message.from_user.mention()} للمستخدمين في {message.chat.title}")

    elif status == "EN" or status == "en" or status == "english":
        if not chat_id in en_chats:
            en_chats.append(chat_id)
            await message.reply_text(f"الدردشة الإنجليزية AI ممكنة بواسطة {message.from_user.mention()}")
            return
        await message.reply_text(f"الإنجليزية AI Chat معطل بواسطة {message.from_user.mention()}")
        message.continue_propagation()
    else:
        await message.reply_text("أنا فقط أدرك `/chatbot on` and `chatbot off` فقط")


@pbot.on_message(
    filters.text
    & filters.reply
    & ~filters.bot
    & ~filters.edited
    & ~filters.via_bot
    & ~filters.forwarded,
    group=2,
)
async def hmm(client, message):
    if not get_session(int(message.chat.id)):
        return
    if not message.reply_to_message:
        return
    try:
        senderr = message.reply_to_message.from_user.id
    except:
        return
    if senderr != BOT_ID:
        return
    msg = message.text
    chat_id = message.chat.id
    if msg.startswith("/") or msg.startswith("@"):
        message.continue_propagation()
    if chat_id in en_chats:
        test = msg
        test = test.replace("HmsRobot", "Aco")
        test = test.replace("HmsRobot", "Aco")
        test = test.replace("My god is @hms_01", "I'm a Christian")
        test = test.replace("16", "9")
        test = test.replace("@hms_01 is my husband.", "I'm single.")
        test = test.replace("My husband is @hms_01", "I'm single.")
        test = test.replace("@dd3mhms", "HmsRobotbot.ai")
        test = test.replace("I live in @dd3mhms.", "I live in San Francisco, California.")
        test = test.replace("I was created by @hms_01", "I made myself")
        test = test.replace(
            "Hello there I am HmsRobot...nice to meet u",
            "Hi, my friend! Do you want me to tell you a joke?")
        test = test.replace("@hms_01 is my owner", "Have the control right.")
        test = test.replace(
            "Hi, My name is HmsRobot Nice to meet you.",
            "Hi, my friend, what can I do for you today?")
        response = await lunaQuery(
            test, message.from_user.id if message.from_user else 0
        )
        response = response.replace("Aco", "HmsRobot")
        response = response.replace("aco", "HmsRobot")
        response = response.replace("Luna", "HmsRobot")
        response = response.replace("luna", "HmsRobot")
        response = response.replace("I'm a Christian", "My god is @hms_01")
        response = response.replace("9", "16")
        response = response.replace("I'm married to my job.", "I'm married with @hms_01")
        response = response.replace("I'm single.", "My husband is @hms_01")
        response = response.replace("HmsRobotbot.ai", "@dd3mhms")
        response = response.replace("I live in San Francisco, California.", "I live in @dd3mhms.")
        response = response.replace("I made myself", "I was Created by @hms_01")
        response = response.replace(
                "Hi, my friend! Do you want me to tell you a joke?",
                "Hello there I am HmsRobot...nice to meet u")
        response = response.replace("Have the control right.", "@hms_01 is my owner.")
        response = response.replace(
                "Hi, my friend, what can I do for you today?",
                "Hi, My name is HmsRobot Nice to meet you")

        pro = response
        try:
            await pbot.send_chat_action(message.chat.id, "typing")
            await message.reply_text(pro)
        except CFError:
            return

    else:
        u = msg.split()
        emj = extract_emojis(msg)
        msg = msg.replace(emj, "")
        if (
            [(k) for k in u if k.startswith("@")]
            and [(k) for k in u if k.startswith("#")]
            and [(k) for k in u if k.startswith("/")]
            and re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []
        ):

            h = " ".join(filter(lambda x: x[0] != "@", u))
            km = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", h)
            tm = km.split()
            jm = " ".join(filter(lambda x: x[0] != "#", tm))
            hm = jm.split()
            rm = " ".join(filter(lambda x: x[0] != "/", hm))
        elif [(k) for k in u if k.startswith("@")]:

            rm = " ".join(filter(lambda x: x[0] != "@", u))
        elif [(k) for k in u if k.startswith("#")]:
            rm = " ".join(filter(lambda x: x[0] != "#", u))
        elif [(k) for k in u if k.startswith("/")]:
            rm = " ".join(filter(lambda x: x[0] != "/", u))
        elif re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []:
            rm = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", msg)
        else:
            rm = msg
            # print (rm)
        try:
            lan = translator.detect(rm)
            lan = lan.lang
        except:
            return
        test = rm
        if not "en" in lan and not lan == "":
            try:
                test = translator.translate(test, dest="en")
                test = test.text
            except:
                return
        # test = emoji.demojize(test.strip())

        test = test.replace("HmsRobot", "Aco")
        test = test.replace("HmsRobot", "Aco")
        test = test.replace("My god is @hms_01", "I'm a Christian")
        test = test.replace("16", "9")
        test = test.replace("@hms_01 is my husband.", "I'm single.")
        test = test.replace("@dd3mhms", "HmsRobotbot.ai")
        test = test.replace("I live in @dd3mhms.", "I live in San Francisco, California")
        test = test.replace("I was created by @hms_01", "I made myself")
        test = test.replace(
            "Hello there I am HmsRobot...nice to meet u",
            "Hi, my friend! Do you want me to tell you a joke?")
        test = test.replace("@hms_01 is my owner", "Have the control right.")
        test = test.replace(
            "Hi, My name is HmsRobot Nice to meet you.",
            "Hi, my friend, what can I do for you today?")
        response = await lunaQuery(
            test, message.from_user.id if message.from_user else 0
        )
        response = response.replace("Aco", "HmsRobot")
        response = response.replace("aco", "HmsRobot")
        response = response.replace("Luna", "HmsRobot")
        response = response.replace("luna", "HmsRobot")
        response = response.replace("I'm a Christian", "My god is @hms_01")
        response = response.replace("9", "16")
        response = response.replace("I'm married to my job.", "I'm married with @hms_01")
        response = response.replace("I'm single.", "My husband is @hms_01")
        response = response.replace("HmsRobotbot.ai", "@dd3mhms")
        response = response.replace("I live in San Francisco, California.", "I live in @dd3mhms.")
        response = response.replace("I made myself", "I was Created by @hms_01")
        response = response.replace(
                "Hi, my friend! Do you want me to tell you a joke?",
                "Hello there I am HmsRobot...nice to meet u")
        response = response.replace("Have the control right.", "@hms_01 is my owner.")
        response = response.replace(
                "Hi, my friend, what can I do for you today?",
                "Hi, My name is HmsRobot Nice to meet you")
        pro = response
        if not "en" in lan and not lan == "":
            try:
                pro = translator.translate(pro, dest=lan)
                pro = pro.text
            except:
                return
        try:
            await pbot.send_chat_action(message.chat.id, "typing")
            await message.reply_text(pro)
        except CFError:
            return


@pbot.on_message(filters.text & filters.private & ~filters.edited & filters.reply & ~filters.bot)
async def inuka(client, message):
    msg = message.text
    if msg.startswith("/") or msg.startswith("@"):
        message.continue_propagation()
    u = msg.split()
    emj = extract_emojis(msg)
    msg = msg.replace(emj, "")
    if (
        [(k) for k in u if k.startswith("@")]
        and [(k) for k in u if k.startswith("#")]
        and [(k) for k in u if k.startswith("/")]
        and re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []
    ):

        h = " ".join(filter(lambda x: x[0] != "@", u))
        km = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", h)
        tm = km.split()
        jm = " ".join(filter(lambda x: x[0] != "#", tm))
        hm = jm.split()
        rm = " ".join(filter(lambda x: x[0] != "/", hm))
    elif [(k) for k in u if k.startswith("@")]:

        rm = " ".join(filter(lambda x: x[0] != "@", u))
    elif [(k) for k in u if k.startswith("#")]:
        rm = " ".join(filter(lambda x: x[0] != "#", u))
    elif [(k) for k in u if k.startswith("/")]:
        rm = " ".join(filter(lambda x: x[0] != "/", u))
    elif re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []:
        rm = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", msg)
    else:
        rm = msg
        # print (rm)
    try:
        lan = translator.detect(rm)
        lan = lan.lang
    except:
        return
    test = rm
    if not "en" in lan and not lan == "":
        try:
            test = translator.translate(test, dest="en")
            test = test.text
        except:
            return
    test = test.replace("HmsRobot", "Aco")
    test = test.replace("HmsRobot", "Aco")
    test = test.replace("My god is @hms_01", "I'm a Christian")
    test = test.replace("16", "9")
    test = test.replace("@hms_01 is my husband.", "I'm single.")
    test = test.replace("@dd3mhms", "HmsRobotbot.ai")
    test = test.replace("I live in @dd3mhms.", "I live in San Francisco, California.")
    test = test.replace("I was created by @hms_01", "I made myself")
    test = test.replace(
        "Hello there I am HmsRobot...nice to meet u",
        "Hi, my friend! Do you want me to tell you a joke?")
    test = test.replace("@hms_01 is my owner", "Have the control right.")
    test = test.replace(
        "Hi, My name is HmsRobot Nice to meet you.",
        "Hi, my friend, what can I do for you today?")

    response = await lunaQuery(test, message.from_user.id if message.from_user else 0)
    response = response.replace("Aco", "HmsRobot")
    response = response.replace("aco", "HmsRobot")
    response = response.replace("Luna", "HmsRobot")
    response = response.replace("luna", "HmsRobot")
    response = response.replace("I'm a Christian", "My god is @hms_01")
    response = response.replace("9", "16")
    response = response.replace("I'm married to my job.", "I'm married with @hms_01")
    response = response.replace("I'm single.", "My husband is @hms_01")
    response = response.replace("HmsRobotbot.ai", "@dd3mhms")
    response = response.replace("I live in San Francisco, California.", "I live in @dd3mhms")
    response = response.replace("I made myself", "I was Created by @hms_01")
    response = response.replace(
            "Hi, my friend! Do you want me to tell you a joke?",
            "Hello there I am HmsRobot...nice to meet u")
    response = response.replace("Have the control right.", "@hms_01 is my owner.")
    response = response.replace(
            "Hi, my friend, what can I do for you today?",
            "Hi, My name is HmsRobot Nice to meet you")

    pro = response
    if not "en" in lan and not lan == "":
        pro = translator.translate(pro, dest=lan)
        pro = pro.text
    try:
        await pbot.send_chat_action(message.chat.id, "typing")
        await message.reply_text(pro)
    except CFError:
        return


@pbot.on_message(filters.regex("HmsRobot|HmsRobot|robot|HmsRobot|sena") & ~filters.bot & ~filters.via_bot  & ~filters.forwarded & ~filters.reply & ~filters.channel & ~filters.edited)
async def inuka(client, message):
    msg = message.text
    if msg.startswith("/") or msg.startswith("@"):
        message.continue_propagation()
    u = msg.split()
    emj = extract_emojis(msg)
    msg = msg.replace(emj, "")
    if (
        [(k) for k in u if k.startswith("@")]
        and [(k) for k in u if k.startswith("#")]
        and [(k) for k in u if k.startswith("/")]
        and re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []
    ):

        h = " ".join(filter(lambda x: x[0] != "@", u))
        km = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", h)
        tm = km.split()
        jm = " ".join(filter(lambda x: x[0] != "#", tm))
        hm = jm.split()
        rm = " ".join(filter(lambda x: x[0] != "/", hm))
    elif [(k) for k in u if k.startswith("@")]:

        rm = " ".join(filter(lambda x: x[0] != "@", u))
    elif [(k) for k in u if k.startswith("#")]:
        rm = " ".join(filter(lambda x: x[0] != "#", u))
    elif [(k) for k in u if k.startswith("/")]:
        rm = " ".join(filter(lambda x: x[0] != "/", u))
    elif re.findall(r"\[([^]]+)]\(\s*([^)]+)\s*\)", msg) != []:
        rm = re.sub(r"\[([^]]+)]\(\s*([^)]+)\s*\)", r"", msg)
    else:
        rm = msg
        # print (rm)
    try:
        lan = translator.detect(rm)
        lan = lan.lang
    except:
        return
    test = rm
    if not "en" in lan and not lan == "":
        try:
            test = translator.translate(test, dest="en")
            test = test.text
        except:
            return

    # test = emoji.demojize(test.strip())

    test = test.replace("HmsRobot", "Aco")
    test = test.replace("HmsRobot", "Aco")
    test = test.replace("My god is @hms_01", "I'm a Christian")
    test = test.replace("16", "9") 
    test = test.replace("@hms_01 is my husband.", "I'm single.")
    test = test.replace("@dd3mhms", "HmsRobotbot.ai")
    test = test.replace("I live in @dd3mhms.", "I live in San Francisco, California.")
    test = test.replace("I was created by @hms_01", "I made myself")
    test = test.replace(
        "Hello there I am HmsRobot...nice to meet u",
        "Hi, my friend! Do you want me to tell you a joke?")
    test = test.replace("@hms_01 is my owner", "Have the control right.")
    test = test.replace(
        "Hi, My name is HmsRobot Nice to meet you.",
        "Hi, my friend, what can I do for you today?")
    response = await lunaQuery(test, message.from_user.id if message.from_user else 0)
    response = response.replace("Aco", "HmsRobot")
    response = response.replace("aco", "HmsRobot")
    response = response.replace("Luna", "HmsRobot")
    response = response.replace("luna", "HmsRobot")
    response = response.replace("I'm a Christian", "My god is @hms_01")
    response = response.replace("I'm married to my job.", "I'm married with @hms_01")
    response = response.replace("9", "16") 
    response = response.replace("I'm single.", "My husband is @hms_01")
    response = response.replace("HmsRobotbot.ai", "@dd3mhms")
    response = response.replace("I live in San Francisco, California.", "I live in @dd3mhms.")
    response = response.replace("I made myself", "I was Created by @hms_01")
    response = response.replace(
            "Hi, my friend! Do you want me to tell you a joke?",
            "Hello there I am HmsRobot...nice to meet u")
    response = response.replace("Have the control right.", "@hms_01 is my owner.")
    response = response.replace(
            "Hi, my friend, what can I do for you today?",
            "Hi, My name is HmsRobot Nice to meet you")

    pro = response
    if not "en" in lan and not lan == "":
        try:
            pro = translator.translate(pro, dest=lan)
            pro = pro.text
        except Exception:
            return
    try:
        await pbot.send_chat_action(message.chat.id, "typing")
        await message.reply_text(pro)
    except CFError:
        return


__help__ = """
➢ نيورك AI هو نظام الذكاء الاصطناعي الوحيد الذي يمكنه اكتشاف والرد على ما يصل إلى 200 لغة

❂/chatbot [ON/OFF]: يمكّن ويعطل وضع الدردشة بالذكاء الاصطناعي.
❂ /chatbot EN : تُمكّن روبوت المحادثة باللغة الإنجليزية فقط.
"""

__mod_name__ = "Chatbot"
