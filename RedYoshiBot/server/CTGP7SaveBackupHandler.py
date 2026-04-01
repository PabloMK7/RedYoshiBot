import threading
import sqlite3
import time
import string
import random
from .CTGP7ServerDatabase import CTGP7ServerDatabase

class CTGP7SaveBackupHandler:
    class DatabaseHandler:
        def __init__(self, path: str):
            self.isConn = False
            self.conn = None
            self.lock = threading.Lock()
            self.path = path

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

        def get_backup_info(self, cID: int, isCitra: bool):
            with self.lock:
                c = self.conn.cursor()
                rows = c.execute("SELECT name, timestamp, sID0, sID1 FROM save_backups WHERE cID = ? AND isCitra = ?", (int(cID), int(isCitra)))
                timestamp = 0
                sID0 = 0
                sID1 = 0
                names = []
                for row in rows:
                    timestamp = row[1]
                    sID0 = row[2]
                    sID1 = row[3]
                    names.append(row[0])
                if timestamp == 0:
                    return None
                else:
                    return {"timestamp": timestamp, "sID0": sID0, "sID1": sID1, "names": names}
                
        def get_backup_item(self, cID: int, isCitra: bool, sID0: int, sID1: int, name: str):
            with self.lock:
                c = self.conn.cursor()
                rows = c.execute("SELECT value FROM save_backups WHERE cID = ? AND isCitra = ? AND sID0 = ? AND sID1 = ? AND name = ?", (int(cID), int(isCitra), int(sID0), int(sID1), str(name)))
                for row in rows:
                    return bytes(row[0])
            return None
                
        def delete_backup(self, cID: int, isCitra: bool):
            with self.lock:
                try:
                    c = self.conn.cursor()
                    c.execute("DELETE FROM save_backups WHERE cID = ? AND isCitra = ?", (int(cID), int(isCitra)))
                except:
                    return False
            return True

        def create_backup(self, cID: int, isCitra: bool, sID0: int, sID1: int, data: dict):
            with self.lock:
                now = time.time()
                try:
                    with self.conn:
                        c = self.conn.cursor()
                        c.execute("DELETE FROM save_backups WHERE cID = ? AND isCitra = ?", (int(cID), int(isCitra)))

                        rows = [
                            (int(cID), int(isCitra), int(sID0), int(sID1), str(name), int(now), bytes(value))
                            for name, value in data.items()
                        ]

                        c.executemany(
                            "INSERT INTO save_backups (cID, isCitra, sID0, sID1, name, timestamp, value) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            rows
                        )

                except Exception:
                    return False
            return True


    def __init__(self):
        self.database = CTGP7SaveBackupHandler.DatabaseHandler("RedYoshiBot/server/data/save.sqlite")
        self.database.connect()

        self.puts = {}
        self.putLock = threading.Lock()

    def disconnect(self):
        self.database.disconnect()

    def handle_put(self, input: dict, cID: int, isCitra: bool, mainDB: CTGP7ServerDatabase):

        manage_cID = input.get("manage_cID", None)
        if manage_cID is not None and mainDB.get_console_is_admin(cID):
            cID = manage_cID
            isCitra = input.get("manage_isCitra", True)

        with self.putLock:
            op = input.get("op", None)
            if op == "start":
                sID0 = int(input.get("sID0", 0))
                sID1 = int(input.get("sID1", 0))
                if sID0 == 0 or sID1 == 0:
                    return {-10, {}}
                
                key = (cID, isCitra)
                if key in self.puts:
                    del self.puts[key]

                tok = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

                data = {}
                data["tok"] = tok
                data["sID0"] = sID0
                data["sID1"] = sID1
                data["items"] = {}
                self.puts[key] = data

                ret = {}
                ret["tok"] = tok
                return (0, ret)
            
            elif op == "item":
                key = (cID, isCitra)
                if not key in self.puts:
                    return (-20, {})
                
                tok = input.get("tok", "")
                if self.puts[key]["tok"] != tok:
                    return (-21, {})
                
                name = input.get("name", "")
                value = bytes(input.get("data", bytes()))
                if len(name) == 0 or len(value) == 0 or len(value) > 0xC000:
                    return (-22, {})
                
                self.puts[key]["items"][name] = value
                return (0, {})
            
            elif op == "commit":
                key = (cID, isCitra)
                if not key in self.puts:
                    return (-30, {})
                
                tok = input.get("tok", "")
                if self.puts[key]["tok"] != tok:
                    return (-31, {})
                
                totSize = int(input.get("totSize", 0))
                actualSize = sum(len(x) for x in self.puts[key]["items"].values())
                if totSize != actualSize:
                    return (-32, {})

                entry = self.puts[key]["items"]
                sID0 = self.puts[key]["sID0"]
                sID1 = self.puts[key]["sID1"]
                del self.puts[key]

                res = self.database.create_backup(cID, isCitra, sID0, sID1, entry)

                if res:
                    return (0, {})
                else:
                    return (-32, {})
            elif op == "delete":
                return (0 if self.database.delete_backup(cID, isCitra) else -40, {})
            else:
                return (-1, {})

    def handle_get(self, input: dict, cID: int, isCitra: bool, mainDB: CTGP7ServerDatabase):

        manage_cID = input.get("manage_cID", None)
        if manage_cID is not None and mainDB.get_console_is_admin(cID):
            cID = manage_cID
            isCitra = input.get("manage_isCitra", True)

        op = input.get("op", None)
        if op == "info":
            info = self.database.get_backup_info(cID, isCitra)
            ret = {}
            if info is None:
                ret["daysAgo"] = -1
                ret["sID0"] = 0
                ret["sID1"] = 0
                ret["names"] = ""
            else:
                ret["daysAgo"] = int((time.time() - info["timestamp"]) // (24 * 60 * 60))
                ret["sID0"] = info["sID0"]
                ret["sID1"] = info["sID1"]
                ret["names"] = ":".join(info["names"])
            return (0, ret)
        elif op == "item":
            name = input.get("name", "")
            sID0 = input.get("sID0", 0)
            sID1 = input.get("sID1", 0)
            data = self.database.get_backup_item(cID, isCitra, sID0, sID1, name)
            if data is None:
                data = bytes()
            return (0, {"data": data})
        else:
            return (-1, {})
