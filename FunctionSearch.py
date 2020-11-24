import struct

class MK7FunctionSearch:

    codeSectionFiles = [["", "", ""], ["", "eur_rev0_v11_code.bin", "eur_rev1_code.bin"], ["", "usa_rev0_v11_code.bin", "usa_rev1_code.bin"], ["", "jap_rev0_v11.bin", "jap_rev1_code.bin"]]
    downloadPlayCode = "code_sections/dlp_code.bin"
    xmapFile = "code_sections/CTRDash.xmap"

    def __init__(self, region, version):
        self.fileData = b""
        self.dlpData = b""
        self.xmapData = {}
        self._populateXmapFile()
        
        try:
            codefile = self.codeSectionFiles[region][version]
            if not (codefile == ""):
                with open("code_sections/" + codefile, "rb") as f:
                    self.fileData = f.read()
            with open(self.downloadPlayCode, "rb") as f:
                self.dlpData = f.read()
        except:
            pass

    def _populateXmapFile(self):
        with open(self.xmapFile, "r") as xmap:
            for l in xmap:
                l2 = l.split("\t")
                fname = l2[1]
                faddr = int(l2[0], 16)
                self.xmapData[faddr] = fname
    
    def _searchDlpOccurences(self, dataBlock):
        index = 0
        start = 0
        ret = []
        while (index != -1):
            index = self.dlpData.find(dataBlock, start)
            if (index != -1):
                ret = ret + [index]
                start = index + 4
        return ret

    def _getFunctionName(self, dlpAddr):
        prevk = 0
        for k in self.xmapData.keys():
            if (dlpAddr >= k):
                prevk = k
                continue
            else:
                return prevk, self.xmapData[prevk]
        return 0, ""

    def functionNameForAddr(self, addr):
        if (addr > 0x07000000 and addr < 0x08000000):
            return "Plugin"
        
        if (self.fileData == b"" or self.dlpData == b"" or addr < 0x100000):
            return "???"

        addr = addr - 0x100000

        if (addr > len(self.fileData) - 0x10):
            return "???"

        currAddr = addr
        dlpAddr = 0
        searchAm = 0x10
        origSearchAm = 0x10
        forward = False
        while (True):
            if (abs(currAddr - addr) > searchAm):
                currAddr = addr
                if (forward):
                    forward = False
                    if (searchAm > 8):
                        searchAm -= 4
                        continue
                    else:
                        break
                else:
                    forward = True
                    continue
            dataBlock = self.fileData[currAddr : currAddr + searchAm]
            if all(v == 0 for v in dataBlock): return "???"
            shouldContinue = False
            for i in range(searchAm // 4):
                shouldContinue = False
                instruction = struct.unpack("I", dataBlock[i*4 : (i+1)*4])[0]
                if ((instruction & 0x0F000000) == 0x0B000000):
                    if forward: currAddr = currAddr + 4 * (i + 1)
                    else: currAddr = currAddr - 4*((searchAm // 4) - i)
                    shouldContinue = True
                    break
            if (shouldContinue): continue
            found = self._searchDlpOccurences(dataBlock)
            if (len(found) != 1):
                if len(found) == 0:
                    return "???"
                else:
                    origSearchAm += 4
                    searchAm = origSearchAm
                    forward = False
                    currAddr = addr
                    if (searchAm > 0x60):
                        return "???"
                    continue
            dlpAddr = found[0]
            break
        offset = currAddr - addr
        if (dlpAddr == 0):
            return "???"
        
        dlpAddr = dlpAddr + 0x100000

        fAddr, fName = self._getFunctionName(dlpAddr)
        if (fAddr == 0):
            return "???"
        else:
            return fName.strip() + "+{:X}".format((dlpAddr - offset) - fAddr)
