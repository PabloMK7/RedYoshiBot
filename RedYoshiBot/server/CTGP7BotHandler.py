from typing import Tuple
from RedYoshiBot.server.CTGP7Requests import CTGP7Requests
from .CTGP7ServerHandler import CTGP7ServerHandler
from .CTGP7ServerDatabase import ConsoleMessageType, CTGP7ServerDatabase
from ..RedYoshiBot import FakeMember, ch_list, is_channel, is_channel_private, get_role, parsetime, sendMultiMessage, escapeFormatting, role_list, get_from_mention, CreateFakeMember, applyRole, removeRole
from ..CTGP7Defines import CTGP7Defines
import discord
import asyncio
import threading
import traceback
import datetime
import matplotlib.pyplot as plt
from PIL import Image
import io

SELF_BOT_MEMBER = None
SELF_BOT_SERVER = None

def handler_server_update_globals(bot_member, bot_server):
    global SELF_BOT_MEMBER
    global SELF_BOT_SERVER
    SELF_BOT_MEMBER = bot_member
    SELF_BOT_SERVER = bot_server

def server_help_array():
    return {
        "help": ">@RedYoshiBot server help\nGets the help for the server specific commands.",
        "stats": ">@RedYoshiBot server stats (ct/ot/ba)\nGets the usage stats for custom tracks (ct), original tracks (ot) or battle arenas (ba).",
        "link": ">@RedYoshiBot server link (link code)\nLinks a console to your discord account using the code provided by the CTGP-7 plugin.",
        "unlink": ">@RedYoshiBot server unlink\nUnlinks your console and discord account."
    }
def staff_server_help_array():
    return {
        "version": ">@RedYoshiBot server version (ctww/beta) [newvalue]\nSets the ctww or beta values. If \'newvalue\' is not specified, the current version is displayed.",
        "tracksplit": ">@RedYoshiBot server tracksplit [newVer]\nSets or gets the current track frequency split. If \'newVer\' is \'enable\' or \'disable\' it will activate or deactivate the feature.",
        "kick": ">@RedYoshiBot server kick (consoleID) (time) (message)\nKicks the console (hex format, 0 for everyone) for the specified time (for example: 2h, 12m, 7d, etc, or 0m for a single time) with the specified message. Takes effect after the next race.",
        "skick": ">@RedYoshiBot server skick (consoleID) (time) (message)\nSilently kicks the console (hex format, 0 for everyone) for the specified time (for example: 2h, 12m, 7d, etc, or 0m for a single time) with the specified message. Takes effect after the next race.",
        "ban": ">@RedYoshiBot server ban (consoleID) (message)\nPermanently bans the console (hex format, 0 for everyone) with the specified message (Use kick for temporary bans). Takes effect after the next race.",
        "sban": ">@RedYoshiBot server sban (consoleID) (message)\nPermanently silently bans the console (hex format, 0 for everyone) with the specified message (Use kick for temporary bans). Takes effect after the next race.",
        "message": ">@RedYoshiBot server message (consoleID) (time) (message)\nShows a message to the console (hex format, 0 for everyone) upon login for the specified time (for example: 2h, 12m, 7d, etc, or 0m for a single time).",
        "clear": ">@RedYoshiBot server clear (consoleID)\nClears all the messages/kicks/bans associated with the console (hex format, 0 for everyone).",
        "disband": ">@RedYoshiBot server disband (roomID)\nDisbands the specified room ID, kicking all players.",
        "console_verify": ">@RedYoshiBot server console_verify (get/set/clear) (consoleID)\nSets or clears the verification mark for the specified console.",
        "console_admin": ">@RedYoshiBot server console_admin (get/set/clear) (consoleID)\nSets or clears the admin status for the specified console.",
        "region": ">@RedYoshiBot server region (newvalue)\nSets the CTWW/CD online region in the server.",
        "manage_vr": ">@RedYoshiBot server manage_vr (get/set) (consoleID) (ctww/cd/points) (newvalue)\nGets or sets the VR or points for the specified console (Don't set if console is in racing state online).",
        "transfer": ">@RedYoshiBot server transfer (oldConsoleID) (newConsoleID)\nTransfers all the transferable data from an old console to a new console (VR and Discord link).",
        "getlink": ">@RedYoshiBot server getlink (consoleID/discordID)\nGets link between console ID and Discord account.",
        "unlink": ">@RedYoshiBot server getlink (consoleID/discordID)\nBreaks the link between console ID and Discord account.",
        "apply_player_role": ">@RedYoshiBot server apply_player_role\nVERY SLOW!!! Applies the Player role to all linked console accounts.",
        "purge_console_link": ">@RedYoshiBot server purge_console_link\nRemoved console links from users that are no longer in the server.",
        "get_mii_icon": ">@RedYoshiBot server get_mii_icon (consoleID)\nGets the mii icon of the specified user.",
        "name_history": ">@RedYoshiBot server name_history (consoleID)\nGets the name history of the specified user.",
        "config": ">@RedYoshiBot server config (ctCPUAmount/cdCPUAmount/rubberBMult/rubberBOffset/blockedTrackHistory/serveraddr/serveravailable/vrmultiplier/allowedCharacters/allowedTracks) [newValue]\nGets or sets the config parameters for online mode.",
        "otplegality": ">@RedYoshiBot server otplegality (get/getall/set/clear) (consoleID)\nGets, sets or clear the otp legality of a specified console.",
        "consoleserver": ">@RedYoshiBot server consoleserver (get/set/clear)\nSets a NEX server address to the specified console.",
        "banned_ultra_shortcut": ">@RedYoshiBot server banned_ultra_shortcut (get/set/clear) (szsName) [from_min] [from_max] [to_min] [to_max] [trigger]\nManages the banned ultra shortcuts for the specified track.",
    }
    
def staff_server_command_level():
    return {
        "version": 0,
        "tracksplit": 0,
        "help": 1,
        "kick": 1,
        "skick": 1,
        "ban": 1,
        "sban": 1,
        "message": 1,
        "clear": 1,
        "disband" : 1,
        "stats": 1,
        "console_verify": 1,
        "console_admin": 0,
        "region": 0,
        "manage_vr": 1,
        "transfer": 1,
        "getlink": 1,
        "unlink": 1,
        "apply_player_role": 0,
        "purge_console_link": 0,
        "get_mii_icon": 1,
        "name_history": 1,
        "config": 0,
        "otplegality": 0,
        "consoleserver": 0,
        "banned_ultra_shortcut": 0,
    }

async def staff_server_can_execute(message, command, silent=False):
    retVal = False
    if (is_channel(message, ch_list()["STAFF"])):
        moderatorRole = get_role(role_list()["MODERATOR"])
        adminRole = get_role(role_list()["ADMIN"])
        hasMod = moderatorRole in message.author.roles
        hasAdmin = (adminRole in message.author.roles) or message.author.id == SELF_BOT_SERVER.owner.id
        privilegeLevel = 0 if hasAdmin else (1 if hasMod else 2)
        try:
            retVal = staff_server_command_level()[command] >= privilegeLevel
        except:
            retVal = False
    if (not retVal and not silent):
        await message.channel.send("{}, you don't have permission to do that!".format(message.author.name))
    return retVal

def get_server_bot_args(content: str, maxslplits=-1): # splits: amount of cuts after "server"
    realsplits = maxslplits + 1 if maxslplits != -1 else maxslplits
    return content.split(maxsplit=realsplits)[1:]

