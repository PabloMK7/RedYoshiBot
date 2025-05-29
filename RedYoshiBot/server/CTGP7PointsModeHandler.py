import asyncio
import random
import time
import threading

from .CTGP7ServerDatabase import CTGP7ServerDatabase
from ..CTGP7Defines import CTGP7Defines

class CTGP7PointsModeHandler:

    class WeeklyChallengeConfig:
        
        def __init__(self, new: bool, db: CTGP7ServerDatabase):
            if not new and self.load(db):
                return

            MAX_DRIVERID = 17-1
            MAX_BODYID = 16
            MAX_TIREID = 9
            MAX_WINGID = 6

            duration = db.get_weekly_points_duration_seconds()
            partAmount = db.get_weekly_points_special_part_amounts()

            self.uid = random.getrandbits(63)
            self.endTime = int(time.time()) + duration
            oldszs = db.get_weekly_points_config("trackSzs", "")
            self.trackSzs = oldszs
            while self.trackSzs == oldszs:
                self.trackSzs = CTGP7Defines.getRandomTrackSZS()
            self.recDrivers = random.sample(range(0, MAX_DRIVERID + 1), int(partAmount[0]))
            self.recBodies = random.sample(range(0, MAX_BODYID + 1), int(partAmount[1]))
            self.recTires = random.sample(range(0, MAX_TIREID + 1), int(partAmount[2]))
            self.recWings = random.sample(range(0, MAX_WINGID + 1), int(partAmount[3]))
            for i in range(0, len(self.recDrivers)): # Skip female mii
                if self.recDrivers[i] >= 10:
                    self.recDrivers[i] += 1

            self.save(db)

        def load(self, db: CTGP7ServerDatabase):
            self.uid = db.get_weekly_points_config("uid", None)
            if self.uid is None:
                self.endTime = 0
                self.trackSzs = ""
                self.recDrivers = []
                self.recBodies = []
                self.recTires = []
                self.recWings = []
                return False
            self.uid = int(self.uid)
            self.endTime = int(db.get_weekly_points_config("endDate", "0"))
            self.trackSzs = db.get_weekly_points_config("trackSzs", "")
            self.recDrivers = [int(x) for x in db.get_weekly_points_config("recDrivers", "").split()]
            self.recBodies = [int(x) for x in db.get_weekly_points_config("recBodies", "").split()]
            self.recTires = [int(x) for x in db.get_weekly_points_config("recTires", "").split()]
            self.recWings = [int(x) for x in db.get_weekly_points_config("recWings", "").split()]
            return True

        def save(self, db: CTGP7ServerDatabase):
            db.set_weekly_points_config("uid", self.uid)
            db.set_weekly_points_config("endDate", self.endTime)
            db.set_weekly_points_config("trackSzs", self.trackSzs)
            db.set_weekly_points_config("recDrivers", " ".join(str(x) for x in self.recDrivers))
            db.set_weekly_points_config("recBodies", " ".join(str(x) for x in self.recBodies))
            db.set_weekly_points_config("recTires", " ".join(str(x) for x in self.recTires))
            db.set_weekly_points_config("recWings", " ".join(str(x) for x in self.recWings))

        def __str__(self):
            ret = "UID: 0x{:016X}\nEnd Date: {}\n".format(self.uid, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.endTime)))
            ret += "Course: {}\n".format(CTGP7Defines.getTrackNameFromSzs(self.trackSzs))
            ret += "Bonus:\n"
            ret += "\tDrivers: {}\n".format(", ".join(CTGP7Defines.getDriverName(x) for x in self.recDrivers))
            ret += "\tKarts: {}\n".format(", ".join(CTGP7Defines.getKartBodyName(x) for x in self.recBodies))
            ret += "\tTires: {}\n".format(", ".join(CTGP7Defines.getKartTireName(x) for x in self.recTires))
            ret += "\tGliders: {}".format(", ".join(CTGP7Defines.getKartWingName(x) for x in self.recWings))
            return ret

        def asBson(self):
            ret = {}
            ret["uid"] = self.uid
            ret["remaining"] = max(self.endTime - int(time.time()), 0)
            ret["trackSzs"] = self.trackSzs
            ret["recDrivers"] = "::".join(str(x) for x in self.recDrivers)
            ret["recBodies"] = "::".join(str(x) for x in self.recBodies)
            ret["recTires"] = "::".join(str(x) for x in self.recTires)
            ret["recWings"] = "::".join(str(x) for x in self.recWings)
            return ret

    def __init__(self, db: CTGP7ServerDatabase):
        self.currDatabase = db
        self.configLock = threading.Lock()
        self.taskRunning = True
        self.task = asyncio.create_task(self._check_task())
        with self.configLock:
            self.config = self.WeeklyChallengeConfig(False, db)

    def __del__(self):
        self.stop()

    def stop(self):
        if self.taskRunning:
            self.taskRunning = False
            self.task.cancel()

    def getConfigBson(self):
        with self.configLock:
            return self.config.asBson()
        
    def getLeaderboardBson(self, cID):
        with self.configLock:
            ret = {}
            ret["uid"] = self.config.uid
            topTen = self.currDatabase.get_weekly_points_leaderboard(1, 10, 10, cID)
            aroundMe = self.currDatabase.get_weekly_points_surrounding(cID)
            topTenArr = []
            aroundMeArr = []
            i = 0
            for l in topTen[1]:
                topTenArr.append(str(-l.rank if i == topTen[0] else l.rank))
                topTenArr.append(l.name)
                topTenArr.append(str(l.score))
                i+=1
            i = 0
            for l in aroundMe[1]:
                aroundMeArr.append(str(-l.rank if i == aroundMe[0] else l.rank))
                aroundMeArr.append(l.name)
                aroundMeArr.append(str(l.score))
                i+=1
            ret["top"] = "\\".join(topTenArr)
            ret["around"] = "\\".join(aroundMeArr)
            return ret
        
    def updatePlayerScore(self, cID, score, uID=-1):
        with self.configLock:
            if uID != -1 and uID != self.config.uid:
                return False
            self.currDatabase.set_weekly_points_leaderboard_score(cID, score)
            return True

    def getConfigStr(self):
        with self.configLock:
            return str(self.config)
        
    def updateEndTime(self, newEndTime):
        with self.configLock:
            self.config.endTime = newEndTime
            self.config.save(self.currDatabase)

    async def _check_task(self):
        while self.taskRunning:
            with self.configLock:
                endTime = self.config.endTime
            if endTime == 0 or int(time.time()) >= endTime:
                with self.configLock:
                    self.config = self.WeeklyChallengeConfig(True, self.currDatabase)
                    self.currDatabase.clear_weekly_points_leaderboard()
            await asyncio.sleep(5)