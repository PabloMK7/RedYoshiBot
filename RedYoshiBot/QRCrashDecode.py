from PIL import Image
import cv2
import numpy as np
import requests
from io import BytesIO
from pyzbar import pyzbar
import base64
import struct
from .CTGP7Defines import CTGP7Defines
from .FunctionSearch import MK7FunctionSearch
import traceback

class QRCrashDecode:

    SEPARATOR = "-----------------------------------\n"
    gameRegion = {0: "None", 1: "Europe", 2: "America", 3: "Japan", 4: "Korea"}
    gameRevision = {0: "Rev0", 1: "Rev0 1.1", 2: "Rev1", 3: "1.2"}
    exceptionType = {0: "Prefetch abort", 1: "Data abort", 2: "Undefined instruction", 3: "Abort", 4: "Custom", 5: "Unknown"}
    gameState = {0: "Uninitialized", 1: "Patch Process", 2: "Main", 3: "Menu (ID: {})", 4: "Race ({})", 5: "Trophy"}
    
    @staticmethod
    def downloadDecodeQR(url):
        try:
            response = requests.get(url, timeout=7, stream=True)
            if (response.status_code != 200):
                raise Exception("Got {}".format(response.status_code))
            response_content = BytesIO()
            size = 0
            for chunk in response.iter_content(1_000_000):
                size += len(chunk)
                response_content.write(chunk)
                if size > 50_000_000:
                    raise ValueError('Image too large!')
        except Exception as e:
            raise Exception("Couldn't download image: " + repr(e))
        response_content.seek(0)
        try:
            file_bytes = np.asarray(bytearray(response_content.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
            # preprocessing using opencv
            blur = cv2.GaussianBlur(img, (5, 5), 0)
            ret, img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        except:
            raise Exception("Invalid image provided!")
        try:
            qrData = pyzbar.decode(img)[0].data
        except:
            raise Exception("QR Code data not found!")
        return qrData

    def __init__(self, url = "", data = ""):
        if (data != ""):
            qrData = data
        elif (url != ""):
            qrData = QRCrashDecode.downloadDecodeQR(url)
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
            traceback.print_exc()
            raise Exception("Crash data version not supported!")

    def __getCrashDataVersion(self):
        if (len(self.crashData) < 4 or self.crashData[1:4] != b'R7C'):
            raise Exception("QR Code data invalid!")
        return self.crashData[0:1].decode("ascii")

    
    @staticmethod
    def __printDataVer0(data):
        try:
            region = (data[13] >> 4) & 0xF
            version = data[13] & 0xF
            fs = MK7FunctionSearch(region, version)
            ret = ""
            major = data[0] >> 24
            minor = (data[0] >> 16) & 0xFF
            micro = (data[0] >> 8) & 0xFF
            ctgpver = "{}.{}.{}".format(major, minor, micro)
            ret += "CTGP-7: v{}\n".format(ctgpver)
            ret += "MK7: {} {}\n".format(QRCrashDecode.gameRegion[region], QRCrashDecode.gameRevision[version])
            ret += QRCrashDecode.SEPARATOR
            ret += "Exception: {}\n".format(QRCrashDecode.exceptionType[data[14]])
            ret += "Registers:\n"
            ret += "- SP: 0x{:08X}\n".format(data[1])
            ret += "- FAR: 0x{:08X}\n".format(data[4])
            ret += "Call Stack:\n"
            ret += "- PC: 0x{:08X} ({})\n".format(data[2], fs.functionNameForAddr(data[2]))
            ret += "- LR: 0x{:08X} ({})\n".format(data[3], fs.functionNameForAddr(data[3]))
            ret += "- 1: 0x{:08X} ({})\n".format(data[5], fs.functionNameForAddr(data[5]))
            ret += "- 2: 0x{:08X} ({})\n".format(data[6], fs.functionNameForAddr(data[6]))
            ret += "- 3: 0x{:08X} ({})\n".format(data[7], fs.functionNameForAddr(data[7]))
            ret += "- 4: 0x{:08X} ({})\n".format(data[8], fs.functionNameForAddr(data[8]))
            ret += "- 5: 0x{:08X} ({})\n".format(data[9], fs.functionNameForAddr(data[9]))
            ret += "- 6: 0x{:08X} ({})\n".format(data[10], fs.functionNameForAddr(data[10]))
            ret += QRCrashDecode.SEPARATOR
            ret += "State: {}".format(QRCrashDecode.gameState[data[11]].format(CTGP7Defines.getMenuString(data[12]) if data[11] == 3 else (CTGP7Defines.getTrackString(data[0], data[12]) if data[11] == 4 else "")))
            return ret
        except:
            raise Exception("QR Code parameters invalid!")
    
    @staticmethod
    def __printDataVerA(data):
        try:
            region = (data[2] >> 4) & 0xF
            version = data[2] & 0xF
            ret = ""
            major = data[0] >> 24
            minor = (data[0] >> 16) & 0xFF
            micro = (data[0] >> 8) & 0xFF
            ctgpver = "{}.{}.{}".format(major, minor, micro)
            ret += "CTGP-7: v{}\n".format(ctgpver)
            ret += "MK7: {} {}\n".format(QRCrashDecode.gameRegion[region], QRCrashDecode.gameRevision[version])
            ret += QRCrashDecode.SEPARATOR
            ret += "Text:\n\t" + data[1].decode("utf-8") + "\n"
            ret += QRCrashDecode.SEPARATOR
            return ret.replace("`", "").replace("@", "(at)")
        except:
            raise Exception("QR Code parameters invalid!")

    versionFormats = {'0': 'IIIII6IIIBBxx', 'A': 'I48sBBxx'}
    versionFunctions = {'0': __printDataVer0.__func__, 'A': __printDataVerA.__func__}

    