player_role_applier_lock = threading.Lock()
player_role_applier_pending = []
async def calc_player_role(ctgp7_server: CTGP7ServerHandler, userID: str):
    role_names = ["PLAYER", "BRONZE_PLAYER", "SILVER_PLAYER", "GOLD_PLAYER", "EMERALD_PLAYER", "DIAMOND_PLAYER", "RAINBOW_PLAYER"]
    for r in role_names:
        await removeRole(userID, role_list()[r])
    cID = ctgp7_server.database.get_discord_link_user(userID)
    if (cID is None):
        return
    count = 0
    for s in CTGP7ServerDatabase.allowed_console_status:
        if (ctgp7_server.database.get_console_status(cID, s) == 1): count += 1
    if (count >= 1):
        await applyRole(userID, role_list()[role_names[count]])
    await applyRole(userID, role_list()[role_names[0]])

def queue_player_role_update(userID: str):
    global player_role_applier_lock
    global player_role_applier_pending
    with player_role_applier_lock:
        player_role_applier_pending.append(userID)

async def process_pending_player_role_update(ctgp7_server: CTGP7ServerHandler):
    global player_role_applier_lock
    global player_role_applier_pending
    local_list = []
    with player_role_applier_lock:
        local_list = player_role_applier_pending.copy()
        player_role_applier_pending.clear()
    for user in local_list:
        await calc_player_role(ctgp7_server, user)

def purge_player_name_symbols(line: str):
    toTranslate = dict.fromkeys(map(ord, '\n\r\u2705\u2757\u2755'), None)
    return line.translate(toTranslate)

