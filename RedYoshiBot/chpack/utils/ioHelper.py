import struct, math, io

class IOHelper:
    endian = False
    fd = None
    closed = True
    relOff = 0
    size = 0

    @staticmethod
    def concatList(l, sep=""):
        s = ""
        for i in l:
            s += str(i)
            if i!=l[-1]: s += sep
        return s
    
    def __init__(self, fd:io.IOBase, e=False):
        if not hasattr(fd, "read"):
            self.fd = io.BytesIO(fd)
            self.relOff = 0
            self.size = 0
        else:
            self.fd = fd
            self.relOff = fd.tell()
            self.size = fd.seek(0,2)
            fd.seek(self.relOff)
        self.endian = e
        self.closed = False
    
    def setEndian(self, e='<'):
        try:
            ("little","<",False).index(e)
            self.endian = False
        except:
            try:
                ("big", ">", True).index(e)
                self.endian = True
            except: pass

    def readStruct(self, f) -> tuple:
        if self.closed: return
        g = f'{"<>"[self.endian]}{f}'
        return struct.unpack(g, self.fd.read(struct.calcsize(g)))

    def writeStruct(self, f, *v):
        if self.closed: return
        g = f'{"<>"[self.endian]}{f}'
        self.fd.write(struct.pack(g, *v))

    def readBOM(self):
        if self.closed: return
        s = struct.unpack('2s', self.fd.read(2))[0]
        self.endian = s[0]==254
        return self.endian
    
    def writeBOM(self):
        if self.closed: return
        self.fd.write(struct.pack(f'{"<>"[self.endian]}H', 0xFEFF))
    
    def readInt(self, len=8, signed=False) -> int:
        if self.closed: return
        bc = math.ceil(len/8)
        return int.from_bytes(self.fd.read(bc), ("little","big")[self.endian], signed=signed) & (2**len-1)
    
    def writeInt(self, v, len=8, signed=False):
        if self.closed: return
        bc = math.ceil(len/8)
        self.fd.write(int.to_bytes(v & (2**len-1), bc, ("little","big")[self.endian], signed=signed))

    def readString(self, len:int, enc="utf-8", cnv="replace"):
        if self.closed: return
        nenc = self.parseStrFmtName(enc)
        return struct.unpack(f"{len}s", self.fd.read(len))[0].rstrip(b'\0').decode(nenc, cnv)

    def writeString(self, s:str, len:int, enc="utf-8", cnv="replace"):
        if self.closed: return
        nenc = self.parseStrFmtName(enc)
        self.fd.write(struct.pack(f"{len}s", s.encode(nenc, cnv)))
    
    def readUTF16(self, len, cnv="replace"):
        if self.closed: return
        enc = f'utf-16-{"lb"[self.endian]}e'
        return struct.unpack(f"{len}s", self.fd.read(len & -2))[0].rstrip(b'\0').decode(enc, cnv)

    def writeUTF16(self, s:str, len:int, cnv="replace"):
        if self.closed: return
        enc = f'utf-16-{"lb"[self.endian]}e'
        self.fd.write(struct.pack(f"{len}s", s.encode(enc, cnv)))
    
    def readRaw(self, len:int) -> bytes:
        if self.closed: return
        return self.fd.read(len)

    def writeRaw(self, b:bytes, len:int, fill=b'\0'):
        if self.closed: return
        self.fd.write(b[:len].ljust(len,fill))
    
    def readRawTillNull(self, alignment=1, offset=0) -> bytes:
        if self.closed: return
        if alignment <= 0: return
        b = b''
        o = offset % alignment
        while True:
            c = self.fd.read(alignment-o)
            if o: o = 0
            if not len(c): break
            b += c
            if b.find(b'\0')>=0: break
        return b

    def writeRawPadded(self, b:bytes, alignment=1):
        if self.closed: return
        if alignment <= 0: return
        self.fd.write(b.ljust(((len(b) + alignment) // alignment) * alignment,b'\0'))
    
    def getSize(self):
        self.size = max(self.size, self.fd.tell())
        return self.size

    def setSize(self, s:int):
        self.size = s
        self.fd.truncate(s)

    def getOffset(self):
        return self.fd.tell()

    def setOffset(self, off:int, whence=0):
        return self.fd.seek(off, whence)

    def readable(self): return self.fd.readable()
    def writable(self): return self.fd.writable()

    def close(self):
        if self.closed: return
        self.fd.close()
        self.closed = True

    def parseStrFmtName(self, s:str):
        while True:
            i = s.find("$[")
            if i<0: break
            j = s.find("]", i)
            t = s[i+2:j].split(";")
            s = s[:i] + t[self.endian] + (s[j+1:] if j>0 else "")
        print(s)
        return s

    def __len__(self):
        s = self.fd.tell()
        if s > self.size: self.size = s
        return self.size - self.relOff
