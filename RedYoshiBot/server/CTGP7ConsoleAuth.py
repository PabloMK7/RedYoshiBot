import hashlib
import re
import secrets
import struct
import threading
import time

# Verification of the console authentication done by the plugin with AM:Sign.
# AM:Sign creates a temporary certificate (AP cert) signed by the console's CTCert and signs the
# data with the AP cert key. The chain checked here is:
#   Nintendo CTR2prod key -> CTCert -> AP cert -> signature over the message.
# All keys are ECC sect233r1, signatures are ECDSA with SHA256. The ECC code is implemented here
# because the "cryptography" module is removing support for binary curves.

class ECC_sect233r1:
    # SEC 2 v2, section 3.3.2
    POLY = (1 << 233) | (1 << 74) | 1
    DEG = 233
    B = 0x0066647EDE6C332C7F8C0923BB58213B333B20E9CE4281FE115F7D8F90AD
    GX = 0x00FAC9DFCBAC8313BB2139F1BB755FEF65BC391F8B36F8F8EB7371FD558B
    GY = 0x01006A08A41903350678E58528BEBF8A0BEFF867A7CA36716F7E01F81052
    N = 0x01000000000000000000000000000013E974E72F8A6922031D2603CFE0D7

    @staticmethod
    def _fmul(a: int, b: int) -> int:
        r = 0
        while b:
            if b & 1:
                r ^= a
            b >>= 1
            a <<= 1
            if a >> 233:
                a ^= ECC_sect233r1.POLY
        return r

    @staticmethod
    def _finv(a: int) -> int:
        # Extended Euclid over GF(2)[t]
        u, v = a, ECC_sect233r1.POLY
        g1, g2 = 1, 0
        while u != 1:
            j = u.bit_length() - v.bit_length()
            if j < 0:
                u, v = v, u
                g1, g2 = g2, g1
                j = -j
            u ^= v << j
            g1 ^= g2 << j
        return ECC_sect233r1._freduce(g1)

    @staticmethod
    def _freduce(a: int) -> int:
        while a.bit_length() > 233:
            a ^= ECC_sect233r1.POLY << (a.bit_length() - 234)
        return a

    # Points are (x, y) tuples, None is the point at infinity. Curve: y^2 + xy = x^3 + x^2 + b
    @staticmethod
    def _padd(p, q):
        if p is None:
            return q
        if q is None:
            return p
        x1, y1 = p
        x2, y2 = q
        if x1 == x2:
            if y1 == y2:
                return ECC_sect233r1._pdouble(p)
            return None
        lam = ECC_sect233r1._fmul(y1 ^ y2, ECC_sect233r1._finv(x1 ^ x2))
        x3 = ECC_sect233r1._fmul(lam, lam) ^ lam ^ x1 ^ x2 ^ 1
        y3 = ECC_sect233r1._fmul(lam, x1 ^ x3) ^ x3 ^ y1
        return (x3, y3)

    @staticmethod
    def _pdouble(p):
        if p is None:
            return None
        x1, y1 = p
        if x1 == 0:
            return None
        lam = x1 ^ ECC_sect233r1._fmul(y1, ECC_sect233r1._finv(x1))
        x3 = ECC_sect233r1._fmul(lam, lam) ^ lam ^ 1
        y3 = ECC_sect233r1._fmul(x1, x1) ^ ECC_sect233r1._fmul(lam ^ 1, x3)
        return (x3, y3)

    @staticmethod
    def is_on_curve(p) -> bool:
        x, y = p
        if x >> 233 or y >> 233:
            return False
        lhs = ECC_sect233r1._fmul(y, y) ^ ECC_sect233r1._fmul(x, y)
        x2 = ECC_sect233r1._fmul(x, x)
        rhs = ECC_sect233r1._fmul(x2, x) ^ x2 ^ ECC_sect233r1.B
        return lhs == rhs

    @staticmethod
    def _shamir(k1: int, p1, k2: int, p2):
        # k1 * p1 + k2 * p2
        p12 = ECC_sect233r1._padd(p1, p2)
        r = None
        for i in range(max(k1.bit_length(), k2.bit_length()) - 1, -1, -1):
            r = ECC_sect233r1._pdouble(r)
            b1 = (k1 >> i) & 1
            b2 = (k2 >> i) & 1
            if b1 and b2:
                r = ECC_sect233r1._padd(r, p12)
            elif b1:
                r = ECC_sect233r1._padd(r, p1)
            elif b2:
                r = ECC_sect233r1._padd(r, p2)
        return r

    @staticmethod
    def verify(public_xy: bytes, data: bytes, signature_rs: bytes) -> bool:
        if len(public_xy) != 60 or len(signature_rs) != 60:
            return False
        q = (int.from_bytes(public_xy[:30], "big"), int.from_bytes(public_xy[30:], "big"))
        if q == (0, 0) or not ECC_sect233r1.is_on_curve(q):
            return False
        n = ECC_sect233r1.N
        r = int.from_bytes(signature_rs[:30], "big")
        s = int.from_bytes(signature_rs[30:], "big")
        if not (0 < r < n and 0 < s < n):
            return False
        e = int.from_bytes(hashlib.sha256(data).digest(), "big") >> (256 - n.bit_length())
        w = pow(s, -1, n)
        x = ECC_sect233r1._shamir((e * w) % n, (ECC_sect233r1.GX, ECC_sect233r1.GY), (r * w) % n, q)
        if x is None:
            return False
        return x[0] % n == r

