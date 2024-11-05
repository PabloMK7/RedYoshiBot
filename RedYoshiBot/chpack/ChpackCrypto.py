from io import BytesIO
from .utils.sarc import SARC
from .utils.ioHelper import IOHelper
from .ChpackKeys import chpack_get_keys
import tempfile
import os
import shutil
import subprocess
import requests

def chpack_crypt(srcSarcUrl: str, dstSarc: BytesIO, key_kind: str, decrypt: bool):

    try:
        response = requests.get(srcSarcUrl, timeout=7, stream=True)
        if (response.status_code != 200):
            raise Exception("Got {}".format(response.status_code))
        srcSarc = BytesIO()
        size = 0
        for chunk in response.iter_content(1_000_000):
            size += len(chunk)
            srcSarc.write(chunk)
            if size > 10_000_000:
                raise ValueError('chpack too large!')
    except Exception as e:
        raise Exception("Couldn't download file: " + repr(e))

    srcSarc.seek(0)

    key = chpack_get_keys(key_kind)
    common = chpack_get_keys("common")
    if key is None or common is None:
        raise Exception("Provided key kind does not exist")

    process_files = [
        # True -> Force common key
        ("select.bclim", False),
        ("rankmenu.bclim", True),
        ("maprace.bclim", True),
        ("rankrace.bclim", True),
        ("driver.bcmdl", False),
        ("driver_menu.bcmdl", False),
        ("driver_lod.bcmdl", True),
        ("body_(body).bcmdl", False),
        ("body_(body)_lod.bcmdl", True),
        ("tire_(tire).bcmdl", False),
        ("tire_(tire)_lod.bcmdl", True),
        ("wing_(wing).bcmdl", False),
        ("wing_(wing)_lod.bcmdl", True),
        ("screw_std.bcmdl", False),
        ("screw_std_lod.bcmdl", True),
        ("emblem.bcmdl", False),
        ("emblem_lod.bcmdl", True),
        ("thankyou_anim.bcmdl", True),
    ]

    body_names = [
        "std",
        "rally",
        "rbn",
        "egg",
        "dsh",
        "cuc",
        "kpc",
        "boat",
        "hny",
        "sabo",
        "gng",
        "pipe",
        "trn",
        "cld",
        "race",
        "jet",
        "gold",
    ]

    tire_names = [
        "std",
        "big",
        "small",
        "race",
        "classic",
        "sponge",
        "gold",
        "wood",
        "bigRed",
        "mush",
    ]

    wing_names = [
        "std",
        "para",
        "umb",
        "flower",
        "basa",
        "met",
        "gold",
    ]

    def generate_files():
        ret = []
        for f in process_files:
            if "(body)" in f[0]:
                for f2 in body_names:
                    ret.append((f[0].replace("(body)", f2), f[1]))
            elif "(tire)" in f[0]:
                for f2 in tire_names:
                    ret.append((f[0].replace("(tire)", f2), f[1]))
            elif "(wing)" in f[0]:
                for f2 in wing_names:
                    ret.append((f[0].replace("(wing)", f2), f[1]))
                pass
            else:
                ret.append(f)
        return ret
    
    sarc = SARC(IOHelper(srcSarc))

    files = generate_files()
    for f in files:
        sfat = sarc.getFile(f[0])
        if (sfat is not None and len(sfat.data) >= 4):
            isEncrypted = sfat.data[0] == 0x43 and sfat.data[1] == 0x52 and sfat.data[2] == 0x59 and sfat.data[3] == 0x50
            if ((decrypt and not isEncrypted) or (not decrypt and isEncrypted)):
                continue
            try:
                temp_dir = tempfile.mkdtemp()
                src_file = os.path.join(temp_dir, "src.bin")
                dst_file = os.path.join(temp_dir, "dst.bin")
                with open(src_file, "wb") as wfile:
                    wfile.write(sfat.data)                

                use_key = common if f[1] else key

                try:
                    res = subprocess.run(["./cryptofile", src_file, dst_file, use_key[0], use_key[1], use_key[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except:
                    raise Exception("Failure on cryptofile call")
                assert res.returncode == 0, "Failure on cryptofile call"

                with open(dst_file, "rb") as rfile:
                    sarc.setFile(f[0], rfile.read())
            except:
                raise
            finally:
                shutil.rmtree(temp_dir)
    
    sarc.pack(IOHelper(dstSarc), combineDup=True)