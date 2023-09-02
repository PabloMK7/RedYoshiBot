from PIL import Image
from .CTGP7ServerDatabase import CTGP7ServerDatabase, ConsoleMessageType
from ..CTGP7Defines import CTGP7Defines
from enum import Enum
import time
import datetime
import textwrap
import uuid
import threading
import random
import string
import subprocess
import sys
from collections import deque

current_time_min = lambda: int(round(time.time() / 60))

class PlayerNameMode(Enum):
    HIDDEN = 0
    SHOW = 1
    CUSTOM = 2

class CTWWLoginStatus(Enum):
    SUCCESS = 0
    NOTLOGGED = 1
    PROCESSING = 2
    FAILED = 3
    VERMISMATCH = 4
    MESSAGE = 5
    MESSAGEKICK = 6

class UserState(Enum):
    IDLE = 0
    SEARCHING = 1
    WATCHING = 2
    HOSTING = 3
    CLIENT = 4

class RoomState(Enum):
    SEARCHING = 0
    PREPARING_RACE = 1
    RACING = 2
    FINISHED = 3

class StarGrade(Enum):
    NONE = 0
    # Unused
    C = 1
    B = 2
    A = 3
    # Used
    STAR_1 = 4
    STAR_2 = 5
    STAR_3 = 6
    # Custom
    CUSTOM_PLAYER = 7
    CUSTOM_BRONZE = 8
    CUSTOM_SILVER = 9
    CUSTOM_GOLD = 10
    CUSTOM_DIAMOND = 11
    CUSTOM_RAINBOW = 12
    # Invalid
    INVALID = 0xFF

class OnlineUserName:
    def __init__(self, mode: int, name: str, miiName: str):
        self.mode = mode
        self.name = name
        self.miiName = miiName

    def getMiiName(self):
        return self.miiName
    
    def __str__(self):
        if (self.mode == PlayerNameMode.HIDDEN.value):
            return "Player"
        elif (self.mode == PlayerNameMode.SHOW.value or self.mode == PlayerNameMode.CUSTOM.value):
            if (self.name is None):
                return "(Unknown)"
            else:
                return self.name.replace("`", "'")

class OnlineUser:
    def __init__(self, name: OnlineUserName, consoleID: int, isVerified: bool):
        self.lastActivity = datetime.datetime.utcnow()
        self.name = name
        self.cID = consoleID
        self.state = UserState.IDLE.value
        self.token = uuid.uuid1().int>>64
        self.isVerified = isVerified
        self.vr = [1000, 1000]
        self.vrIncr = None
        self.debug = False
        self.isctgp7network = False

    def setDebug(self):
        self.debug = True

    def isDebug(self):
        return self.debug
    
    def setCTGP7Network(self, isCTGP7Network: bool):
        self.isctgp7network = isCTGP7Network
    
    def getCTGP7Network(self):
        return self.isctgp7network

    def setVR(self, vr):
        self.vr = vr
    
    def getVR(self):
        return self.vr

    def setVRIncr(self, vrIncr):
        self.vrIncr = vrIncr

    def getVRIncr(self):
        return self.vrIncr

    def setState(self, state: int):
        self.state = state

    def getState(self):
        return self.state
    
    def getToken(self):
        return self.token
    
    def isAlive(self):
        self.lastActivity = datetime.datetime.utcnow()

    def lastActive(self):
        return self.lastActivity

    def getStateName(self):
        if (self.state == UserState.SEARCHING.value):
            return "(Searching)"
        elif (self.state == UserState.WATCHING.value):
            return "(Watching)"
        elif (self.state == UserState.HOSTING.value):
            return "(Host)"
        elif(self.state == UserState.CLIENT.value):
            return "(Client)"
        return ""

    def getMiiName(self):
        return self.name.getMiiName()

    def getName(self):
        return str(self.name)
    
    def verified(self):
        return self.isVerified

    def __hash__(self):
        return hash(self.cID)
    
    def __eq__(self,other):
        return self.cID == other.cID

