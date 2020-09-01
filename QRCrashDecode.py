from PIL import Image
import requests
from io import BytesIO
from pyzbar import pyzbar
import base64
import struct
from CTGP7Defines import CTGP7Defines

class QRCrashDecode:

    SEPARATOR = "-----------------------------------\n"
    gameRegion = {0: "None", 1: "Europe", 2: "America", 3: "Japan"}
    gameRevision = {0: "Rev0", 1: "Rev0 1.1", 2: "Rev1"}
    exceptionType = {0: "Prefetch abort", 1: "Data abort", 2: "Undefined instruction", 3: "Abort", 4: "Custom", 5: "Unknown"}
    gameState = {0: "Uninitialized", 1: "Patch Process", 2: "Main", 3: "Menu (ID: {})", 4: "Race ({})", 5: "Trophy"}

    def __init__(self, url = "", data = ""):
        if (data != ""):
            qrData = data
        elif (url != ""):
            try:
                response = requests.get(url)
                if (response.status_code != 200):
                    raise Exception()
            except:
                raise Exception("Couldn't download image!")
            try:
                img = Image.open(BytesIO(response.content))
            except:
                raise Exception("Invalid image provided!")
            try:
                qrData = pyzbar.decode(img)[0].data
            except:
                raise Exception("QR Code data not found!")
        else:
            raise Exception("No data provided!")
        
        try:
            self.crashData = base64.b64decode(qrData)
        except:
            raise Exception("QR Code data invalid!")
        
        self.dataVersion = self.__getCrashDataVersion()
        try:
            self.parsedData = struct.unpack(QRCrashDecode.versionFormats[self.dataVersion], self.crashData[4:])
        except:
            raise Exception("QR Code data invalid!")
    
    def printData(self):
        try:
            return QRCrashDecode.versionFunctions[self.dataVersion](self.parsedData)
        except:
            raise Exception("Crash data version not supported!")

    def __getCrashDataVersion(self):
        if (len(self.crashData) < 4 or self.crashData[1:4] != b'R7C'):
            raise Exception("QR Code data invalid!")
        return self.crashData[0:1].decode("ascii")

    
    @staticmethod
    def __printDataVer0(data):
        try:
            ret = ""
            major = data[0] >> 24
            minor = (data[0] >> 16) & 0xFF
            micro = (data[0] >> 8) & 0xFF
            ctgpver = "{}.{}.{}".format(major, minor, micro)
            ret += "CTGP-7 version: {}\n".format(ctgpver)
            ret += "MK7 version: {} {}\n".format(QRCrashDecode.gameRegion[(data[13] >> 4) & 0xF], QRCrashDecode.gameRevision[data[13] & 0xF])
            ret += QRCrashDecode.SEPARATOR
            ret += "Exception type: {}\n".format(QRCrashDecode.exceptionType[data[14]])
            ret += "Registers:\n"
            ret += "    SP: 0x{:08X}  PC: 0x{:08X}\n".format(data[1], data[2])
            ret += "   FAR: 0x{:08X}  LR: 0x{:08X}\n".format(data[4], data[3])
            ret += "Call Stack:\n"
            ret += "     1: 0x{:08X}   2: 0x{:08X}   3: 0x{:08X}\n".format(data[5], data[6], data[7])
            ret += "     4: 0x{:08X}   5: 0x{:08X}   6: 0x{:08X}\n".format(data[8], data[9], data[10])
            ret += QRCrashDecode.SEPARATOR
            ret += "Game state: {}".format(QRCrashDecode.gameState[data[11]].format(CTGP7Defines.getMenuString(data[12]) if data[11] == 3 else (CTGP7Defines.getTrackString(data[0], data[12]) if data[11] == 4 else "")))
            return ret
        except:
            raise Exception("QR Code parameters invalid!")

    versionFormats = {'0': 'IIIII6IIIBBxx'}
    versionFunctions = {'0': __printDataVer0.__func__}

    