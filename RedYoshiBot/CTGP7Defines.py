
class CTGP7Defines(object):
    
    versionIDs = [0, 0x1010a00]

    trackNames = { 
        0x1010a00: {
            0: "Mario Circuit",
            3: "Daisy Hills",
            2: "Cheep Cheep Cape",
            1: "Alpine Pass",
            4: "Toad Circuit",
            5: "Shy Guy Bazaar",
            8: "Wuhu Island Loop",
            14: "Wario's Galleon",
            12: "Piranha Plant Pipeway",
            15: "Melody Motorway",
            6: "Koopa City",
            9: "Wuhu Mountain Loop",
            7: "DK Jungle",
            10: "Rosalina's Ice World",
            11: "Bowser's Castle",
            13: "Rainbow Road",
            30: "SNES Mario Circuit 2",
            29: "GBA Bowser Castle 1",
            26: "N64 Luigi Raceway",
            27: "N64 Kalimari Desert",
            20: "DS Luigi's Mansion",
            23: "DS Waluigi Pinball",
            22: "DS DK Pass",
            21: "DS Airship Fortress",
            16: "Wii Coconut Mall",
            17: "Wii Koopa Cape",
            18: "Wii Maple Treeway",
            19: "Wii Mushroom Gorge",
            24: "GCN Dino Dino Jungle",
            25: "GCN Daisy Cruiser",
            28: "N64 Koopa Troopa Beach",
            31: "SNES Rainbow Road",

            33: "Honeybee House",
            34: "Sherbet Rink",
            32: "Wuhu Town",
            37: "GBA Battle Course 1",
            36: "N64 Big Donut",
            35: "DS Palm Shore",

            38: "Winning Run",
            39: "Invalid",
            40: "Invalid",
            41: "Invalid",

            42: "Concord Town",
            59: "N64 Mario Raceway",
            44: "Galvarny Falls",
            45: "GBA Sky Garden",
            46: "Autumn Forest",
            68: "GBA Riverside Park",
            43: "SNES Mario Circuit 1",
            49: "GBA Bowser Castle 3",
            50: "Evergreen Crossing",
            54: "N64 Moo Moo Farm",
            52: "Archipelago Avenue",
            53: "N64 Frappe Snowland",
            55: "Banshee Boardwalk 2",
            62: "Elemental Cave",
            57: "SNES Ghost Valley 2",
            65: "DS Cheep Cheep Beach",
            67: "DS Tick Tock Clock",
            58: "Melody Sanctum",
            66: "DS Desert Hills",
            69: "Castle of Time",
            63: "DS Yoshi Falls",
            47: "N64 Choco Mountain",
            48: "DS Shroom Ridge",
            51: "CTR Crash Cove",
            56: "CTR Cortex Castle",
            60: "Warp Pipe Island",
            61: "SNES Choco Island 2",
            64: "Star Slope",
            74: "Sandcastle Park",
            75: "DS Mario Circuit",
            76: "GCN Luigi Circuit",
            77: "Volcano Beach Ruins",
            78: "GCN Yoshi Circuit",
            79: "GBA Peach Circuit",
            80: "Metro Madness",
            81: "GBA Luigi Circuit",
            82: "SMO RC Challenge",
            83: "GBA Bowser Castle 4",
            84: "SNES Donut Plains 1",
            85: "Secret Slide",
            86: "DS Wario Stadium",
            87: "Ermii Circuit",
            88: "GCN Baby Park",
            89: "Revo Circuit",
            90: "SNES Mario Circuit 3",
            91: "Big Blue",
            92: "GBA Shy Guy Beach",
            93: "Bingo Party",
            94: "Doge Desert",
            95: "N64 Banshee Boardwalk",
            96: "GCN Mario Circuit",
            73: "Miku's Birthday Spec.",
            70: "N64 Rainbow Road",
            71: "GBA Rainbow Road",
            72: "Space Road",
            97: "Rainbow Road DX",
            98: "Stargaze Summit",
            99: "Sunset Raceway",
            100: "GBA Broken Pier",
            101: "Glacier Mine",
            102: "Flowerbed Fortress",
            103: "Seaside Palace",
            104: "DKR Star City",
            105: "Mushroom Mountain",
            106: "N64 Sherbet Land",
            107: "Block Island",
            108: "DS Bowser Castle",
            109: "DKR Jungle Falls",
            110: "Retro Raceway",
            111: "Frozen Grotto",
            112: "GBA Lakeside Park",
            113: "Dragon Burial Grounds",
            114: "RMX Rainbow Road 1",
            115: "Neo Metropolis",
            116: "Frosty Heights",
            117: "Gnasty Gnorc's Lair",
            118: "RMX Vanilla Lake 1",
            119: "Cliffside Circuit",
            120: "Interstellar Laboratory",
            121: "Dark Matter Fortress"
        }
    }

    trackszsnames = {
        0x1010a00: {
            "Gctr_MarioCircuit": 0,
            "Gctr_RallyCourse": 1,
            "Gctr_MarineRoad": 2,
            "Gctr_GlideLake": 3,
            "Gctr_ToadCircuit": 4,
            "Gctr_SandTown": 5,
            "Gctr_AdvancedCircuit": 6,
            "Gctr_DKJungle": 7,
            "Gctr_WuhuIsland1": 8,
            "Gctr_WuhuIsland2": 9,
            "Gctr_IceSlider": 10,
            "Gctr_BowserCastle": 11,
            "Gctr_UnderGround": 12,
            "Gctr_RainbowRoad": 13,
            "Gctr_WarioShip": 14,
            "Gctr_MusicPark": 15,
            "Gwii_CoconutMall": 16,
            "Gwii_KoopaCape": 17,
            "Gwii_MapleTreeway": 18,
            "Gwii_MushroomGorge": 19,
            "Gds_LuigisMansion": 20,
            "Gds_AirshipFortress": 21,
            "Gds_DKPass": 22,
            "Gds_WaluigiPinball": 23,
            "Ggc_DinoDinoJungle": 24,
            "Ggc_DaisyCruiser": 25,
            "Gn64_LuigiCircuit": 26,
            "Gn64_KalimariDesert": 27,
            "Gn64_KoopaTroopaBeach": 28,
            "Gagb_BowserCastle1": 29,
            "Gsfc_MarioCircuit2": 30,
            "Gsfc_RainbowRoad": 31,
            
            "Bctr_WuhuIsland3": 32,
            "Bctr_HoneyStage": 33,
            "Bctr_IceRink": 34,
            "Bds_PalmShore": 35,
            "Bn64_BigDonut": 36,
            "Bagb_BattleCourse1": 37,
            "Gctr_WinningRun": 38,
            
            "Invalid1": 39,
            "Invalid2": 40,
            "Invalid3": 41,

            "Ctgp_ConcTown": 42,
            "Ctgp_MarioCircuit1": 43,
            "Ctgp_GalvarnyFalls": 44,
            "Ctgp_SkaiiGarden": 45,
            "Ctgp_AutumnForest": 46,
            "Gn64_ChocoMountainn": 47,
            "Ctgp_DSShroomRidge": 48,
            "Ctgp_BowserCastle3": 49,
            "Ctgp_EvGre": 50,
            "Ctgp_CrashCov": 51,
            "Ctgp_ArchipAvenue": 52,
            "Ctgp_FrapeSnow": 53,
            "Ctgp_MoooMoooFarm": 54,
            "Ctgp_BanshBoardT": 55,
            "Ctgp_CortexCastleeee": 56,
            "Ctgp_GhostValleyT": 57,
            "Ctgp_MelodSanc": 58,
            "Ctgp_MarioRacewa": 59,
            "Ctgp_WarpPipeIsland": 60,
            "Gsfc_ChocoIsland": 61,
            "Ctgp_ElementalCave": 62,
            "Ctgp_YoshFalls": 63,
            "Ctgp_StarSlopeee": 64,
            "Ctgp_ChpChpBch": 65,
            "Ctgp_DeseHill": 66,
            "Ctgp_TickTockClock": 67,
            "Ctgp_RiversiPark": 68,
            "Ctgp_CastlOfTime": 69,
            "Ctgp_N64RainbowR": 70,
            "Gagb_RainbowRoad": 71,
            "Ctgp_SpeiceRouad": 72,
            "Ctgp_MikuBirtSpe": 73,
            "Ctgp_SandCastle": 74,
            "Ctgp_MarioCircuit": 75,
            "Gcn_LuigiCircuit": 76,
            "Ctgp_VolcanoBeachRuins": 77,
            "Gcn_YoshiCircuit": 78,
            "Gagb_PeachCircuitt": 79,
            "Ctgp_MetroMadness": 80,
            "Ctgp_GBALuigiCirc": 81,
            "Ctgp_SMORCChallen": 82,
            "Gagb_BowserCastle4": 83,
            "Gsfc_DonutPlainsThree": 84,
            "Gn64_SecretSl": 85,
            "Gds_WarioStad": 86,
            "Ctgp_ErmiiCir": 87,
            "Ggcn_BabyParkNin": 88,
            "Ctgp_RevoCircuit": 89,
            "Gsfc_MarioCircTh": 90,
            "Ctgp_BigBlueFZero1": 91,
            "Ggba_ShyGuyBeach": 92,
            "Ctgp_BingoPartyyyy": 93,
            "Ctgp_DogeDesert": 94,
            "Gn64_BansheeBoard": 95,
            "Ctgp_GCNMarioCirc": 96,
            "Ctgp_RainbowRdDX": 97,
            "Ctgp_StarGSumm": 98,
            "Ctgp_SunsetRacewa": 99,
            "Ctgp_GBABroknPier": 100,
            "Ctgp_GlacrMine": 101,
            "Ctgp_FlowerBFort": 102,
            "Ctgp_SeasidePalace": 103,
            "Ctgp_DKRStaCi": 104,
            "Ctgp_MushroomMount": 105,
            "Ctgp_N64ShbLnd": 106,
            "Ctgp_BlockIslandd": 107,
            "Ctgp_DSBowserCastle": 108,
            "Ctgp_DKRJunFa": 109,
            "Ctgp_RetroRaceway": 110,
            "Ctgp_FrzGrotto": 111,
            "Ctgp_GBALksdPrk": 112,
            "Ctgp_DrgnBGrounds": 113,
            "Ctgp_RMXSFCRbwRd": 114,
            "Ctgp_NeoMetropolisss": 115,
            "Ctgp_FrostyHeights": 116,
            "Ctgp_GnsGnoLair": 117,
            "Ctgp_VaLkO": 118,
            "Ctgp_CliffCircuit": 119,
            "Ctgp_InterstellarLabb": 120,
            "Ctgp_DarkMatterFortress": 121
        }
    }

    @staticmethod
    def getTypeFromSZS(szsName, ctgpver=-1):
        lastVer = CTGP7Defines.versionIDs[0]
        if (ctgpver == -1):
            ctgpver = CTGP7Defines.versionIDs[-1]
        for v in CTGP7Defines.versionIDs:
            if v > ctgpver:
                break
            lastVer = v
        try:
            id = CTGP7Defines.trackszsnames[lastVer][szsName]
        except:
            return 1
        if (id <= 31):
            return 0
        if (id >= 42):
            return 1
        if (id >= 32 and id <= 38):
            return 2
        return 1

    @staticmethod
    def getTrackString(ctgpver, trackID):
        lastVer = CTGP7Defines.versionIDs[0]
        for v in CTGP7Defines.versionIDs:
            if v > ctgpver:
                break
            lastVer = v
        try:
            return CTGP7Defines.trackNames[lastVer][trackID]
        except:
            return "???"
    
    @staticmethod
    def getTrackNameFromSzs(szsName, ctgpver=-1):
        lastVer = CTGP7Defines.versionIDs[0]
        if (ctgpver == -1):
            ctgpver = CTGP7Defines.versionIDs[-1]
        for v in CTGP7Defines.versionIDs:
            if v > ctgpver:
                break
            lastVer = v
        try:
            return CTGP7Defines.trackNames[lastVer][CTGP7Defines.trackszsnames[lastVer][szsName]]
        except:
            return "???"

    @staticmethod
    def getMenuString(menuID):
        return str(menuID)