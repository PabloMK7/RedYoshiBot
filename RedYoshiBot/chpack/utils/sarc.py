from struct import pack, unpack_from
from io import BytesIO, IOBase
from typing import Any
from .ioHelper import IOHelper
import os
from hashlib import sha256
from math import log2, ceil

VERBOSE = False

def vprint(*s, **kwd):
    if VERBOSE: print(*s, **kwd)

def nametrunc(s:str):
    r = 0
    r = s.rfind(os.sep, 0, r-1)
    r = s[s.rfind(os.sep, 0, r-1)+1:]
    if len(s)!=len(r): r = ".../"+r
    return r

class SAHT:
    def __init__(self, data=None):
        self.key = 101 # It's not defined here, is SAHT a custom format?
        self.hashes = dict()
        self.alignment = 0x10
        if data is None:
            return
        elif type(data) is dict:
            self.hashes = data
            return
        elif isinstance(data, IOBase):
            fd = IOHelper(data)
        elif type(data) is IOHelper:
            fd = data
        else:
            fd = IOHelper(BytesIO(data))
        
        assert fd.readRaw(4)==b'SAHT', "Invalid SAHT file"
        size = fd.readInt(32)
        self.alignment = fd.readInt(32)
        count = fd.readInt(32)
        curOffset = 0x10
        i = 0
        while curOffset < size and i < count:
            chash = fd.readInt(32)
            cname = fd.readRawTillNull(self.alignment, 4).decode("utf-8","ignore").strip("\0")
            self.hashes[chash] = cname
            i += 1
    def getHash(self, key):
        h = SARC.hash(key, self.key)
        return h if (h in self.hashes) else 0
    def getAddHash(self, key):
        h = SARC.hash(key, self.key)
        if not h in self.hashes:
            self.hashes[h] = key
        return h
    def remove(self, key):
        if type(key) is str:
            h = SARC.hash(key, self.key)
        else:
            h = key
        self.hashes.pop(h,None)
    def add(self, key):
        h = SARC.hash(key, self.key)
        self.hashes[h] = key
    def verify(self, action=""):
        out = True
        removeKey = action=="remove"
        fixHash = action=="fix"
        badKeys = []
        for h,n in self.hashes.items():
            nh = SARC.hash(n, self.key)
            if h != nh:
                out = False
                badKeys.append(h)
        
        for h in badKeys:
            if removeKey:
                vprint(f"SAHT: Removed key {h:08X}({self.hashes[h]})")
                self.hashes.pop(h)
            if fixHash:
                nh = SARC.hash(n, self.key)
                vprint(f"SAHT: Fixed key {h:08X} -> {nh:08X}({self.hashes[h]})")
                self.hashes.pop(h)
                self.hashes[nh] = n
        return out
    def getName(self, key) -> str:
        return self.hashes.get(key, "")
    def __add__(self, key):
        self.hashes[SARC.hash(key, self.key)] = key
        return SAHT(self.hashes)
    def save(self, fd:IOHelper):
        self.hashes = dict(sorted(self.hashes.items(), key=lambda x:x[0]))
        foff = fd.getOffset()
        fd.writeRaw(b'SAHT',4)
        fd.writeInt(0, 32)
        fd.writeInt(self.alignment, 32)
        fd.writeInt(len(self.hashes), 32)
        for hash, fileName in self.hashes.items():
            fd.writeRawPadded(
                int.to_bytes(hash, 4, ["little","big"][fd.endian]) +
                fileName.encode("utf-8","ignore"),
                self.alignment
            )
        size = fd.getSize() - foff
        fd.setOffset(foff + 4)
        fd.writeInt(size, 32)

