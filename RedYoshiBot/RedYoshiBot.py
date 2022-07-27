from operator import contains
from RedYoshiBot.server.CTGP7Requests import CTGP7Requests
import discord
import datetime
import random
import os
import io
import re
import sys
import time
import asyncio
import json
from .QRCrashDecode import QRCrashDecode
from .FunctionSearch import MK7FunctionSearch
from . import MKTranslationDownload
from .server.CTGP7ServerHandler import CTGP7ServerHandler
from .HomeMenuVersionList import HomeMenuVersionList
import hashlib
import sqlite3
import struct
from urllib.request import *
from urllib.error import *
from urllib.parse import urlparse
import traceback
import atexit

current_time_min = lambda: int(round(time.time() / 60))
SELF_BOT_MEMBER = None
SELF_BOT_SERVER = None
db_mng = None
ctgp7_server = None
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
debug_mode = False
current_talk_id = ''
miku_last_message_time = datetime.datetime.utcnow()

class ServerDatabase:
    global debug_mode
    global current_time_min
    def __init__(self):
        self.isTerminated = False
        self.conn = sqlite3.connect('RedYoshiBot/data/fc.sqlite')
        print('Addon "{}" loaded\n'.format(self.__class__.__name__))

    def terminate(self):
        global ctgp7_server
        if not (self.isTerminated):
            self.isTerminated = True
            self.conn.commit()
            self.conn.close()
            print('Addon "{}" unloaded\n'.format(self.__class__.__name__))
            try: # Python stupid, sometimes it undefines the ctgp7_server name...
                if (ctgp7_server is not None): 
                    ctgp7_server.terminate()
                    del ctgp7_server
            except NameError:
                traceback.print_exc()
                pass
    async def warn_set(self, memberid, value):
        c = self.conn.cursor()
        if(value == 0):
            c.execute('DELETE FROM usr_warns WHERE userid = ?', (int(memberid),))
            return
        rows = c.execute("SELECT * FROM usr_warns WHERE userid = ?", (int(memberid),))
        for row in rows:
            c.execute("UPDATE usr_warns SET warns = ? WHERE userid = ?", (value, int(memberid)))
            return
        c.execute('INSERT INTO usr_warns VALUES (?,?)', (int(memberid), int(value)))
    async def fact_add(self, memberid, fact):
        c = self.conn.cursor()
        c.execute('INSERT INTO facts VALUES (?,?)', (int(memberid), fact))
    async def fact_delete(self, id):
        c = self.conn.cursor()
        c.execute("DELETE FROM facts WHERE rowid = ?", (id,))
    async def fact_deleteuser(self, memberid):
        c = self.conn.cursor()
        c.execute("DELETE FROM facts WHERE userid = ?", (int(memberid),))
    async def fact_userreg(self, memberid):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM facts WHERE userid = ?", (int(memberid),))
        for row in rows:
            return True
        return False
    async def fact_get(self, withid):
        c = self.conn.cursor()
        rows = []
        if (withid == True):
            rows = c.execute("SELECT rowid,* FROM facts")
        else:
            rows = c.execute("SELECT * FROM facts")
        ret = []
        for row in rows:
            ret.append(row)
        return ret
    async def fact_get_byrow(self, row_id):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM facts WHERE rowid = ?", (row_id,))
        ret = []
        for row in rows:
            ret.append(row)
        return ret
    async def fact_getuser(self, memberid):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM facts WHERE userid = ?", (int(memberid),))
        for row in rows:
            return row[1]
        return None
    async def warn_get(self, memberid):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM usr_warns WHERE userid = ?", (int(memberid),))
        for row in rows:
            return int(row[1])
        return 0
    async def warn_get_all(self):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM usr_warns")
        return rows
    async def schedule_add(self, messageid, dest_id, amountmin, text):
        c = self.conn.cursor()
        c.execute('INSERT INTO sched_msg VALUES (?,?,?,?,?)', (int(messageid), int(dest_id), current_time_min(), amountmin, text))
    async def schedule_get(self):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM sched_msg")
        return rows
    async def schedule_del(self, messageid):
        c = self.conn.cursor()
        c.execute("DELETE FROM sched_msg WHERE botmsgid = ?", (int(messageid),))
    async def schedule_del_confirm(self, messageid):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM sched_msg WHERE botmsgid = ?", (int(messageid),))
        return_code = -1
        for row in rows:
            return_code = 1
        c.execute("DELETE FROM sched_msg WHERE botmsgid = ?", (int(messageid),))
        return return_code
    async def mute_apply(self, memberid, amountmin):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM usr_mute WHERE userid = ?", (int(memberid),))
        for row in rows:
            c.execute("UPDATE usr_mute SET start = ?, amount = ? WHERE userid = ?", (current_time_min(), amountmin, int(memberid)))
            return
        c.execute('INSERT INTO usr_mute VALUES (?,?,?)', (int(memberid),current_time_min(), amountmin))
    async def mute_get(self):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM usr_mute")
        return rows
    async def mute_remove(self, memberid):
        c = self.conn.cursor()
        c.execute('DELETE FROM usr_mute WHERE userid = ?', (int(memberid),))
    async def bug_add(self, authorid, explain, botmessage):
        c = self.conn.cursor()
        c.execute('INSERT INTO bugs VALUES (?,?,?,?)', (int(authorid), explain, int(botmessage.id), 1))
    async def bug_close(self, botmessageid):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM bugs WHERE botmsgid = ?", (int(botmessageid),))
        for row in rows:
            if(row[3] == 1):
                c.execute("UPDATE bugs SET state = ? WHERE botmsgid = ?", (0, int(botmessageid)))
                return row
            else:
                return []
        return []
    async def bug_count(self):
        c  =self.conn.cursor()
        cursor = c.execute("SELECT COUNT(*) FROM bugs")
        (tot_t,)=cursor.fetchone()
        cursor = c.execute("SELECT COUNT(*) FROM bugs WHERE state = 0")
        (clo_t,)=cursor.fetchone()
        ope_t = tot_t - clo_t
        return [ope_t, clo_t]
    async def get_cookie(self, user):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
        for row in rows:
            return row[1]
        return 0
    async def add_cookie(self, user, amount):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
        for row in rows:
            calc = row[1] + amount 
            if (calc < 0 ):
                calc = 0
            c.execute("UPDATE cookies SET amount = ? WHERE userid = ?", (calc, user))
            return
        if (amount < 0):
            amount = 0
        c.execute('INSERT INTO cookies VALUES (?,?)', (int(user), amount))
        return
    async def set_cookie(self, user, amount):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
        if (amount <= 0):
            amount = 0
        for row in rows:
            c.execute("UPDATE cookies SET amount = ? WHERE userid = ?", (amount, user))
            return
        c.execute('INSERT INTO cookies VALUES (?,?)', (int(user), amount))
        return
    async def top_ten_cookie(self):
        c = self.conn.cursor()
        return c.execute("SELECT * FROM cookies ORDER BY amount DESC limit 10")
    async def delete_cookie(self, user):
        c = self.conn.cursor()
        c.execute('DELETE FROM cookies WHERE userid = ?', (int(user),))
        return
    async def get_MikuTimes(self):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM miku_remove WHERE dummyid = ?", (0,))
        for row in rows:
            return int(row[1])
        return 0
    async def set_MikuTimes(self, value):
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM miku_remove WHERE dummyid = ?", (0,))
        for row in rows:
            c.execute("UPDATE miku_remove SET valuetimes = ? WHERE dummyid = ?", (int(value), 0))
            return
        c.execute('INSERT INTO miku_remove VALUES (?,?)', (0, int(value)))
    

class FakeMember:
    def __init__(self, memberID):
        self.id = int(memberID)
        self.name = "(ID: {})".format(self.id)
        self.mention = self.name
    def send(self, message):
        pass

def CreateFakeMember(memberID):
    ret = None
    try:
        ret = FakeMember(int(memberID))
    except:
        pass
    return ret

def get_retry_times ():
    try:
        with open("RedYoshiBot/data/retry.flag", "r") as f:
            data = f.read()
            ret = int(data)
            return ret
    except:
        set_retry_times(0)
        return 0

def set_retry_times(amount):
    with open("RedYoshiBot/data/retry.flag", "w") as f:
        f.write(str(amount))

def is_channel(message, ch_id):
    return (message.channel.id == ch_id)

def is_channel_private(channel):
    return isinstance(channel, discord.DMChannel)

def get_role(roleid):
    global SELF_BOT_SERVER
    roles = SELF_BOT_SERVER.roles
    for rol in roles:
        if(rol.id == roleid):
            return rol
    return None
def get_from_mention(mention):
    global SELF_BOT_SERVER
    global SELF_BOT_MEMBER
    
    mID = 0
    if (type(mention) is str):
        memberID = re.sub("\D", "", mention)
        try:
            mID = int(memberID)
        except:
            return None
    elif (type(mention) is int):
        mID = mention
    try:
        ret : discord.Member
        ret = client.get_guild(SERVER_ID()).get_member(mID)
        return ret
    except:
        return None

def itercount(iterable, count):
    checkcnt = 0
    for element in iterable:
        if element:
            checkcnt = checkcnt + 1
    return checkcnt >= count
def int_to_emoji(num):
    num = int(num)
    eml = NUMBER_EMOJI()
    if (num == 0):
        return eml[0]
    retstr = ""
    while (num != 0):
        retstr = eml[num % 10] + retstr
        num = int(num/10)
    return retstr

def int_to_rps(num):
    num = num % 3
    if (num == 0):
        return ":punch:"
    elif (num == 1):
        return ":hand_splayed:"
    return ":v:"