class OnlineRoom:
    def __init__(self, gID: int, gamemode: int):
        self.gID = gID
        self.gamemode = gamemode
        self.roomKeySeed = random.getrandbits(64)
        self.players = set()
        self.state = RoomState.SEARCHING.value
        self.race = ""
        self.messageID = 0
        self.needsUpdate = True
        self.isDisbanding = False
        self.logToStaff = False
        self.cpuRandomSeed = random.getrandbits(31)
        self.trackHistory = deque()

    def joinPlayer(self, user: OnlineUser):
        self.players.add(user.cID)
        self.needsUpdate = True
    
    def getKeySeed(self, user):
        return self.roomKeySeed + (1 if user is not None and user.isDebug() else 0)
    
    def removePlayer(self, user: OnlineUser=None, cID:int =None):
        cidRem = None
        if (user is not None):
            cidRem = user.cID
        elif (cID is not None):
            cidRem = cID
        self.players.discard(cidRem)
        self.needsUpdate = True

    def hasPlayer(self, user: OnlineUser):
        return user.cID in self.players

    def getPlayers(self):
        return self.players

    def playerCount(self):
        return len(self.players)

    def getStateName(self):
        if (self.state == RoomState.SEARCHING.value):
            return "Waiting For Players"
        elif (self.state == RoomState.PREPARING_RACE.value):
            action = "Round" if self.gamemode == 3 else "Race"
            return "Preparing {}".format(action)
        elif (self.state == RoomState.RACING.value):
            action = "Battling" if self.gamemode == 3 else "Racing"
            return "{} ({})".format(action, CTGP7Defines.getTrackNameFromSzs(self.race))
        elif (self.state == RoomState.FINISHED.value):
            action = "Round" if self.gamemode == 3 else "Race"
            return "{} Finished".format(action)
        return ""

    def getModeName(self):
        if (self.gamemode == 0):
            return "Custom Tracks"
        elif (self.gamemode == 1):
            return "Countdown"
        elif (self.gamemode == 2):
            return "Original Tracks"
        elif (self.gamemode == 3):
            return "Battle"
        return ""
    
    def getRoomColor(self): # Returns RGB color
        if (self.gamemode == 0):
            return 0xFF0000
        elif (self.gamemode == 1):
            return 0xFFC000
        elif (self.gamemode == 2):
            return 0x0096FF
        elif (self.gamemode == 3):
            return 0xB500B5
        return 0x000000
    
    def getMode(self):
        return self.gamemode

    def setState(self, state: int):
        self.state = state
        self.needsUpdate = True
    
    def setRace(self, race: str):
        self.race = race
        self.needsUpdate = True

    def getMessageID(self):
        return self.messageID

    def setMessageID(self, messageID: int):
        self.messageID = messageID
    
    def disband(self):
        self.isDisbanding = True
    
    def wasDisbanded(self):
        return self.isDisbanding

    def forceUpdate(self):
        self.needsUpdate = True
    
    def wasUpdated(self):
        return self.needsUpdate
    
    def resetUpdate(self):
        self.needsUpdate = False

    def enableLog(self):
        self.logToStaff = True
    
    def needsLog(self):
        ret = self.logToStaff
        self.logToStaff = False
        return ret
    
    def updateCPURandomSeed(self):
        self.cpuRandomSeed = random.getrandbits(31)

    def getCPURandomSeed(self):
        return self.cpuRandomSeed

    def getMinPlayerAmount(self, database: CTGP7ServerDatabase):
        if (self.gamemode > 1):
            return 1
        return database.get_room_player_amount(self.gamemode == 1)
    
    def getVRMean(self, database: CTGP7ServerDatabase):
        if self.gamemode > 1:
            return 1000
        vrTot = 0
        for cID in self.players:
            vrData = database.get_console_vr(cID)
            vrTot += vrData.ctVR if self.gamemode == 0 else vrData.cdVR
        vrTot //= len(self.players)
        return vrTot
    
    def appendToTrackHistory(self, szsName: str, database: CTGP7ServerDatabase):
        amount = database.get_room_blocked_track_history_count()
        if (szsName in self.trackHistory):
            self.trackHistory.remove(szsName)
        self.trackHistory.append(szsName)
        while (len(self.trackHistory) > amount):
            self.trackHistory.popleft()
    
    def getTrackHistory(self):
        return "::".join(self.trackHistory)