class CTRCertificate:
    SIZE = 0x180
    SIG_ECDSA_SHA256 = 0x00010005
    KEY_ECC = 2

    def __init__(self, data: bytes):
        if len(data) != CTRCertificate.SIZE:
            raise ValueError("Invalid certificate size")
        self.raw = bytes(data)
        self.sig_type = struct.unpack(">I", data[0:4])[0]
        self.signature = data[4:4 + 0x3C]
        self.body = data[0x80:0x180]
        self.issuer = CTRCertificate._str(data[0x80:0xC0])
        self.key_type = struct.unpack(">I", data[0xC0:0xC4])[0]
        self.name = CTRCertificate._str(data[0xC4:0x104])
        self.expiration = struct.unpack(">I", data[0x104:0x108])[0]
        self.public_key = data[0x108:0x108 + 0x3C]
        if self.sig_type != CTRCertificate.SIG_ECDSA_SHA256 or self.key_type != CTRCertificate.KEY_ECC:
            raise ValueError("Unsupported certificate type")

    @staticmethod
    def _str(b: bytes) -> str:
        return b.split(b"\x00", 1)[0].decode("ascii", errors="replace")

    def verify_by(self, parent_public_key: bytes) -> bool:
        return ECC_sect233r1.verify(parent_public_key, self.body, self.signature)

class AuthResult:
    OK = 0
    CHALLENGE = 1
    MISMATCH = 2
    INVALID = 3

