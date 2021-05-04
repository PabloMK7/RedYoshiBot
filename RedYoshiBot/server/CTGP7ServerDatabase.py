import threading
import sqlite3
from enum import Enum
import time

from ..CTGP7Defines import CTGP7Defines

current_time_min = lambda: int(round(time.time() / 60))

class ConsoleMessageType(Enum):
    SINGLE_MESSAGE = 0
    TIMED_MESSAGE = 1
    SINGLE_KICKMESSAGE = 2
    TIMED_KICKMESSAGE = 3

class CTGP7ServerDatabase:
    def __init__(self):
        self.isConn = False
        self.conn = None
        self.lock = threading.Lock()
        self.kickCallback = None

    def setKickLogCallback(self, callback):
        self.kickCallback = callback

    def connect(self):
        if not self.isConn:
            self.conn = sqlite3.connect('RedYoshiBot/server/data/data.sqlite', check_same_thread=False)
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

    def get_stats_message_id(self):
        return int(self.get_database_config("stats_message_id"))

    def set_stats_message_id(self, messageID):
        self.set_database_config("stats_message_id", messageID)

    def get_most_played_tracks(self, course_type, amount):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_tracksfreq WHERE type = ? ORDER BY freq DESC", (int(course_type),))
            i = 0
            ret = []
            for row in rows:
                if (i >= amount): break
                ret.append([row[0], row[1]])
                i += 1
            return ret

    def increment_track_frequency(self, szsName, value):
        with self.lock:
            c = self.conn.cursor()
            rows = c.execute("SELECT * FROM stats_tracksfreq WHERE id = ?", (str(szsName),))
            for _ in rows:
                c.execute("UPDATE stats_tracksfreq SET freq = freq + {} WHERE id = ?".format(str(int(value))), (str(szsName),))
                return
            courseType = CTGP7Defines.getTypeFromSZS(szsName)
            if (courseType != -1):
                c.execute('INSERT INTO stats_tracksfreq VALUES (?,?,?)', (str(szsName), int(value), int(courseType)))
    
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
            self.kickCallback(cID, messageType, message, amountMin, isSilent)

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