class CTGP7CtwwHandler:
    
    def __init__(self, database: CTGP7ServerDatabase):
        self.database = database
        self.loggedUsers = {}
        self.activeRooms = {}
        self.lock = threading.Lock()
        self.newLogins = 0
        self.newRooms = 0
        self.tokenslock = threading.Lock()
        self.onlinepasswords = {}

    def get_password_from_token(self, token: str):
        with self.tokenslock:
            if (token in self.onlinepasswords):
                password = self.onlinepasswords[token][1]
                del self.onlinepasswords[token]
                return password
            return None
    
    def generate_password_token(self, password: str):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        with self.tokenslock:
            self.onlinepasswords[token] = (datetime.datetime.utcnow(), password)
            return token

    def get_console_message(self, user: OnlineUser):
        msg = self.database.get_console_message(user.cID, user.cID)
        if msg is None:
            return None
        typeStr = ""
        timeStr = ""
        retType = None
        remTime = None if msg[2] is None or msg[3] is None else (msg[2] + msg[3]) - current_time_min()
        if (remTime is not None):
            if (remTime < 1):
                remTime = 1
            days = int(remTime // (60 * 24))
            hours = int((remTime // 60) % 24)
            minutes = int((remTime) % 60)
            remTime = "Time Left: {}d {}h {}m\n".format(days, hours, minutes)
        else:
            remTime = "Time Left: Permanent\n"
        if msg[0] == ConsoleMessageType.SINGLE_MESSAGE.value:
            retType = CTWWLoginStatus.MESSAGE.value
            typeStr = "CTGP-7 Information Message\n"
            timeStr = "\n"
        elif msg[0] == ConsoleMessageType.SINGLE_KICKMESSAGE.value:
            retType = CTWWLoginStatus.MESSAGEKICK.value
            typeStr = "CTGP-7 Kick Message\n"
            timeStr = "\n"
        elif msg[0] == ConsoleMessageType.TIMED_MESSAGE.value:
            retType = CTWWLoginStatus.MESSAGE.value
            typeStr = "CTGP-7 Information Message\n"
            timeStr = remTime
        elif msg[0] == ConsoleMessageType.TIMED_KICKMESSAGE.value:
            retType = CTWWLoginStatus.MESSAGEKICK.value
            typeStr = "CTGP-7 Kick Message\n"
            timeStr = remTime

        if (retType is None):
            return None
        
        msgParts = textwrap.wrap(msg[1], 30)
        msgReal = ""
        for i in range(len(msgParts)):
            if (i != 2):
                addstr = "\n" if i < len(msgParts) - 1 else ""
                msgReal += msgParts[i] + addstr
            else:
                addstr = " [...]" if i < len(msgParts) - 1 else ""
                msgReal += textwrap.shorten(msgParts[i] + addstr, 30)
                break
        return (retType, typeStr + timeStr + "\n" + msgReal)

    def user_login(self, user: OnlineUser):
        self.loggedUsers[user.cID] = user
        self.database.set_console_last_name(user.cID, user.getName())

    def user_logout(self, user: OnlineUser=None, cID=None):
        cidRem = None
        if (user is not None):
            cidRem = user.cID
        elif (cID is not None):
            cidRem = cID
        try:
            del self.loggedUsers[cidRem]
        except:
            pass
    
    def remove_from_all_rooms(self, user: OnlineUser=None, cID: int=None):
        for k in self.activeRooms:
            room = self.activeRooms[k]
            if (user is not None):
                room.removePlayer(user)
            elif (cID is not None):
                room.removePlayer(cID=cID)

    def getUser(self, cID: int, token: int):
        user = self.loggedUsers.get(cID)
        if (user is not None and user.getToken() == token):
            return user
        else:
            return None
    
    def getMiiIconData(self, cID):
        miiIcon = self.database.get_mii_icon(cID)
        if miiIcon is None:
            return None
        process = subprocess.Popen(["./lz77", "d"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(len(miiIcon).to_bytes(4, sys.byteorder))
        process.stdin.write(miiIcon)
        process.stdin.flush()
        uncompData = process.stdout.read()
        process.wait()
        if (process.returncode != 0):
            return None
        return uncompData

    def getMiiIcon(self, cID):
        miiIcon = self.getMiiIconData(cID)
        if (miiIcon is None):
            return None
        
        decoder = TEXRGBA5551(miiIcon, 64, 64)

        im = Image.new("RGBA", (64, 64))
        im.putdata(decoder.ToRGBA8888())
        return im

    def handle_user_login(self, input: dict, cID: int):
        with self.lock:
            nameMode = input.get("nameMode")
            nameValue = input.get("nameValue")
            localver = input.get("localVer")
            betaVer = input.get("localBetaVer")
            isRelogin = input.get("reLogin")
            miiName : str = input.get("miiName")
            isDebug = input.get("debugRegion")
            miiChecksum = input.get("miiIconChecksum")
            isCTGP7Network = input.get("ctgp7network")
            retDict = {}
            
            if (isCTGP7Network is None):
                isCTGP7Network = False

            if (isRelogin is None or localver is None or miiName is None):
                return (-1, {})

            if (not isRelogin and (self.database.get_ctww_version() != localver or (betaVer is not None and self.database.get_beta_version() != betaVer))):
                return (CTWWLoginStatus.VERMISMATCH.value, retDict)

            if (nameMode is None):
                return (-1, {})
            if (nameMode == PlayerNameMode.SHOW.value and nameValue is None):
                return (-1, {})
            if (nameMode == PlayerNameMode.CUSTOM.value and nameValue is None):
                return (-1, {})

            if "%" in miiName or "\\" in miiName or (nameValue is not None and ( "%" in nameValue or "\\" in nameValue)):
                retDict["loginMessage"] = "Invalid name,\nplease change it."
                return (CTWWLoginStatus.MESSAGEKICK.value, retDict)
            
            user = OnlineUser(OnlineUserName(nameMode, nameValue, miiName), cID, self.database.get_console_is_verified(cID))

            consoleMsg = None
            if (not isRelogin):
                consoleMsg = self.get_console_message(user)
                if (consoleMsg is not None and consoleMsg[0] == CTWWLoginStatus.MESSAGEKICK.value):
                    retDict["loginMessage"] = consoleMsg[1]
                    return (CTWWLoginStatus.MESSAGEKICK.value, retDict)
            
            user.setCTGP7Network(isCTGP7Network)
            self.remove_from_all_rooms(user)
            self.user_logout(user)
            self.user_login(user)
            self.newLogins += 1
            retDict["token"] = user.getToken()
            vrData = self.database.get_console_vr(cID)
            if (isDebug): user.setDebug()
            user.setVR(list((vrData.ctVR, vrData.cdVR)))
            retDict["ctvr"] = vrData.ctVR
            retDict["cdvr"] = vrData.cdVR
            retDict["ctvrPos"] = vrData.ctPos
            retDict["cdvrPos"] = vrData.cdPos
            retDict["regionID"] = self.database.get_debugonline_region() if isDebug else self.database.get_online_region()
            gradeCount = 0
            for s in CTGP7ServerDatabase.allowed_console_status:
                if (self.database.get_console_status(cID, s) == 1): gradeCount += 1
            retDict["myStarGrade"] = 0 if gradeCount == 0 else gradeCount + StarGrade.CUSTOM_PLAYER.value

            if (miiChecksum is not None):
                storedChecksum = self.database.get_mii_icon_checksum(cID)
                retDict["needsMiiUpload"] = storedChecksum is None or storedChecksum != miiChecksum

            if (consoleMsg is not None and consoleMsg[0] == CTWWLoginStatus.MESSAGE.value):
                retDict["loginMessage"] = consoleMsg[1]
                return (CTWWLoginStatus.MESSAGE.value, retDict)
            else:
                return (CTWWLoginStatus.SUCCESS.value, retDict)
    
    def handle_user_room_join(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            gMode = input.get("gameMode")
            token = input.get("token")
            retDict = {}
            
            if (gID is None or gMode is None or token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            self.remove_from_all_rooms(user)
            
            room = self.activeRooms.get(gID)
            if (room is None): # Create room if it doesn't exist
                room = OnlineRoom(gID, gMode)
                self.activeRooms[gID] = room
                self.newRooms += 1
            
            room.joinPlayer(user)
            retDict["roomKeySeed"] = room.getKeySeed(user)
            user.setState(UserState.SEARCHING.value)
            vrData = self.database.get_console_vr(cID)
            user.setVR(list((vrData.ctVR, vrData.cdVR)))
            retDict["ctvr"] = vrData.ctVR
            retDict["cdvr"] = vrData.cdVR
            retDict["ctvrPos"] = vrData.ctPos
            retDict["cdvrPos"] = vrData.cdPos
            retDict["trackHistory"] = room.getTrackHistory()
            user.setVRIncr(None)

            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, retDict)
    
    def handle_user_prepare_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            isHost = input.get("imHost")
            localver = input.get("localVer")
            betaVer = input.get("localBetaVer")
            token = input.get("token")
            retDict = {}

            if (localver is None):
                return (-1, {})

            if (self.database.get_ctww_version() != localver or (betaVer is not None and self.database.get_beta_version() != betaVer)):
                return (CTWWLoginStatus.VERMISMATCH.value, {})

            if (gID is None or isHost is None or token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            vrData = self.database.get_console_vr(cID)
            user.setVR(list((vrData.ctVR, vrData.cdVR)))
            user.setVRIncr(None)

            room = self.activeRooms.get(gID)
            if (room is None or not room.hasPlayer(user)):
                return (CTWWLoginStatus.FAILED.value, {})
            
            consoleMsg = self.get_console_message(user)
            if (consoleMsg is not None and consoleMsg[0] == CTWWLoginStatus.MESSAGEKICK.value):
                retDict = {}
                retDict["loginMessage"] = consoleMsg[1]
                return (CTWWLoginStatus.MESSAGEKICK.value, retDict)

            if (room.wasDisbanded()):
                retDict = {}
                retDict["loginMessage"] = "The room has been\ndisbanded."
                return (CTWWLoginStatus.MESSAGEKICK.value, retDict)

            if (isHost):
                room.setState(RoomState.PREPARING_RACE.value)
                user.setState(UserState.HOSTING.value)
            else:
                user.setState(UserState.CLIENT.value)

            retDict["neededPlayerAmount"] = room.getMinPlayerAmount(self.database)
            retDict["cpuRandomSeed"] = room.getCPURandomSeed()
            retDict["vrMean"] = room.getVRMean(self.database)
            retDict["rubberBMult"] = self.database.get_room_rubberbanding_config(False) if room.getMode() <= 1 else 1.0
            retDict["rubberBOffset"] = self.database.get_room_rubberbanding_config(True) if room.getMode() <= 1 else 0.0

            user.isAlive()
            
            return (CTWWLoginStatus.SUCCESS.value, retDict)

    def handle_user_racestart_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            szsName = input.get("courseSzsID")
            token = input.get("token")
            ctvr = input.get("ctvr")
            cdvr = input.get("cdvr")

            if (gID is None or szsName is None or token is None or ctvr is None or cdvr is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            room = self.activeRooms.get(gID)
            if (room is None or not room.hasPlayer(user)):
                return (CTWWLoginStatus.FAILED.value, {})
            
            if (user.getState() == UserState.HOSTING.value):
                room.setState(RoomState.RACING.value)
                room.setRace(szsName)
                room.appendToTrackHistory(szsName, self.database)
                room.enableLog()
            
            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})
    
    def handle_user_racefinish_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            token = input.get("token")
            ctvr = input.get("ctvr")
            cdvr = input.get("cdvr")
            retDict = {}

            if (gID is None or token is None or ctvr is None or cdvr is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            room = self.activeRooms.get(gID)
            if (room is None or not room.hasPlayer(user)):
                return (CTWWLoginStatus.FAILED.value, {})
            
            if room.getMode() <= 1:
                self.database.set_console_vr(cID, [ctvr, cdvr])
            
            if (user.getState() == UserState.HOSTING.value):
                self.database.set_stats_dirty(True)
                room.setState(RoomState.FINISHED.value)
                room.updateCPURandomSeed()
            
            if room.getMode() <= 1:
                prevVr = user.getVR()[0 if room.getMode() == 0 else 1]
                nowVR = ctvr if room.getMode() == 0 else cdvr
                user.setVRIncr(nowVR - prevVr)

            user.isAlive()

            retDict["trackHistory"] = room.getTrackHistory()

            return (CTWWLoginStatus.SUCCESS.value, retDict)

    def handle_user_watch_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            token = input.get("token")

            if (gID is None or token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            room = self.activeRooms.get(gID)
            if (room is None or not room.hasPlayer(user)):
                return (CTWWLoginStatus.FAILED.value, {})
            
            user.setState(UserState.WATCHING.value)
            room.forceUpdate()

            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})

    def handle_user_leave_room(self, input, cID):
        with self.lock:
            token = input.get("token")

            if (token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            self.remove_from_all_rooms(user)

            user.setState(UserState.IDLE.value)

            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})

    def handle_user_heartbeat(self, input, cID):
        with self.lock:
            token = input.get("token")

            if (token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})

    def handle_user_logout(self, input, cID):
        with self.lock:
            user = self.loggedUsers.get(cID)
            if (user is None):
                self.remove_from_all_rooms(cID=cID)
                self.user_logout(cID=cID)
            else:
                self.remove_from_all_rooms(user)
                self.user_logout(user)
            return (CTWWLoginStatus.SUCCESS.value, {})

    def purge_users(self, margin: datetime.timedelta):
        with self.lock:
            timeNow = datetime.datetime.utcnow()
            candidates = []
            for k in self.loggedUsers:
                user = self.loggedUsers[k]
                if (timeNow - user.lastActive() > margin):
                    self.remove_from_all_rooms(user)
                    candidates.append(user)
            for u in candidates:
                self.user_logout(u)

    def purge_tokens(self, margin: datetime.timedelta):
        with self.tokenslock:
            timeNow = datetime.datetime.utcnow()
            candidates = []
            for k in self.onlinepasswords:
                lasttime = self.onlinepasswords[k][0]
                if (timeNow - lasttime > margin):
                    candidates.append(k)
            for k in candidates:
                del self.onlinepasswords[k]

    def purge_rooms(self):
        with self.lock:
            candidates = []
            for k in self.activeRooms:
                room = self.activeRooms[k]
                if (room.playerCount() == 0):
                    candidates.append(k)
            for k in candidates:
                del self.activeRooms[k]

    def update_room_messageID(self, gID: int, messageID: int):
        with self.lock:
            room = self.activeRooms.get(gID)
            if (room is None):
                return False
            room.setMessageID(messageID)
            return True

    def disband_room(self, gID:int):
        with self.lock:
            room = self.activeRooms.get(gID)
            if (room is not None):
                room.disband()
                return True
            return False

    def getSpecialRoomState(self, room: OnlineRoom):
        isDebug = False
        for u in room.getPlayers():
            user = self.loggedUsers.get(u)
            if (user is None):
                continue
            if (user.isDebug()):
                isDebug = True
        ret = ""
        if (isDebug): ret += " (Debug)"
        return ret

    def fetch_state(self):
        with self.lock:
            ret = {}
            nnUsers = 0
            ctgpUsers = 0
            for u in self.loggedUsers:
                if self.loggedUsers[u].getCTGP7Network():
                    ctgpUsers += 1
                else:
                    nnUsers += 1
            ret["userCount"] = (ctgpUsers, nnUsers)
            ret["roomCount"] = len(self.activeRooms)
            ret["newUserCount"] = self.newLogins
            ret["newRoomCount"] = self.newRooms
            ret["rooms"] = []
            self.newLogins = 0
            self.newRooms = 0
            for k in self.activeRooms:
                room = self.activeRooms[k]
                playerCount = room.playerCount()
                if (playerCount == 0):
                    continue
                roomInfo = {}
                roomInfo["gID"] = room.gID
                roomInfo["playerCount"] = playerCount
                roomInfo["state"] = room.getStateName()
                roomInfo["color"] = room.getRoomColor()
                roomInfo["gameMode"] = room.getModeName() + self.getSpecialRoomState(room)
                roomInfo["fakeID"] = (room.getKeySeed(None) & 0xFFFFFF) | 0x03000000
                roomInfo["messageID"] = room.getMessageID()
                roomInfo["updated"] = room.wasUpdated()
                roomInfo["log"] = room.needsLog()
                roomInfo["players"] = []
                for u in room.getPlayers():
                    user = self.loggedUsers.get(u)
                    if (user is None):
                        continue
                    userInfo = {}
                    userInfo["name"] = user.getName()
                    if (room.getMode() <= 1):
                        userInfo["vr"] = user.getVR()[0 if room.getMode() == 0 else 1]
                        userInfo["vrIncr"] = user.getVRIncr()
                    else:
                        userInfo["vr"] = None
                        userInfo["vrIncr"] = None
                    userInfo["miiName"] = user.getMiiName()
                    userInfo["state"] = user.getStateName()
                    userInfo["cID"] = u
                    userInfo["verified"] = user.verified()
                    roomInfo["players"].append(userInfo)
                if (room.getMode() <= 1):
                    roomInfo["players"].sort(key=lambda x:x["vr"], reverse=True)
                ret["rooms"].append(roomInfo)
                room.resetUpdate()
            
            return ret


# From https://github.com/kwsch/png2bclim/blob/master/png2bclim/BCLIM.cs
class TEXRGBA5551:
    
    def __init__(self, data, sizeX, sizeY):
        self.data = data
        self.sizeX = sizeX
        self.sizeY = sizeY
    
    def __gcm(self, n, m):
        return ((n + m - 1) // m) * m

    def __d2xy(self, d):
        x = d
        y = (x >> 1)
        x &= 0x55555555
        y &= 0x55555555
        x |= (x >> 1)
        y |= (y >> 1)
        x &= 0x33333333
        y &= 0x33333333
        x |= (x >> 2)
        y |= (y >> 2)
        x &= 0x0f0f0f0f
        y &= 0x0f0f0f0f
        x |= (x >> 4)
        y |= (y >> 4)
        x &= 0x00ff00ff
        y &= 0x00ff00ff
        x |= (x >> 8)
        y |= (y >> 8)
        x &= 0x0000ffff
        y &= 0x0000ffff
        return (x, y)

    def ToRGBA8888(self):
        dataRet = [()] * (self.sizeX * self.sizeY)

        def iteru16(data:bytes):
            for i in range(0, len(data), 2):
                yield data[i] | (data[i+1] << 8)

        i = 0
        p = self.__gcm(self.sizeX, 8) // 8
        if (p == 0): p = 1

        for px in iteru16(self.data): #RGBA5551 to RGBA8888
            r = ((px >> 11) & 0x1F) * 255/31
            g = ((px >> 6) & 0x1F) * 255/31
            b = ((px >> 1) & 0x1F) * 255/31
            a = (px & 1) * 255

            x, y = self.__d2xy(i % 64)
            tile = i // 64
            x += (tile % p) * 8
            y += (tile // p) * 8

            dataRet[x + y * self.sizeX] = (int(r),int(g),int(b),int(a))
            i+=1
        return dataRet