async def game_numberguess(user, machine, diff, message):
    global db_mng
    mach1 = int_to_emoji(int(machine/10))
    mach2 = int_to_emoji(machine % 10)
    i = 0
    game_message = await message.reply("You guessed: {} , I guessed: :question::question:".format(int_to_emoji(user)))
    randsec = random.randint(1, 3)
    while (i < randsec):
        await asyncio.sleep(1)
        i = i + 1 
    await game_message.edit(content="You guessed: {} , I guessed: {}:question:".format(int_to_emoji(user), mach1))
    randsec = random.randint(1, 3)
    while (i < randsec):
        await asyncio.sleep(1)
        i = i + 1
    await game_message.edit(content="You guessed: {} , I guessed: {}{}".format(int_to_emoji(user), mach1, mach2))
    if (user == machine):
        if diff == 0:
            await game_message.edit(content="You guessed: {} , I guessed: {}{} . **You won 10 <:yoshicookie:416533826869657600>!**".format( int_to_emoji(user), mach1, mach2))
            await db_mng.add_cookie(message.author.id, 10)
        elif diff == 1:
            await game_message.edit(content="You guessed: {} , I guessed: {}{} . **You won 50 <:yoshicookie:416533826869657600>!**".format( int_to_emoji(user), mach1, mach2))
            await db_mng.add_cookie(message.author.id, 50)
        elif diff == 2:
            await game_message.edit(content="You guessed: {} , I guessed: {}{} . **You won 100 <:yoshicookie:416533826869657600>!**".format( int_to_emoji(user), mach1, mach2))
            await db_mng.add_cookie(message.author.id, 100)
    else:
        await game_message.edit(content="You guessed: {} , I guessed: {}{} . **You lost 1 <:yoshicookie:416533826869657600>.**".format( int_to_emoji(user), mach1, mach2))
        await db_mng.add_cookie(message.author.id, -1)
    return
async def game_rps(bot_ch, usr_ch, message):
    ##0 - rock; 1 - paper; 2 - scissors
    state = 0 #0 lose; 1 match; 2 win
    bot_ch = bot_ch + 3
    usr_ch = usr_ch + 3
    winstr = "**You lost 1 <:yoshicookie:416533826869657600>.**"
    if (bot_ch == usr_ch):
        state = 1
        winstr = "**That's a match.**"
    elif (bot_ch % 3) == (usr_ch - 1) % 3:
        state  = 2
        winstr = "**You won 2 <:yoshicookie:416533826869657600>.**"
        await db_mng.add_cookie(message.author.id, 2)
    else:
        await db_mng.add_cookie(message.author.id, -1)
    await message.reply( "Your choice: {} , my choice: {} . {}".format(int_to_rps(usr_ch), int_to_rps(bot_ch), winstr))
    return

async def game_coin(bot_ch, usr_ch, message):
    choice_str = "head"
    if (usr_ch == 1):
        choice_str = "tails"
    bot_str = "head"
    if (bot_ch % 2 == 1):
        bot_str = "tails"
    if (bot_ch == 145):
        await message.reply( "You guessed: **{}** , the coin landed on its **side**. **How lucky! You won 500 <:yoshicookie:416533826869657600>.**".format( choice_str))
        await db_mng.add_cookie(message.author.id, 500)
    elif(bot_ch % 2 == usr_ch):
        await message.reply( "You guessed: **{}** , the coin landed on its **{}**. **You won 1 <:yoshicookie:416533826869657600>.**".format( choice_str, bot_str))
        await db_mng.add_cookie(message.author.id, 1)
    else:
        await message.reply( "You guessed: **{}** , the coin landed on its **{}**. **You lost 1 <:yoshicookie:416533826869657600>.**".format( choice_str, bot_str))
        await db_mng.add_cookie(message.author.id, -1)    
    return

def help_array():
    return {
        "ping": ">@RedYoshiBot ping\r\nPings the bot.",
        "membercount": ">@RedYoshiBot membercount\r\nDisplays the member count of the server.",
        "getwarn": ">@RedYoshiBot getwarn\nSends your warning amount in a DM.",
        "getmute": ">@RedYoshiBot getmute\nSends your muted time in a DM.",
        "fact": ">@RedYoshiBot fact (factID)\nDisplays a random fact. If factID is specified, the fact with that id will be displayed. (Use listfact to get all fact IDs.)",
        "addfact": ">@RedYoshiBot addfact (fact)\nAdds a fact (only one per user). Use lists between brackets {item1, item2, ...} to replace that part with a random choice from the list. List items may also have more nested lists.\n\nExamples:\n{Mario, Luigi, Yoshi} is number {NUMBER:1:3} -> Luigi is number 2\nI {hate, love} {{blue, yellow} cheese, apples, USER} {:wink:, :weary:} -> I love blue cheese :wink:\n\nNUMBER:X:Y -> Random number between X and Y\nUSER -> Random server member.",
        "delfact": ">@RedYoshiBot delfact\nRemoves your own fact.",
        "listfact": ">@RedYoshiBot listfact\nDisplays all facts.",
        "communities": ">@RedYoshiBot communities\nShows the main CTGP-7 communities.",
        "game": ">@RedYoshiBot game (gamemode) (options)\nPlays a game.",
        "report": "!report (Explanation)\nReports a bug with the given explanation. Can only be used in #bugs_discussion.",
        "bugcount": ">@RedYoshiBot bugcount\nShows the amount of open and closed bugs.",
        "getlang": ">@RedYoshiBot getlang (Language)\nGets the language file from the MK Translation Project spreadsheet. Can only be used by translators.",
        "parseqr": ">@RedYoshiBot parseqr [url]\nParses the CTGP-7 QR crash data from the image url. You can either specify the image url or attach the image to the message.",
        "funcname": ">@RedYoshiBot funcname (address) (region) (version)\nFinds the Mario Kart 7 function name for a given address, region and version combination.\n- address: Address to find in hex.\n- region: Region of the game (1 - EUR, 2 - USA, 3 - JAP).\n- version: Version of the game (1 - rev0 v1.1, 2 - rev1).",

        "server": ">@RedYoshiBot server (command) (options)\nRuns a server related command.\nUse \'@RedYoshiBot server help\' to get all the available server commands."
    }
def staff_help_array():
    return {
        "say": ">@RedYoshiBot say (channel/user) (text)\r\nSends a message in the specified channel or a DM if it is a user.",
        "edit": ">@RedYoshiBot edit (messageid) (text)\r\nEdits the specified message. Can only edit recent bot messages in the server.",
        "release": ">@RedYoshiBot release (version) (tag)\r\nAnnounces the release of the specified version (data taken from github) in #announcements. If (tag) is 1, it will tag @everyone (only tag everyone for major releases)",
        "restart": ">@RedYoshiBot restart\r\nRestarts the bot.",
        "stop": ">@RedYoshiBot stop\r\nStops the bot, once stopped is has to be manually started again from a terminal, so no way to start it from discord.",
        "mute": ">@RedYoshiBot mute (user) (amount)\r\nMutes an user for a certain amount. The amount can be m (minutes), h (hours), d (days) and y (years). For example: 2h, 12m, 7d, etc",
        "unmute": ">@RedYoshiBot unmute (user)\r\nUnmutes a muted user.",
        "warn": ">@RedYoshiBot warn (user) [Reason]\nGives a warning to an user. Reason is optional.",
        "ban": ">@RedYoshiBot ban (user) [Reason]\nSets warnings to 4 and bans the user.",
        "kick": ">@RedYoshiBot warn (user) [Reason]\nSets warnings to 3 and kicks the user",
        "setwarn": ">@RedYoshiBot setwarn (user) (amount) [Reason]\nSets the warning amount of an user. Reason is optional.",
        "getwarn": ">@RedYoshiBot getwarn [user]\nGets all the warned users or the warnings for the specified user.",
        "getmute": ">@RedYoshiBot getmute\nGets all the muted users.",
        "delfact": ">@RedYoshiBot delfact (id)\nDeletes specified fact.",
        "change_game": ">@RedYoshiBot change_game\nChanges the current playing game to a new random one.",
        "closebug": ">@RedYoshiBot closebug (bugID) [Reason]\nCloses the specified bug with the specified reason.",
        "schedule": ">@RedYoshiBot schedule (channel/user) (time_amount) (text)\nSchedules a message to be sent in/to the channel/user specified after time_amount has passed. (Works the same way as mute time amount).",
        "cancel_schedule": ">@RedYoshiBot cancel_schedule (scheduleid)\nCancels the specified scheduled message. The schedule id can be obtained from the id of the message sent by the bot.",
        "emergency": "!emergency\nEnables emergency mode.",
        "emergency_off": "!emergency_off\nDisables emergency mode.", 
        "talk": ">@RedYoshiBot talk (channel/user)\nSets the chat destination ID (don't specify an ID to clear the current one). Use `+` before a message to talk with the specified ID and `++` to talk and clear the destination ID afterwards."
    }
    
def staff_command_level():
    return {
        "say": 0,
        "edit": 0,
        "release": 0,
        "restart": -1,
        "stop": -1,
        "mute": 1,
        "unmute": 1,
        "warn": 1,
        "setwarn": 1,
        "ban": 1,
        "kick": 1,
        "getwarn": 1,
        "getmute": 1,
        "delfact": 1,
        "change_game": 1,
        "closebug": 1,
        "schedule": 0,
        "cancel_schedule": 0,
        "emergency": 1,
        "talk": 0,
        "help": 1,
        "showcookie": 1,
        "setcookie": 1,
        "listfact": 1,
        "addfact": 1,
        "game": 1
    }
    
def game_help_array():
    return {
        "guessanumber": ">@RedYoshiBot game guessanumber (easy/normal/hard) (number)\nGuess a number game.\n\neasy: Guess a number between 0 and 10 (Win: +10 yoshi cookies).\nnormal: Guess a number between 0 and 50 (Win: +50 yoshi cookies).\nhard: Guess a number between 0 and 99 (Win: +100 yoshi cookies).\nLose: -1 yoshi cookies.",
        "rps": ">@RedYoshiBot game rps (rock/paper/scissors)\nRock-Paper-Scissors.\n\nWin: +2 yoshi cookies.\nMatch: nothing.\nLose: -1 yoshi cookies.",
        "coin": ">@RedYoshiBot game coin (head/tails)\nFlip a coin.\n\nWin: +1 yoshi cookies.\nLose: -1 yoshi cookies.",
        "showcookie": ">@RedYoshiBot game showcookie\nShows your amount of yoshi cookies.",
        "top10": ">@RedYoshiBot game top10\nShows the top 10 users with the highest amount of yoshi cookies."
    }