class CTGP7ConsoleAuth:
    # Public key of "Nintendo CA - G3_NintendoCTR2prod", which signs the retail CTCerts.
    # Dev CTCerts (NintendoCTR2dev) are rejected.
    CTR2PROD_PUBLIC_KEY = bytes.fromhex("004e3bb74d5d959e68ce900434fe9e4a3f094a33771fa7c0e4b023264d98014ca1fc799d3fa52171d5f9bd5b1777ec0fef7a38d1669bbf830325843a")
    CTR2PROD_ISSUER = "Nintendo CA - G3_NintendoCTR2prod"
    SIGN_TITLE_ID = 0x0004000003070C00
    MESSAGE_MAGIC = b"CTGP7AUTH\x00\x00\x00\x00\x00\x00\x01"
    CTCERT_NAME_RE = re.compile(r"^CT([0-9A-F]{8})-([0-9A-F]{2})$")

    NONCE_TIMEOUT = 120
    TOKEN_TIMEOUT = 24 * 60 * 60

    def __init__(self):
        self.lock = threading.Lock()
        self.nonces = {}
        self.tokens = {}

    @staticmethod
    def build_message(nonce: bytes, consoleID: int) -> bytes:
        return CTGP7ConsoleAuth.MESSAGE_MAGIC + nonce + struct.pack("<QQ", consoleID >> 64, consoleID & 0xFFFFFFFFFFFFFFFF)

    @staticmethod
    def verify_signature(ctcert: bytes, apcert: bytes, signature: bytes, message: bytes):
        ct = CTRCertificate(ctcert)
        if ct.issuer != CTGP7ConsoleAuth.CTR2PROD_ISSUER:
            raise ValueError("CTCert issuer not accepted: {}".format(ct.issuer))
        m = CTGP7ConsoleAuth.CTCERT_NAME_RE.match(ct.name)
        if m is None:
            raise ValueError("Invalid CTCert name: {}".format(ct.name))
        if not ct.verify_by(CTGP7ConsoleAuth.CTR2PROD_PUBLIC_KEY):
            raise ValueError("CTCert signature invalid")
        ap = CTRCertificate(apcert)
        if ap.issuer != ct.issuer + "-" + ct.name:
            raise ValueError("AP cert issuer mismatch: {}".format(ap.issuer))
        if ap.name.lower() != "ap{:016x}".format(CTGP7ConsoleAuth.SIGN_TITLE_ID):
            raise ValueError("AP cert name mismatch: {}".format(ap.name))
        if not ap.verify_by(ct.public_key):
            raise ValueError("AP cert signature invalid")
        if not ECC_sect233r1.verify(ap.public_key, message, signature):
            raise ValueError("Message signature invalid")
        return (int(m.group(1), 16), hashlib.sha256(ct.public_key).hexdigest().upper())

    def _purge(self, now):
        self.nonces = {k: v for k, v in self.nonces.items() if v[1] > now}
        self.tokens = {k: v for k, v in self.tokens.items() if v[1] > now}

    def new_nonce(self, consoleID: int) -> bytes:
        nonce = secrets.token_bytes(32)
        with self.lock:
            now = time.monotonic()
            self._purge(now)
            self.nonces[nonce] = (consoleID, now + CTGP7ConsoleAuth.NONCE_TIMEOUT)
        return nonce

    def take_nonce(self, nonce: bytes, consoleID: int) -> bool:
        with self.lock:
            entry = self.nonces.pop(bytes(nonce), None)
            return entry is not None and entry[0] == consoleID and entry[1] > time.monotonic()

    def new_token(self, consoleID: int) -> int:
        token = secrets.randbits(63) | 1
        with self.lock:
            self.tokens[token] = (consoleID, time.monotonic() + CTGP7ConsoleAuth.TOKEN_TIMEOUT)
        return token

    def check_token(self, token: int, consoleID: int) -> bool:
        with self.lock:
            entry = self.tokens.get(token)
            now = time.monotonic()
            if entry is None or entry[0] != consoleID or entry[1] <= now:
                return False
            self.tokens[token] = (consoleID, now + CTGP7ConsoleAuth.TOKEN_TIMEOUT)
            return True

    def drop_console(self, consoleID: int):
        with self.lock:
            self.tokens = {k: v for k, v in self.tokens.items() if v[0] != consoleID}

    def authenticate(self, database, inputData: dict, consoleID: int, outputData: dict, logFunc) -> bool:
        token = inputData.get("_auth")
        if token is not None and self.check_token(int(token), consoleID):
            return True

        authSig = inputData.get("_authsig")
        if authSig is None:
            outputData["_authres"] = AuthResult.CHALLENGE
            outputData["_authnonce"] = self.new_nonce(consoleID)
            return False

        try:
            nonce = bytes(authSig["nonce"])
        except Exception as e:
            logFunc("Console authentication failed: {}".format(e))
            outputData["_authres"] = AuthResult.INVALID
            return False
        if not self.take_nonce(nonce, consoleID):
            logFunc("Unknown or expired nonce, new challenge")
            outputData["_authres"] = AuthResult.CHALLENGE
            outputData["_authnonce"] = self.new_nonce(consoleID)
            return False

        try:
            message = CTGP7ConsoleAuth.build_message(nonce, consoleID)
            deviceID, keyHash = CTGP7ConsoleAuth.verify_signature(bytes(authSig["ctcert"]), bytes(authSig["apcert"]), bytes(authSig["sig"]), message)
        except Exception as e:
            logFunc("Console authentication failed: {}".format(e))
            outputData["_authres"] = AuthResult.INVALID
            return False

        if not database.bind_console_auth(consoleID, keyHash, deviceID):
            logFunc("CTCert mismatch or blocked: device ID 0x{:08X}, key {}".format(deviceID, keyHash))
            boundID = database.get_console_auth_by_ctcert(keyHash)
            if boundID is not None:
                self.drop_console(boundID)
            outputData["_authres"] = AuthResult.MISMATCH
            return False

        outputData["_auth"] = self.new_token(consoleID)
        return True
