
class CTGP7Defines(object):
    
    versionIDs = [0x1010a00]

    versionMappings = {0x1010a00: {0: 0, 3: 3, 2: 2, 1: 1, 4: 4, 5: 5, 8: 8, 14: 14, 12: 12, 15: 15, 6: 6, 9: 9, 7: 7, 10: 10, 11: 11, 13: 13, 30: 30, 29: 29, 26: 26, 27: 27, 20: 20, 23: 23, 22: 22, 21: 21, 16: 16, 17: 17, 18: 18, 19: 19, 24: 24, 25: 25, 28: 28, 31: 31, 33: 33, 34: 34, 32: 32, 37: 37, 36: 36, 35: 35, 38: 38, 39: 39, 40: 40, 41: 41, 42: 42, 59: 59, 44: 44, 45: 45, 46: 46, 68: 68, 43: 43, 49: 49, 50: 50, 54: 54, 52: 52, 53: 53, 55: 55, 62: 62, 57: 57, 65: 65, 67: 67, 58: 58, 66: 66, 69: 69, 63: 63, 47: 47, 48: 48, 51: 51, 56: 56, 60: 60, 61: 61, 64: 64, 74: 74, 75: 75, 76: 76, 77: 77, 78: 78, 79: 79, 80: 80, 81: 81, 82: 82, 83: 83, 84: 84, 85: 85, 86: 86, 87: 87, 88: 88, 89: 89, 90: 90, 91: 91, 92: 92, 93: 93, 94: 94, 95: 95, 96: 96, 73: 73, 70: 70, 71: 71, 72: 72, 97: 97} }

    trackNames = {
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
        60: "DS Dokan Course",
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
        97: "Rainbow Road DX"
    }

    @staticmethod
    def getTrackString(ctgpver, trackID):
        lastVer = 0
        for v in CTGP7Defines.versionIDs:
            if ctgpver >= v:
                lastVer = v
                break
        
        return CTGP7Defines.trackNames[CTGP7Defines.versionMappings[lastVer][trackID]]
    
    @staticmethod
    def getMenuString(menuID):
        return str(menuID)