def staff_game_help_array():
    return {
        "showcookie":">@RedYoshiBot game showcookie (user)\nShows the amount of yoshi cookies of the specified user.",
        "setcookie": ">@RedYoshiBot game setcookie (user) (amount)\nSets the amount of yoshi cookies of the specified user."
    }
# All the ids

# Main server
def ch_list():
    return {
        "ANN": 163072540061728768,
        "STAFF": 382885324575211523,
        "FRIEND": 163333095725072384,
        "DOORSTEP": 339476078244397056,
        "BOTCHAT": 324672297812099093,
        "BUGS": 315921603756163082,
        "BUG_OPEN": 426318663327547392,
        "BUG_CLOSE": 492231060919287834,
        "GENERAL_OFFTOPIC": 163074261903343616,
        "TRANSLATIONS": 633302999292444672,
        "STATS": 815663064560828457,
        "CTWW": 815663222946005022,
        "KICKS": 815663318365896724,
        "STAFFKICKS": 816640864994066434,
        "ONLINELOGS": 815663494945964072,
        "EMERGENCY": 839085550606614558,
        "PHISING": 882574850688950322
    }

def NUMBER_EMOJI():
    return [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:"]

def PLAYING_GAME():
    return ["Yoshi's Story", "Yoshi's Cookie", "Yoshi's Island", "Super Smash Bros.", "Mario Party 8", "Yoshi's Woolly World", "Mario Kart 7", "CTGP-R", "Yoshi Touch & Go"]

def role_list():
    return {
        "MUTE": 385544890030751754,
        "ADMIN": 222417567036342272,
        "MODERATOR": 315474999001612288,
        "STAFF": 383673430030942208,
        "CONTRIBUTOR": 326154532977377281,
        "COURSECREATOR": 325843915125030914,
        "BETAACCESS": 894352603830419506,
        # Roles with icons
        "PLAYER": 946727706005995561
    }

def SERVER_ID():
    return 163070769067327488

def EMERGENCY_SPECIAL_ROLES():
    return [
        608313379668623411, # Nitro boost
        389785433124634638, # Translators
        325843915125030914, # Course creator
        326154532977377281, # Contributor
        385544890030751754, # Muted
        # Roles with icons
        946727706005995561, # Player
    ]

def MIKU_EMOJI_ID():
    return 749336816745709648

# Test Server
"""
def ch_list():
    return {
        "ANN": 749237961928998912,
        "STAFF": 749237999811690516,
        "FRIEND": 749238058704044192,
        "DOORSTEP": 749237228248629308,
        "BOTCHAT": 749238108033122347,
        "BUGS": 749238142686724096,
        "BUG_OPEN": 749238165071724645,
        "BUG_CLOSE": 749238185132949574,
        "GENERAL_OFFTOPIC": 749238232700682260,
        "TRANSLATIONS": 749238264262688778,
        "STATS": 811222039503175710,
        "CTWW": 813073781912371241,
        "KICKS": 813408189684514876,
        "STAFFKICKS": 839229838485225512,
        "ONLINELOGS": 813408297524265000,
        "EMERGENCY": 839229978657816646
    }

def NUMBER_EMOJI():
    return [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:"]

def PLAYING_GAME():
     return ["Yoshi's Story", "Yoshi's Cookie", "Yoshi's Island", "Super Smash Bros.", "Mario Party 8", "Yoshi's Woolly World", "Mario Kart 7", "CTGP-R", "Yoshi Touch & Go"]

def role_list()["MUTE"]:
     return 749238545922654271

def role_list()["ADMIN"]:
    return 749238765351862282

def role_list()["MODERATOR"]:
    return 808687591331332117

def role_list()["CONTRIBUTOR"]:
    return 0

def role_list()["COURSECREATOR"]():
    return 0

def SERVER_ID():
    return 739825190456000567

def EMERGENCY_SPECIAL_ROLES():
    return []

def MIKU_EMOJI_ID():
    return 813179872327106601
"""
# Beta server
"""
def ch_list():
    return {
        "ANN": 813449380844666931,
        "STAFF": 813449124456038462,
        "FRIEND": 813449418145136650,
        "DOORSTEP": 813448803491119155,
        "BOTCHAT": 813449466773766164,
        "BUGS": 813448974647427152,
        "BUG_OPEN": 813448998677118976,
        "BUG_CLOSE": 813449069116522516,
        "GENERAL_OFFTOPIC": 813449510641991720,
        "TRANSLATIONS": 813449541210079252,
        "STATS": 813449585342677004,
        "CTWW": 813449624001314937,
        "KICKS": 813449821855416370,
        "ONLINELOGS": 813449844152598539
    }

def NUMBER_EMOJI():
    return [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:"]

def PLAYING_GAME():
     return ["Yoshi's Story", "Yoshi's Cookie", "Yoshi's Island", "Super Smash Bros.", "Mario Party 8", "Yoshi's Woolly World", "Mario Kart 7", "CTGP-R", "Yoshi Touch & Go"]

def role_list()["MUTE"]:
     return 813449937244127232

def role_list()["ADMIN"]:
    return 813450092437962813

def role_list()["MODERATOR"]:
    return 813450017343406130

def role_list()["CONTRIBUTOR"]:
    return 0

def role_list()["COURSECREATOR"]():
    return 0

def SERVER_ID():
    return 813443857114595399

def MUTABLE_CHANNELS():
    return [813448916698660915, 813448974647427152, 813449418145136650, 813449466773766164, 813449510641991720]

def MIKU_EMOJI_ID():
    return 813450615812259890
"""
COMMUNITIES_TEXT = "```Here are the main CTGP-7 communities:\n\nCustom Tracks: 29-1800-5228-2361\nCustom Tracks, 200cc: 52-3127-4613-8641\nNormal Tracks: 02-5770-2485-4638\nNormal Tracks, 200cc: 54-0178-4815-8814\n\nMake sure you are in 0.17.1 or greater to play in those communities.```"

def parsetime(timestr):
    try:
        basenum = float(timestr[0:-1])
        unit = timestr[-1:]
    except:
        return [-1, -1, " "]
    if(unit == "m"):
        return [basenum, basenum, "minutes"]
    elif(unit == "h"):
        return [basenum * 60, basenum, "hours"]
    elif(unit == "d"):
        return [basenum * 60 * 24, basenum, "days"]
    elif(unit == "y"):
        return [basenum * 60 * 24 * 365, basenum, "years"]
    else:
        return [-1, -1, " "]

async def staff_can_execute(message, command, silent=False):
    retVal = False
    if (is_channel(message, ch_list()["STAFF"])):
        moderatorRole = get_role(role_list()["MODERATOR"])
        adminRole = get_role(role_list()["ADMIN"])
        hasMod = moderatorRole in message.author.roles
        hasAdmin = (adminRole in message.author.roles) or message.author.id == SELF_BOT_SERVER.owner.id
        privilegeLevel = -1 if message.author.id == SELF_BOT_SERVER.owner.id else (0 if hasAdmin else (1 if hasMod else 2))
        try:
            retVal = staff_command_level()[command] >= privilegeLevel
        except:
            retVal = False
    if (not retVal and not silent):
        await message.reply("You don't have permission to do that!")
    return retVal

async def punish(member, amount, onRejoin=False):
    global client
    if (onRejoin):
        if(amount >= 4):
            try:
                await member.send("**CTGP-7 server:** You have been banned.")
            except:
                pass
            try:
                if (type(member) is not FakeMember):
                    await member.ban(delete_message_days=7)
            except:
                pass
    else:
        if(amount == 2):
            try:
                await member.send("**CTGP-7 server:** You have been muted for 1 day.")
            except:
                pass
            await mute_user(member.id, 1*24*60)
        elif(amount == 3):
            try:
                await member.send("**CTGP-7 server:** You have been kicked and muted 7 days, you may join again.")
            except:
                pass
            await mute_user(member.id, 7*24*60)
            try:
                if (type(member) is not FakeMember):
                    await member.kick()
            except:
                pass
        elif(amount >= 4):
            try:
                await member.send("**CTGP-7 server:** You have been banned.")
            except:
                pass
            try:
                if (type(member) is not FakeMember):
                    await member.ban(delete_message_days=7)
            except:
                pass

async def applyRole(memberID, roleID, atomic = False):
    try:
        user = get_from_mention(memberID)
        if (user is not None):
            role = get_role(roleID)
            await user.add_roles(role, atomic=atomic)
    except:
        pass

async def removeRole(memberID, roleID, atomic = False):
    try:
        user = get_from_mention(memberID)
        if (user is not None):
            role = get_role(roleID)
            await user.remove_roles(role, atomic=atomic)
    except:
        pass

async def mute_user(memberid, amount):
    global db_mng
    global client
    global SELF_BOT_SERVER
    await db_mng.mute_apply(memberid, amount)
    await applyRole(memberid, role_list()["MUTE"])

async def unmute_user(memberid):
    global db_mng
    global client
    global SELF_BOT_SERVER
    await db_mng.mute_remove(memberid)
    await removeRole(memberid, role_list()["MUTE"])
    muted_user = get_from_mention(memberid)
    if (muted_user is not None):
        try:
            await muted_user.send("**CTGP-7 server:** You have been unmuted.")
        except:
            pass

def checkdestvalid(dest_id):
    channel_id = int(re.sub("\D", "", dest_id))
    channel_obj = client.get_channel(channel_id)
    if (channel_obj != None):
        return channel_obj
    else:
        return get_from_mention(dest_id)

async def sayfunc(dest_id, text, chanOrMsg):
    sendFunc = None
    if (isinstance(chanOrMsg, discord.Message)):
        sendFunc = chanOrMsg.reply
    else:
        sendFunc = chanOrMsg.send
    if (text == ''):
        await sendFunc("Cannot send empty message.")
        return
    channel_id = int(re.sub("\D", "", dest_id))
    channel_obj = client.get_channel(channel_id)
    if (channel_obj != None):
        await channel_obj.trigger_typing()
        await asyncio.sleep(random.randint(1,5))
        await channel_obj.send(text)
        await sendFunc("Message successfully sent in {}.".format(channel_obj.name))
    else:
        member_obj = get_from_mention(dest_id)
        if (member_obj != None):
            try:
                await member_obj.trigger_typing()
                await asyncio.sleep(random.randint(1,5))
                await member_obj.send(text)
                await sendFunc("Message successfully sent to {}.".format(member_obj.name))
            except:
                await sendFunc("Can't send message to member (not in the server or blocked the bot).")
        else:
            await sendFunc("Invalid channel or member specified.")

async def fact_get_top_level_brakcets(s1):
    depth = 0
    index = 0
    startindex = -1
    for c in s1:
        if c == '{':
            if (depth == 0):
                startindex = index
            depth += 1
        elif c == '}':
            depth -= 1
            if (depth == 0):
                return [startindex, index]
            elif (depth < 0):
                break
        index += 1
    if (depth != 0):
        raise ValueError("Invalid fact format")
    
    return [-1, -1]

async def fact_get_top_level_split(s):
    balance = 0
    parts = []
    part = ''

    for c in s:
        part += c
        if c == '{':
            balance += 1
        elif c == '}':
            balance -= 1
            if (balance < 0):
                break
        elif c == ',' and balance == 0:
            parts.append(part[:-1].strip())
            part = ''
    
    if (balance != 0):
        raise ValueError("Invalid fact format: " + s)
    
    if len(part):
        parts.append(part.strip())

    return parts

async def fact_parse(s1):
    brackets = await fact_get_top_level_brakcets(s1)
    iterations = 0
    while (brackets[0] != -1 and iterations < 20):
        choicelist = await fact_get_top_level_split(s1[brackets[0] + 1:brackets[1]])
        choice = choicelist[random.randint(0, len(choicelist) - 1)]
        choice = choice.replace("==", " ")
        if (choice.startswith("NUMBER")):
            numbers = re.split("[:]", choice)
            choice = str(random.randint(int(numbers[1]),int(numbers[2])))
        elif (choice == "USER"):
            memberlist = list(SELF_BOT_SERVER.members)
            choice = memberlist[random.randint(0,len(memberlist) - 1)].name
        s1 = s1[0:brackets[0]] + choice + s1[brackets[1] + 1:]
        brackets = await fact_get_top_level_brakcets(s1)
        iterations += 1
    return s1

async def isfact_dynamic(s1):
    brackets = await fact_get_top_level_brakcets(s1)
    return brackets[0] != -1

async def muted_task():
    global db_mng
    global current_time_min
    while True:
        await asyncio.sleep(60)
        rows = await db_mng.mute_get()
        for row in rows:
            timeleft = (row[1] + row[2]) - current_time_min()
            if(timeleft <= 0):
                await unmute_user(row[0])
        tobedeleted = []
        rows = await db_mng.schedule_get()
        for row in rows:
            timeleft = (row[2] + row[3]) - current_time_min()
            if(timeleft <= 0):
                tobedeleted.append(row[0])
                staffchan = client.get_channel(ch_list()["STAFF"])
                await sayfunc(str(row[1]), row[4], staffchan)
        for delitm in tobedeleted:
            await db_mng.schedule_del(delitm)


async def perform_game_change():
    names = PLAYING_GAME()
    name = names[random.randint(0, len(names) - 1)]
    await client.change_presence(activity=discord.Game(name))
    return name

async def change_game():
    while True:
        await perform_game_change()
        await asyncio.sleep(600)

async def check_version_list():
    global db_mng
    keepChecking = True
    await asyncio.sleep(15)
    while True:
        if keepChecking:
            try:
                vList = HomeMenuVersionList()
                japV = vList.get_version_for_title(0x0004000E00030600)
                eurV = vList.get_version_for_title(0x0004000E00030700)
                usaV = vList.get_version_for_title(0x0004000E00030800)
                maxver = max(japV, eurV, usaV)
                if (maxver > 1040):
                    staffchan = client.get_channel(ch_list()["STAFF"])
                    msg = await staffchan.send("@everyone\nAn update for Mario Kart 7 has been detected! (Version: {})\nSending update message in #announcements in 10 minutes... (use the messageID from this message to cancel with @RedYoshiBot cancel_schedule)".format(maxver))
                    await db_mng.schedule_add(msg.id, ch_list()["ANN"], 10, "@everyone\nAn update for Mario Kart 7 has been detected!\n\n**DO NOT UPDATE MARIO KART 7 IF YOU WANT TO KEEP PLAYING CTGP-7.**\n\nPlease wait while we investigate this update.")
                    keepChecking = False
            except:
                pass
        await asyncio.sleep(60)

G_LAST_PUNISH_TIME = datetime.datetime(year=2000, month=1, day=1)
G_LAST_PUNISH_AMOUNT = 0
def checkCanPunish(warnamount):
    global G_LAST_PUNISH_TIME
    global G_LAST_PUNISH_AMOUNT
    if (warnamount < 3):
        return True
    if (datetime.datetime.now() - G_LAST_PUNISH_TIME <= datetime.timedelta(hours=4)):
        if (G_LAST_PUNISH_AMOUNT >= 9):
            return False
        else:
            G_LAST_PUNISH_AMOUNT += 1
            return True
    else:
        G_LAST_PUNISH_TIME = datetime.datetime.now()
        G_LAST_PUNISH_AMOUNT = 0
        return True


async def enableEmergency():
    
    emerchn = client.get_channel(ch_list()["EMERGENCY"])
    emerstr = ":rotating_light: " * 16 + "\n\n"
    emerstr += "Emergency mode has been enabled by the server staff.\n"
    emerstr += "Please wait until staff addresses the issue.\n"
    emerstr += "For any urgent matter, send a Direct Message to PabloMK7.\n"
    emerstr += "\nSorry for the incovenience.\n"
    emerstr += "- CTGP-7 Staff\n\n"
    emerstr += ":rotating_light: " * 16 + "\n"
    await emerchn.send(emerstr)

    emeroverwrite = emerchn.overwrites_for(SELF_BOT_SERVER.default_role)
    emeroverwrite.read_messages = True
    await emerchn.set_permissions(SELF_BOT_SERVER.default_role, overwrite=emeroverwrite)

    targetroles = [SELF_BOT_SERVER.default_role]
    for rID in EMERGENCY_SPECIAL_ROLES():
        targetroles.append(SELF_BOT_SERVER.get_role(rID))
    for role in targetroles:
        roleperm = role.permissions
        roleperm.read_messages = False
        await role.edit(permissions=roleperm)
    
    staffchn = client.get_channel(ch_list()["STAFF"])
    await staffchn.send("@everyone, emergency mode has been enabled!")

async def disableEmergency():
    
    targetroles = [SELF_BOT_SERVER.default_role]
    for rID in EMERGENCY_SPECIAL_ROLES():
        targetroles.append(SELF_BOT_SERVER.get_role(rID))
    for role in targetroles:
        roleperm = role.permissions
        roleperm.read_messages = True
        await role.edit(permissions=roleperm)

    emerchn = client.get_channel(ch_list()["EMERGENCY"])
    emeroverwrite = emerchn.overwrites_for(SELF_BOT_SERVER.default_role)
    emeroverwrite.read_messages = False
    await emerchn.set_permissions(SELF_BOT_SERVER.default_role, overwrite=emeroverwrite)

    async for m in emerchn.history(limit=200):
        await m.delete()
    
    staffchn = client.get_channel(ch_list()["STAFF"])
    await staffchn.send("Emergency mode has been disabled.")

async def sendMikuMessage(message):
    global db_mng
    global miku_last_message_time
    mikuem = client.get_emoji(MIKU_EMOJI_ID())
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
    numbTimes = await db_mng.get_MikuTimes()
    await db_mng.set_MikuTimes(numbTimes + 1)
    try:
        if (datetime.datetime.utcnow() - miku_last_message_time > datetime.timedelta(seconds=5)):
            emb = discord.Embed(description="For the {} time,\nMiku's Birthday Spectacular\n**WILL NOT** be removed!!!!".format(ordinal(numbTimes)), colour=discord.Colour(0x00FFFF))
            emb.set_thumbnail(url=mikuem.url)
            await message.reply(embed=emb)
            miku_last_message_time = datetime.datetime.utcnow()
    except:
        raise

def escapeFormatting(text: str, onlyCodeBlock: bool):
    if (onlyCodeBlock):
        return text.replace("`", "'")
    else:
        return text.replace("@", "(at)").replace("*", "\\*").replace("_", "\\_").replace("~", "\\~").replace("`", "\\`")

async def sendMultiMessage(channel, message, startStr, endStr):
    
    def splitStrByLimit(string, size):
        return [string[i:i+size] for i in range(0, len(string), size)]
    def splitListByLimit(stringList, size):
        curr = ""
        ret = []
        for m in message:
            if (len(m) > size):
                ret = ret + splitStrByLimit(m, size)
            elif (len(curr) + len(m) > size):
                ret.append(curr)
                curr = ""
            else:
                curr += m
        ret.append(curr)
        return ret
    
    messageList = []
    f = None
    if (type(message) == type([])):
        f = splitListByLimit
    elif (type(message) == type("")):
        f = splitStrByLimit
                
    messageList = f(message, 2000 - (len(startStr) + len(endStr)))
    
    for m in messageList:
        await channel.send(startStr + m + endStr)

async def bulkDeleteUserMessages(member, afterDateTime):
    for ch in SELF_BOT_SERVER.channels:
        if isinstance(ch, discord.TextChannel):
            await ch.purge(limit=25, check=lambda m: m.author.id == member.id, after=afterDateTime)

def getURLs(s: str):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex,s)      
    return [x[0] for x in url]

