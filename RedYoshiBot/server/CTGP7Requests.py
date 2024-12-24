import sqlite3
import traceback
import time
import datetime
import random

from ..CTGP7Defines import CTGP7Defines
from .CTGP7ServerDatabase import CTGP7ServerDatabase, ConsoleMessageType
from .CTGP7CtwwHandler import CTGP7CtwwHandler, CTWWLoginStatus

class CTGP7Requests:

    statsList = {
        "launches",
		"races",
		"ttrials",
		"coin_battles",
		"balloon_battles",
		"online_races",
		"comm_races",
		"ctww_races",
		"cd_races",
		"online_coin_battles",
		"online_balloon_battles",
        "failed_mission#2",
        "completed_mission#2",
        "perfect_mission#2",
        "custom_mission#2",
        "grademean_mission#2",
        "gradecount_mission#2",
        "race_points"
    }

    badge_ids = {
        "PLAYER": 0x3948021956F56992,
        "BRONZE_PLAYER": 0x7C75C991E735033D,
        "SILVER_PLAYER": 0x7E0955D6480E675E,
        "GOLD_PLAYER": 0x32D6D624AFA2D9B0,
        "EMERALD_PLAYER": 0x1CCC2665E559048F,
        "DIAMOND_PLAYER": 0x4957511C8EFE3A8A,
        "RAINBOW_PLAYER": 0x0721EFB83424F89F,
        "DISCORD_LINK": 0x005BEE8EE0F9EE79,
        "CONTRIBUTOR": 0x3AEF2F9B8A3DA167,
        "CURRENT_SERVER_BOOSTER": 0x242239C1E96A2B37,
        "SERVER_BOOSTER": 0x3A20DBEE90993942,
    }

    get_user_info = None
    unlink_console = None
    queue_player_role_update = None

    pendingDiscordLinks = {}

    def __init__(self, database: CTGP7ServerDatabase, ctwwHandler: CTGP7CtwwHandler, request: dict, debug: bool, consoleID: int, isCitra: bool):
        self.req = request
        self.info = ""
        self.debug = debug
        self.currDatabase = database
        self.currCtwwHandler = ctwwHandler
        self.cID = consoleID
        self.isCitra = isCitra

    def handle_status(self, input):
        STATUS_VERSION = 0
        
        version = input.get("version")
        if version is None or version != STATUS_VERSION:
            return

        queue_update = False
        
        count = 0
        for s in CTGP7ServerDatabase.allowed_console_status:
            prev = self.currDatabase.get_console_status(self.cID, s) == 1
            new = input.get(s, False)
            if new: count += 1
            if (not prev and new):
                self.currDatabase.set_console_status(self.cID, s, 1)
                queue_update = True
        
        badges = self.currDatabase.get_console_badges(self.cID)

        if count >= 1 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["BRONZE_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["BRONZE_PLAYER"])
        if count >= 2 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["SILVER_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["SILVER_PLAYER"])
        if count >= 3 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["GOLD_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["GOLD_PLAYER"])
        if count >= 4 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["EMERALD_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["EMERALD_PLAYER"])
        if count >= 5 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["DIAMOND_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["DIAMOND_PLAYER"])
        if count >= 6 and not self.currDatabase.has_console_badge(self.cID, CTGP7Requests.badge_ids["RAINBOW_PLAYER"], badges):
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["RAINBOW_PLAYER"])

        contrib_badge = False
        booster_badge = False
        discordLink = self.currDatabase.get_discord_link_console(self.cID)
        if discordLink is not None:
            (_, usrInfoPrivate) = CTGP7Requests.get_user_info(discordLink)
            if usrInfoPrivate is not None:
                contrib_badge = usrInfoPrivate["contrib"]
                booster_badge = usrInfoPrivate["booster"]
        if contrib_badge:
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["CONTRIBUTOR"])
        if booster_badge:
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["CURRENT_SERVER_BOOSTER"])
            self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["SERVER_BOOSTER"])
        else:
            self.currDatabase.ungrant_badge(self.cID, CTGP7Requests.badge_ids["CURRENT_SERVER_BOOSTER"])

        if (queue_update):
            discordID = self.currDatabase.get_discord_link_console(self.cID)
            if (discordID is not None):
                CTGP7Requests.queue_player_role_update(discordID)

    def put_stats(self, input):
        msgSeqID = 0
        if (not "seqID" in input):
            return (-1, 0)
        msgSeqID = input["seqID"]
        isFirstReport = input.get("firstReport", False)
        self.currDatabase.grant_badge(self.cID, CTGP7Requests.badge_ids["PLAYER"])
        if (len(input) == 1):
            if (msgSeqID == 0): # Request sequence ID
                seqID = self.currDatabase.get_stats_seqid(self.cID)
                if (seqID == 0):
                    self.currDatabase.increment_today_unique_consoles()
                    seqID = self.currDatabase.fetch_stats_seqid(self.cID)
                return (1, seqID)
            else:
                return (-1, 0)
        else:
            if (msgSeqID != 0 and msgSeqID == self.currDatabase.get_stats_seqid(self.cID)): # Sequence ID is valid
                if (isFirstReport):
                    self.currDatabase.increment_today_launches()
                for k in input:
                    # Fix typo in the plugin
                    namefixed = k
                    if k == "completed_missionv#2":
                        namefixed = "completed_mission#2"
                    if (namefixed in CTGP7Requests.statsList):
                        self.currDatabase.increment_general_stats(namefixed.split("#", 1)[0], input[k])
                    elif (k == "played_tracks"):
                        for t in input[k]:
                            self.currDatabase.increment_track_frequency(t, input[k][t])
                    elif (k == "status"):
                        self.handle_status(input[k])
                self.currDatabase.set_stats_dirty(True)
                return (0, self.currDatabase.fetch_stats_seqid(self.cID))
            else: # Sequence ID is invalid
                seqID = self.currDatabase.get_stats_seqid(self.cID)
                if (seqID == 0):
                    seqID = self.currDatabase.fetch_stats_seqid(self.cID)
                return (2, seqID)
    
    def put_statsv2(self, input):
        ret = self.put_stats(input)
        retVal = {}
        retVal["seqID"] = ret[1]
        if (ret[0] == 0):
            pts = ()
            if ("race_points" in input):
                pts = self.currDatabase.add_console_points(self.cID, input["race_points"])
                self.currDatabase.set_stats_dirty(True)
            else:
                pts = self.currDatabase.get_console_points(self.cID)
            retVal["points"] = pts[0]
            retVal["pointsPos"] = pts[1]
            badge_list = self.currDatabase.get_console_badges(self.cID)
            badges = b""
            times = b""
            for b in badge_list:
                badges += b[0].to_bytes(8, "little")
                times += b[1].to_bytes(8, "little")
            retVal["badges"] = badges
            retVal["badge_times"] = times
        return (ret[0], retVal)

    def req_online_token(self, input):
        if (not "password" in input):
            return (-1, 0)
        token = self.currCtwwHandler.generate_password_token(str(input["password"]))
        timenow = datetime.datetime.utcnow()
        server_addr = self.currDatabase.get_console_unique_server_address(self.cID)
        if server_addr is None:
            server_addr = self.currDatabase.get_ctgp7_server_address()
        addrport = server_addr.split(":")
        serveravailable = self.currDatabase.get_ctgp7_server_available() != 0 or self.currDatabase.get_console_is_admin(self.cID)
        return (0, {"online_token": token, "server_time": int(timenow.strftime("%Y%m%d%H%M%S")), "address": str(addrport[0]), "port": int(addrport[1]), "available": serveravailable})

    def req_unique_pid(self, input):
        return (0, {"unique_pid": self.currDatabase.fetch_unique_PID()})
    
    def req_discord_info(self, input):
        if (self.isCitra):
            return (-1, 0)
        unlink = input.get("unlink")
        if unlink is not None and unlink:
            CTGP7Requests.unlink_console(self.currDatabase, self.cID)
            return (0, {})
        discordLink = self.currDatabase.get_discord_link_console(self.cID)
        if (discordLink is None):
            if ("request" in input and input["request"]):
                if (not self.cID in CTGP7Requests.pendingDiscordLinks):
                    CTGP7Requests.pendingDiscordLinks[self.cID] = random.getrandbits(32) | 1
                return (1, {"code" : CTGP7Requests.pendingDiscordLinks[self.cID]})
            else:
                return (1, {})
        else:
            if (self.cID in CTGP7Requests.pendingDiscordLinks):
                del CTGP7Requests.pendingDiscordLinks[self.cID]
            (usrInfo, _) = CTGP7Requests.get_user_info(discordLink)
            if (usrInfo is None):
                self.currDatabase.delete_discord_link_console(self.cID)
                self.currDatabase.ungrant_badge(self.cID, CTGP7Requests.badge_ids["DISCORD_LINK"])
                return self.req_discord_info(input)
            return (0, usrInfo)

    def get_beta_version(self, input):
        
        if (type(input) is not int):
            return (-1, 0)

        return (0 if self.currDatabase.get_beta_version() == input else 1, 0)

    def server_login_handler(self, input):
        return self.currCtwwHandler.handle_user_login(input, self.cID)

    def server_logout_handler(self, input):
        return self.currCtwwHandler.handle_user_logout(input, self.cID)

    def server_user_room_join_handler(self, input):
        return self.currCtwwHandler.handle_user_room_join(input, self.cID)

    def server_user_room_prepare_handler(self, input):
        return self.currCtwwHandler.handle_user_prepare_room(input, self.cID)

    def server_user_room_racestart_handler(self, input):
        return self.currCtwwHandler.handle_user_racestart_room(input, self.cID)

    def server_user_room_racefinish_handler(self, input):
        return self.currCtwwHandler.handle_user_racefinish_room(input, self.cID)

    def server_user_room_watch_handler(self, input):
        return self.currCtwwHandler.handle_user_watch_room(input, self.cID)
    
    def server_user_room_leave_handler(self, input):
        return self.currCtwwHandler.handle_user_leave_room(input, self.cID)

    def server_user_heartbeat(self, input):
        return self.currCtwwHandler.handle_user_heartbeat(input, self.cID)
    
    def server_get_room_charids(self, input):
        return self.currCtwwHandler.handle_get_room_char_ids(input.get("gatherID"))
    
    def server_get_console_message(self, input):
        localver = input.get("localVer")
        if localver is None: localver = -1
        if (self.currDatabase.get_ctww_version() != localver):
            return (CTWWLoginStatus.VERMISMATCH.value, {})
        message = self.currCtwwHandler.get_console_message(self.cID)
        if message is None:
            return (0, {})
        retDict = {}
        retDict["loginMessage"] = message[1]
        return (message[0], retDict)

    def server_get_badges(self, input):
        badge_list = input.get("badges")
        if (type(badge_list) is not bytes):
            return (-1, 0)
        
        ret = {}
        for i in range(0, len(badge_list), 8):
            bID = int.from_bytes(badge_list[i:i+8], "little")
            badge = self.currDatabase.get_badge(bID)
            if badge is None:
                continue
            badge_dict = {}
            badge_dict["name"] = badge[1]
            badge_dict["desc"] = badge[2]
            badge_dict["icon"] = badge[3]
            ret["badge_{}".format(str(bID))] = badge_dict
        return (0, ret)

    def put_mii_icon(self, input):
        miiIcon = input.get("miiIcon")
        miiIconChecksum = input.get("miiIconChecksum")
        if (miiIcon is None or miiIconChecksum is None):
            return (-1, 0)
        self.currDatabase.set_mii_icon(self.cID, miiIcon, miiIconChecksum)
        return (0, 0)
    
    def put_ultra_shortcut(self, input):
        with self.currCtwwHandler.lock:
            if not self.cID in self.currCtwwHandler.loggedUsers: return
        self.currDatabase.set_console_message(self.cID, ConsoleMessageType.TIMED_KICKMESSAGE.value, "Use of ultrashortcut", 60)
        self.currCtwwHandler.kick_user(self.cID)
        return (0, 0)

    request_functions = {
        "betaver": get_beta_version,
        "login": server_login_handler,
        "logout": server_logout_handler,
        "discordinfo": req_discord_info,
        "onlinetoken": req_online_token,
        "uniquepid": req_unique_pid,
        "roomcharids": server_get_room_charids,
        "message": server_get_console_message,
        "badges": server_get_badges,
    }

    put_functions = {
        "generalstatsv2": put_statsv2,
        "onlsearch": server_user_room_join_handler,
        "onlprepare": server_user_room_prepare_handler,
        "onlrace": server_user_room_racestart_handler,
        "onlracefinish": server_user_room_racefinish_handler,
        "onlwatch": server_user_room_watch_handler,
        "onlleaveroom": server_user_room_leave_handler,
        "hrtbt": server_user_heartbeat,
        "miiicon": put_mii_icon,
        "ultrashortcut": put_ultra_shortcut,
    }

    hide_logs_input = [
        "miiicon",
    ]

    hide_logs_output = [
        "onlinetoken",
        "badges",
    ]

    def solve(self):
        outData = {}
        requestList = ""
        putList = ""
        for k in self.req.keys():
            if (len(k) > 4 and k.startswith("req_")):
                reqType = k[4:]
                outData[k] = {}
                inData = {}
                res = -1
                value = 0
                try:
                    inData = self.req[k]["value"]
                    res, value = CTGP7Requests.request_functions[reqType](self, inData)
                    outData[k]["res"] = res
                    outData[k]["value"] = value
                except:
                    traceback.print_exc()
                    outData[k]["res"] = -1
                if reqType in CTGP7Requests.hide_logs_input:
                    inData = "__HIDDEN__"
                if reqType in CTGP7Requests.hide_logs_output:
                    value = "__HIDDEN__"
                requestList += "  " + k + "\n    in:\n      {}\n    res:\n      {}\n    out:\n      {}\n".format(inData, res, value)
            elif (len(k) > 4 and k.startswith("put_")):
                putType = k[4:]
                outData[k] = {}
                inData = {}
                res = -1
                value = 0
                try:
                    inData = self.req[k]["value"]
                    res, value = CTGP7Requests.put_functions[putType](self, inData)
                    outData[k]["res"] = res
                    outData[k]["value"] = value
                except:
                    traceback.print_exc()
                    outData[k]["res"] = -1
                if putType in CTGP7Requests.hide_logs_input:
                    inData = "__HIDDEN__"
                if putType in CTGP7Requests.hide_logs_output:
                    value = "__HIDDEN__"
                putList += "  " + k + "\n    in:\n      {}\n    res:\n      {}\n    out:\n      {}\n".format(inData, res, value)
        self.info = ""
        if (requestList != ""):
            self.info += "Requests:\n" + requestList + "\n"
        if (putList != ""):
            self.info += "Puts:\n" + putList + "\n"
        return outData