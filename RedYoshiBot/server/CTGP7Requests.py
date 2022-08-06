import sqlite3
import traceback
import time
import random

from ..CTGP7Defines import CTGP7Defines
from .CTGP7ServerDatabase import CTGP7ServerDatabase
from .CTGP7CtwwHandler import CTGP7CtwwHandler

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
        "failed_mission",
        "completed_mission",
        "perfect_mission",
        "custom_mission",
        "grademean_mission",
        "gradecount_mission",
        "race_points"
    }

    get_user_info = None

    pendingDiscordLinks = {}

    def __init__(self, database: CTGP7ServerDatabase, ctwwHandler: CTGP7CtwwHandler, request: dict, debug: bool, consoleID: int):
        self.req = request
        self.info = ""
        self.debug = debug
        self.database = database
        self.ctwwHandler = ctwwHandler
        self.cID = consoleID

    def put_stats(self, input):
        msgSeqID = 0
        if (not "seqID" in input):
            return (-1, 0)
        msgSeqID = input["seqID"]
        isFirstReport = input.get("firstReport", False)
        if (len(input) == 1):
            if (msgSeqID == 0): # Request sequence ID
                seqID = self.database.get_stats_seqid(self.cID)
                if (seqID == 0):
                    self.database.increment_today_unique_consoles()
                    seqID = self.database.fetch_stats_seqid(self.cID)
                return (1, seqID)
            else:
                return (-1, 0)
        else:
            if (msgSeqID != 0 and msgSeqID == self.database.get_stats_seqid(self.cID)): # Sequence ID is valid
                if (isFirstReport):
                    self.database.increment_today_launches()
                for k in input:
                    if (k in CTGP7Requests.statsList):
                        self.database.increment_general_stats(k, input[k])
                    elif (k == "played_tracks"):
                        for t in input[k]:
                            self.database.increment_track_frequency(t, input[k][t])
                self.database.set_stats_dirty(True)
                return (0, self.database.fetch_stats_seqid(self.cID))
            else: # Sequence ID is invalid
                seqID = self.database.get_stats_seqid(self.cID)
                if (seqID == 0):
                    seqID = self.database.fetch_stats_seqid(self.cID)
                return (2, seqID)
    
    def put_statsv2(self, input):
        ret = self.put_stats(input)
        retVal = {}
        retVal["seqID"] = ret[1]
        if (ret[0] == 0):
            pts = ()
            if ("race_points" in input):
                pts = self.database.add_console_points(self.cID, input["race_points"])
                self.database.set_stats_dirty(True)
            else:
                pts = self.database.get_console_points(self.cID)
            retVal["points"] = pts[0]
            retVal["pointsPos"] = pts[1]
        return (ret[0], retVal)

    def req_discord_info(self, input):
        discordLink = self.database.get_discord_link_console(self.cID)
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
            usrInfo = CTGP7Requests.get_user_info(discordLink)
            if (usrInfo is None):
                self.database.delete_discord_link_console(self.cID)
                return self.req_discord_info(input)
            return (0, usrInfo)

    def get_beta_version(self, input):
        
        if (type(input) is not int):
            return (-1, 0)

        return (0 if self.database.get_beta_version() == input else 1, 0)

    def server_login_handler(self, input):
        return self.ctwwHandler.handle_user_login(input, self.cID)

    def server_logout_handler(self, input):
        return self.ctwwHandler.handle_user_logout(input, self.cID)

    def server_user_room_join_handler(self, input):
        return self.ctwwHandler.handle_user_room_join(input, self.cID)

    def server_user_room_prepare_handler(self, input):
        return self.ctwwHandler.handle_user_prepare_room(input, self.cID)

    def server_user_room_racestart_handler(self, input):
        return self.ctwwHandler.handle_user_racestart_room(input, self.cID)

    def server_user_room_racefinish_handler(self, input):
        return self.ctwwHandler.handle_user_racefinish_room(input, self.cID)

    def server_user_room_watch_handler(self, input):
        return self.ctwwHandler.handle_user_watch_room(input, self.cID)
    
    def server_user_room_leave_handler(self, input):
        return self.ctwwHandler.handle_user_leave_room(input, self.cID)

    def server_user_heartbeat(self, input):
        return self.ctwwHandler.handle_user_heartbeat(input, self.cID)
    
    def put_mii_icon(self, input):
        miiIcon = input.get("miiIcon")
        miiIconChecksum = input.get("miiIconChecksum")
        if (miiIcon is None or miiIconChecksum is None):
            return (-1, 0)
        self.database.set_mii_icon(self.cID, miiIcon, miiIconChecksum)
        return (0, 0)

    request_functions = {
        "betaver": get_beta_version,
        "login": server_login_handler,
        "logout": server_logout_handler,
        "discordinfo": req_discord_info
    }

    put_functions = {
        "generalstats": put_stats,
        "generalstatsv2": put_statsv2,
        "onlsearch": server_user_room_join_handler,
        "onlprepare": server_user_room_prepare_handler,
        "onlrace": server_user_room_racestart_handler,
        "onlracefinish": server_user_room_racefinish_handler,
        "onlwatch": server_user_room_watch_handler,
        "onlleaveroom": server_user_room_leave_handler,
        "hrtbt": server_user_heartbeat,
        "miiicon": put_mii_icon
    }

    hide_logs_input = [
        "miiicon"
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
                putList += "  " + k + "\n    in:\n      {}\n    res:\n      {}\n    out:\n      {}\n".format(inData, res, value)
        self.info = ""
        if (requestList != ""):
            self.info += "Requests:\n" + requestList + "\n"
        if (putList != ""):
            self.info += "Puts:\n" + putList + "\n"
        return outData