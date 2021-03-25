from .CTGP7ServerDatabase import CTGP7ServerDatabase, ConsoleMessageType
from ..CTGP7Defines import CTGP7Defines
from enum import Enum
import time
import datetime
import textwrap
import uuid
import threading

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
        self.players = set()
        self.state = RoomState.SEARCHING.value
        self.race = ""
        self.messageID = 0
        self.needsUpdate = True
        self.isDisbanding = False
        self.logToStaff = False

    def joinPlayer(self, user: OnlineUser):
        self.players.add(user.cID)
        self.needsUpdate = True
    
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
            return "Preparing Race"
        elif (self.state == RoomState.RACING.value):
            return "Racing ({})".format(CTGP7Defines.getTrackNameFromSzs(self.race))
        return ""

    def getModeName(self):
        if (self.gamemode == 0):
            return "Custom Tracks"
        elif (self.gamemode == 1):
            return "Countdown"
        return ""

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

class CTGP7CtwwHandler:
    
    def __init__(self, database: CTGP7ServerDatabase):
        self.database = database
        self.loggedUsers = {}
        self.activeRooms = {}
        self.lock = threading.Lock()
        self.newLogins = 0
        self.newRooms = 0

    def get_console_message(self, user: OnlineUser):
        msg = self.database.get_console_message(user.cID)
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

    def handle_user_login(self, input: dict, cID: int):
        with self.lock:
            nameMode = input.get("nameMode")
            nameValue = input.get("nameValue")
            localver = input.get("localVer")
            seed = input.get("seed")
            isRelogin = input.get("reLogin")
            miiName = input.get("miiName")
            retDict = {}
            
            if (isRelogin is None or localver is None or seed is None or miiName is None):
                return (-1, {})
            
            retDict["seed"] = seed

            if (not isRelogin and self.database.get_ctww_version() != localver):
                return (CTWWLoginStatus.VERMISMATCH.value, retDict)

            if (nameMode is None):
                return (-1, {})
            if (nameMode == PlayerNameMode.SHOW.value and nameValue is None):
                return (-1, {})
            if (nameMode == PlayerNameMode.CUSTOM.value and nameValue is None):
                return (-1, {})
            
            user = OnlineUser(OnlineUserName(nameMode, nameValue, miiName), cID, self.database.get_console_is_verified(cID))

            consoleMsg = None
            if (not isRelogin):
                consoleMsg = self.get_console_message(user)
                if (consoleMsg is not None and consoleMsg[0] == CTWWLoginStatus.MESSAGEKICK.value):
                    retDict["loginMessage"] = consoleMsg[1]
                    return (CTWWLoginStatus.MESSAGEKICK.value, retDict)
            
            self.remove_from_all_rooms(user)
            self.user_logout(user)
            self.user_login(user)
            self.newLogins += 1
            retDict["token"] = user.getToken()

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
            user.setState(UserState.SEARCHING.value)

            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})
    
    def handle_user_prepare_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            isHost = input.get("imHost")
            localver = input.get("localVer")
            token = input.get("token")

            if (localver is None):
                return (-1, {})

            if (self.database.get_ctww_version() != localver):
                return (CTWWLoginStatus.VERMISMATCH.value, {})

            if (gID is None or isHost is None or token is None):
                return (-1, {})

            user = self.getUser(cID, token)
            if (user is None): # User not logged in
                return (CTWWLoginStatus.NOTLOGGED.value, {})

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

            user.isAlive()
            
            return (CTWWLoginStatus.SUCCESS.value, {})

    def handle_user_racestart_room(self, input, cID):
        with self.lock:
            gID = input.get("gatherID")
            szsName = input.get("courseSzsID")
            token = input.get("token")

            if (gID is None or szsName is None or token is None):
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
                room.enableLog()
            
            user.isAlive()

            return (CTWWLoginStatus.SUCCESS.value, {})

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
                return
            room.setMessageID(messageID)

    def disband_room(self, gID:int):
        with self.lock:
            room = self.activeRooms.get(gID)
            if (room is not None):
                room.disband()
                return True
            return False

    def fetch_state(self):
        with self.lock:
            ret = {}
            ret["userCount"] = len(self.loggedUsers)
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
                roomInfo["gameMode"] = room.getModeName()
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
                    userInfo["miiName"] = user.getMiiName()
                    userInfo["state"] = user.getStateName()
                    userInfo["cID"] = u
                    userInfo["verified"] = user.verified()
                    roomInfo["players"].append(userInfo)
                ret["rooms"].append(roomInfo)
                room.resetUpdate()
            
            return ret