class SFATEntry:
    _SIZE_ = 16
    
    def __init__(self, fd:IOHelper=None, dataOff=0, mul=101):
        self.mul = mul
        self.name = 0
        self.humanName = ""
        self.type = "bin"
        self.strOff = 0
        self.data = b''
        if fd:
            self.name = fd.readInt(32)
            self.humanName = f"{self.name:08X}.bin"
            self.strOff = fd.readInt(32)

            dataStart = fd.readInt(32)
            dataLength = fd.readInt(32) - dataStart

            fo = fd.getOffset()
            fd.setOffset(dataStart + dataOff)
            self.data = fd.readRaw(dataLength)
            fd.setOffset(fo)
            self.type = SARC.guessExt(self.data)
    
    def pack(self, fd:IOHelper, off, mainOff, combineDup=False, shahash:dict={}, forcePad:int=None):
        if type(self.name)==str:
            fd.writeInt(SARC.hash(self.name, self.mul), 32)
        else:
            fd.writeInt(self.name, 32)
        fd.writeInt(self.strOff, 32)
        
        if combineDup:
            sh = sha256(self.data).digest()
            if sh in shahash:
                fd.writeInt(shahash[sh].fileOff, 32)
                fd.writeInt(shahash[sh].fileEnd, 32)
                return
            else:
                shahash[sh] = self

        pad = 4
        
        if self.type=="aamp": pad = 3
        try:
            [
                "bclyt", "bclan", "bctr"
            ].index(self.type)
            pad = 4
        except: pass
        try:
            [
                "bcwav", "bcstm", "div", "kmp", "byml"
            ].index(self.type)
            pad = 5
        except: pass
        try:
            [
                "bcfnt", "msbt", "msbp", "yaz", "cbmd",
                "bclim", "cgfx", "bch",  "ctpk"
            ].index(self.type)
            pad = 7
        except: pass
        try:
            [
                "sarc", "darc"
            ].index(self.type)
            pad = 17
        except: pass

        pad = forcePad if forcePad else pad

        pad = (2**pad) - 1
        dataLen = (len(self.data) + pad) & ~pad
        off = (off + pad) & ~pad
        
        self.fileOff = off - mainOff
        self.fileEnd = self.fileOff + len(self.data)
        fd.writeInt(self.fileOff, 32)
        fd.writeInt(self.fileEnd, 32)
        
        co = fd.getOffset()
        fd.setOffset(off)
        fd.writeRaw(self.data, dataLen)
        fd.getSize()
        fd.setOffset(co)

    def __lt__(self, other):
        if type(other) is type(self):
            if type(self.name) is str:
                self.name = SARC.hash(self.name, self.mul)
            if type(other.name) is str:
                other.name = SARC.hash(other.name, other.mul)
            return self.name < other.name
    
    def __repr__(self) -> str:
        return f"0x{self.name:08X}"

