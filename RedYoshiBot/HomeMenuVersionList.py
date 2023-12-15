import requests
import struct
import warnings
from urllib3.exceptions import InsecureRequestWarning

class HomeMenuVersionList:

    def __init__(self):
        self.versionlist = {}
        try:
            warnings.simplefilter("ignore", InsecureRequestWarning)
            response = requests.get("https://tagaya-ctr.cdn.nintendo.net/tagaya/versionlist", verify=False, timeout=7)
        except Exception:
            raise Exception("Failed to download version list")
        finally:
            warnings.simplefilter("default", InsecureRequestWarning)
        if (response.status_code == 200):
            data = response.content
            for entry in struct.iter_unpack("<QII", data):
                self.versionlist[entry[0]] = entry[1]
        else:
            raise Exception("Got response: {}".format(response.status_code))

    def print_version_list(self):
        for k in self.versionlist:
            print("{:016X}: {}".format(k, self.versionlist[k]))

    def get_version_for_title(self, titleID):
        try:
            return self.versionlist[titleID]
        except:
            return None