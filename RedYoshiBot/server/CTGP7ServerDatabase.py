import threading
import sqlite3
from enum import Enum
import time
import datetime
import random
from typing import List, Tuple

from ..CTGP7Defines import CTGP7Defines

current_time_min = lambda: int(round(time.time() / 60))



class ConsoleMessageType(Enum):
    SINGLE_MESSAGE = 0
    TIMED_MESSAGE = 1
    SINGLE_KICKMESSAGE = 2
    TIMED_KICKMESSAGE = 3

class CTGP7ServerDatabase:
    created_badges = {}

    allowed_console_status = [
        "allgold",
        "all1star",
        "all3star",
        "all10pts",
        "vr5000",
        "bluecoin",
    ]
    class VRInfos:
        def __init__(self, withPos: bool):
            self.ctVR = 1000
            self.cdVR = 1000
            if withPos:
                self.ctPos = 0
                self.cdPos = 0

    class RankInfo:
        def __init__(self):
            self.rank = 0
            self.cID = 0
            self.name = ""
            self.score = 0

    def __init__(self, path: str, isCitra: bool):
        self.isConn = False
        self.conn = None
        self.lock = threading.Lock()
        self.kickCallback = None
        self.path = path
        self.isCitra = isCitra

    def setKickLogCallback(self, callback):
        self.kickCallback = callback

    def connect(self):
        if not self.isConn:
            self.conn = sqlite3.connect(self.path, check_same_thread=False)
            self.isConn = True
    
    def disconnect(self):
        if (self.isConn):
            self.commit()
            with self.lock:
                self.isConn = False
                self.conn.close()
                self.conn = None
    
    def commit(self):
        if (self.isConn):
            with self.lock:
                self.conn.commit()

    def set_database_config(self, field, value):
        with self.lock:
            c = self.conn.cursor()
            c.execute("UPDATE config SET value = ? WHERE field = ?", (str(value), str(field)))
    
    def get_database_config(self, field):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM config WHERE field = ?", (str(field),))
            for row in rows:
                return row[1]

    def get_online_region(self):
        return int(self.get_database_config("onlregion"))

    def get_debugonline_region(self):
        return int(self.get_database_config("onlregion")) + 2
    
    def set_online_region(self, value):
        self.set_database_config("onlregion", value)

    def get_track_freq_split(self):
        return abs(int(self.get_database_config("trackfreqsplit")))
    
    def set_track_freq_split(self, value):
        self.set_database_config("trackfreqsplit", abs(value))

    def get_track_freq_split_enabled(self):
        return int(self.get_database_config("trackfreqsplit")) >= 0
    
    def set_track_frew_split_enabled(self, enable):
        value = self.get_track_freq_split()
        self.set_database_config("trackfreqsplit", value if enable else -value)

    def get_ctww_version(self):
        return int(self.get_database_config("ctwwver"))
    
    def set_ctww_version(self, value):
        self.set_database_config("ctwwver", value)

    def get_beta_version(self):
        return int(self.get_database_config("betaver"))
    
    def set_beta_version(self, value):
        self.set_database_config("betaver", value)
    
    def get_stats_dirty(self):
        return int(self.get_database_config("stats_dirty")) == 1

    def set_stats_dirty(self, isDirty):
        self.set_database_config("stats_dirty", 1 if isDirty else 0)

    def get_room_player_amount(self, isCountDown):
        return int(self.get_database_config("cdRoomPlayerAmount" if isCountDown else "ctRoomPlayerAmount"))
    
    def set_room_player_amount(self, isCountDown, value):
        self.set_database_config("cdRoomPlayerAmount" if isCountDown else "ctRoomPlayerAmount", value)

    def get_room_rubberbanding_config(self, isOffset: bool):
        return float(self.get_database_config("rubberBOffset" if isOffset else "rubberBMult"))

    def set_room_rubberbanding_config(self, isOffset: bool, value: float):
        self.set_database_config("rubberBOffset" if isOffset else "rubberBMult", float(value))

    def get_room_blocked_track_history_count(self):
        return int(self.get_database_config("blockTrackHistoryCount"))

    def set_room_blocked_track_history_count(self, value: int):
        self.set_database_config("blockTrackHistoryCount", int(value))

    def get_ctgp7_server_address(self):
        return str(self.get_database_config("ctgp7serveraddress"))
    
    def set_ctgp7_server_address(self, addr: str):
        self.set_database_config("ctgp7serveraddress", str(addr))

    def get_ctgp7_server_available(self):
        return int(self.get_database_config("ctgp7serveravailable"))
    
    def set_ctgp7_server_available(self, available: int):
        self.set_database_config("ctgp7serveravailable", int(available))

    def get_vr_multiplier(self) -> float:
        return float(self.get_database_config("vrMultiplier"))

    def set_vr_multiplier(self, multiplier: float):
        self.set_database_config("vrMultiplier", float(multiplier))

    def get_allowed_characters(self) -> str:
        return str(self.get_database_config("allowedCharacters"))
    
    def set_allowed_characters(self, l: str):
        self.set_database_config("allowedCharacters", str(l))

    def get_allowed_tracks(self) -> str:
        return str(self.get_database_config("allowedTracks"))
    
    def set_allowed_tracks(self, l: str):
        self.set_database_config("allowedTracks", str(l))

    def get_allowed_items(self) -> str:
        return str(self.get_database_config("allowedItems"))
    
    def set_allowed_items(self, l: str):
        self.set_database_config("allowedItems", str(l))

    def fetch_unique_PID(self):
        pid = int(self.get_database_config("currUniquePID"))
        self.set_database_config("currUniquePID", pid + 1)
        return pid
    
    def get_nex_aes_key(self):
        return str(self.get_database_config("nexaeskey"))
    
    def get_nex_http_server(self):
        return str(self.get_database_config("nexhttpserver"))

    def get_event_grant_badge(self):
        return int(self.get_database_config("eventGrantBadge"))
    
    def set_event_grant_badge(self, bID: int):
        self.set_database_config("eventGrantBadge", int(bID))

    def set_blue_shell_showdown(self, isShowdown):
        self.set_database_config("blueshellshowdown", 1 if bool(isShowdown) else 0)

    def get_blue_shell_showdown(self):
        return int(self.get_database_config("blueshellshowdown")) != 0
    
    def get_special_char_vr_multiplier(self) -> float:
        return float(self.get_database_config("specialvrcharmultiplier"))

    def set_special_char_vr_multiplier(self, multiplier: float):
        self.set_database_config("specialvrcharmultiplier", float(multiplier))

    def get_special_vr_characters(self) -> str:
        return str(self.get_database_config("specialvrcharacters"))
    
    def set_special_vr_characters(self, l: str):
        self.set_database_config("specialvrcharacters", str(l))

    def get_weekly_points_duration_seconds(self):
        return int(self.get_database_config("weeklypointsduration"))
    
    def set_weekly_points_duration_seconds(self, seconds: int):
        self.set_database_config("weeklypointsduration", str(seconds))

    def get_weekly_points_special_part_amounts(self):
        return str(self.get_database_config("specialpartamounts"))
    
    def set_weekly_points_special_part_amounts(self, amounts: str):
        self.set_database_config("specialpartamounts", str(amounts))

    def verify_console_legality(self, cID, cSH1, cSH2):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT cID FROM console_secure WHERE cSH1 = ? AND cSH2 = ?", (int(cSH1), int(cSH2)))
            for row in rows:
                if row[0] == 0:
                    return False
                if row[0] != int(cID):
                    c.execute("UPDATE console_secure SET cID = ? WHERE cSH1 = ? AND cSH2 = ?", (0, int(cSH1), int(cSH2)))
                    return False
                return True
            c.execute("INSERT INTO console_secure VALUES (?,?,?,?)", (int(cSH1), int(cSH2), int(cID), int(cID)))
            return True
    
    def get_console_legality(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT cID FROM console_secure WHERE first_cID = ?", (int(cID),))
            for row in rows:
                if row[0] == 0:
                    return False
        return True

    def getall_console_legality(self):
        ret = []
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT first_cID FROM console_secure WHERE cID = 0")
            for row in rows:
                ret.append(row[0])
        return ret

    def clear_console_legality(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("UPDATE console_secure SET cID = ? WHERE first_cID = ?", (int(cID), int(cID)))
    
    def set_console_legality(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("UPDATE console_secure SET cID = ? WHERE first_cID = ?", (0, int(cID)))

    def get_most_played_tracks(self, course_type, amount):
        splitenabled = self.get_track_freq_split_enabled()
        currsplit = self.get_track_freq_split()
        with self.lock:
            if (not splitenabled):
                c = self.conn.cursor()
                rows = c.execute("SELECT id, SUM(freq) FROM stats_tracksfreq WHERE type = ? GROUP BY id ORDER BY SUM(freq) DESC", (int(course_type),))
                i = 0
                ret = []
                for row in rows:
                    if (i >= amount): break
                    if CTGP7Defines.getTrackNameFromSzs(row[0]) == "???":
                        continue
                    ret.append([row[0], 0, row[1]])
                    i += 1
                return ret
            else:
                c = self.conn.cursor()
                c2 = self.conn.cursor()
                rows = c.execute("SELECT * FROM stats_tracksfreq WHERE split = ? AND type = ? ORDER BY freq DESC", (int(currsplit), int(course_type)))
                i = 0
                ret = []
                for row in rows:
                    if (i >= amount): break
                    if CTGP7Defines.getTrackNameFromSzs(row[0]) == "???":
                        continue
                    prevValue = c2.execute("SELECT SUM(freq) FROM stats_tracksfreq WHERE id = ? AND split < ?", (str(row[0]), int(currsplit))).fetchone()[0]
                    ret.append([row[0], row[2], 0 if prevValue is None else prevValue])
                    i += 1
                return ret

    def get_max_saved_track_split(self):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_tracksfreq ORDER BY split DESC")
            for row in rows:
                return row[1]
            return 0

    def increment_track_frequency(self, szsName, value):
        currsplit = self.get_track_freq_split()
        if CTGP7Defines.getTrackNameFromSzs(szsName) == "???":
            return
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_tracksfreq WHERE id = ? AND split = ?", (str(szsName),int(currsplit)))
            for _ in rows:
                c.execute("UPDATE stats_tracksfreq SET freq = freq + {} WHERE id = ? AND split = ?".format(str(int(value))), (str(szsName),int(currsplit)))
                return
            courseType = CTGP7Defines.getTypeFromSZS(szsName)
            if (courseType != -1):
                c.execute('INSERT INTO stats_tracksfreq VALUES (?,?,?,?)', (str(szsName), int(currsplit), int(value), int(courseType)))
    
    def get_stats(self):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_general WHERE 1=1")
            ret = {}
            i = 0
            names = [description[0] for description in rows.description]
            for row in rows:
                for val in row:
                    ret[names[i]] = val
                    i += 1
                break
            return ret
    
    def increment_general_stats(self, param, value):
        with self.lock:
            c = self.conn.cursor()
            c.execute("UPDATE stats_general SET {} = {} + {} WHERE 1=1".format(param, param, str(int(value))))
    
    def fetch_stats_seqid(self, cID):
         with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_seqid WHERE cID = ?", (int(cID),))
            for row in rows:
                newSeqID = row[1] + 1
                c.execute("UPDATE stats_seqid SET seqID = ? WHERE cID = ?", (int(newSeqID), int(cID)))
                return newSeqID
            c.execute('INSERT INTO stats_seqid VALUES (?,?)', (int(cID), int(1)))
            return 1

    def get_stats_seqid(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_seqid WHERE cID = ?", (int(cID),))
            for row in rows:
                return row[1]
            return 0
        
    def get_unique_console_count(self):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT COUNT(*) FROM stats_seqid")
            for row in rows:
                return row[0]
            return 0

    def delete_console_message(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_message WHERE cID = ?", (int(cID),))

    def set_console_message(self, cID, messageType, message, amountMin=None, isSilent=False):
        currTime = current_time_min() if amountMin is not None else None
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_message WHERE cID = ?", (int(cID),))
            c.execute('INSERT INTO console_message VALUES (?,?,?,?,?)', (int(cID), str(message), int(messageType), currTime, amountMin))
        if (self.kickCallback):
            self.kickCallback(cID, messageType, message, amountMin, isSilent, self.isCitra)

    def get_console_message(self, cID, realConsoleID): # Real console ID is to keep track if cID is 0
        ret = None
        startTime = None
        amountTime = None
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_message WHERE cID = ?", (int(cID),))
            for row in rows:
                messageText = row[1]
                messageType = row[2]
                startTime = row[3]
                amountTime = row[4]
                ret = [messageType, messageText, startTime, amountTime]
                
        if (ret is not None):
            if (ret[0] == ConsoleMessageType.SINGLE_KICKMESSAGE.value and self.get_console_is_admin(realConsoleID)):
                ret[0] = ConsoleMessageType.SINGLE_MESSAGE.value
            elif (ret[0] == ConsoleMessageType.TIMED_KICKMESSAGE.value and self.get_console_is_admin(realConsoleID)):
                ret[0] = ConsoleMessageType.TIMED_MESSAGE.value
            
            if ret[0] == ConsoleMessageType.SINGLE_MESSAGE.value or ret[0] == ConsoleMessageType.SINGLE_KICKMESSAGE.value:
                self.delete_console_message(cID)
            elif (startTime is not None and amountTime is not None and startTime + amountTime < current_time_min()):
                self.delete_console_message(cID)
        if (ret is None and cID != 0):
            ret = self.get_console_message(0, realConsoleID)
        
        return tuple(ret) if ret is not None else None

    def set_console_is_verified(self, cID, isVerified):
        wasVerified = self.get_console_is_verified(cID)
        if (wasVerified == isVerified):
            return
        with self.lock:
            c = self.conn.cursor()
            if (isVerified):
                c.execute('INSERT INTO verified_consoles VALUES (?)', (int(cID),))
            else:
                c.execute("DELETE FROM verified_consoles WHERE cID = ?", (int(cID),))


    def get_console_is_verified(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM verified_consoles WHERE cID = ?", (int(cID),))
            for row in rows:
                return True
            return False

    def set_console_is_admin(self, cID, isAdmin):
        wasAdmin = self.get_console_is_admin(cID)
        if (wasAdmin == isAdmin):
            return
        with self.lock:
            c = self.conn.cursor()
            if (isAdmin):
                c.execute('INSERT INTO admin_consoles VALUES (?)', (int(cID),))
            else:
                c.execute("DELETE FROM admin_consoles WHERE cID = ?", (int(cID),))


    def get_console_is_admin(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM admin_consoles WHERE cID = ?", (int(cID),))
            for row in rows:
                return True
            return False
    
    def set_console_last_name(self, cID, lastName):
        now = int(datetime.datetime.utcnow().timestamp())
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_name WHERE cID = ? ORDER BY timestamp DESC", (int(cID),))
            counter = 0
            insert = True
            for row in rows:
                if counter == 0 and str(row[1]) == lastName:
                    insert = False
                if (counter >= 19):
                    c.execute("DELETE FROM console_name WHERE cID = ? AND timestamp = ?", (int(cID), int(row[2])))
                counter += 1
            if insert:
                c.execute('INSERT INTO console_name VALUES (?,?,?)', (int(cID), str(lastName), int(now)))


    def get_console_last_name(self, cID, default="(Unknown)"):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_name WHERE cID = ? ORDER BY timestamp DESC", (int(cID),))
            for row in rows:
                return str(row[1])
            return default
        
    def get_console_name_history(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_name WHERE cID = ? ORDER BY timestamp DESC", (int(cID),))
            ret = []
            for row in rows:
                ret.append([str(row[1]), int(row[2])])
            return ret
    
    def set_console_vr(self, cID, vr):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE console_vr SET ctvr = ?, cdvr = ? WHERE cID = ?", (int(vr[0]), int(vr[1]), int(cID)))
                return
            c.execute('INSERT INTO console_vr VALUES (?,?,?,?)', (int(cID), int(vr[0]), int(vr[1]), 0))

    def get_console_vr(self, cID, withPos: bool) -> VRInfos:
        with self.lock:
            vrData = CTGP7ServerDatabase.VRInfos(withPos)
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr WHERE cID = ?", (int(cID),))
            for row in rows:
                vrData.ctVR = row[1]
                vrData.cdVR = row[2]
                break
            if withPos:
                rows = c.execute("SELECT COUNT(*) from console_vr WHERE ctvr > ?", (int(vrData.ctVR),))
                for row in rows:
                    vrData.ctPos = row[0] + 1
                rows = c.execute("SELECT COUNT(*) from console_vr WHERE cdvr > ?", (int(vrData.cdVR),))
                for row in rows:
                    vrData.cdPos = row[0] + 1
            return vrData

    def set_console_points(self, cID, points):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE console_vr SET points = ? WHERE cID = ?", (int(points), int(cID)))
                return
            c.execute('INSERT INTO console_vr VALUES (?,?,?,?)', (int(cID), 1000, 1000, int(points)))

    def add_console_points(self, cID, points):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr WHERE cID = ?", (int(cID),))
            skipInsert = False
            prevPoints = 0
            pointsPos = 0
            for row in rows:
                skipInsert = True
                prevPoints = row[3]
                c.execute("UPDATE console_vr SET points = ? WHERE cID = ?", (int(points + prevPoints), int(cID)))
                break
            if (not skipInsert):
                c.execute('INSERT INTO console_vr VALUES (?,?,?,?)', (int(cID), 1000, 1000, int(points)))
            rows = c.execute("SELECT COUNT(*) from console_vr WHERE points > ?", (int(points + prevPoints),))
            for row in rows:
                pointsPos = row[0] + 1
            return (prevPoints + points, pointsPos)

    def get_console_points(self, cID) -> VRInfos:
        with self.lock:
            points = 0
            pointsPos = 0
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr WHERE cID = ?", (int(cID),))
            for row in rows:
                points = row[3]
                break
            rows = c.execute("SELECT COUNT(*) from console_vr WHERE points > ?", (int(points),))
            for row in rows:
                pointsPos = row[0] + 1
            return (points, pointsPos)

    def get_unique_console_vr_count(self):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT COUNT(*) FROM console_vr WHERE (ctvr != 1000 OR cdvr != 1000)")
            for row in rows:
                return row[0]

    def get_most_users_vr(self, mode, amount):
        with self.lock:
            modeKind = ["ctvr", "cdvr", "points"]
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_vr ORDER BY {} DESC".format(modeKind[mode]))
            i = 0
            ret = []
            for row in rows:
                if (i >= amount): break
                ret.append([row[0], row[mode + 1]])
                i += 1
            return ret
    
    def increment_today_launches(self):
        with self.lock:
            now = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM launch_times WHERE date = ?", (now,))
            for row in rows:
                c.execute("UPDATE launch_times SET value = ? WHERE date = ?", (row[1] + 1, now))
                return
            c.execute('INSERT INTO launch_times VALUES (?,?)', (now, 1))
    
    def get_daily_launches(self, date: datetime.datetime):
        with self.lock:
            d = date.strftime('%Y-%m-%d')
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM launch_times WHERE date = ?", (d,))
            for row in rows:
                return row[1]
            return 0

    def increment_today_unique_consoles(self):
        with self.lock:
            now = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM new_launch_times WHERE date = ?", (now,))
            for row in rows:
                c.execute("UPDATE new_launch_times SET value = ? WHERE date = ?", (row[1] + 1, now))
                return
            c.execute('INSERT INTO new_launch_times VALUES (?,?)', (now, 1))
    
    def get_daily_unique_consoles(self, date: datetime.datetime):
        with self.lock:
            d = date.strftime('%Y-%m-%d')
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM new_launch_times WHERE date = ?", (d,))
            for row in rows:
                return row[1]
            return 0

    def set_discord_link_console(self, discordID, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM discord_link WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE discord_link SET discordID = ? WHERE cID = ?", (int(discordID), int(cID)))
                return
            c.execute('INSERT INTO discord_link VALUES (?,?)', (int(cID), int(discordID)))

    def get_discord_link_console(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM discord_link WHERE cID = ?", (int(cID),))
            for row in rows:
                return row[1]
            return None

    def get_discord_link_user(self, discordID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM discord_link WHERE discordID = ?", (int(discordID),))
            for row in rows:
                return row[0]
            return None
    
    def get_all_discord_link(self):
        ret = []
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM discord_link")
            for row in rows:
                ret.append((row[0], row[1]))
            return ret

    def delete_discord_link_console(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM discord_link WHERE cID = ?", (int(cID),))

    def delete_discord_link_user(self, discordID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM discord_link WHERE discordID = ?", (int(discordID),))

    def get_mii_icon(self, cID) -> bytes:
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT data FROM mii_icon WHERE cID = ?", (int(cID),))
            for row in rows:
                return bytes(row[0])
            return None
    
    def get_mii_icon_checksum(self, cID) -> int:
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT checksum FROM mii_icon WHERE cID = ?", (int(cID),))
            for row in rows:
                return row[0]
            return None
    
    def set_mii_icon(self, cID, data: bytes, checksum: int):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT cID FROM mii_icon WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE mii_icon SET data = ?, checksum = ? WHERE cID = ?", (sqlite3.Binary(data), int(checksum), int(cID)))
                return
            c.execute('INSERT INTO mii_icon VALUES (?,?,?)', (int(cID), sqlite3.Binary(data), int(checksum)))

    def delete_mii_icon(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM mii_icon WHERE cID = ?", (int(cID),))

    def get_console_status(self, cID, status):
        if (not status in CTGP7ServerDatabase.allowed_console_status):
            return None
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT {} FROM console_status WHERE cID = ?".format(str(status)), (int(cID),))
            for row in rows:
                return row[0]
            return None
    
    def set_console_status(self, cID, status, value):
        if (not status in CTGP7ServerDatabase.allowed_console_status):
            return None
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT cID FROM console_status WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE console_status SET {} = ? WHERE cID = ?".format(str(status)), (int(value), int(cID)))
                return
            # Create entry
            c.execute('INSERT INTO console_status VALUES (?,?,?,?,?,?,?)', (int(cID), int(0), int(0), int(0), int(0), int(0), int(0),))
            # Update entry
            c.execute("UPDATE console_status SET {} = ? WHERE cID = ?".format(str(status)), (int(value), int(cID)))

    def clear_console_status(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_status WHERE cID = ?", (int(cID),))

    def transfer_console_status(self, oldcID, newcID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_status WHERE cID = ?", (int(newcID),))
            c.execute("UPDATE console_status SET cID = ? WHERE cID = ?", (int(newcID), int(oldcID)))

    def get_console_unique_server_address(self, cID):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT serveraddr FROM server_address WHERE cID = ?", (int(cID),))
            for row in rows:
                return row[0]
        return None
    
    def clear_console_unique_server_address(self, cID):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM server_address WHERE cID = ?", (int(cID),))
    
    def set_console_unique_server_address(self, cID, value: str):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT cID FROM server_address WHERE cID = ?", (int(cID),))
            for row in rows:
                c.execute("UPDATE server_address SET serveraddr = ? WHERE cID = ?", (str(value), int(cID)))
                return
            # Create entry
            c.execute('INSERT INTO server_address VALUES (?,?)', (int(cID), str(value)))

    def set_track_banned_ultrasc(self, szsname, from_min, from_max, to_min, to_max, trigger):
        with self.lock:
            c = self.conn.cursor()
            c.execute('INSERT INTO banned_ultrasc VALUES (?,?,?,?,?,?)', (str(szsname), float(from_min), float(from_max), float(to_min), float(to_max), float(trigger)))
    
    def clear_track_banned_ultrasc(self, szsname):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM banned_ultrasc WHERE szsname = ?", (str(szsname),))

    def get_track_banned_ultrasc(self, szsname):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM banned_ultrasc WHERE szsname = ?", (str(szsname),))
            ret = []
            for row in rows:
                ret.append([float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])])
        return ret
    
    def add_badge(self, name: str, desc: str, icon: bytes) -> int:
        with self.lock:
            c = self.conn.cursor()
            # Maintain same ID for console and Citra DBs
            if name in CTGP7ServerDatabase.created_badges:
                bID = CTGP7ServerDatabase.created_badges[name]
            else:
                bID = random.getrandbits(63)
                CTGP7ServerDatabase.created_badges[name] = bID
            c.execute('INSERT INTO badges VALUES (?,?,?,?)', (int(bID), str(name), str(desc), sqlite3.Binary(icon)))
            return bID
        
    def edit_badge(self, bID: int, name: str, desc: str, icon: bytes):
         with self.lock:
            c = self.conn.cursor()
            c.execute("UPDATE badges SET name = ?, description = ?, icon = ? WHERE bID = ?", (str(name), str(desc), sqlite3.Binary(icon), int(bID)))

    def get_badge(self, bID: int):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM badges WHERE bID = ?", (int(bID),))
            for row in rows:
                return (row[0], row[1], row[2], bytes(row[3]))
            return None
    
    def delete_badge(self, bID: int):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM badges WHERE bID = ?", (int(bID),))
            c.execute("DELETE FROM console_badges WHERE bID = ?", (int(bID),))

    def get_all_badges(self):
        with self.lock:
            c = self.conn.cursor()
            c2 = self.conn.cursor()
            rows = c.execute("SELECT bID, name, description FROM badges")
            ret = []
            for row in rows:
                count = 0
                rows2 = c2.execute("SELECT COUNT(*) FROM console_badges WHERE bID = ?", (int(row[0]),))
                for row2 in rows2:
                    count = row2[0]
                ret.append((row[0], row[1], row[2], count))
            return ret
        
    def get_console_badges(self, cID: int) -> List[Tuple[int, int]]:
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM console_badges WHERE cID = ?", (int(cID),))
            ret = []
            for row in rows:
                ret.append((row[1], row[2]))
            return ret
    
    def has_console_badge(self, cID: int, bID: int, badges = None):
        if badges is None:
            badges = self.get_console_badges(cID)
        for b in badges:
            if bID == b[0]:
                return True
        return False

    def grant_badge(self, cID: int, bID: int):
        if self.has_console_badge(cID, bID):
            return
        with self.lock:
            c = self.conn.cursor()
            c.execute("INSERT INTO console_badges VALUES (?,?,?)", (int(cID), int(bID), int(time.time())))

    def ungrant_badge(self, cID: int, bID: int):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_badges WHERE cID = ? AND bID = ?", (int(cID), int(bID)))
    
    def ungrant_all_badges(self, cID: int):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_badges WHERE cID = ?", (int(cID),))

    def transfer_badges(self, oldcID: int, newcID: int):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM console_badges WHERE cID = ?", (int(newcID),))
            c.execute("UPDATE console_badges SET cID = ? WHERE cID = ?", (int(newcID), int(oldcID)))

    def set_weekly_points_config(self, field, value):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM weekly_points_config WHERE field = ?", (str(field),))
            for row in rows:
                c.execute("UPDATE weekly_points_config SET value = ? WHERE field = ?", (str(value), str(field)))
                return
            # Create entry
            c.execute('INSERT INTO weekly_points_config VALUES (?,?)', (str(field), str(value)))
    
    def get_weekly_points_config(self, field, default: str) -> str:
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM weekly_points_config WHERE field = ?", (str(field),))
            for row in rows:
                return str(row[1])
        return default
    
    def get_weekly_points_leaderboard(self, minRank, maxRank, limit, cID=-1):
        query = """
            WITH ranked AS (
                SELECT
                    cID,
                    score,
                    RANK() OVER (ORDER BY score DESC) AS rank
                FROM weekly_points_leaderboard
            )
            SELECT
                cID,
                score,
                rank
            FROM ranked
            WHERE rank >= ? AND rank <= ?
            ORDER BY rank
            LIMIT ?;
            """
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute(query, (int(minRank), int(maxRank), int(limit)))
            ret: List[CTGP7ServerDatabase.RankInfo] = []
            for row in rows:
                rank = CTGP7ServerDatabase.RankInfo()
                rank.rank = row[2]
                rank.cID = row[0]
                rank.score = row[1]
                ret.append(rank)
            i=0
            self_index=-1
            for r in ret:
                c2 = self.conn.cursor()
                if cID == int(r.cID):
                    self_index = i
                rows = c2.execute("SELECT * FROM console_name WHERE cID = ? ORDER BY timestamp DESC", (int(r.cID),))
                name = "Player"
                for row in rows:
                    name = str(row[1])
                    break
                r.name = name
                i+=1
            return (self_index, ret)

    def get_weekly_points_surrounding(self, cID, amount=4):
        query = """
        WITH ranked AS (
            SELECT
                cID,
                score,
                RANK() OVER (ORDER BY score DESC) AS position
            FROM weekly_points_leaderboard
        ),
        target AS (
            SELECT position AS target_pos
            FROM ranked
            WHERE cID = ?
        )
        SELECT
            cID,
            score,
            position
        FROM ranked
        WHERE position BETWEEN (SELECT target_pos FROM target) - {}
                        AND (SELECT target_pos FROM target) + {}
        ORDER BY position;
        """.format(amount, amount)
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute(query, (int(cID), ))
            ret: List[CTGP7ServerDatabase.RankInfo] = []
            for row in rows:
                rank = CTGP7ServerDatabase.RankInfo()
                rank.rank = row[2]
                rank.cID = row[0]
                rank.score = row[1]
                ret.append(rank)
            i = 0
            self_index = -1
            for r in ret:
                c2 = self.conn.cursor()
                if cID == int(r.cID):
                    self_index = i
                rows = c2.execute("SELECT * FROM console_name WHERE cID = ? ORDER BY timestamp DESC", (int(r.cID),))
                name = "Player"
                for row in rows:
                    name = str(row[1])
                    break
                r.name = name
                i+=1
            return (self_index, ret)
        
    def set_weekly_points_leaderboard_score(self, cID: int, score: int):
        query = """
            INSERT INTO weekly_points_leaderboard (cID, score)
            VALUES (?, ?)
            ON CONFLICT(cID) DO UPDATE SET
            score = excluded.score;"""
        with self.lock:
            c = self.conn.cursor()
            c.execute(query, (int(cID), int(score)))
        
    def clear_weekly_points_leaderboard(self):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM weekly_points_leaderboard WHERE 1 = 1")