checkNitroScam_data = {}

async def checkNitroScam(message):
    global checkNitroScam_data
    contents = message.content
    phisingScore = sum([contents.count("@everyone") * 2, contents.count("nitro") * 2, contents.count("free"), contents.count("CS:GO"), contents.count("claim"), contents.count("steam"), contents.count("gift")])
    if (phisingScore == 0): return
    urlCount = 0
    for url in getURLs(contents):
        website = urlparse(url).netloc
        if (website.startswith("www.")):
            website = website[4:]
        whitelist = ["google.com", "discord.gift"]
        if website in whitelist:
            continue
        urlCount += 1
    if (urlCount > 0):
        data = checkNitroScam_data.get(message.author.id, None)
        if (data is None):
            data = {}
            data["score"] = 0
            data["last"] = datetime.datetime.utcnow()
            checkNitroScam_data[message.author.id] = data
        if (datetime.datetime.utcnow() - data["last"] > datetime.timedelta(hours=1)):
            data["score"] = 0
        data["last"] = datetime.datetime.utcnow()
        data["score"] += phisingScore
        if (data["score"] > 2):
            if (data["score"] <= 5): 
                try:
                    await message.author.send("**CTGP-7 server:** Suspicious phising activity has been detected.\nThis is only a warning and won't have any consequences, but further suspicious activity will result in a mute.\nPlease contact a staff member if you think this is a mistake.")
                except:
                    pass
            phisChn = client.get_channel(ch_list()["PHISING"])
            await sendMultiMessage(phisChn, "User: {} ({})\nScore: {}\nContents:\n--------------\n{}\n--------------".format(message.author.name, message.author.id, data["score"], contents.replace("@", "(at)")), "", "")
        if (data["score"] > 5):
            await mute_user(message.author.id, 3*24*60)
            await bulkDeleteUserMessages(message.author, message.created_at - datetime.timedelta(hours=1))
            try:
                await message.author.send("**CTGP-7 server:** Suspicious phising activity has been detected.\nYou have been kicked and muted for 3 days.\nPlease contact a staff member if you think this is a mistake.")
            except:
                pass
            await message.author.kick()
            

