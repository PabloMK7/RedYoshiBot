from Crypto.Cipher import AES
import secrets
import threading
import requests
import json
import time
from typing import List
import traceback

class CTGP7NEXHTTPHandler:
    class HTTPStats:
        class HTTPStatsUserInfo:
            def __init__(self, json: dict):
                self.pid: int = json["PID"]
                self.cid: int = json["CID"]
                self.natreport: List[int] = json["NatReport"]["Results"]

        class HTTPStatsSessionInfo:
            def __init__(self, json: dict):
                self.gid: int = json["GID"]
                self.hostpid: int = json["HostPID"]
                self.ownerpid: int = json["OwnerPID"]
                self.connections: List[int] = json["Connections"]
        
        def __init__(self, json: dict):
            users = json.get("Users")
            sessions = json.get("Sessions")

            self.users: List[CTGP7NEXHTTPHandler.HTTPStats.HTTPStatsUserInfo] = []
            self.sessions: List[CTGP7NEXHTTPHandler.HTTPStats.HTTPStatsSessionInfo] = []

            if users is not None:
                for u in users:
                    self.users.append(CTGP7NEXHTTPHandler.HTTPStats.HTTPStatsUserInfo(u))
            if sessions is not None:
                for s in sessions:
                    self.sessions.append(CTGP7NEXHTTPHandler.HTTPStats.HTTPStatsSessionInfo(s))
        def __str__(self) -> str:
            ret = "Users:\n"
            for u in self.users:
                ret += "\t{} ({})\n".format(u.cid, u.pid)
            ret += "Sessions:\n"
            for s in self.sessions:
                ret += "\tGID {}, Host: {}, Owner: {}\n".format(s.gid, s.hostpid, s.ownerpid)
                for c in s.connections:
                    user = None
                    for u in self.users:
                        if u.cid == c:
                            user = u
                    ret += "\t\t{} ({})\n".format(user.cid, user.pid)
            return ret
        
    def __init__(self, database) -> None:
        from . import CTGP7ServerDatabase as ServerDatabase
        db: ServerDatabase.CTGP7ServerDatabase = database
        self.key = bytes.fromhex(db.get_nex_aes_key())
        self.httpaddr = db.get_nex_http_server()
        self.database = db
        self.lock = threading.Lock()
        self.stats = CTGP7NEXHTTPHandler.HTTPStats({})
        self.httpsessionlock = threading.Lock()
        self.httpsession = requests.Session()
        self.terminated = False
        pass

    def encrypt(self, plaintext: bytes) -> bytes:
        block_size = AES.block_size
        iv = secrets.token_bytes(16)
        pad = lambda s: s + ((block_size - len(s) % block_size) * int.to_bytes(block_size - len(s) % block_size, 1))
        plaintext = pad(plaintext)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(plaintext)
        return iv + ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        block_size = AES.block_size
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        if len(ciphertext) <= block_size or len(ciphertext) % block_size != 0: return bytes()
        iv = ciphertext[:16]
        ciphertext = ciphertext[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        try:
            return unpad(cipher.decrypt(ciphertext))
        except:
            return bytes()
        
    def terminate(self):
        self.terminated = True
        self.httpsession.close()
        
    def fetch_http_stats(self):
        while (True):
            if self.terminated:
                return
            time.sleep(3)
            try:
                with self.httpsessionlock:
                    resp = self.httpsession.get(self.httpaddr + "/stats", timeout=10)

                if (resp.status_code != 200):
                    continue
                
                body = resp.content
                js: dict = json.loads(self.decrypt(body).decode())
            except:
                time.sleep(7)
                continue

            with self.lock:
                self.stats = CTGP7NEXHTTPHandler.HTTPStats(js)
    
    def get_stats(self) -> HTTPStats:
        # return copy reference
        with self.lock:
            return self.stats
    
    def get_user_from_pid(self, pid: int) -> HTTPStats.HTTPStatsUserInfo | None:
        stats = self.get_stats()
        for u in stats.users:
            if u.pid == pid:
                return u
        return None

    def get_room_from_gid(self, gid: int) -> HTTPStats.HTTPStatsSessionInfo | None:
        stats = self.get_stats()
        for r in stats.sessions:
            if r.gid == gid:
                return r
        return None

    def get_total_users(self) -> int:
        stats = self.get_stats()
        return len(stats.users)
    
    def get_total_rooms(self) -> int:
        stats = self.get_stats()
        return len(stats.sessions)

    def is_user_online(self, user) -> bool:
        return self.get_user_from_pid(user.pid) is not None
    
    def is_room_registered(self, room) -> bool:
        return self.get_room_from_gid(room.gID) is not None
    
    def is_user_in_room(self, user, room) -> bool:
        u = self.get_user_from_pid(user.pid)
        if u is None:
            return False
        r = self.get_room_from_gid(room.gID)
        if r is None:
            return False
        for cid in r.connections:
            if cid == u.cid:
                return True
        return False
    

    def kick_users(self, only_users = [], all_users: bool | None = None):
        users_to_kick: List[int] = []
        if all_users is not None and all_users == True:
            stats = self.get_stats()
            for u in stats.users:
                users_to_kick.append(u.cid)
        elif only_users is not None:
            for ou in only_users:
                u = self.get_user_from_pid(ou.pid)
                if u is not None:
                    users_to_kick.append(u.cid)

        if len(users_to_kick) == 0:
            return
        
        js = json.dumps({"Connections": users_to_kick})
        body = self.encrypt(js.encode())

        for i in range(0, 10):
            try:
                with self.httpsessionlock:
                    r = self.httpsession.post(self.httpaddr + "/kick", body, timeout=10)
                if (r.status_code != 200 or r.content.decode() != "ACK"):
                    raise Exception()
                break
            except:
                time.sleep(3)
                pass