class SARC:
    class SFNT:
        _SIZE_ = 8

        def __init__(self, fd:IOHelper = None, dataOff=0):
            self.unk1 = 0
            self.data = b''
            if fd:
                assert fd.readRaw(4) == b'SFNT', "Invalid SFNT entry"
                fd.readInt(16)
                self.unk1 = fd.readInt(16)
                self.data = fd.readRaw(dataOff)
        
        def calcsize(self):
            return 8 + (len(self.data)+4)//4*4 if self.data else 8
        
        def pack(self, fd:IOHelper, sfat=None):
            fd.writeRaw(b'SFNT', 4)
            fd.writeInt(self._SIZE_, 16)
            fd.writeInt(self.unk1, 16)
            if self.data: fd.writeRawPadded(self.data, 4)
    
    class SFAT:
        _SIZE_ = 0xC
        multiplier = 101
        nodes:list[SFATEntry] = None
        
        def __init__(self, fd:IOHelper = None, dataOff = 0):
            self.multiplier = 101
            self.nodes = []
            if fd:
                assert fd.readRaw(4)==b'SFAT', "Invalid SFAT entry"
                fd.readInt(16)
                nodeCount = fd.readInt(16)
                self.multiplier = fd.readInt(32)

                for i in range(nodeCount):
                    self.nodes.append(SFATEntry(fd, dataOff, self.multiplier))
                self.nodes.sort()

        def getFile(self, name) -> SFATEntry:
            if type(name)==str:
                h = SARC.hash(name, self.multiplier)
            else:
                h = name
            
            for i in self.nodes:
                if type(i.name)==str:
                    i.name = SARC.hash(i.name, self.multiplier)
                if i.name == h: return i
            else:
                return None
        
        def remove(self, name):
            try:
                self.nodes.remove(self.getFile(name))
            except: pass
        
        def add(self, name, data):
            s = SFATEntry(mul=self.multiplier)
            if type(name) is str:
                s.name = SARC.hash(name, s.mul)
                s.humanName = name
            else:
                s.name = name
                s.humanName = f"0x{name:08X}"

            s.data = data
            s.strOff = 0
            s.type = SARC.guessExt(s.data)
            self.nodes.append(s)

        def calcsize(self):
            return self._SIZE_ + SFATEntry._SIZE_ * len(self.nodes)

        def packSFNTData(self, saveSFNT=False):
            b = b''
            for i in self.nodes:
                i.strOff = 0
                if saveSFNT:
                    i.strOff = 1<<24 | len(b)//4
                    n = i.humanName.encode("utf-8","ignore")
                    b += n.ljust((len(n)+4)//4*4,b'\0')
            return b

        def prepareExport(self):
            self.nodes.sort()

        def pack(self, fd:IOHelper, dataOff:int, combineDup=False, forcePad:int=None):
            fd.writeRaw(b'SFAT', 4)
            fd.writeInt(self._SIZE_, 16)
            fd.writeInt(len(self.nodes), 16)
            fd.writeInt(self.multiplier, 32)

            off = dataOff
            shaHash = dict()
            for i in self.nodes:
                i.pack(fd, off, dataOff, combineDup, shaHash, forcePad)
                off = fd.getSize()

    sfnt:SFNT = None
    sfat:SFAT = None
    _HDR_SIZE_ = 20
    version = 256

    @staticmethod
    def guessExt(data:bytes):
        if data[-0x28:-0x24]==b"CLIM": return "bclim"
        if data[:4]==b"BADC": return "div"
        if data[:4]==b"DMDC": return "kmp"
        if data[:4]==b"BCTR": return "bctr"
        if data[:3]==b"Yaz": return "yaz"
        if data[:3]==b"BCH": return "bch"
        if data[:4]==b"SARC": return "sarc"
        if data[:4]==b"DARC": return "darc"
        if data[:4]==b"SMDH": return "smdh"
        if data[:4]==b"CLYT": return "bclyt"
        if data[:4]==b"CLAN": return "bclan"
        if data[:4]==b"CBMD": return "cbmd"
        if data[:4]==b"CGFX": return "bcres"
        if data[:4]==b"CTPK": return "ctpk"
        if data[:4]==b"AAMP": return "aamp"
        if data[:4]==b"CWAV": return "bcwav"
        if data[:4]==b"CSTM": return "bcstm"
        if data[:4]==b"CFNT": return "bcfnt"
        if data[:8]==b"MsgStdBn": return "msbt"
        if data[:8]==b"MsgPrjBn": return "msbp"
        if data[:2]==b"YB": return "byml"
        return "bin"

    @staticmethod
    def hash(name, multiplier):
        if type(name) is int:
            return name
        hash = 0
        for i in name:
            hash = (hash * multiplier + ord(i)) & (2**32-1)
        return hash
    
    def hashName(self, name):
        return SARC.hash(name, self.sfat.multiplier)
    
    def hasFile(self, name):
        return self.sfat.getFile(name)!=None

    def getFile(self, name):
        vprint(f"SARC.getFile[{nametrunc(self.name)}]: {name}")
        return self.sfat.getFile(name)
    
    def setFile(self, name, data, raiseErr=False):
        if not isinstance(data, IOBase):
            if type(data) is bytes:
                fd = BytesIO(data)
            else:
                if os.path.exists(data):
                    fd = open(data, "rb")
                elif raiseErr:
                    raise Exception("File doesn't exist: "+data)
                else:
                    return
        else:
            fd = data
        
        vprint(f"SARC.setFile[{nametrunc(self.name)}]: {name}")
        
        if self.hasFile(name):
            self.sfat.remove(name)
        
        self.sfat.add(name, fd.read())

    def __init__(self, data=None, saht:SAHT=None):
        self.name = "new"
        if data:
            self.load(data)
        else:
            self.sfat = SARC.SFAT()
            self.sfnt = SARC.SFNT()
        
        self.resolveHumanNames(saht)

    def resolveHumanNames(self, saht:SAHT=None):
        sfnt:bytes = self.sfnt.data
        useHT = saht and self.sfat.multiplier == 101 # SAHT hardcodes this for whatever reason (custom format?)
        for i in self.sfat.nodes:
            i:SFATEntry
            i.humanName = sfnt[i.strOff*4:sfnt.find(b'\0', i.strOff*4)].strip(b'\0').decode("utf-8","ignore")
            if useHT:
                i.humanName = saht.getName(i.name)
            if not len(i.humanName):
                i.humanName = f"0x{i.name:08X}.{i.type}"

    def load(self, data):
        if not isinstance(data, IOHelper):
            self.name = "<bytes>"
            f = IOHelper(data, False)
        else:
            f = data
        
        if hasattr(f.fd, "name"): self.name = f.fd.name
        assert f.readRaw(4)==b"SARC", "Invalid SARC file"
        f.readInt(16)
        f.readBOM()
        assert f.getSize() >= f.readInt(32), "SARC size mismatch"
        dataOff = f.readInt(32)
        self.version = f.readInt(16)
        assert self.version == 0x100, "SARC version mismatch"
        f.readRaw(2)

        self.sfat = SARC.SFAT(f, dataOff)
        self.sfnt = SARC.SFNT(f, dataOff - f.getOffset())

    def pack(self, fd:IOHelper, combineDup=False, saveSFNT=False, forcePad:int=None):
        vprint(f"Packing SARC to {fd.fd.name if hasattr(fd.fd,'name') else '<bytes>'}...")
        fd.setSize(0)
        self.sfat.prepareExport()
        self.sfnt.data = self.sfat.packSFNTData(saveSFNT)
        dataOff = (self._HDR_SIZE_ + self.sfat.calcsize() + self.sfnt.calcsize() + 127) & ~127
        
        fd.setSize(dataOff)
        fd.writeRaw(b'SARC', 4)
        fd.writeInt(self._HDR_SIZE_, 16)
        fd.writeBOM()
        fd.writeInt(0, 32)
        fd.writeInt(dataOff, 32)
        fd.writeInt(self.version, 16)
        fd.writeInt(0, 16)

        fd.setOffset(self._HDR_SIZE_ + self.sfat.calcsize())
        self.sfnt.pack(fd, self.sfat)
        fd.setOffset(self._HDR_SIZE_)
        self.sfat.pack(fd, dataOff, combineDup, forcePad)

        fd.getSize()
        fd.setOffset(8)
        fd.writeInt(fd.getSize(), 32)

    def __repr__(self) -> str:
        return f"<SARC version={self.version}, nodes={self.sfat.nodes}>"