from .server.CTGP7BotHandler import get_user_info, handle_server_command, handler_server_init_loop, handler_server_update_globals, kick_message_callback, server_message_logger_callback, server_on_member_remove

on_ready_completed = False
@client.event
async def on_ready():
    print("\n-------------------------\n")
    global db_mng
    global ctgp7_server
    global SELF_BOT_SERVER
    global SELF_BOT_MEMBER
    global debug_mode
    global on_ready_completed
    if (on_ready_completed):
        print("Skipping on_ready...")
        print('------\n')
        return
    if(os.path.isfile("debug.flag")):
        print("Debug mode enabled.")
        debug_mode = True
        atexit.unregister(exit_handler)
    SELF_BOT_SERVER = client.get_guild(SERVER_ID())
    SELF_BOT_MEMBER = SELF_BOT_SERVER.get_member(client.user.id)
    db_mng = ServerDatabase()
    atexit.register(db_mng.terminate)
    ctgp7_server = CTGP7ServerHandler(debug_mode)
    ctgp7_server.database.setKickLogCallback(kick_message_callback)
    CTGP7ServerHandler.loggerCallback = server_message_logger_callback
    CTGP7Requests.get_user_info = get_user_info
    asyncio.ensure_future(muted_task())
    asyncio.ensure_future(change_game())
    asyncio.ensure_future(check_version_list())
    handler_server_update_globals(SELF_BOT_MEMBER, SELF_BOT_SERVER)
    handler_server_init_loop(ctgp7_server)
    print("Bot running: {}".format(str(datetime.datetime.now())))
    print('Logged in as: {} in server: {}'.format(SELF_BOT_MEMBER.name,SELF_BOT_SERVER.name))
    print('------\n')
    set_retry_times(0)
    on_ready_completed = True

@client.event
async def wait_until_login():
    await client.change_presence(activity=discord.Game(name='something goes here'))


@client.event
async def on_member_join(member):
    global SELF_BOT_SERVER
    global client
    global db_mng
    door_chan = SELF_BOT_SERVER.get_channel(ch_list()["DOORSTEP"])
    await door_chan.send("Everybody welcome {} to the server! Make sure to check the rules in <#739808582979027025>.\nWe are now {} members.".format(member.mention, SELF_BOT_SERVER.member_count))
    rows = await db_mng.mute_get()
    for row in rows:
        if (row[0] == int(member.id)):
            timeleft = (row[1] + row[2]) - current_time_min()
            if (timeleft > 0):
                await mute_user(member.id, timeleft)
    await punish(member, await db_mng.warn_get(member.id), onRejoin=True)

@client.event
async def on_member_remove(member):
    global SELF_BOT_SERVER
    global db_mng
    global client
    global ctgp7_server
    await server_on_member_remove(ctgp7_server, member)
    door_chan = SELF_BOT_SERVER.get_channel(ch_list()["DOORSTEP"])
    await door_chan.send("See ya **{}**. We are now {} members.".format(member.name, SELF_BOT_SERVER.member_count))
    
@client.event
async def on_message_delete(message):
    staff_chan = SELF_BOT_SERVER.get_channel(ch_list()["STAFF"])
    if (message.channel != staff_chan and not message.author.bot and not is_channel_private(message.channel)):
        parsedcontent = message.content.replace("@", "(at)")
        await staff_chan.send("Message by {} ({}) was deleted in {}\n\n------------------------\n{}\n------------------------".format(message.author.name, message.author.id, message.channel.mention, parsedcontent))

@client.event
async def on_message_edit(before, after):
    if (len(before.mentions) > 0 or len(before.role_mentions) > 0) and not before.author.bot:
        staff_chan = SELF_BOT_SERVER.get_channel(ch_list()["STAFF"])
        if (before.channel != staff_chan):
            parsedcontent = before.content.replace("@", "(at)")
            await staff_chan.send("Message by {} ({}) was edited in {} at:\n`{} {}`\n\n------------------------\n{}\n------------------------".format(before.author.name, before.author.id, before.channel.mention, str(datetime.datetime.now()), time.tzname[time.localtime().tm_isdst], parsedcontent))