def gen_course_usage_embed(database: CTGP7ServerDatabase, course_type: int):
    mostTracks = database.get_most_played_tracks(course_type, 10000)
    tName = ""
    if (course_type == 0):
        tName = "Original Tracks"
    elif (course_type == 1):
        tName = "Custom Tracks"
    elif (course_type == 2):
        tName = "Battle Arenas"
    embed = discord.Embed(title="Most Played Tracks", description=tName, color=0xff0000, timestamp=datetime.datetime.now())
    currTrack = 1
    for d in range(0, 4):
        slic = []
        if (d < 2):
            slic = mostTracks[:(len(mostTracks)//2)]
        else:
            slic = mostTracks[(len(mostTracks)//2):]
        if (d == 2):
            embed.add_field(name="** **", value="** **", inline=False)
        mostPlayedStr = "```\n"
        for k in slic:
            if (d % 2 == 0):
                trackName = CTGP7Defines.getTrackNameFromSzs(k[0])
                position = str(currTrack)
                positionSpaces = " " * max((4 - len(position)), 0)
                mostPlayedStr += "{}.{}{}\n".format(position, positionSpaces, trackName)
                currTrack += 1
            else:
                if (k[1] != 0):
                    mostPlayedStr += "{} ({})\n".format(str(k[1]), str(k[1]+k[2]))
                else:
                    mostPlayedStr += "{}\n".format(str(k[2]))
        mostPlayedStr += "```"
        embed.add_field(name="** **", value=mostPlayedStr, inline=True)
    return embed

server_message_logger_lock = threading.Lock()
server_message_logger_pending = ""
def server_message_logger_callback(text: str):
    global server_message_logger_lock
    global server_message_logger_pending
    with server_message_logger_lock:
        server_message_logger_pending += text

async def server_message_logger():
    global server_message_logger_lock
    global server_message_logger_pending
    text = ""
    with server_message_logger_lock:
        if (len(server_message_logger_pending) <= 1800): # Reduces the amount of messages sent to discord api
            return
        text = server_message_logger_pending
        server_message_logger_pending = ""
        
    chPrivate = SELF_BOT_SERVER.get_channel(ch_list()["ONLINELOGS"])
    await sendMultiMessage(chPrivate, escapeFormatting(text, True), "```\n", "```")

kick_message_logger_lock = threading.Lock()
kick_message_logger_pending = []
def kick_message_callback(cID, messageType, message, amountMin, isSilent, isCitra):
    global kick_message_logger_lock
    global kick_message_logger_pending
    with kick_message_logger_lock:
        kick_message_logger_pending.append([cID, messageType, message, amountMin, isSilent, isCitra])

async def kick_message_logger():
    global kick_message_logger_lock
    global kick_message_logger_pending
    pending = []
    with kick_message_logger_lock:
        pending = kick_message_logger_pending.copy()
        kick_message_logger_pending.clear()
    for m in pending:
        cID = m[0]
        messageType = m[1]
        message = m[2]
        amountMin = m[3]
        isSilent = m[4]
        isCitra = m[5]
        if (isSilent or (messageType != ConsoleMessageType.SINGLE_KICKMESSAGE.value and messageType != ConsoleMessageType.TIMED_KICKMESSAGE.value) or cID == 0):
            continue
        embedPrivate=discord.Embed(title="{}Kick Report".format("Citra " if isCitra else ""), description="Console ID: 0x{:016X}".format(cID), color=0xff0000, timestamp=datetime.datetime.now())
        embedPrivate.add_field(name="Reason", value=message, inline=False)
        if (messageType == ConsoleMessageType.TIMED_KICKMESSAGE.value):
            time = ""
            if amountMin is None:
                time = "Permanent"
            else:
                days = int(amountMin // (60 * 24))
                hours = int((amountMin // 60) % 24)
                minutes = int((amountMin) % 60)
                time = "{} days,  {} hours, {} minutes".format(days, hours, minutes)
            embedPrivate.add_field(name="Duration", value=time, inline=False)
        chPrivate = SELF_BOT_SERVER.get_channel(ch_list()["STAFFKICKS"])
        await chPrivate.send(embed=embedPrivate)
            

tried_edit_stats_message_times = 0
stats_curr_online_users = 0
stats_curr_pub_online_rooms = 0
stats_curr_pri_online_rooms = 0
stats_curr_online_stuff_changed = True
stats_message_id = [0, 0]
vr_message_id = 0
graph_launches_message_id = 0
last_graph_update_date = None

async def update_graph_message(ctgp7_server: CTGP7ServerHandler):
    def generate_graph(today, days_past, database: CTGP7ServerDatabase, isCitra: bool) -> io.BytesIO | None:
        x = []
        y1 = []
        y2 = []
        for i in range(days_past):
            date = today - datetime.timedelta(days=days_past - i)
            # x.append(date.strftime("%Y %b %-d"))
            x.append(date.strftime("%b %-d"))
            y1.append(database.get_daily_launches(date))
            y2.append(database.get_daily_unique_consoles(date))
        
        # plt.rcParams["figure.figsize"] = (plt.rcParamsDefault["figure.figsize"][0] * 20, plt.rcParamsDefault["figure.figsize"][1])
        plt.rcParams["figure.figsize"] = (plt.rcParamsDefault["figure.figsize"][0] * 1.75, plt.rcParamsDefault["figure.figsize"][1])
        if not isCitra:
            plt.plot(x, y1, color = "dodgerblue", label = "Launches", marker="o", markersize=3)
            plt.plot(x, y2, color = "lightskyblue", linestyle='dashed', label = "New Consoles", marker="o", markersize=3)
        else:
            plt.plot(x, y1, color = "darkorange", label = "Citra Launches", marker="o", markersize=3)
            plt.plot(x, y2, color = "gold", linestyle='dashed', label = "Citra New Consoles", marker="o", markersize=3)
        for i,j in zip(x,y1):
            plt.annotate(str(j),xy=(i,j), fontsize=8)
        for i,j in zip(x,y2):
            plt.annotate(str(j),xy=(i,j), fontsize=8)
        plt.xticks(rotation = 45)
        plt.subplots_adjust(bottom=0.15)
        plt.grid()
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.clf()
        plt.rcParams["figure.figsize"] = plt.rcParamsDefault["figure.figsize"]
        buf.seek(0)
        return buf

    def get_concat_v_resize(im1: Image.Image, im2: Image.Image, resample=Image.BICUBIC, resize_big_image=True):
        if im1.width == im2.width:
            _im1 = im1
            _im2 = im2
        elif (((im1.width > im2.width) and resize_big_image) or
            ((im1.width < im2.width) and not resize_big_image)):
            _im1 = im1.resize((im2.width, int(im1.height * im2.width / im1.width)), resample=resample)
            _im2 = im2
        else:
            _im1 = im1
            _im2 = im2.resize((im1.width, int(im2.height * im1.width / im2.width)), resample=resample)
        dst = Image.new('RGB', (_im1.width, _im1.height + _im2.height))
        dst.paste(_im1, (0, 0))
        dst.paste(_im2, (0, _im1.height))
        return dst
    
    global graph_launches_message_id
    global last_graph_update_date
    DAYS_PAST = 30
    #DAYS_PAST = (datetime.datetime.utcnow() - datetime.datetime(year=2021, month=6, day=15)).days
    today = datetime.datetime.utcnow().date()
    if (today == last_graph_update_date):
        return
    last_graph_update_date = today

    bufNormal = generate_graph(today, DAYS_PAST, ctgp7_server.database, False)
    bufCitra = generate_graph(today, DAYS_PAST, ctgp7_server.citraDatabase, True)

    imNormal = Image.open(bufNormal)
    imCitra =  Image.open(bufCitra)

    imFinal = get_concat_v_resize(imNormal, imCitra, resize_big_image=False)
    buf = io.BytesIO()
    imFinal.save(buf, format="png")
    buf.seek(0)

    file = discord.File(fp=buf, filename="image.png")
    embed = discord.Embed(title="Daily Statistics (UTC)", color=0xff0000, timestamp=datetime.datetime.now())
    chPrivate = SELF_BOT_SERVER.get_channel(ch_list()["ONLINELOGS"])
    tmpMsg = await chPrivate.send(file=file)
    imageUrl = tmpMsg.attachments[0].url
    embed.set_image(url=imageUrl)
    ch = SELF_BOT_SERVER.get_channel(ch_list()["STATS"])
    msg = await ch.fetch_message(graph_launches_message_id)
    msg = await msg.edit(embed=embed, content=None)
    await asyncio.sleep(1.5)
    imNormal.close()
    imCitra.close()
    imFinal.close()
    buf.close()
    bufNormal.close()
    bufCitra.close()

async def update_stats_message(ctgp7_server: CTGP7ServerHandler):
    global tried_edit_stats_message_times
    global stats_curr_online_stuff_changed
    global stats_curr_online_users
    global stats_curr_pub_online_rooms
    global stats_curr_pri_online_rooms
    global stats_message_id
    global vr_message_id
    stats_curr_online_stuff_changed = False
    try:
        ch = SELF_BOT_SERVER.get_channel(ch_list()["STATS"])
        if (ch is None):
            raise Exception("Couldn't get stats channel")
        msg1 = await ch.fetch_message(stats_message_id[0])
        msg2 = await ch.fetch_message(stats_message_id[1])
        vrLead = await ch.fetch_message(vr_message_id)
        if (msg1 is None or msg1.author != SELF_BOT_MEMBER or msg2 is None or msg2.author != SELF_BOT_MEMBER or vrLead is None or vrLead.author != SELF_BOT_MEMBER):
            raise Exception("Stats message invalid state")
        tried_edit_stats_message_times = 0

        genStats = ctgp7_server.database.get_stats()
        totOfflineRaces = genStats["races"] + genStats["ttrials"] + genStats["coin_battles"] + genStats["balloon_battles"]
        totMissions = genStats["failed_mission"] + genStats["completed_mission"] + genStats["perfect_mission"]
        completedMissions = genStats["completed_mission"] + genStats["perfect_mission"]
        averageGrade = genStats["grademean_mission"] / genStats["gradecount_mission"]
        totOnlineRaces = genStats["online_races"] + genStats["comm_races"] + genStats["ctww_races"] + genStats["cd_races"] + genStats["online_coin_battles"] + genStats["online_balloon_battles"]
        mostTracks = ctgp7_server.database.get_most_played_tracks(1, 10)
        uniqueConsoles = ctgp7_server.database.get_unique_console_count()
        uniqueOnlineUsers = ctgp7_server.database.get_unique_console_vr_count()

        embed=discord.Embed(title="CTGP-7 Statistics", description="Statistics from all CTGP-7 players! (Citra users not included)", color=0xff0000, timestamp=datetime.datetime.now())
        embed2=discord.Embed(color=0xff0000, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=str(SELF_BOT_SERVER.icon.url))
        embed.add_field(name="Total Launches", value=str(genStats["launches"]), inline=True)
        embed.add_field(name="Unique Consoles", value=str(uniqueConsoles), inline=True)
        embed.add_field(name="** **", value="** **", inline=False)
        embed.add_field(name="Total Offline Races", value=str(totOfflineRaces), inline=False)
        embed.add_field(name="Normal Races", value=str(genStats["races"]), inline=True)
        embed.add_field(name="Time Trials", value=str(genStats["ttrials"]), inline=True)
        embed.add_field(name="Coin Battles", value=str(genStats["coin_battles"]), inline=True)
        embed.add_field(name="Balloon Battles", value=str(genStats["balloon_battles"]), inline=True)
        embed.add_field(name="Total Race Points", value=str(genStats["race_points"]), inline=True)
        embed.add_field(name="** **", value="** **", inline=False)
        embed.add_field(name="Total Missions Played", value=str(totMissions), inline=False)
        embed.add_field(name="Completed Missions", value=str(completedMissions), inline=True)
        embed.add_field(name="(with perfect grade)", value=str(genStats["perfect_mission"]), inline=True)
        embed.add_field(name="Failed Missions", value=str(genStats["failed_mission"]), inline=True)
        embed.add_field(name="Average Grade", value="{:.3f}".format(averageGrade), inline=True)
        embed.add_field(name="Custom Missions Played", value=str(genStats["custom_mission"]), inline=False)
        embed.add_field(name="** **", value="** **", inline=False)
        embed.add_field(name="Total Online Races", value=str(totOnlineRaces), inline=False)
        embed.add_field(name="Vanilla Races", value=str(genStats["online_races"]), inline=True)
        embed.add_field(name="Community Races", value=str(genStats["comm_races"]), inline=True)
        embed.add_field(name="CTWW Races", value=str(genStats["ctww_races"]), inline=True)
        embed.add_field(name="Countdown Races", value=str(genStats["cd_races"]), inline=True)
        embed.add_field(name="Coin Battles", value=str(genStats["online_coin_battles"]), inline=True)
        embed.add_field(name="Balloon Battles", value=str(genStats["online_balloon_battles"]), inline=True)
        

        embed2.add_field(name="Total Logins", value=str(genStats["total_logins"]), inline=True)
        embed2.add_field(name="Unique Logins", value=str(uniqueOnlineUsers), inline=True)
        embed2.add_field(name="Total Online Rooms", value=str(genStats["total_rooms"]), inline=True)
        embed2.add_field(name="Current Network Users", value="{}".format(stats_curr_online_users), inline=False)
        embed2.add_field(name="Current Public Rooms", value=str(stats_curr_pub_online_rooms), inline=True)
        embed2.add_field(name="Current Private Rooms", value=str(stats_curr_pri_online_rooms), inline=True)
        embed2.add_field(name="** **", value="** **", inline=False)
        mostPlayedStr = "```\n"
        currTrack = 1
        for k in mostTracks:
            trackName = CTGP7Defines.getTrackNameFromSzs(k[0])
            trackNameSpaces = " " * max((24 - len(trackName)), 0)
            position = str(currTrack)
            positionSpaces = " " * max((4 - len(position)), 0)
            if (k[1] != 0):
                mostPlayedStr += "{}.{}{}{}{} ({})\n".format(position, positionSpaces, trackName, trackNameSpaces, str(k[1]), str(k[1]+k[2]))
            else:
                mostPlayedStr += "{}.{}{}{}{}\n".format(position, positionSpaces, trackName, trackNameSpaces, str(k[2]))
            currTrack += 1
        mostPlayedStr += "```"
        embed2.add_field(name="Most Played Tracks", value=mostPlayedStr, inline=False)
        msg1 = await msg1.edit(embed=embed, content=None)
        await asyncio.sleep(1.5)
        msg2 = await msg2.edit(embed=embed2, content=None)
        await asyncio.sleep(1.5)
        tried_edit_stats_message_times = 0

        vrRankCtww = ctgp7_server.database.get_most_users_vr(0, 20)
        vrRankCD = ctgp7_server.database.get_most_users_vr(1, 20)
        pointRank = ctgp7_server.database.get_most_users_vr(2, 20)
        rankArray = [vrRankCtww, vrRankCD, pointRank]
        nameArray = ["CTWW", "Countdown", "Race Points"]
        embed=discord.Embed(title="Leaderboard", color=0xff0000, timestamp=datetime.datetime.now())
        currPos = 1
        for i in range(3):
            
            leaderText = "```"
            leaderTextVR = "```"
            for user in rankArray[i]:
                userName = ctgp7_server.database.get_console_last_name(user[0], "Player")
                position = str(currPos)
                positionSpaces = " " * max((4 - len(position)), 0)
                leaderText += "{}.{}{}{}\n".format(position, positionSpaces, purge_player_name_symbols(userName), " \u2705" if ctgp7_server.database.get_console_is_verified(user[0]) else "")
                leaderTextVR += "{}.{}{}{}\n".format(position, positionSpaces, str(user[1]), "vr" if i < 2 else "pts")
                currPos += 1
            leaderText += "```"
            leaderTextVR += "```"
            embed.add_field(name=nameArray[i], value=leaderText, inline=True)
            embed.add_field(name="** **", value=leaderTextVR, inline=True)
            currPos = 1
            if (i < 2):
                embed.add_field(name="** **", value="** **", inline=False)
        vrLead = await vrLead.edit(embed=embed, content=None)
        await asyncio.sleep(1.5)
        
        await update_graph_message(ctgp7_server)

    except Exception:
        traceback.print_exc()
        tried_edit_stats_message_times += 1
        if (tried_edit_stats_message_times == 6 * 30):
            staff_chan = SELF_BOT_SERVER.get_channel(ch_list()["STAFF"])
            await staff_chan.send("<@&383673430030942208> Failed to update stats for more than 30 min.")
        return

async def prepare_server_channels(ctgp7_server: CTGP7ServerHandler):
    global stats_message_id
    global vr_message_id
    global graph_launches_message_id
    ctwwChan = SELF_BOT_SERVER.get_channel(ch_list()["CTWW"])
    async for m in ctwwChan.history(limit=200):
        await m.delete()
    ctwwPrivChan = SELF_BOT_SERVER.get_channel(ch_list()["CTWW_PRIV"])
    async for m in ctwwPrivChan.history(limit=200):
        await m.delete()
    statsChan = SELF_BOT_SERVER.get_channel(ch_list()["STATS"])
    mIds = []
    i = 0
    async for m in statsChan.history(limit=200, oldest_first=True):
        if (i < 4 and m.author.id == SELF_BOT_MEMBER.id):
            mIds.append(m.id)
            i += 1
        else:
            await m.delete()
    stats_message_id[0] = mIds[0] if len(mIds) > 0 else (await statsChan.send("Loading...")).id
    stats_message_id[1] = mIds[1] if len(mIds) > 1 else (await statsChan.send("Loading...")).id
    graph_launches_message_id = mIds[2] if len(mIds) > 2 else (await statsChan.send("Loading...")).id
    vr_message_id = mIds[3] if len(mIds) > 3 else (await statsChan.send("Loading...")).id

all_prev_room_msg_ids = set()
all_prev_room_msg_ids_citra = set()
async def update_online_room_info(ctgp7_server: CTGP7ServerHandler, isCitra: bool):
    currDatabase = ctgp7_server.citraDatabase if isCitra else ctgp7_server.database
    currCtwwHandler = ctgp7_server.citraCtwwHandler if isCitra else ctgp7_server.ctwwHandler
    global all_prev_room_msg_ids
    global all_prev_room_msg_ids_citra
    global stats_curr_online_stuff_changed
    global stats_curr_online_users
    global stats_curr_pub_online_rooms
    global stats_curr_pri_online_rooms
    ctwwChan = SELF_BOT_SERVER.get_channel(ch_list()["CTWW"])
    ctwwPrivChan = SELF_BOT_SERVER.get_channel(ch_list()["CTWW_PRIV"])
    currCtwwHandler.purge_tokens(datetime.timedelta(minutes=5))
    currCtwwHandler.purge_users(datetime.timedelta(minutes=5))
    currCtwwHandler.purge_rooms()
    serverInfo = currCtwwHandler.fetch_state()
    currUser = serverInfo["userCount"]
    if (not isCitra and stats_curr_online_users != currUser):
        stats_curr_online_users = currUser
        stats_curr_online_stuff_changed = True
    pubCurrRoom = serverInfo["pubRoomCount"]
    priCurrRoom = serverInfo["priRoomCount"]
    if (not isCitra and (stats_curr_pub_online_rooms != pubCurrRoom or stats_curr_pri_online_rooms != priCurrRoom)):
        stats_curr_pub_online_rooms = pubCurrRoom
        stats_curr_pri_online_rooms = priCurrRoom
        stats_curr_online_stuff_changed = True
    nowUser = serverInfo["newUserCount"]
    currDatabase.increment_general_stats("total_logins", nowUser)
    nowRoom = serverInfo["newRoomCount"]
    currDatabase.increment_general_stats("total_rooms", nowRoom)
    if (nowUser != 0 or nowRoom != 0):
        currDatabase.set_stats_dirty(True)
    currMsgIds = set()
    for room in serverInfo["rooms"]:
        msgID = room["messageID"]
        isHidden = room["hidden"]
        msg = None
        if (room["updated"]):
            try:
                if (msgID != 0):
                    if isHidden:
                        msg = await ctwwPrivChan.fetch_message(msgID)
                    else:
                        msg = await ctwwChan.fetch_message(msgID)
            except:
                msgID = 0
            if msgID == 0:
                if (isHidden):
                    msg = await ctwwPrivChan.send("Room is being created...")
                else:
                    msg = await ctwwChan.send("Room is being created...")
                msgID = msg.id
                if (not currCtwwHandler.update_room_messageID(room["gID"], msgID)):
                    await msg.delete()
                    continue
            
            bordercolor = room["color"]
            embed=discord.Embed(title="{}{} Room".format("Citra " if isCitra else "", room["gameMode"]), description="State: {}\nID: 0x{:08X}".format(room["state"], room["fakeID"]), color=bordercolor, timestamp=datetime.datetime.now())
            playerString = "```\n"
            for player in room["players"]:
                vrStr = ""
                if (player["vr"] is not None):
                    if (player["vrIncr"] is not None):
                        vrStr = " - {}({:+}) VR".format(player["vr"], player["vrIncr"])
                    else:
                        vrStr = " - {} VR".format(player["vr"])
                stat = ""
                if (player["state"] != ""):
                    stat = " - " + player["state"]
                symbolstring = "\u2705" if player["verified"] else ""
                symbolstring += "\u2755" if player["badnatmyself"] else ""
                symbolstring += "\u2757" if player["badnatother"] else ""
                if len(symbolstring) != 0:
                    symbolstring = " " + symbolstring
                playerString += "{}{}{}{}\n".format(purge_player_name_symbols(player["name"]), symbolstring, vrStr, stat)
            playerString += "```"
            if (playerString == "```\n```"):
                playerString = "```\n- (None)\n```"
            embed.add_field(name="Players", value=playerString, inline=False)
            msg = await msg.edit(embed=embed, content=None)
            if (room["log"]):
                playerString = "```\n"
                for player in room["players"]:
                    playerString += "- 0x{:016X} ({})\n".format(player["cID"], player["miiName"])
                playerString += "```"
                if (playerString == "```\n```"):
                    playerString = "```\n- (None)\n```"
                embed.add_field(name="Room ID", value="0x{:08X}".format(room["gID"]))
                embed.add_field(name="Players IDs", value=playerString, inline=False)
                chPrivate = SELF_BOT_SERVER.get_channel(ch_list()["ONLINELOGS"])
                await chPrivate.send(embed=embed)
            
        currMsgIds.add((isHidden, msgID))
    otherRooms = (all_prev_room_msg_ids_citra if isCitra else all_prev_room_msg_ids) - currMsgIds
    for (hidden, mID) in otherRooms:
        try:
            if hidden:
                msg = await ctwwPrivChan.fetch_message(mID)
            else:
                msg = await ctwwChan.fetch_message(mID)
            await msg.delete()
        except:
            # Message failed to delete, try to delete again in next iteration
            currMsgIds.add((hidden,mID))
            pass
    if (isCitra):
        all_prev_room_msg_ids_citra = currMsgIds
    else:
        all_prev_room_msg_ids = currMsgIds

async def server_on_member_remove(ctgp7_server: CTGP7ServerHandler, member: discord.Member):
    try:
        ctgp7_server.database.delete_discord_link_user(member.id)
    except:
        pass
    try:
        ctgp7_server.citraDatabase.delete_discord_link_user(member.id)
    except:
        pass

server_bot_loop_dbcommit_cnt = 0
async def server_bot_loop(ctgp7_server: CTGP7ServerHandler):
    firstLoop = True
    global stats_curr_online_stuff_changed
    global server_bot_loop_dbcommit_cnt
    while (True):
        try:
            if (firstLoop):
                await prepare_server_channels(ctgp7_server)
            await update_online_room_info(ctgp7_server, False)
            await update_online_room_info(ctgp7_server, True)
            if (firstLoop or ctgp7_server.database.get_stats_dirty() or stats_curr_online_stuff_changed):
                await update_stats_message(ctgp7_server)
                ctgp7_server.database.set_stats_dirty(False)
            await kick_message_logger()
            await server_message_logger()
            await process_pending_player_role_update(ctgp7_server)
            server_bot_loop_dbcommit_cnt += 1
            if (server_bot_loop_dbcommit_cnt >= (60 * 5) // 7): # Commit every 5 minutes
                ctgp7_server.database.commit()
                ctgp7_server.citraDatabase.commit()
                server_bot_loop_dbcommit_cnt = 0
            firstLoop = False
        except:
            traceback.print_exc()
            pass
        await asyncio.sleep(7)

def get_user_info(userID):
    member = get_from_mention(userID)
    if (member is None):
        return None
    ret = {}
    ret["name"] = member.name
    if (member.discriminator is not None and str(member.discriminator) != "0"):
        ret["discrim"] = str(member.discriminator)
    ret["nick"] = member.display_name

    contrRole = get_role(role_list()["CONTRIBUTOR"])
    courseRole = get_role(role_list()["COURSECREATOR"])
    betaAccessRole = get_role(role_list()["BETAACCESS"])
    ret["canBeta"] = contrRole in member.roles or courseRole in member.roles or betaAccessRole in member.roles or member.premium_since is not None
    return ret

def transfer_console_data(ctgp7_server: CTGP7ServerHandler, srcCID: int, dstCID: int, isCitra: bool):
    currDatabase = ctgp7_server.citraDatabase if isCitra else ctgp7_server.database
    currCtwwHandler = ctgp7_server.citraCtwwHandler if isCitra else ctgp7_server.ctwwHandler
    try:
        # Transfer VR
        srcVR = currDatabase.get_console_vr(srcCID)
        srcPoints = currDatabase.get_console_points(srcCID)
        currDatabase.set_console_vr(dstCID, (srcVR.ctVR, srcVR.cdVR))
        currDatabase.set_console_points(dstCID, srcPoints[0])
        currDatabase.set_console_vr(srcCID, (1000, 1000))
        currDatabase.set_console_points(srcCID, 0)
        # Transfer discord link
        discordID = currDatabase.get_discord_link_console(srcCID)
        if (discordID is not None):
            currDatabase.delete_discord_link_console(srcCID)
            currDatabase.set_discord_link_console(discordID, dstCID)
        currDatabase.transfer_console_status(srcCID, dstCID)
        return ""
    except Exception as e:
        return str(e)

stats_command_last_exec = datetime.datetime.utcnow()
async def handle_server_command(ctgp7_server: CTGP7ServerHandler, message: discord.Message, isCitra: bool):
    global stats_command_last_exec
    currDatabase = ctgp7_server.citraDatabase if isCitra else ctgp7_server.database
    currCtwwHandler = ctgp7_server.citraCtwwHandler if isCitra else ctgp7_server.ctwwHandler
    try:
        bot_cmd = get_server_bot_args(message.content, 2)[1]
    except IndexError:
        await message.reply( "Invalid syntax, use `@RedYoshiBot server help` to get all the available server commands")
        return
    if (bot_cmd == "help"):
        tag = get_server_bot_args(message.content)
        if is_channel(message, ch_list()["BOTCHAT"]) or await staff_server_can_execute(message, bot_cmd, silent=True) or is_channel_private(message.channel):
            if (len(tag) > 2):
                if await staff_server_can_execute(message, bot_cmd, silent=True):
                    if tag[2] in staff_server_help_array():
                        await message.reply( "Here is the help for the specified server command:\r\n```" + staff_server_help_array()[tag[2]] + "```")
                        return
                if tag[2] in server_help_array():
                    await message.reply( "Here is the help for the specified server command:\r\n```" + server_help_array()[tag[2]] + "```")
                else:
                    await message.reply( "Unknown server command, use `@RedYoshiBot server help` to get a list of all the available server commands.")
            else:
                help_str = "Here is a list of all the available server commands:\n\n"
                for index, _ in server_help_array().items():
                    help_str += "`" + index + "`, "
                help_str = help_str[:-2]
                help_str += "\n\nUse `@RedYoshiBot server help (command)` to get help of a specific server command."
                await message.reply( help_str)
                if await staff_server_can_execute(message, bot_cmd, silent=True):
                    help_str = "\nHere is a list of all the available staff server commands:\n\n"
                    for index, _ in staff_server_help_array().items():
                        help_str += "`" + index + "`, "
                    help_str = help_str[:-2]
                    help_str += "\n\nUse `@RedYoshiBot server help (command)` to get help of a specific server command."
                    await message.reply( help_str)
        else:
            await message.reply( "`@RedYoshiBot server help` can only be used in <#324672297812099093> or DM.")
            return
    elif bot_cmd == "version":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3 and len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["version"] + "```")
                return
            mode = tag[2]
            if mode not in ["ctww", "beta"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()["version"] + "```")
                return
            if (len(tag) == 3):
                version = -1
                if mode == "ctww":
                    version = currDatabase.get_ctww_version()
                elif mode == "beta":
                    version = currDatabase.get_beta_version()
                await message.reply( "Current {} version is: {}".format( mode, version))
                return
            else:
                try:
                    version = int(tag[3])
                except ValueError:
                    await message.reply( "Invalid number.")
                    return
                if mode == "ctww":
                    currDatabase.set_ctww_version(version)
                    currCtwwHandler.kick_user(0)
                elif mode == "beta":
                    currDatabase.set_beta_version(version)
                await message.reply( "{} version set to: {}".format( mode, version))
                return
    elif bot_cmd == "tracksplit":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 2 and len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["tracksplit"] + "```")
                return
            if (len(tag) == 2):
                split = currDatabase.get_track_freq_split()
                isenabled = currDatabase.get_track_freq_split_enabled()
                await message.reply( "Current split value is: {} ({})".format(split, "enabled" if isenabled else "disabled"))
                return
            else:
                if (tag[2] == "enable" or tag[2] == "disable"):
                    currDatabase.set_track_frew_split_enabled(tag[2] == "enable")
                    await message.reply( "Operation succeeded")
                    return
                try:
                    split = int(tag[2])
                except ValueError:
                    await message.reply( "Invalid number.")
                    return
                currDatabase.set_track_freq_split(split)
                await message.reply( "Split value set to: {}".format(split))
                return
    elif bot_cmd == "region":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 2 and len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["region"] + "```")
                return
            if (len(tag) == 2):
                region = -1
                region = currDatabase.get_online_region()
                await message.reply( "Current region is: {}".format(region))
                return
            else:
                try:
                    region = int(tag[2])
                except ValueError:
                    await message.reply( "Invalid number.")
                    return
                currDatabase.set_online_region(region)
                await message.reply( "Region set to: {}".format(region))
                return
    elif bot_cmd == "kick" or bot_cmd == "skick":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 4)
            if (len(tag) < 2):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            consoleID = tag[2]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
            except ValueError:
                users, names = currCtwwHandler.get_users_from_name(consoleID)
                if len(users) == 0:
                    await message.reply( "Invalid console ID or display name.")
                    return
                elif len(users) == 1:
                    await message.reply( "Found user {} with ID 0x{:016X}".format(names[0], users[0]))
                    consoleID = users[0]
                elif len(users) >= 2:
                    userlist = "```"
                    i = 0
                    for u in names:
                        userlist += "{} (0x{:016X})\n".format(u, users[i])
                        i += 1
                    userlist += "```\n"
                    await message.reply("Error, name matches with multiple users:\n{}".format(userlist))
                    return
            if (consoleID == 0):
                await message.reply( "**WARNING THIS OPERATION AFFECTS ALL CONSOLES.**")
            kickTime = [0, 0, "minutes"] if len(tag) <= 3 else parsetime(tag[3])
            if kickTime[0] == -1:
                await message.reply( "Invalid time specified.")
                return
            messageType = ConsoleMessageType.TIMED_KICKMESSAGE.value
            if (kickTime[0] == 0):
                messageType = ConsoleMessageType.SINGLE_KICKMESSAGE.value
            reason = "No reason provided" if len(tag) <= 4 else tag[4]
            currDatabase.set_console_message(consoleID, messageType, reason, None if kickTime[0] == 0 else kickTime[0], bot_cmd == "skick")
            currCtwwHandler.kick_user(consoleID)
            await message.reply( "Operation succeeded.")
            return
    elif bot_cmd == "ban" or bot_cmd == "sban":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 3)
            if (len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            consoleID = tag[2]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if (consoleID == 0):
                await message.reply( "**WARNING THIS OPERATION AFFECTS ALL CONSOLES.**")
            messageType = ConsoleMessageType.TIMED_KICKMESSAGE.value
            currDatabase.set_console_message(consoleID, messageType, tag[3], None, bot_cmd == "sban")
            await message.reply( "Operation succeeded.")
            return
    elif bot_cmd == "message":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 4)
            if (len(tag) != 5):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["message"] + "```")
                return
            consoleID = tag[2]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if (consoleID == 0):
                await message.reply( "**WARNING THIS OPERATION AFFECTS ALL CONSOLES.**")
            msgTime = parsetime(tag[3])
            if msgTime[0] == -1:
                await message.reply( "Invalid time specified.")
                return
            messageType = ConsoleMessageType.TIMED_MESSAGE.value
            messageTime = msgTime[0]
            if (msgTime[0] == 0):
                messageType = ConsoleMessageType.SINGLE_MESSAGE.value
                messageTime = None
            elif (msgTime[0] >= parsetime("10y")[0]): # Permanent message
                messageTime = None
            currDatabase.set_console_message(consoleID, messageType, tag[4], messageTime)
            await message.reply( "Operation succeeded.")
            return
    elif bot_cmd == "clear":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 2)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["clear"] + "```")
                return
            consoleID = tag[2]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if (consoleID == 0):
                await message.reply( "**WARNING THIS OPERATION AFFECTS ALL CONSOLES.**")
            
            currDatabase.delete_console_message(consoleID)
            await message.reply( "Operation succeeded.")
            return
    elif bot_cmd == "disband":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 2)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["disband"] + "```")
                return
            roomID = tag[2]
            if (roomID.startswith("0x")):
                roomID = roomID[2:]
            try:
                roomID = int(roomID, 16)
            except ValueError:
                await message.reply( "Invalid room ID.")
                return
            if (currCtwwHandler.disband_room(roomID)):
                await message.reply( "Operation succeeded.")
            else:
                await message.reply( "The specified room is not active.")
            return
    elif bot_cmd == "console_verify":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 3)
            if (len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            consoleID = tag[3]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
                if (consoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if mode not in ["get", "set", "clear"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if (mode == "get"):
                if (currDatabase.get_console_is_verified(consoleID)):
                    await message.reply("The specified console ID is verified.")
                else:
                    await message.reply("The specified console ID is not verified.")
            else:
                currDatabase.set_console_is_verified(consoleID, mode == "set")
                await message.reply( "Operation succeeded.")
    elif bot_cmd == "console_admin":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 3)
            if (len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            consoleID = tag[3]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
                if (consoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply("Invalid console ID.")
                return
            if mode not in ["get", "set", "clear"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if (mode == "get"):
                if (currDatabase.get_console_is_admin(consoleID)):
                    await message.reply("The specified console ID is admin.")
                else:
                    await message.reply("The specified console ID is not admin.")
            else:
                currDatabase.set_console_is_admin(consoleID, mode == "set")
                await message.reply( "Operation succeeded.")
    elif bot_cmd == "stats":
        tag = get_server_bot_args(message.content)
        if (len(tag) != 3):
            await message.reply( "Invalid syntax, correct usage:\r\n```" + server_help_array()["stats"] + "```")
            return
        if (tag[2] not in ["ct", "ot", "ba"]):
            await message.reply( "Invalid option, correct usage:\r\n```" + server_help_array()["stats"] + "```")
            return
        if (datetime.datetime.utcnow() - stats_command_last_exec < datetime.timedelta(seconds=10)):
            await message.reply( "Please wait a few seconds before using this command again.")
            return
        stats_command_last_exec = datetime.datetime.utcnow()
        opt = 0
        if (tag[2] == "ot"):
            opt = 0
        elif (tag[2] == "ct"):
            opt = 1
        elif (tag[2] == "ba"):
            opt = 2
        embed = gen_course_usage_embed(currDatabase, opt)
        await message.reply(embed=embed)
    elif bot_cmd == "link":
        if (isCitra):
            await message.reply("Operation not supported with Citra.")
            return
        
        tag = get_server_bot_args(message.content)
        if (len(tag) != 3):
            await message.reply( "Invalid syntax, correct usage:\r\n```" + server_help_array()["link"] + "```")
            return
        
        linkcode = tag[2]
        try:
            linkcode = int(linkcode, 16)
            cID = [k for k, v in CTGP7Requests.pendingDiscordLinks.items() if v == linkcode][0]
        except:
            await message.reply("Invalid code provided.")
            return
        
        if (currDatabase.get_discord_link_console(cID) is not None):
            await message.reply("The specified console is linked to another discord account. Use `@RedYoshiBot server unlink` from the other account to unlink your console.")
            return
        
        if (currDatabase.get_discord_link_user(message.author.id) is not None):
            await message.reply("Your discord account is already linked to another console. Use `@RedYoshiBot server unlink` to unlink the other console.")
            return

        currDatabase.set_discord_link_console(message.author.id, cID)
        del CTGP7Requests.pendingDiscordLinks[cID]
        await message.reply("Operation succeeded.")
        queue_player_role_update(message.author.id)
    elif bot_cmd == "getlink":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["getlink"] + "```")
                return
            
            checkid = tag[2]
            consoleID = None
            discordID = None

            if (checkid.startswith("0x")): # Console ID
                try:
                    consoleID = int(checkid, 16)
                except:
                    await message.reply("Invalid console ID provided.")
                    return
                discordID = currDatabase.get_discord_link_console(consoleID)
            else:
                try:
                    discordID = get_from_mention(checkid).id
                except:
                    await message.reply("Invalid discord ID provided.")
                    return
                consoleID = currDatabase.get_discord_link_user(discordID)
            
            if (consoleID is None or discordID is None):
                await message.reply("Specified ID has no link established.")
                return

            member = get_from_mention(discordID)
            if (member is None):
                member = CreateFakeMember(discordID)
            
            lastName = currDatabase.get_console_last_name(consoleID)
            await message.reply("`{:016X} {}` -> {}".format(consoleID, lastName, member.mention))
    elif bot_cmd == "unlink":
        if await staff_server_can_execute(message, bot_cmd, True):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + server_help_array()["unlink"] + "```")
                return
            
            checkid = tag[2]
            consoleID = None
            discordID = None

            if (checkid.startswith("0x")): # Console ID
                try:
                    consoleID = int(checkid, 16)
                except:
                    await message.reply("Invalid console ID provided.")
                    return
                discordID = currDatabase.get_discord_link_console(consoleID)
            else:
                try:
                    discordID = get_from_mention(checkid).id
                except:
                    await message.reply("Invalid discord ID provided.")
                    return
                consoleID = currDatabase.get_discord_link_user(discordID)

            if (consoleID is None or discordID is None):
                await message.reply("Specified ID has no link established.")
                return

            if (discordID is None):
                discordID = currDatabase.get_discord_link_console(consoleID)
            currDatabase.delete_discord_link_console(consoleID)
            queue_player_role_update(discordID)
            await message.reply("Operation succeeded.")
        else:
            tag = get_server_bot_args(message.content)
            if (len(tag) != 2):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + server_help_array()["unlink"] + "```")
                return
            consoleID = currDatabase.get_discord_link_user(message.author.id)
            if (consoleID is None):
                await message.reply("There is no console linked with your account.")
                return
            currDatabase.delete_discord_link_console(consoleID)
            queue_player_role_update(message.author.id)
            await message.reply("Operation succeeded.")
    elif bot_cmd == "manage_vr":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 5 and len(tag) != 6):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            game = tag[4]
            consoleID = tag[3]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
                if (consoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if mode not in ["get", "set"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if game not in ["ctww", "cd", "points"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if (mode == "get"):
                if (game == "ctww" or game == "cd"):
                    vrData = currDatabase.get_console_vr(consoleID)
                    vr = vrData.ctVR if game == "ctww" else vrData.cdVR
                    vrPos = vrData.ctPos if game == "ctww" else vrData.cdPos
                    await message.reply("Console has {} VR (Position: {}) in {}".format(vr, vrPos, "Custom Tracks" if game == "ctww" else "Countdown"))
                elif (game == "points"):
                    pointData = currDatabase.get_console_points(consoleID)
                    await message.reply("Console has {} Points (Position: {})".format(pointData[0], pointData[1]))
            else:
                if (len(tag) != 6):
                    await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                    return
                try:
                    vr = int(tag[5])
                    if (game != "points"):
                        if (vr < 1 or vr > 99999):
                            raise ValueError()
                except ValueError:
                    await message.reply( "Invalid number.")
                    return
                if (game == "ctww" or game == "cd"):
                    vrData = currDatabase.get_console_vr(consoleID)
                    vrData = list((vrData.ctVR, vrData.cdVR))
                    vrData[0 if game == "ctww" else 1] = vr
                    currDatabase.set_console_vr(consoleID, tuple(vrData))
                elif (game == "points"):
                    currDatabase.set_console_points(consoleID, vr)
                await message.reply( "Operation succeeded.")
    elif bot_cmd == "transfer":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            srcConsoleID = tag[2]
            if (srcConsoleID.startswith("0x")):
                srcConsoleID = srcConsoleID[2:]
            try:
                srcConsoleID = int(srcConsoleID, 16)
                if (srcConsoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply( "Invalid source console ID.")
                return
            dstConsoleID = tag[3]
            if (dstConsoleID.startswith("0x")):
                dstConsoleID = dstConsoleID[2:]
            try:
                dstConsoleID = int(dstConsoleID, 16)
                if (dstConsoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply( "Invalid destination console ID.")
                return
            res = transfer_console_data(ctgp7_server, srcConsoleID, dstConsoleID, isCitra)
            if (res == ""):
                await message.reply( "Operation succeeded.")
            else:
                await message.reply( "Operation failed:```{}```".format(res))
    elif bot_cmd == "apply_player_role":
        if (isCitra):
            await message.reply("Operation not supported with Citra.")
            return

        if await staff_server_can_execute(message, bot_cmd):
            await message.channel.send("WARNING: This operation is slow and will take some time!")
            allCons = currDatabase.get_all_discord_link()
            total = 0
            curr = 0
            for ac in allCons:
                userID = ac[1]
                member = get_from_mention(userID)
                if (member is not None):
                    queue_player_role_update(member.id)
                    curr += 1
                total += 1
            await message.reply("Done! Success: {}, Fail: {}".format(curr, total - curr))
    elif bot_cmd == "purge_console_link":
        if (isCitra):
            await message.reply("Operation not supported with Citra.")
            return
        
        if await staff_server_can_execute(message, bot_cmd):
            allCons = currDatabase.get_all_discord_link()
            total = 0
            for ac in allCons:
                userID = ac[1]
                member = get_from_mention(userID)
                if (member is None):
                    currDatabase.delete_discord_link_user(userID)
                    total += 1
            await message.reply("Done! Purged {} users.".format(total))
    elif bot_cmd == "get_mii_icon":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["get_mii_icon"] + "```")
                return
            try:
                consoleID = int(tag[2], 16)
            except:
                await message.reply("Invalid console ID provided.")
                return
            miiIcon = currCtwwHandler.getMiiIcon(consoleID)
            miiName = currDatabase.get_console_last_name(consoleID)
            if (miiIcon is None):
                await message.reply("Specified ID has no mii icon.")
                return
            with io.BytesIO() as image_binary:
                miiIcon.save(image_binary, 'PNG')
                image_binary.seek(0)
                await message.reply("Mii for {}:".format(miiName), file=discord.File(fp=image_binary, filename='mii.png'))
    elif bot_cmd == "name_history":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["name_history"] + "```")
                return
            try:
                consoleID = int(tag[2], 16)
            except:
                await message.reply("Invalid console ID provided.")
                return
            name_list = currDatabase.get_console_name_history(consoleID)
            msg = "Name history for specified ID: ```\n"
            for name in name_list:
                msg += "{} ({})\n".format(name[0], str(datetime.datetime.fromtimestamp(float(name[1]))))
            msg += "```"
            await message.reply(msg)
    elif bot_cmd == "config":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 3 and len(tag) != 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()["config"] + "```")
                return
            mode = tag[2]
            if mode not in ["ctCPUAmount", "cdCPUAmount", "rubberBMult", "rubberBOffset", "blockedTrackHistory", "serveraddr", "serveravailable", "vrmultiplier", "allowedCharacters", "allowedTracks"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()["config"] + "```")
                return
            if (len(tag) == 3):
                version = -1
                if mode == "ctCPUAmount":
                    amount = currDatabase.get_room_player_amount(False)
                elif mode == "cdCPUAmount":
                    amount = currDatabase.get_room_player_amount(True)
                elif mode == "rubberBMult":
                    amount = currDatabase.get_room_rubberbanding_config(False)
                elif mode == "rubberBOffset":
                    amount = currDatabase.get_room_rubberbanding_config(True)
                elif mode == "blockedTrackHistory":
                    amount = currDatabase.get_room_blocked_track_history_count()
                elif mode == "serveraddr":
                    amount = currDatabase.get_ctgp7_server_address()
                elif mode == "serveravailable":
                    amount = currDatabase.get_ctgp7_server_available()
                elif mode == "vrmultiplier":
                    amount = currDatabase.get_vr_multiplier()
                elif mode == "allowedCharacters":
                    amount = currDatabase.get_allowed_characters()
                await message.reply( "Config for \"{}\" is: {}".format(mode, amount))
                return
            else:
                try:
                    if (mode == "ctCPUAmount" or mode == "cdCPUAmount" or mode == "blockedTrackHistory" or mode == "serveravailable"):
                        amount = int(tag[3])
                    elif (mode == "rubberBMult" or mode == "rubberBOffset" or mode == "vrmultiplier"):
                        amount = float(tag[3])
                    elif (mode == "serveraddr"):
                        amount = str(tag[3])
                        if not ":" in amount:
                            raise ValueError()
                    elif (mode == "allowedCharacters" or mode == "allowedTracks"):
                        amount = str(tag[3])
                        if amount == "clear":
                            amount = ""
                except ValueError:
                    await message.reply("Invalid format.")
                    return
                if mode == "ctCPUAmount":
                    currDatabase.set_room_player_amount(False, amount)
                elif mode == "cdCPUAmount":
                    currDatabase.set_room_player_amount(True, amount)
                elif mode == "rubberBMult":
                    currDatabase.set_room_rubberbanding_config(False, amount)
                elif mode == "rubberBOffset":
                    currDatabase.set_room_rubberbanding_config(True, amount)
                elif mode == "blockedTrackHistory":
                    currDatabase.set_room_blocked_track_history_count(amount)
                elif mode == "serveraddr":
                    currDatabase.set_ctgp7_server_address(amount)
                elif mode == "serveravailable":
                    currDatabase.set_ctgp7_server_available(amount)
                elif mode == "vrmultiplier":
                    currDatabase.set_vr_multiplier(amount)
                elif mode == "allowedCharacters":
                    currDatabase.set_allowed_characters(amount)
                elif mode == "allowedTracks":
                    currDatabase.set_allowed_tracks(amount)
                await message.reply("Config for \"{}\" is: {}".format(mode, amount))
                return
    elif bot_cmd == "otplegality":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) != 4 and len(tag) != 3):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            consoleID = None
            if mode != "getall":
                if (len(tag) != 4):
                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                    return
                consoleID = tag[3]
                if (consoleID.startswith("0x")):
                    consoleID = consoleID[2:]
                try:
                    consoleID = int(consoleID, 16)
                    if (consoleID == 0):
                        raise ValueError()
                except ValueError:
                    await message.reply("Invalid console ID.")
                    return
            else:
                if (len(tag) != 3):
                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                    return
            if mode not in ["getall", "get", "set", "clear"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format(mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if (mode == "get"):
                islegal = currDatabase.get_console_legality(consoleID)
                await message.reply("Console is legal." if islegal else "Console is NOT legal.")
            if (mode == "getall"):
                allilegal = currDatabase.getall_console_legality()
                info = ""
                for e in allilegal: info += "0x{:016X}\n".format(e)
                if len(info) == 0:
                    info = " "
                await sendMultiMessage(message.channel, info, "```\n---------------\n", "---------------\n```\n")
            if (mode == "set"):
                currDatabase.set_console_legality(consoleID)
                await message.reply( "Operation succeeded.")
            if (mode == "clear"):
                currDatabase.clear_console_legality(consoleID)
                await message.reply( "Operation succeeded.")
    elif bot_cmd == "consoleserver":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content, 4)
            if (len(tag) != 4 and len(tag) != 5):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            consoleID = tag[3]
            if (consoleID.startswith("0x")):
                consoleID = consoleID[2:]
            try:
                consoleID = int(consoleID, 16)
                if (consoleID == 0):
                    raise ValueError()
            except ValueError:
                await message.reply( "Invalid console ID.")
                return
            if mode not in ["get", "set", "clear"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if (mode == "get"):
                serveraddr = currDatabase.get_console_unique_server_address(consoleID)
                if serveraddr is None:
                    await message.reply("Specified console has no unique server address.")
                else:
                    await message.reply("Server address for specified console is `{}`".format(serveraddr))
            elif (mode == "set"):
                if (len(tag) != 5):
                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                    return
                serveraddr = tag[4]
                currDatabase.set_console_unique_server_address(consoleID, serveraddr)
                await message.reply( "Operation succeeded.")
            elif (mode == "clear"):
                currDatabase.clear_console_unique_server_address(consoleID)
                await message.reply( "Operation succeeded.")
    elif bot_cmd == "banned_ultra_shortcut":
        if await staff_server_can_execute(message, bot_cmd):
            tag = get_server_bot_args(message.content)
            if (len(tag) < 4):
                await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                return
            mode = tag[2]
            track = tag[3]
            if mode not in ["get", "set", "clear"]:
                await message.reply( "Invalid option `{}`, correct usage:\r\n```".format( mode) + staff_server_help_array()[bot_cmd] + "```")
                return
            if mode == "get":
                bannedsc = currDatabase.get_track_banned_ultrasc(track)
                msg ="Banned shortcuts for specified track:\n```\n"
                for entry in bannedsc:
                    msg += "- from_min: {:.04f}, from_max: {:.04f}, to_min: {:.04f}, to_max: {:.04f}, trigger: {:.04f}\n".format(entry[0], entry[1], entry[2], entry[3], entry[4])
                msg += "```"
                await message.reply(msg)
            elif mode == "clear":
                currDatabase.clear_track_banned_ultrasc(track)
                await message.reply( "Operation succeeded.")
            elif mode == "set":
                entry = tag[4:]
                if (len(entry) != 5):
                    await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                    return
                entryfloats = []
                for e in entry:
                    try:
                        entryfloats.append(float(e))
                    except:
                        await message.reply( "Invalid syntax, correct usage:\r\n```" + staff_server_help_array()[bot_cmd] + "```")
                        return
                currDatabase.set_track_banned_ultrasc(track, entryfloats[0], entryfloats[1], entryfloats[2], entryfloats[3], entryfloats[4])

                bannedsc = currDatabase.get_track_banned_ultrasc(track)
                msg ="Set banned shortcuts for specified track:\n```\n"
                for entry in bannedsc:
                    msg += "- from_min: {:.04f}, from_max: {:.04f}, to_min: {:.04f}, to_max: {:.04f}, trigger: {:.04f}\n".format(entry[0], entry[1], entry[2], entry[3], entry[4])
                msg += "```"
                await message.reply(msg)


    else:
        await message.reply( "Invalid server command, use `@RedYoshiBot server help` to get all the available server commands.")
        
def handler_server_init_loop(ctgp7_server: CTGP7ServerHandler):
    asyncio.ensure_future(server_bot_loop(ctgp7_server))