@client.event
async def on_message(message):
    global db_mng
    global ctgp7_server
    global SELF_BOT_SERVER
    global SELF_BOT_MEMBER
    global COMMUNITIES_TEXT
    global client
    global debug_mode
    global current_time_min
    global current_talk_id
    if (client.user == None) or (SELF_BOT_SERVER == None) or (SELF_BOT_MEMBER == None):
        print("Error, some variable is None")
        return None
    try:
        if (message.content == ""): return
        random.seed()
        bot_mtn = message.content.split()[0]
        if (get_from_mention(bot_mtn) == client.user) and (message.author != client.user): #@RedYoshiBot
            try:
                bot_cmd = message.content.split()[1]
                if bot_cmd == 'mute':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split()
                        if (len(tag) != 4):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["mute"] + "```")
                            return
                        muted_member = get_from_mention(tag[2])
                        if (muted_member is None):
                            muted_member = CreateFakeMember(tag[2])
                        if(muted_member != None):
                            mutemin = parsetime(tag[3])
                            if (mutemin[0] == -1):
                                await message.reply( "Invalid time amount.")
                                return
                            await mute_user(muted_member.id, mutemin[0])
                            await message.reply( "{} was muted for {} {}.".format(muted_member.name, mutemin[1], mutemin[2]))
                            try:
                                await muted_member.send("**CTGP-7 server:** You have been muted for {} {}.".format(mutemin[1], mutemin[2]))
                            except:
                                pass
                            return
                        else:
                            await message.reply( "Invalid member.")
                            return
                elif bot_cmd == 'unmute':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split()
                        if (len(tag) != 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["unmute"] + "```")
                            return
                        muted_member = get_from_mention(tag[2])
                        if (muted_member is None):
                            muted_member = CreateFakeMember(tag[2])
                        if(muted_member != None):
                            await unmute_user(muted_member.id)
                            await message.reply( "{} was unmuted.".format(muted_member.name))
                        else:
                            await message.reply( "Invalid member.")
                elif bot_cmd == 'getmute':
                    tag = message.content.split()
                    if await staff_can_execute(message, bot_cmd):
                        if (len(tag) != 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["getmute"] + "```")
                            return
                        rows = await db_mng.mute_get()
                        nameList = []
                        for row in rows:
                            member = get_from_mention(str(row[0]))
                            if (member is None):
                                member = CreateFakeMember(row[0])
                            membname = member.name
                            nameList.append("{}: {}m\n".format(membname, (row[1] + row[2]) - current_time_min()))
                        await sendMultiMessage(message.channel, nameList, "```", "```")
                    else:
                        if (len(tag) != 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["getmute"] + "```")
                            return
                        await message.reply( "I've sent your muted time in a DM")
                        rows = await db_mng.mute_get()
                        for row in rows:
                            if (int(row[0]) == message.author.id):
                                try:
                                    await message.author.send("**CTGP-7 server:** You are muted for {} minutes.".format((row[1] + row[2]) - current_time_min()))
                                except:
                                    pass
                                return
                        try:
                            await message.author.send("**CTGP-7 server:** You are not muted.")
                        except:
                            pass
                elif bot_cmd == 'getlang':
                    if is_channel(message, ch_list()["TRANSLATIONS"]):
                        tag = message.content.split(None)
                        if not (len(tag) == 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["getlang"] + "```")
                            return
                        try:
                            outString = io.StringIO()
                            await message.reply( "Downloading {} language, please wait...".format(tag[2]))
                            MKTranslationDownload.executeScript(tag[2], outString)
                            outString.seek(0)
                            sendFile = discord.File(outString, filename=tag[2]+".txt")
                            await message.channel.send(file=sendFile, content="Here is your file:")
                        except Exception as e:
                            await message.channel.send( "An exception occured with your request: ```{}```".format(str(e)))
                elif bot_cmd == 'talk':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None)
                        if not (len(tag) == 3 or len(tag) == 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["talk"] + "```")
                            return
                        if (len(tag) == 2):
                            current_talk_id = ''
                            await message.reply( "Cleared chat destination.")
                        else:
                            if (checkdestvalid(tag[2]) != None):
                                current_talk_id = re.sub("\D", "", tag[2])
                                await message.reply( "Set chat destination to: {}".format(current_talk_id))
                            else:
                                await message.reply( "Invalid user or channel specified.")
                elif bot_cmd == 'closebug':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 3)
                        if not (len(tag) == 4 or len(tag) == 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["closebug"] + "```")
                            return
                        try:
                            bug_entry = await db_mng.bug_close(tag[2])
                        except:
                            bug_entry = []
                        if (len(bug_entry) == 0):
                            await message.reply( "Invalid ID specified or bug is already closed.")
                            return
                        bug_reports = SELF_BOT_SERVER.get_channel(ch_list()["BUG_OPEN"])
                        bug_closed = SELF_BOT_SERVER.get_channel(ch_list()["BUG_CLOSE"])
                        bugs = SELF_BOT_SERVER.get_channel(ch_list()["BUGS"])
                        bot_msg = await bug_reports.fetch_message(tag[2])
                        member = get_from_mention(str(bug_entry[0]))
                        if (member is None):
                            member = FakeMember(str(bug_entry[0]))
                        if (len(tag) == 4):
                            try:
                                await bug_closed.send("```State: Closed\nReason: {}\n------------------\nReported by: {}\nExplanation: {}```".format(tag[3], member.name, bug_entry[1]))
                                await bot_msg.delete()
                            except:
                                pass
                            await bugs.send("{}, your bug with ID: `{}` has been closed. Reason: ```{}```".format(member.mention, bot_msg.id, tag[3]))
                        else:
                            try:
                                await bug_closed.send("```State: Closed\nReason: No reason given.\n------------------\nReported by: {}\nExplanation: {}```".format(member.name, bug_entry[1]))
                                await bot_msg.delete()
                            except:
                                pass
                            await bugs.send("{}, your bug with ID: `{}` has been closed. Reason: ```No reason given.```".format(member.mention, bot_msg.id))
                        await message.reply( "Closed successfully.")
                elif bot_cmd == "bugcount":
                    tag = message.content.split()
                    if (len(tag) != 2):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["bugcount"] + "```")
                        return
                    count_bug = await db_mng.bug_count()
                    await message.reply( "**Bug stats:**```Open: {}\nClosed: {}\n\nTotal: {}```".format(count_bug[0], count_bug[1], count_bug[0] + count_bug[1]))    
                elif bot_cmd == 'communities' or bot_cmd == 'community':
                    tag = message.content.split(None)
                    if (len(tag) != 2):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["communities"] + "```")
                        return
                    await message.reply( COMMUNITIES_TEXT)
                elif bot_cmd == 'change_game':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None)
                        if (len(tag) != 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["change_game"] + "```")
                            return
                        retgame = await perform_game_change()
                        await message.reply( "Changed current playing game to: `{}`".format(retgame))
                elif bot_cmd == 'warn':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 3)
                        if (len(tag) < 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["warn"] + "```")
                            return
                        warn_member = get_from_mention(tag[2])
                        if (warn_member is None):
                            warn_member = CreateFakeMember(tag[2])
                        warnreason = ""
                        if(len(tag) == 3):
                            warnreason = "No reason given."
                        else:
                            warnreason = tag[3]
                        if(warn_member != None):
                            warncount = await db_mng.warn_get(warn_member.id)
                            warncount += 1
                            if (not checkCanPunish(warncount)):
                                await message.reply("Operation Denied. Max amount of kick/bans in the last 4 hours reached.\nEnable emergency mode with `!emergency` and contact PabloMK7.")
                                return
                            await db_mng.warn_set(warn_member.id, warncount)
                            await message.reply( "{} got a warning. {} warnings in total.".format(warn_member.name, warncount))
                            try:
                                await warn_member.send("**CTGP-7 server:** You got a warning. Total warnings: {}.\nReason:\n```{}```".format(warncount, warnreason))
                            except:
                                pass
                            await punish(warn_member, warncount)
                        else:
                            await message.reply( "Invalid member.")
                elif bot_cmd == 'setwarn' or bot_cmd == "ban" or bot_cmd == "kick":
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 4)
                        if (bot_cmd == "setwarn"):
                            if (len(tag) < 4):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()[bot_cmd] + "```")
                                return
                        else:
                            if (len(tag) < 3):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()[bot_cmd] + "```")
                                return
                        warn_member = get_from_mention(tag[2])
                        if (warn_member is None):
                            warn_member = CreateFakeMember(tag[2])
                        warnreason = ""
                        warncount = 0
                        if (bot_cmd == "ban"):
                            warncount = 4
                        elif (bot_cmd == "kick"):
                            warncount = 3
                        else:
                            try:
                                warncount = int(tag[3])
                            except:
                                await message.reply( "Invalid amount.")
                                return
                        if (bot_cmd == "setwarn"):
                            if(len(tag) == 4):
                                warnreason = "No reason given."
                            else:
                                warnreason = tag[4]
                        else:
                            if(len(tag) == 3):
                                warnreason = "No reason given."
                            else:
                                warnreason = tag[3]
                        if(warn_member != None):
                            if (not checkCanPunish(warncount)):
                                await message.reply("Operation Denied. Max amount of kick/bans in the last 4 hours reached.\nEnable emergency mode with `!emergency` and contact PabloMK7.")
                                return
                            await db_mng.warn_set(warn_member.id, warncount)
                            await message.reply( "Set {} warnings to {}.".format(warn_member.name, warncount))
                            try:
                                await warn_member.send("**CTGP-7 server:** You now have {} warnings.\nReason:\n```{}```".format(warncount, warnreason))
                            except:
                                pass
                            await punish(warn_member, warncount)
                        else:
                            await message.reply( "Invalid member.")
                elif bot_cmd == 'getwarn':
                    tag = message.content.split()
                    if await staff_can_execute(message, bot_cmd):
                        if (len(tag) != 2 and len(tag) != 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["getwarn"] + "```")
                            return
                        if (len(tag) == 2):
                            rows = await db_mng.warn_get_all()
                            nameList = []
                            for row in rows:
                                member = get_from_mention(str(row[0]))
                                if (member is None):
                                    member = CreateFakeMember(str(row[0]))
                                membname = member.name
                                nameList.append("{}: {}\n".format(membname, row[1]))
                            await sendMultiMessage(message.channel, nameList, "```", "```")
                        else:
                            warn_member = get_from_mention(tag[2])
                            if (warn_member is None):
                                warn_member = CreateFakeMember(tag[2])
                            if (warn_member is not None):
                                warncount = await db_mng.warn_get(warn_member.id)
                                await message.reply("{} has {} warnings.".format(warn_member.name, warncount))
                            else:
                                await message.reply( "Invalid member.")
                    else:
                        if (len(tag) != 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["getwarn"] + "```")
                            return
                        await message.reply( "I've sent your amount of warnings in a DM")
                        warncount = await db_mng.warn_get(message.author.id)
                        try:
                            await message.author.send("**CTGP-7 server:** You have {} warnings.".format(warncount))
                        except:
                            pass
                elif bot_cmd == 'release':
                    if await staff_can_execute(message, bot_cmd): 
                        tag = message.content.split()
                        try:
                            d = urlopen("https://api.github.com/repos/PabloMK7/CTGP-7updates/releases/tags/" + tag[2])
                        except HTTPError as err:
                            await message.reply( "Release tag invalid. (Example: v0.14-1)\r\nError: " + str(err.code))
                        else:
                            json_data = json.loads(d.read().decode("utf-8"))
                            ch = client.get_channel(ch_list()["ANN"]) #announcements
                            try:
                                if tag[3] == "1":
                                    await ch.send("@everyone\r\n" + json_data["name"] +" (" + json_data["tag_name"] + ") has been released! Here is the changelog:\r\n```" + json_data["body"] + "```")
                            except IndexError:
                                await ch.send(json_data["name"] +" (" + json_data["tag_name"] + ") has been released! Here is the changelog:\r\n```" + json_data["body"] + "```")
                elif bot_cmd == 'cancel_schedule':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split()
                        if (len(tag) != 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["cancel_schedule"] + "```")
                            return
                        try:
                            retcode = await db_mng.schedule_del_confirm(int(tag[2]))
                            if (retcode == -1):
                                await message.reply( "Invalid schedule id specified.")
                                return
                            else:
                                await message.reply( "The schedule was cancelled successfully.")
                                return
                        except:
                            await message.reply( "Invalid schedule id specified.")
                            return

                elif bot_cmd == 'schedule':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 4)
                        if (len(tag) != 5):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["schedule"] + "```")
                            return
                        timeamount = parsetime(tag[3])
                        if (timeamount[0] == -1):
                            await message.reply( "Invalid time specified.")
                            return
                        messagedest = checkdestvalid(tag[2]) 
                        if (messagedest == None):
                            await message.reply( "Invalid user or channel specified.")
                            return
                        messagesent = await message.reply( "The message will be sent in {} {} to {}".format(timeamount[1], timeamount[2], messagedest.name))
                        await db_mng.schedule_add(messagesent.id, messagedest.id, timeamount[0], tag[4])
                elif bot_cmd == 'say':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 3)
                        if (len(tag) != 4):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["schedule"] + "```")
                            return
                        await sayfunc(tag[2], tag[3], message)
                elif bot_cmd == 'edit':
                    if await staff_can_execute(message, bot_cmd):
                        tag = message.content.split(None, 3)
                        if (len(tag) != 4):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["edit"] + "```")
                            return
                        for chan in SELF_BOT_SERVER.channels:
                            try:
                                msg = await chan.fetch_message(tag[2])
                                if (msg.author == client.user):
                                    try:
                                        old_content = msg.content
                                        await msg.edit(content=tag[3])
                                        sendMultiMessage(message.channel, "Edited successfully:\nOld: \n--------\n{}\n--------\nNew:\n--------\n{}\n--------\n".format(old_content, msg.content), "```", "```")
                                        return
                                    except:
                                        await message.reply( "**Couldn't edit message:** Internal error.")
                                        traceback.print_exc()
                                        return
                                else:
                                    await message.reply( "**Couldn't edit message:** Not a bot message.")
                                    return
                            except:
                                pass
                        await message.reply( "**Couldn't edit message:** Message not found (may be too old).")
                        return
                elif bot_cmd == 'restart':
                    if await staff_can_execute(message, bot_cmd):
                        await message.channel.send( "The bot is now restarting...")
                        print("Manually restarting by {} ({})".format(message.author.id, message.author.name))
                        db_mng.terminate()
                        await client.close()
                        client = None
                        atexit.unregister(exit_handler)
                        os.execv(sys.executable, ['python3'] + sys.argv)
                elif bot_cmd == 'stop':
                    if await staff_can_execute(message, bot_cmd):
                        await message.reply( "The bot is now stopping, see ya.")
                        print("Manually stopping by {} ({})".format(message.author.id, message.author.name))
                        db_mng.terminate()
                        await client.close()
                        client = None
                        atexit.unregister(exit_handler)
                        try:
                            os._exit(0)
                        except:
                            traceback.print_exc()
                            while(True): pass
                elif bot_cmd == 'ping':
                    tag = message.content.split()
                    if (len(tag) != 2):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["ping"] + "```")
                        return
                    msg_time = message.created_at
                    now_dt = datetime.datetime.utcnow()
                    delay_time = now_dt - msg_time
                    await message.reply( "Pong! ({}s, {}ms)".format(delay_time.seconds, delay_time.microseconds / 1000))
                elif bot_cmd == 'membercount':
                    if not (is_channel_private(message.channel)):
                        await message.reply( "We are now {} members.".format(SELF_BOT_SERVER.member_count))
                    else:
                        await message.reply( "This command cannot be used here.")
                elif bot_cmd == 'fact':
                    tag = message.content.split()
                    if not (len(tag) == 2 or len(tag) == 3):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["fact"] + "```")
                        return
                    final_text = ""
                    if (len(tag) == 2):
                        fact_text = await db_mng.fact_get(False)
                        fact_id = fact_text[random.randint(0, len(fact_text) - 1)][1]
                        try:
                            final_text = await fact_parse(fact_id)
                        except:
                            print("Error parsing: " + fact_id)
                            traceback.print_exc()
                            raise
                    else:
                        try:
                            fact_text = await db_mng.fact_get_byrow(int(tag[2]))
                            fact_id = fact_text[0][1]
                        except:
                            await message.reply( "Invalid id specified.")
                            return
                        try:
                            final_text = await fact_parse(fact_id)
                        except:
                            print("Error parsing: " + fact_id)
                            traceback.print_exc()
                            raise
                    if (len(final_text) < 1994):
                        await message.reply( "```" + final_text + "```")
                elif bot_cmd == 'listfact':
                    tag = message.content.split()
                    if (len(tag) != 2):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["listfact"] + "```")
                        return
                    fact_text = await db_mng.fact_get(True)
                    factSend = []
                    if await staff_can_execute(message, bot_cmd, silent=True):
                        for row in fact_text:
                            member = get_from_mention(str(row[1]))
                            if (member is None):
                                member = CreateFakeMember(str(row[1]))
                            membname = member.name
                            factSend.append(str(row[0]) + " - " + membname + " - " + row[2] + "\n----------\n")
                    else:
                        await message.reply( "I've sent you all the facts in a DM.")
                        for row in fact_text:
                            try:
                                final_text = await fact_parse(row[2])
                                text_isdyn = "(dynamic)" if await isfact_dynamic(row[2]) else "(static)"
                            except:
                                continue
                            factSend.append(str(row[0]) + " - " + text_isdyn +  " - " + final_text + "\n----------\n")
                    await sendMultiMessage(message.author, factSend, "```\n----------\n", "```")
                elif bot_cmd == 'delfact':
                    if await staff_can_execute(message, bot_cmd, silent=True):
                        tag = message.content.split()
                        if (len(tag) != 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_help_array()["delfact"] + "```")
                            return
                        try:
                            await db_mng.fact_delete(int(tag[2]))
                        except:
                            await message.reply( "Invalid id.")
                            return
                        await message.reply( "Fact {} deleted.".format(tag[2]))
                    else:
                        tag = message.content.split()
                        if (len(tag) != 2):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["delfact"] + "```")
                            return
                        await db_mng.fact_deleteuser(message.author.id)
                        await message.reply( "Your fact has been removed.")
                elif bot_cmd == 'addfact':
                    if not await staff_can_execute(message, bot_cmd, silent=True):
                        if(await db_mng.fact_userreg(message.author.id)):
                            await message.reply( "You can only have one fact registered. Use `@RedYoshiBot delfact` to delete the existing one.")
                            return
                    tag = message.content.split(None, 2)
                    if (len(tag) != 3):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["addfact"] + "```")
                        return
                    tag[2] = tag[2].replace("@", "(at)")
                    tag[2] = tag[2].replace("`", "")
                    try:
                        dummy = await fact_parse(tag[2])
                    except:
                        await message.reply( "Error parsing fact, correct usage:\r\n```" + help_array()["addfact"] + "```")
                        return
                    await db_mng.fact_add(int(message.author.id), tag[2])
                    await message.reply( "Fact added: \n```{}```".format(dummy))                        
                elif bot_cmd == "parseqr":
                    tag = message.content.split(None, 2)
                    if ((len(tag) != 3 and len(tag) != 2) or (len(tag) == 2 and len(message.attachments) == 0 and message.reference is None)):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["parseqr"] + "```")
                        return
                    try:
                        url = ""
                        if (len(tag) == 3):
                            url = tag[2]
                        else:
                            if (message.reference is not None):
                                replyFromID = message.reference.message_id
                                try:
                                    url = (await message.channel.fetch_message(replyFromID)).attachments[0].url
                                except:
                                    raise Exception("Image not found in replied message.")
                            else:
                                url = message.attachments[0].url
                        await message.channel.trigger_typing()
                        if (url.startswith("data:")):
                            qr = QRCrashDecode(data=url[5:])
                        else:
                            qr = QRCrashDecode(url=url)
                        qrtext = qr.printData()
                    except Exception as e:
                        await message.reply( "Failed to parse QR data:\n```{}```".format(str(e)))
                        return
                    await message.reply( "Parsed QR data:\n```{}```".format(qrtext))
                elif bot_cmd == "funcname":
                    tag = message.content.split(None)
                    if (len(tag) != 5):
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["funcname"] + "```")
                        return
                    try:
                        hexval = tag[2].lstrip("0x")
                        try:
                            hexval = int(hexval, 16)
                            if (hexval % 4 != 0):
                                raise ValueError("Address not aligned.")
                        except:
                            await message.reply("`Invalid address.`\nCorrect usage:\r\n```" + help_array()["funcname"] + "```")
                            return
                        try:
                            region = int(tag[3])
                            version = int(tag[4])
                            if (region < 1 or region > 3 or version < 1 or version > 2):
                                raise ValueError("Invalid region or version value.")
                        except:
                            await message.reply("`Invalid region or version.`\nCorrect usage:\r\n```" + help_array()["funcname"] + "```")
                            return
                        await message.channel.trigger_typing()
                        fs = MK7FunctionSearch(region, version)
                        name = fs.functionNameForAddr(hexval)
                        await message.reply("```0x{:08X}: ({})```".format(hexval, name))
                    except Exception as e:
                        await message.reply("Failed to get function name.")
                        raise e
                elif bot_cmd == 'help':
                    if is_channel(message, ch_list()["BOTCHAT"]) or await staff_can_execute(message, bot_cmd, silent=True) or is_channel_private(message.channel):
                        tag = message.content.split()
                        if (len(tag) > 2):
                            if tag[2] == "game":
                                if (len(tag) == 3):
                                    help_str = "Here is the help for the specified command:\r\n```" + help_array()["game"] + "```"
                                    help_str += "Here is a list of all the available game modes:\n\n"
                                    for index, content in game_help_array().items():
                                        help_str += "`" + index + "`, "
                                    help_str = help_str[:-2]
                                    help_str += "\n\nUse `@RedYoshiBot help game (gamemode)` to get help of a specific command."
                                    await message.reply( help_str)
                                    if await staff_can_execute(message, bot_cmd, silent=True):
                                        help_str = "\nHere is a list of all the available game staff commands:\n\n"
                                        for index, content in staff_game_help_array().items():
                                            help_str += "`" + index + "`, "
                                        help_str = help_str[:-2]
                                        help_str += "\n\nUse `@RedYoshiBot help game (gamemode)` to get help of a specific command."
                                        await message.reply( help_str)
                                    return
                                else:
                                    if await staff_can_execute(message, bot_cmd, silent=True):
                                        if tag[3] in staff_game_help_array():
                                            await message.reply( "Here is the help for the specified game mode:\r\n```" + staff_game_help_array()[tag[3]] + "```")
                                            return
                                    if tag[3] in game_help_array():
                                        await message.reply( "Here is the help for the specified game mode:\r\n```" + game_help_array()[tag[3]] + "```")
                                    else:
                                        await message.reply( "Unknown game mode, use `@RedYoshiBot help game` to get a list of all the available game modes.")
                                    return
                            if await staff_can_execute(message, bot_cmd, silent=True):
                                if tag[2] in staff_help_array():
                                    await message.reply( "Here is the help for the specified command:\r\n```" + staff_help_array()[tag[2]] + "```")
                                    return
                            if tag[2] in help_array():
                                await message.reply( "Here is the help for the specified command:\r\n```" + help_array()[tag[2]] + "```")
                            else:
                                await message.reply( "Unknown command, use `@RedYoshiBot help` to get a list of all the available commands.")
                        else:
                            help_str = "Here is a list of all the available commands:\n\n"
                            for index, content in help_array().items():
                                help_str += "`" + index + "`, "
                            help_str = help_str[:-2]
                            help_str += "\n\nUse `@RedYoshiBot help (command)` to get help of a specific command."
                            await message.reply( help_str)
                            if await staff_can_execute(message, bot_cmd, silent=True):
                                help_str = "\nHere is a list of all the available staff commands:\n\n"
                                for index, content in staff_help_array().items():
                                    help_str += "`" + index + "`, "
                                help_str = help_str[:-2]
                                help_str += "\n\nUse `@RedYoshiBot help (command)` to get help of a specific command."
                                await message.reply( help_str)
                    else:
                        await message.reply( "`@RedYoshiBot help` can only be used in <#324672297812099093> or DM.")
                        return
                elif bot_cmd == "game":
                    if (is_channel(message, ch_list()["BOTCHAT"]) or await staff_can_execute(message, bot_cmd, silent=True)):
                        tag = message.content.split()
                        if (len(tag) < 3):
                            await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["game"] + "```")
                            return
                        if (tag[2] == "guessanumber"):
                            if (len(tag) != 5):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + game_help_array()["guessanumber"] + "```")
                                return
                            if (tag[3] == "easy"):
                                try:
                                    guessed = int(tag[4])
                                    if not guessed in range(0, 11):
                                        raise ValueError("Number out of range.")
                                except:
                                    await message.reply( "Invalid number specified. (Must be between 0 and 10)")
                                    return
                                result = random.randint(0, 10)
                                await game_numberguess(guessed, result, 0, message)
                                return
                            elif (tag[3] == "normal"):
                                try:
                                    guessed = int(tag[4])
                                    if not guessed in range(0, 51):
                                        raise ValueError("Number out of range.")
                                except:
                                    await message.reply( "Invalid number specified. (Must be between 0 and 50)")
                                    return
                                result = random.randint(0, 50)
                                await game_numberguess(guessed, result, 1, message)
                                return
                            elif (tag[3] == "hard"):
                                try:
                                    guessed = int(tag[4])
                                    if not guessed in range(0, 100):
                                        raise ValueError("Number out of range.")
                                except:
                                    await message.reply( "Invalid number specified. (Must be between 0 and 99)")
                                    return
                                result = random.randint(0, 99)
                                await game_numberguess(guessed, result, 2, message)
                                return
                            else:
                                await message.reply( "Invalid difficulty specified. (easy/normal/hard)")
                                return
                        elif (tag[2] == "rps"):
                            if (len(tag) != 4):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + game_help_array()["rps"] + "```")
                                return
                            bot_ch = random.randint(0, 2)
                            usr_ch = 0
                            if (tag[3] == "rock" or tag[3] == "r"):
                                usr_ch = 0
                            elif (tag[3] == "paper" or tag[3] == "p"):
                                usr_ch = 1
                            elif (tag[3] == "scissors" or tag[3] == "s"):
                                usr_ch = 2
                            else:
                                await message.reply( "Invalid choice (rock/paper/scissors).")
                                return
                            await game_rps(bot_ch, usr_ch, message)
                            return
                        elif (tag[2] == "coin"):
                            if (len(tag) != 4):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + game_help_array()["coin"] + "```")
                                return
                            bot_ch = random.randint(1, 500)
                            usr_ch = 0
                            if (tag[3] == "head" or tag[3] == "h"):
                                usr_ch = 0
                            elif (tag[3] == "tails" or tag[3] == "t" or tag[3] == "tail"):
                                usr_ch = 1
                            else:
                                await message.reply( "Invalid choice (head/tails).")
                                return
                            await game_coin(bot_ch, usr_ch, message)
                            return
                        elif (tag[2] == "showcookie"):
                            if await staff_can_execute(message, bot_cmd, silent=True):
                                if (len(tag) != 4):
                                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_game_help_array()["showcookie"] + "```")
                                    return
                                cookie_member = get_from_mention(tag[3])
                                if (cookie_member is None):
                                    cookie_member = CreateFakeMember(tag[3])
                                if (cookie_member != None):
                                    cookie_amount = await db_mng.get_cookie(cookie_member.id)
                                    await message.reply( "{} has {} <:yoshicookie:416533826869657600> .".format(cookie_member.name, cookie_amount))
                                    return
                                else:
                                    await message.reply( "Invalid member specified.")
                            else:
                                if (len(tag) != 3):
                                    await message.reply( "Invalid syntax, correct usage:\r\n```" + game_help_array()["showcookie"] + "```")
                                    return
                                cookie_amount = await db_mng.get_cookie(message.author.id)
                                await message.reply( "You have {} <:yoshicookie:416533826869657600> .".format(cookie_amount))
                                return
                        elif (tag[2] == "top10"):
                            if (len(tag) != 3):
                                await message.reply( "Invalid syntax, correct usage:\r\n```" + game_help_array()["top10"] + "```")
                                return
                            rows = await db_mng.top_ten_cookie()
                            retstr = "Users with most <:yoshicookie:416533826869657600> .\n\n---------------------------------\n"
                            for row in rows:
                                cookie_member = get_from_mention(str(row[0]))
                                if cookie_member != None:
                                    retstr += "**{}** = **{}** <:yoshicookie:416533826869657600>\n---------------------------------\n".format(cookie_member.name, row[1])
                                else:
                                    await db_mng.delete_cookie(row[0])
                            await message.reply(retstr)
                        elif (tag[2] == "setcookie"):
                            if await staff_can_execute(message, bot_cmd):
                                if (len(tag) != 5):
                                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_game_help_array()["setcookie"] + "```")
                                    return
                                cookie_member = get_from_mention(tag[3])
                                if (cookie_member is None):
                                    cookie_member = CreateFakeMember(tag[3])
                                try:
                                    amount = int(tag[4])
                                except:
                                    await message.reply( "Invalid amount specified.")
                                    return
                                if (cookie_member != None):
                                    await db_mng.set_cookie(cookie_member.id, amount)
                                    await message.reply( "Set {} <:yoshicookie:416533826869657600> to {} .".format(cookie_member.name, amount))
                                    return
                                else:
                                    await message.reply( "Invalid user specified.")
                                    return
                        else:
                            await message.reply( "Invalid game mode specified. Use `@RedYoshiBot help game` to get a list of game modes.")
                            return
                        return
                    else:
                        await message.reply( "`@RedYoshiBot game` can only be used in <#324672297812099093>.")
                        return
                elif bot_cmd == "server":
                    await handle_server_command(ctgp7_server, message)
                    return
                else:
                    await message.reply( 'Hi! :3\nTo get the list of all the available commands use `@RedYoshiBot help`')    
            except IndexError:
                await message.reply( 'Hi! :3\nTo get the list of all the available commands use `@RedYoshiBot help`')
        elif (is_channel_private(message.channel) and not message.author == client.user):
            staff_chan = SELF_BOT_SERVER.get_channel(ch_list()["STAFF"])
            await staff_chan.send("{} sent me the following in a DM:\n```{}```".format(message.author.mention, message.content))
        elif (is_channel(message, ch_list()["BUGS"]) and (message.author != client.user) and bot_mtn == "!report"):
            tag = message.content.split(None, 1)
            if (len(tag) > 1):
                notif_msg = await message.reply( "Adding your bug report: ```{}```".format(tag[1]))
                bug_reports = SELF_BOT_SERVER.get_channel(ch_list()["BUG_OPEN"])
                bot_msg = await bug_reports.send("Processing...")
                await bot_msg.edit(content="```State: Open\n------------------\nReported by: {}\nExplanation: {}\nID: {}```".format(message.author.name, tag[1], bot_msg.id))
                if (bot_msg != None):
                    await db_mng.bug_add(message.author.id, tag[1], bot_msg)
                    await notif_msg.edit(content="{}, adding your bug report: ```{}```**Success**".format(message.author.name, tag[1]))
                else:
                    await notif_msg.edit(content="{}, adding your bug report: ```{}```**Fail**".format(message.author.name, tag[1]))
            else:
                await message.reply( "Invalid syntax, correct usage:\r\n```" + help_array()["report"] + "```")            
        elif ((bot_mtn == "!emergency" or  bot_mtn == "!emergency_off") and await staff_can_execute(message, "emergency", silent=True) and (message.author != client.user)):
            if ( bot_mtn == "!emergency"):
                await enableEmergency()
            else:
                await disableEmergency()
        elif (await staff_can_execute(message, "talk", silent=True) and (message.author != client.user) and message.content[0] == '+' and len(message.content) > 2):
            if (message.content[1] == '+'):
                subsindex = 2
            else:
                subsindex = 1
            if (current_talk_id == ''):
                await message.reply( "No chat destination set, please use `@RedYoshiBot talk` to set the chat destination ID")
                return
            await sayfunc(current_talk_id, message.content[subsindex:].strip(), message)
            if (subsindex == 2):
                current_talk_id = ''
                await message.reply( "Cleared chat destination.")
        elif (all(x in message.content.lower() for x in ["miku"]) or all(x in message.content.lower() for x in ["mbs"])) and itercount((x in message.content.lower() for x in ["remove", "replace", "delete"]), 1) and message.author != client.user:
            await sendMikuMessage(message)
        else:
            if (message.author != client.user):
                await checkNitroScam(message)
    except:
        traceback.print_exc()
        pass

def exit_handler():
    print("Unexpected exit at {}, rebooting in 10 seconds.".format(str(datetime.datetime.now())))
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("Exiting...")
        os._exit(0)
    os.execv(sys.executable, ['python3'] + sys.argv)

def perform_exit():
    try:
        db_mng.terminate()
    except:
        print("Got exception on exit:")
        traceback.print_exc()
    print("Bot exiting, see ya!")
    os._exit(0)

try:
    atexit.register(exit_handler)
    client.run(sys.argv[1])
except:
    perform_exit()
    pass