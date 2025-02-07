import json
import os
import sys
import time
import traceback
from contextlib import redirect_stdout
from os import path
import argparse

import psycopg2


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


parser = argparse.ArgumentParser()
parser.add_argument("--METRICS_PATH", type=str, required=True)
parser.add_argument("--DATABASE", type=str, required=True)
parser.add_argument("--DATABASE_USER", type=str, required=True)
parser.add_argument("--DATABASE_PASSWORD", type=str, required=True)
parser.add_argument("--FIND_NEW_RUNS_TO_PROCESS", type=str2bool, required=False, default=False)
parser.add_argument("--PROCESS_RUNS", type=str2bool, required=False, default=False)
parser.add_argument("--AVERAGE_DAMAGE_TAKEN_COUNT_THRESHOLD", type=int, required=False, default=5)
parser.add_argument("--CARD_CHOICES_CARDS_THRESHOLD", type=int, required=False, default=5)
parser.add_argument("--CHARACTER_GAMES_THRESHOLD", type=int, required=False, default=5)
parser.add_argument("--WIN_RATIO_CARDS_THRESHOLD", type=int, required=False, default=5)
parser.add_argument("--WIN_RATIO_RELICS_THRESHOLD", type=int, required=False, default=5)
parser.add_argument("--HOSTS_THRESHOLD", type=int, required=False, default=0)
parser.add_argument("--CHARACTER_CARD_PREFIX", type=str, required=False, default="")
parser.add_argument("--RELIC_PREFIX", type=str, required=False, default="")

args = parser.parse_args()

print("Run with params: " + str(args))

METRICS_PATH = args.METRICS_PATH
DATABASE = args.DATABASE
DATABASE_USER = args.DATABASE_USER
DATABASE_PASSWORD = args.DATABASE_PASSWORD
FIND_NEW_RUNS_TO_PROCESS = args.FIND_NEW_RUNS_TO_PROCESS
PROCESS_RUNS = args.PROCESS_RUNS
AVERAGE_DAMAGE_TAKEN_COUNT_THRESHOLD = args.AVERAGE_DAMAGE_TAKEN_COUNT_THRESHOLD
CARD_CHOICES_CARDS_THRESHOLD = args.CARD_CHOICES_CARDS_THRESHOLD
CHARACTER_GAMES_THRESHOLD = args.CHARACTER_GAMES_THRESHOLD
WIN_RATIO_CARDS_THRESHOLD = args.WIN_RATIO_CARDS_THRESHOLD
WIN_RATIO_RELICS_THRESHOLD = args.WIN_RATIO_RELICS_THRESHOLD
HOSTS_THRESHOLD = args.HOSTS_THRESHOLD
CHARACTER_CARD_PREFIX = args.CHARACTER_CARD_PREFIX
RELIC_PREFIX = args.RELIC_PREFIX

BASE_GAME_STARTER_RELICS = [
    "Burning Blood",
    "Cracked Core",
    "PureWater",
    "Ring of the Snake",
]
BASE_GAME_COMMON_RELICS = [
    "Akabeko",
    "Anchor",
    "Ancient Tea Set",
    "Art of War",
    "Bag of Marbles",
    "Bag of Preparation",
    "Blood Vial",
    "Boot",
    "Bronze Scales",
    "Centennial Puzzle",
    "CeramicFish",
    "Damaru",
    "DataDisk",
    "Dream Catcher",
    "Happy Flower",
    "Juzu Bracelet",
    "Lantern",
    "MawBank",
    "MealTicket",
    "Nunchaku",
    "Oddly Smooth Stone",
    "Omamori",
    "Orichalcum",
    "Pen Nib",
    "Potion Belt",
    "PreservedInsect",
    "Red Skull",
    "Regal Pillow",
    "Smiling Mask",
    "Snake Skull",
    "Strawberry",
    "Tiny Chest",
    "Toy Ornithopter",
    "Vajra",
    "War Paint",
    "Whetstone",
]
BASE_GAME_UNCOMMON_RELICS = [
    "Blue Candle",
    "Bottled Flame",
    "Bottled Lightning",
    "Bottled Tornado",
    "Cables",
    "Darkstone Periapt",
    "Eternal Feather",
    "Frozen Egg 2",
    "Gremlin Horn",
    "HornCleat",
    "InkBottle",
    "Kunai",
    "Letter Opener",
    "Matryoshka",
    "Meat on the Bone",
    "Mercury Hourglass",
    "Molten Egg 2",
    "Mummified Hand",
    "Ninja Scroll",
    "Ornamental Fan",
    "Pantograph",
    "Paper Crane",
    "Paper Frog",
    "Pear",
    "Question Card",
    "Self Forming Clay",
    "Shuriken",
    "Singing Bowl",
    "StrikeDummy",
    "Sundial",
    "Symbiotic Virus",
    "TeardropLocket",
    "The Courier",
    "Toxic Egg 2",
    "White Beast Statue",
    "Yang",
]
BASE_GAME_RARE_RELICS = [
    "Bird Faced Urn",
    "Calipers",
    "CaptainsWheel",
    "Champion Belt",
    "Charon's Ashes",
    "CloakClasp",
    "Dead Branch",
    "Du-Vu Doll",
    "Emotion Chip",
    "FossilizedHelix",
    "Gambling Chip",
    "Ginger",
    "Girya",
    "GoldenEye",
    "Ice Cream",
    "Incense Burner",
    "Lizard Tail",
    "Magic Flower",
    "Mango",
    "Old Coin",
    "Peace Pipe",
    "Pocketwatch",
    "Prayer Wheel",
    "Shovel",
    "StoneCalendar",
    "The Specimen",
    "Thread and Needle",
    "Tingsha",
    "Torii",
    "Tough Bandages",
    "TungstenRod",
    "Turnip",
    "Unceasing Top",
    "WingedGreaves",
]
BASE_GAME_BOSS_RELICS = [
    "Astrolabe",
    "Black Blood",
    "Black Star",
    "Busted Crown",
    "Calling Bell",
    "Coffee Dripper",
    "Cursed Key",
    "Ectoplasm",
    "Empty Cage",
    "FrozenCore",
    "Fusion Hammer",
    "HolyWater",
    "HoveringKite",
    "Inserter",
    "Mark of Pain",
    "Nuclear Battery",
    "Pandora's Box",
    "Philosopher's Stone",
    "Ring of the Serpent",
    "Runic Cube",
    "Runic Dome",
    "Runic Pyramid",
    "SacredBark",
    "SlaversCollar",
    "Snecko Eye",
    "Sozu",
    "Tiny House",
    "Velvet Choker",
    "VioletLotus",
    "WristBlade",
]
BASE_GAME_SHOP_RELICS = [
    "Brimstone",
    "Cauldron",
    "Chemical X",
    "ClockworkSouvenir",
    "DollysMirror",
    "Frozen Eye",
    "HandDrill",
    "Lee's Waffle",
    "Medical Kit",
    "Melange",
    "Membership Card",
    "OrangePellets",
    "Orrery",
    "PrismaticShard",
    "Runic Capacitor",
    "Sling",
    "Strange Spoon",
    "TheAbacus",
    "Toolbox",
    "TwistedFunnel",
]
BASE_GAME_SPECIAL_RELICS = [
    "Bloody Idol",
    "CultistMask",
    "Enchiridion",
    "FaceOfCleric",
    "Golden Idol",
    "GremlinMask",
    "Mark of the Bloom",
    "MutagenicStrength",
    "Necronomicon",
    "NeowsBlessing",
    "Nilry's Codex",
    "Nloth's Gift",
    "NlothsMask",
    "Odd Mushroom",
    "Red Mask",
    "Spirit Poop",
    "SsserpentHead",
    "WarpedTongs",
]
BASE_GAME_RELICS = (
    BASE_GAME_STARTER_RELICS
    + BASE_GAME_COMMON_RELICS
    + BASE_GAME_UNCOMMON_RELICS
    + BASE_GAME_RARE_RELICS
    + BASE_GAME_BOSS_RELICS
    + BASE_GAME_SHOP_RELICS
    + BASE_GAME_SPECIAL_RELICS
)


def getNewEmptyWonAndLostDict():
    return {"won": 0, "lost": 0}


def getNewEmptyPickedNotPickedDict():
    return {"picked": 0, "not_picked": 0}


def getNewAscRange(ascMin, ascMax):
    return {"min": ascMin, "max": ascMax}


def timeString(timeInSeconds):
    return time.strftime("%H:%M:%S", time.gmtime(timeInSeconds))


def winRatioString(won, lost):
    return str("??.??%" if (won + lost == 0) else ("%.2f%%" % round(100 * won / (won + lost), 2)))


def winRatioStringDifference(difference):
    return str("??.??%" if difference is None else ("%.2f%%" % round(100 * difference, 2)))


def printWinRatio(wonRuns, lostRuns):
    print("Played: " + str(wonRuns + lostRuns) + ", W=" + str(wonRuns) + ", L=" + str(lostRuns) + ", R=" + winRatioString(wonRuns, lostRuns))


def printAverageLength(averageLength):
    sum = averageLength["sum"]
    count = averageLength["count"]
    print("??:??:??" if count == 0 else "%s" % timeString(round(sum / count)))


def printMedianLength(averageLength):
    median = averageLength["median"]
    count = averageLength["count"]
    print("??:??:??" if count == 0 else "%s" % timeString(int(median)))


def printAverageDamageTaken(averageDamageTaken):
    for enemiesKey, enemiesValue in sorted(averageDamageTaken.items(), key=lambda e: -e[1]["sum"] / e[1]["count"]):
        sum = enemiesValue["sum"]
        count = enemiesValue["count"]
        if count < AVERAGE_DAMAGE_TAKEN_COUNT_THRESHOLD:
            continue
        print(enemiesKey + ", Avg=%.2f" % (sum / count) + ", Sum=" + str(sum) + ", Count=" + str(count))
    print()


def printAverageCombatLength(averageCombatLength):
    for enemiesKey, enemiesValue in sorted(averageCombatLength.items(), key=lambda e: -e[1]["sum"] / e[1]["count"]):
        sum = enemiesValue["sum"]
        count = enemiesValue["count"]
        print(enemiesKey + ", Avg=%.2f" % (sum / count) + ", Sum=" + str(sum) + ", Count=" + str(count))
    print()


def printKilledBy(killedBy):
    for key, value in sorted(killedBy.items(), key=lambda e: -e[1]):
        print(str(key) + " -> " + str(value))
    print()


def printCardChoices(cardChoices):
    for key, value in sorted(
        cardChoices.items(),
        key=lambda e: -e[1]["picked"] / (e[1]["picked"] + e[1]["not_picked"]),
    ):
        if not key.startswith(CHARACTER_CARD_PREFIX):
            continue
        picked = value["picked"]
        notPicked = value["not_picked"]
        total = picked + notPicked
        if total < CARD_CHOICES_CARDS_THRESHOLD:
            continue
        print(key + ": P=" + str(picked) + ", NP=" + str(notPicked) + ", R=" + winRatioString(picked, notPicked))
    print()


def printIsSpecificCardInDeckAndWinRatio(isSpecificCardInDeckAndWinRatio):
    for cardKey, cardValue in sorted(
        isSpecificCardInDeckAndWinRatio.items(),
        key=lambda e: -e[1]["won"] / (e[1]["won"] + e[1]["lost"]),
    ):
        if not cardKey.startswith(CHARACTER_CARD_PREFIX):
            continue
        won = cardValue["won"]
        lost = cardValue["lost"]
        if won + lost < WIN_RATIO_CARDS_THRESHOLD:
            continue
        print(cardKey + ", W=" + str(won) + ", L=" + str(lost) + ", R=" + winRatioString(won, lost))
    print()


def printNumberOfSpecificCardsAndWinRatio(numberOfSpecificCardsAndWinRatio):
    for cardKey, cardValue in sorted(numberOfSpecificCardsAndWinRatio.items(), key=lambda e: e[0]):
        if not cardKey.startswith(CHARACTER_CARD_PREFIX):
            continue
        for numberKey, numberValue in sorted(cardValue.items(), key=lambda e: e[0]):
            won = numberValue["won"]
            lost = numberValue["lost"]
            if won + lost < WIN_RATIO_CARDS_THRESHOLD:
                continue
            print(cardKey + ", " + str(numberKey) + ", W=" + str(won) + ", L=" + str(lost) + ", R=" + winRatioString(won, lost))
    print()


def printHasSpecificRelicAndWinRatio(hasSpecificRelicAndWinRatio, onlyBaseGameRelics, sortByPrefix):
    def relicPrefix(relicId):
        array = relicId.split(":")
        if len(array) == 1:
            return "Unknown"
        else:
            return array[0]

    prefixes = set()
    if sortByPrefix and not onlyBaseGameRelics:
        for relicKey, relicValue in hasSpecificRelicAndWinRatio.items():
            prefixes.add(relicPrefix(relicKey))
    else:
        prefixes = ("Unknown",)

    if onlyBaseGameRelics:
        rarities = {
            "Starter": BASE_GAME_STARTER_RELICS,
            "Common": BASE_GAME_COMMON_RELICS,
            "Uncommon": BASE_GAME_UNCOMMON_RELICS,
            "Rare": BASE_GAME_RARE_RELICS,
            "Boss": BASE_GAME_BOSS_RELICS,
            "Shop": BASE_GAME_SHOP_RELICS,
            "Special": BASE_GAME_SPECIAL_RELICS,
        }
    else:
        rarities = {"Unknown": []}

    for prefix in sorted(prefixes):
        for rarityKey, rarityList in rarities.items():
            if rarityKey != "Unknown":
                print()
                print(rarityKey)
            for relicKey, relicValue in sorted(
                hasSpecificRelicAndWinRatio.items(),
                key=lambda e: -e[1]["won"] / (e[1]["won"] + e[1]["lost"]),
            ):
                if not relicKey.startswith(RELIC_PREFIX):
                    continue
                if sortByPrefix and relicPrefix(relicKey) != prefix:
                    continue
                if onlyBaseGameRelics and relicKey not in rarityList:
                    continue
                won = relicValue["won"]
                lost = relicValue["lost"]
                if won + lost < WIN_RATIO_RELICS_THRESHOLD:
                    continue
                print(relicKey + ", W=" + str(won) + ", L=" + str(lost) + ", R=" + winRatioString(won, lost))
    print()


def printSwappedStarterRelic(swappedStarterRelic):
    total = swappedStarterRelic["total"]
    swapped = swappedStarterRelic["swapped"]
    swappedAndWon = swappedStarterRelic["swappedAndWon"]
    swappedAndLost = swappedStarterRelic["swappedAndLost"]
    won = swappedStarterRelic["won"]
    lost = swappedStarterRelic["lost"]
    difference = swappedStarterRelic["difference"]
    print(
        "Swapped Ratio="
        + winRatioString(swapped, total - swapped)
        + ", "
        + "Swapped="
        + str(swapped)
        + ", Total="
        + str(total)
        + ", Won="
        + str(swappedAndWon)
        + ", Lost="
        + str(swappedAndLost)
        + ", Win Ratio="
        + winRatioString(swappedAndWon, swappedAndLost)
        + ", General Win Ratio="
        + winRatioString(won, lost)
        + ", Difference="
        + winRatioStringDifference(difference)
    )


def printHosts(hosts):
    for key, value in sorted(hosts.items(), key=lambda e: -e[1]):
        if value < HOSTS_THRESHOLD:
            continue
        print(str(key) + " -> " + str(value))
    print()


def printLanguage(hosts):
    for key, value in sorted(hosts.items(), key=lambda e: -e[1]):
        print(str(key) + " -> " + str(value))
    print()


def printActsVisited(actsVisited):
    for key, value in sorted(actsVisited.items(), key=lambda e: -e[1]):
        print(str(key) + " -> " + str(value))
    print()


def printEnabledMods(modsEnabled):
    for key, value in sorted(modsEnabled.items(), key=lambda e: -e[1]):
        print(str(key) + " -> " + str(value))
    print()


def emptyStringIfNone(string):
    return string if string else ""


def minFromAscRange(ascRange):
    return ascRange["min"] if ascRange else -20


def maxFromAscRange(ascRange):
    return ascRange["max"] if ascRange else 1000000000


def getWinRatio(asc, character, victory):
    cur.execute(
        """SELECT count(*) FROM run 
        WHERE status = 'PROCESSED' and (ascension = %(asc)s or %(asc)s = '') and (character = %(character)s or %(character)s = '') AND victory = %(victory)s""",
        {
            "asc": emptyStringIfNone(asc),
            "character": emptyStringIfNone(character),
            "victory": victory,
        },
    )
    return cur.fetchone()[0]


def getAverageLength(asc, character, victory):
    cur.execute(
        """SELECT sum(play_time::int), count(*) FROM run 
        WHERE status = 'PROCESSED' and (ascension = %(asc)s or %(asc)s = '') and (character = %(character)s or %(character)s = '') AND victory = %(victory)s""",
        {
            "asc": emptyStringIfNone(asc),
            "character": emptyStringIfNone(character),
            "victory": victory,
        },
    )
    row = cur.fetchone()
    sum = row[0]
    count = row[1]
    if not sum:
        sum = 0
    return {"sum": sum, "count": count}


def getMedianLength(asc, character, victory):
    cur.execute(
        """SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY play_time), count(*) FROM run 
        WHERE status = 'PROCESSED' and (ascension = %(asc)s or %(asc)s = '') and (character = %(character)s or %(character)s = '') AND victory = %(victory)s""",
        {
            "asc": emptyStringIfNone(asc),
            "character": emptyStringIfNone(character),
            "victory": victory,
        },
    )
    row = cur.fetchone()
    median = row[0]
    count = row[1]
    if not median:
        median = 0
    return {"median": median, "count": count}


def getAverageGoldGained(asc, character, victory):
    cur.execute(
        """SELECT sum(play_time::int), count(*) FROM run 
        WHERE status = 'PROCESSED' and (ascension = %(asc)s or %(asc)s = '') and (character = %(character)s or %(character)s = '') AND victory = %(victory)s""",
        {
            "asc": emptyStringIfNone(asc),
            "character": emptyStringIfNone(character),
            "victory": victory,
        },
    )
    row = cur.fetchone()
    sum = row[0]
    count = row[1]
    if not sum:
        sum = 0
    return {"sum": sum, "count": count}


def getCardChoices(ascRange, character, upgradedCardsGrouped):
    cur.execute(
        """SELECT CASE WHEN %(upgradedCardsGrouped)s = false THEN card_id ELSE regexp_replace(card_id, '\+.*', '') END card_id_calc,
        picked, count(*) 
        FROM card_choice c 
        LEFT JOIN run r
        ON (c.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY card_id_calc, picked""",
        {
            "ascMin": minFromAscRange(ascRange),
            "ascMax": maxFromAscRange(ascRange),
            "character": emptyStringIfNone(character),
            "upgradedCardsGrouped": upgradedCardsGrouped,
        },
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        cardId = row[0]
        picked = row[1]
        if cardId not in results:
            results[cardId] = getNewEmptyPickedNotPickedDict()
        if picked:
            results[cardId]["picked"] = row[2]
        else:
            results[cardId]["not_picked"] = row[2]
    return results


def getIsSpecificCardInDeckAndWinRatio(ascRange, character, upgradedCardsGrouped):
    cur.execute(
        """SELECT CASE WHEN %(upgradedCardsGrouped)s = false THEN card_id ELSE regexp_replace(card_id, '\+.*', '') END card_id_calc,
         victory, count(distinct(run_file_path)) 
        FROM master_deck md 
        LEFT JOIN run r
        ON (md.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY card_id_calc, victory""",
        {
            "ascMin": minFromAscRange(ascRange),
            "ascMax": maxFromAscRange(ascRange),
            "character": emptyStringIfNone(character),
            "upgradedCardsGrouped": upgradedCardsGrouped,
        },
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        cardId = row[0]
        victory = row[1]
        if cardId not in results:
            results[cardId] = getNewEmptyWonAndLostDict()
        if victory:
            results[cardId]["won"] = row[2]
        else:
            results[cardId]["lost"] = row[2]
    return results


def getNumberOfSpecificCardsAndWinRatio(ascRange, character, upgradedCardsGrouped):
    cur.execute(
        """SELECT card_id_calc, number, victory, count(*)
        FROM 
        (
            SELECT CASE WHEN %(upgradedCardsGrouped)s = false THEN card_id ELSE regexp_replace(card_id, '\+.*', '') END card_id_calc, victory, count(*) as number
            FROM master_deck md 
            LEFT JOIN run r
            ON (md.run_file_path = r.file_path)
            WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
            GROUP BY card_id_calc, file_path, victory
        ) AS amd
        GROUP BY card_id_calc, number, victory""",
        {
            "ascMin": minFromAscRange(ascRange),
            "ascMax": maxFromAscRange(ascRange),
            "character": emptyStringIfNone(character),
            "upgradedCardsGrouped": upgradedCardsGrouped,
        },
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        cardId = row[0]
        number = row[1]
        victory = row[2]
        if cardId not in results:
            results[cardId] = {}
        if number not in results[cardId]:
            results[cardId][number] = getNewEmptyWonAndLostDict()
        if victory:
            results[cardId][number]["won"] = row[3]
        else:
            results[cardId][number]["lost"] = row[3]
    return results


def getHasSpecificRelicAndWinRatio(ascRange, character):
    cur.execute(
        """SELECT relic_id, victory, count(distinct(run_file_path)) 
        FROM relic re 
        LEFT JOIN run r
        ON (re.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY relic_id, victory""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        cardId = row[0]
        victory = row[1]
        if cardId not in results:
            results[cardId] = getNewEmptyWonAndLostDict()
        if victory:
            results[cardId]["won"] = row[2]
        else:
            results[cardId]["lost"] = row[2]
    return results


def getAverageDamageTaken(ascRange, character):
    cur.execute(
        """SELECT enemies, sum(damage), count(*)
        FROM damage_taken dt
        LEFT JOIN run r
        ON (dt.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY enemies""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = {"sum": row[1], "count": row[2]}
    return results


def getAverageCombatLength(ascRange, character):
    cur.execute(
        """SELECT enemies, sum(turns), count(*)
        FROM damage_taken dt
        LEFT JOIN run r
        ON (dt.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY enemies""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = {"sum": row[1], "count": row[2]}
    return results


def getKilledBy(ascRange, character):
    cur.execute(
        """SELECT enemy_id, count(*)
        FROM killed_by kb
        LEFT JOIN run r
        ON (kb.run_file_path = r.file_path)
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY enemy_id""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = row[1]
    return results


def getSwappedStarterRelic(asc, character):
    cur.execute(
        """SELECT count(*), count(*) filter (where neow_bonus = 'BOSS_RELIC'), 
        count(*) filter (where neow_bonus = 'BOSS_RELIC' and victory = true), 
        count(*) filter (where neow_bonus = 'BOSS_RELIC' and victory = false), 
        count(*) filter (where victory = true), 
        count(*) filter (where victory = false)
        FROM run r
        WHERE status = 'PROCESSED' and (ascension = %(asc)s or %(asc)s = '') and (character = %(character)s or %(character)s = '')""",
        {"asc": emptyStringIfNone(asc), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    total = rows[0][0]
    swapped = rows[0][1]
    swappedAndWon = rows[0][2]
    swappedAndLost = rows[0][3]
    won = rows[0][4]
    lost = rows[0][5]
    return {
        "total": total,
        "swapped": swapped,
        "swappedAndWon": swappedAndWon,
        "swappedAndLost": swappedAndLost,
        "won": won,
        "lost": lost,
        "difference": (
            None if (swappedAndWon + swappedAndLost == 0) or (won + lost == 0) else ((swappedAndWon / (swappedAndWon + swappedAndLost)) - (won / (won + lost)))
        ),
    }


def getHosts(ascRange, character):
    cur.execute(
        """SELECT host, count(*)
        FROM run r
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY host""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = row[1]
    return results


def getLanguage(ascRange, character):
    cur.execute(
        """SELECT language, count(*)
        FROM run r
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY language""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = row[1]
    return results


def getActsVisited(ascRange, character):
    cur.execute(
        """SELECT act_name, count(*) as c 
        FROM act_visited av 
        LEFT JOIN run r ON av.run_file_path = r.file_path
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY act_name""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = row[1]
    return results


def getEnabledMods(ascRange, character):
    cur.execute(
        """SELECT mod_name, count(*) as c 
        FROM mod m 
        LEFT JOIN run r ON m.run_file_path = r.file_path
        WHERE status = 'PROCESSED' and (ascension::int >= %(ascMin)s and ascension::int <= %(ascMax)s) and (character = %(character)s or %(character)s = '')
        GROUP BY mod_name""",
        {"ascMin": minFromAscRange(ascRange), "ascMax": maxFromAscRange(ascRange), "character": emptyStringIfNone(character)},
    )
    rows = cur.fetchall()
    results = {}
    for row in rows:
        results[row[0]] = row[1]
    return results


conn = None

try:
    conn = psycopg2.connect(database=DATABASE, user=DATABASE_USER, password=DATABASE_PASSWORD)
    cur = conn.cursor()

    if FIND_NEW_RUNS_TO_PROCESS:
        for root, dirs, files in os.walk(METRICS_PATH):
            for file in files:
                absPath = path.join(root, file)
                if path.isfile(absPath):
                    cur.execute(
                        "INSERT INTO run(file_path, status) VALUES (%s, %s) ON CONFLICT (file_path) DO NOTHING",
                        (absPath, "NEW"),
                    )
                    conn.commit()

    if PROCESS_RUNS:
        cur.execute("SELECT file_path FROM run WHERE status = 'NEW' order by file_path")
        rows = cur.fetchall()
        for row in rows:
            absPath = row[0]
            try:
                runJson = json.loads(open(absPath, "r", encoding="utf-8").read())
                if runJson["event"]["is_endless"]:
                    cur.execute(
                        "UPDATE run SET status = %s, is_endless = %s where file_path = %s",
                        ("SKIPPED", True, absPath),
                    )
                    conn.commit()
                    continue
                if runJson["event"]["floor_reached"] <= 1:
                    cur.execute(
                        "UPDATE run SET status = %s, left_too_early = %s where file_path = %s",
                        ("SKIPPED", True, absPath),
                    )
                    conn.commit()
                    continue

                character = runJson["event"]["character_chosen"]
                asc = runJson["event"]["ascension_level"]
                host = runJson["host"] if "host" in runJson and not runJson["event"]["is_beta"] else "Unknown"
                language = runJson["event"]["language"] if "language" in runJson["event"] else "Unknown"
                victory = runJson["event"]["victory"]
                playTime = runJson["event"]["playtime"]
                neowBonus = runJson["event"]["neow_bonus"]
                runTime = runJson["time"]
                floor_reached = runJson["event"]["floor_reached"]
                score = runJson["event"]["score"]
                play_id = runJson["event"]["play_id"]
                local_time = runJson["event"]["local_time"]
                is_ascension_mode = runJson["event"]["is_ascension_mode"]
                circlet_count = runJson["event"]["circlet_count"]
                seed_played = runJson["event"]["seed_played"]
                is_trial = runJson["event"]["is_trial"]
                campfire_rested = runJson["event"]["campfire_rested"]
                gold = runJson["event"]["gold"]
                is_daily = runJson["event"]["is_daily"]
                chose_seed = runJson["event"]["chose_seed"]
                campfire_upgraded = runJson["event"]["campfire_upgraded"]
                win_rate = runJson["event"]["win_rate"]
                timestamp = runJson["event"]["timestamp"]
                build_version = runJson["event"]["build_version"]
                purchased_purges = runJson["event"]["purchased_purges"]
                player_experience = runJson["event"]["player_experience"]
                is_beta = runJson["event"]["is_beta"]

                cur.execute(
                    """UPDATE run SET character = %s, ascension = %s, host = %s, language = %s, victory = %s, 
                    play_time = %s, neow_bonus = %s, time = %s, floor_reached = %s, score = %s, play_id = %s, 
                    local_time = %s, is_ascension_mode = %s, circlet_count = %s, seed_played = %s, is_trial = %s,
                    campfire_rested = %s, gold = %s, is_daily = %s, chose_seed = %s, campfire_upgraded = %s, 
                    win_rate = %s, timestamp = %s, build_version = %s, purchased_purges = %s, player_experience = %s, 
                    is_beta = %s, error_message = %s where file_path = %s""",
                    (
                        character,
                        asc,
                        host,
                        language,
                        victory,
                        playTime,
                        neowBonus,
                        runTime,
                        floor_reached,
                        score,
                        play_id,
                        local_time,
                        is_ascension_mode,
                        circlet_count,
                        seed_played,
                        is_trial,
                        campfire_rested,
                        gold,
                        is_daily,
                        chose_seed,
                        campfire_upgraded,
                        win_rate,
                        timestamp,
                        build_version,
                        purchased_purges,
                        player_experience,
                        is_beta,
                        "",
                        absPath,
                    ),
                )
                conn.commit()

                cur.execute(
                    "DELETE FROM damage_taken where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                for damageTakenEntry in runJson["event"]["damage_taken"]:
                    if damageTakenEntry["damage"] >= 99999:
                        continue
                    if "enemies" not in damageTakenEntry:
                        continue
                    enemies = damageTakenEntry["enemies"]
                    damage = damageTakenEntry["damage"]
                    floor = damageTakenEntry["floor"]
                    turns = damageTakenEntry["turns"]
                    cur.execute(
                        "INSERT INTO damage_taken(run_file_path, enemies, damage, floor, turns) VALUES (%s, %s, %s, %s, %s)",
                        (absPath, enemies, damage, floor, turns),
                    )
                conn.commit()
                cur.execute(
                    "DELETE FROM killed_by where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                if "killed_by" in runJson["event"]:
                    enemyKilling = runJson["event"]["killed_by"]
                    cur.execute(
                        "INSERT INTO killed_by(run_file_path, enemy_id) VALUES (%s, %s)",
                        (absPath, enemyKilling),
                    )
                    conn.commit()
                cur.execute(
                    "DELETE FROM card_choice where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                for cardChoice in runJson["event"]["card_choices"]:
                    cardPicked = cardChoice["picked"]
                    cur.execute(
                        "INSERT INTO card_choice(run_file_path, card_id, picked) VALUES (%s, %s, %s)",
                        (absPath, cardPicked, True),
                    )
                    for notPicked in cardChoice["not_picked"]:
                        cur.execute(
                            "INSERT INTO card_choice(run_file_path, card_id, picked) VALUES (%s, %s, %s)",
                            (absPath, notPicked, False),
                        )
                conn.commit()
                cur.execute(
                    "DELETE FROM master_deck where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                masterDeck = runJson["event"]["master_deck"]
                masterDeckGrouped = {}
                for card in masterDeck:
                    cur.execute(
                        "INSERT INTO master_deck(run_file_path, card_id) VALUES (%s, %s)",
                        (absPath, card),
                    )
                conn.commit()
                cur.execute(
                    "DELETE FROM relic where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                relics = runJson["event"]["relics"]
                for relicId in relics:
                    cur.execute(
                        "INSERT INTO relic(run_file_path, relic_id) VALUES (%s, %s)",
                        (absPath, relicId),
                    )
                conn.commit()

                cur.execute(
                    "DELETE FROM act_visited where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                actsVisited = runJson["event"]["acts_visited"] if "acts_visited" in runJson["event"] else ["no_acts_visited_data"]
                for actName in actsVisited:
                    cur.execute(
                        "INSERT INTO act_visited(run_file_path, act_name) VALUES (%s, %s)",
                        (absPath, actName),
                    )
                conn.commit()

                cur.execute(
                    "DELETE FROM mod where run_file_path = %s",
                    (absPath,),
                )
                conn.commit()
                mods = runJson["event"]["mods"] if "mods" in runJson["event"] else ["no_mods_data"]
                for modName in mods:
                    cur.execute(
                        "INSERT INTO mod(run_file_path, mod_name) VALUES (%s, %s)",
                        (absPath, modName),
                    )
                conn.commit()

                cur.execute(
                    "UPDATE run SET status = %s WHERE file_path = %s",
                    ("PROCESSED", absPath),
                )
                conn.commit()

            except Exception as e:
                cur.execute(
                    "UPDATE run SET status = %s, error_message = %s WHERE file_path = %s",
                    ("ERROR", traceback.format_exc(), absPath),
                )
                conn.commit()

    ascKeysInts = set()
    characterKeys = set()
    ascRanges = (getNewAscRange(0, 1), getNewAscRange(2, 19), getNewAscRange(20, 20))

    def stringFromAscRange(ascRange):
        if ascRange["min"] == ascRange["max"]:
            return str(ascRange["min"])
        return str(ascRange["min"]) + "-" + str(ascRange["max"])

    cur.execute("SELECT ascension FROM run WHERE status = 'PROCESSED'")
    rows = cur.fetchall()
    for row in rows:
        ascKeysInts.add(int(row[0]))

    cur.execute("SELECT character FROM run WHERE status = 'PROCESSED'")
    rows = cur.fetchall()
    for row in rows:
        characterKeys.add(row[0])

    cur.execute("SELECT count(*) FROM run")
    totalRuns = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM run WHERE status = 'SKIPPED' and is_endless = true")
    endlessRuns = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM run WHERE status = 'SKIPPED' and left_too_early = true")
    leftTooEarlyRuns = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM run WHERE status = 'ERROR'")
    exceptionRuns = cur.fetchone()[0]

    if not os.path.exists("report"):
        os.makedirs("report")

    with open("report/01_summary.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print(str(totalRuns) + " total runs")
        print(str(endlessRuns) + " endless runs were skipped")
        print(str(leftTooEarlyRuns) + " runs were skipped, because they were left too early")
        print(str(exceptionRuns) + " runs threw an exception")
        print(str(totalRuns - endlessRuns - leftTooEarlyRuns - exceptionRuns) + " total runs processed")

    def printWinRatioSortedBy(fileName, keyLambda):
        global winRatio
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print("Win ratio on all ascensions:", end=" ")
            printWinRatio(getWinRatio(None, None, True), getWinRatio(None, None, False))
            print()
            for ascInt in sorted(ascKeysInts):
                asc = str(ascInt)
                print("Win ratio on ascension " + asc + ":", end=" ")
                printWinRatio(getWinRatio(asc, None, True), getWinRatio(asc, None, False))
            if len(characterKeys) > 1:
                with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                    winRatio = {}
                    for character in characterKeys:
                        won = getWinRatio(None, character, True)
                        lost = getWinRatio(None, character, False)
                        winRatio[character] = {"won": won, "lost": lost}
                    for character in sorted(characterKeys, key=keyLambda):
                        won = winRatio[character]["won"]
                        lost = winRatio[character]["lost"]
                        if won + lost <= CHARACTER_GAMES_THRESHOLD:
                            continue
                        print(
                            "Win ratio on character " + character + " on all ascensions:",
                            end=" ",
                        )
                        printWinRatio(won, lost)
                        print()
                        for ascInt in sorted(ascKeysInts):
                            asc = str(ascInt)
                            won = getWinRatio(asc, character, True)
                            lost = getWinRatio(asc, character, False)
                            if won + lost == 0:
                                continue
                            print(
                                "Win ratio on character " + character + " on ascension " + str(asc) + ":",
                                end=" ",
                            )
                            printWinRatio(won, lost)
                        print()

    printWinRatioSortedBy("02_win_ratio_sorted_alphabetically", lambda e: e[0])
    printWinRatioSortedBy(
        "03_win_ratio_sorted_by_most_played",
        lambda e: -(winRatio[e]["won"] + winRatio[e]["lost"]),
    )
    printWinRatioSortedBy(
        "04_win_ratio_sorted_by_value",
        lambda e: -winRatio[e]["won"] / (winRatio[e]["won"] + winRatio[e]["lost"]),
    )

    def printAverageLengthForRuns(fileName, isVictory, runsString):
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print(
                "Average length of " + runsString + " runs on all ascensions:",
                end=" ",
            )
            printAverageLength(getAverageLength(None, None, isVictory))
            print()
            for ascInt in sorted(ascKeysInts):
                asc = str(ascInt)
                length = getAverageLength(asc, None, isVictory)
                if length["count"] <= CHARACTER_GAMES_THRESHOLD:
                    continue
                print(
                    "Average length of " + runsString + " runs on ascension " + str(asc) + ":",
                    end=" ",
                )
                printAverageLength(length)
            print()
            if len(characterKeys) > 1:
                with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                    lengthDict = {}
                    for character in characterKeys:
                        lengthDict[character] = getAverageLength(None, character, isVictory)
                    for character in sorted(
                        characterKeys,
                        key=lambda e: -lengthDict[e]["sum"] / lengthDict[e]["count"] if lengthDict[e]["count"] != 0 else 0,
                    ):
                        length = lengthDict[character]
                        if length["count"] <= CHARACTER_GAMES_THRESHOLD:
                            continue
                        print(
                            "Average length of " + runsString + " runs on character " + character + " on all ascensions:",
                            end=" ",
                        )
                        printAverageLength(length)
                        print()
                        for ascInt in sorted(ascKeysInts):
                            asc = str(ascInt)
                            length = getAverageLength(asc, character, isVictory)
                            if length["count"] == 0:
                                continue
                            print(
                                "Average length of " + runsString + " runs on character " + character + " on ascension " + str(asc) + ":",
                                end=" ",
                            )
                            printAverageLength(length)
                        print()
            f.close()

    printAverageLengthForRuns("05_average_length_won", True, "won")
    printAverageLengthForRuns("06_average_length_lost", False, "lost")

    def printMedianLengthForRuns(fileName, isVictory, runsString):
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print(
                "Median length of " + runsString + " runs on all ascensions:",
                end=" ",
            )
            median = getMedianLength(None, None, isVictory)
            printMedianLength(median)
            print()
            for ascInt in sorted(ascKeysInts):
                asc = str(ascInt)
                median = getMedianLength(asc, None, isVictory)
                if median["count"] <= CHARACTER_GAMES_THRESHOLD:
                    continue
                print(
                    "Median length of " + runsString + " runs on ascension " + str(asc) + ":",
                    end=" ",
                )
                printMedianLength(median)
            print()
            if len(characterKeys) > 1:
                with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                    medianDict = {}
                    for character in characterKeys:
                        medianDict[character] = getMedianLength(None, character, isVictory)
                    for character in sorted(
                        characterKeys,
                        key=lambda e: -medianDict[e]["median"] if medianDict[e]["count"] != 0 else 0,
                    ):
                        median = medianDict[character]
                        if median["count"] <= CHARACTER_GAMES_THRESHOLD:
                            continue
                        print(
                            "Median length of " + runsString + " runs on character " + character + " on all ascensions:",
                            end=" ",
                        )
                        printMedianLength(median)
                        print()
                        for ascInt in sorted(ascKeysInts):
                            asc = str(ascInt)
                            median = getMedianLength(asc, character, isVictory)
                            if median["count"] == 0:
                                continue
                            print(
                                "Median length of " + runsString + " runs on character " + character + " on ascension " + str(asc) + ":",
                                end=" ",
                            )
                            printMedianLength(median)
                        print()
            f.close()

    printMedianLengthForRuns("07_median_length_won", True, "won")
    printMedianLengthForRuns("08_median_length_lost", False, "lost")

    def printCardChoicesForRuns(fileName, upgradedCardsGrouped, runsString):
        # It doesn't really make sense to show it without specifying a character
        with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print("P = Picked")
            print("NP = Not Picked")
            print("R = Ratio")
            print()
            for character in sorted(characterKeys):
                print(runsString + " on character " + character + " on all ascensions:")
                printCardChoices(getCardChoices(None, character, upgradedCardsGrouped))
                for ascRange in ascRanges:
                    print(runsString + " on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                    printCardChoices(getCardChoices(ascRange, character, upgradedCardsGrouped))

    printCardChoicesForRuns("09_card_choices", False, "Card choices")
    printCardChoicesForRuns(
        "10_card_choiced_upgraded_cards_grouped",
        True,
        "Card choices (upgraded cards grouped)",
    )

    def printIsSpecificCardInDeckAndWinRatioForRuns(fileName, upgradedCardsGrouped, runsString):
        # It doesn't really make sense to show it without specifying a character
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            for character in sorted(characterKeys):
                print(runsString + " and win ratio on character " + character + " on all ascensions:")
                printIsSpecificCardInDeckAndWinRatio(getIsSpecificCardInDeckAndWinRatio(None, character, upgradedCardsGrouped))
                for ascRange in ascRanges:
                    print(runsString + " and win ratio on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                    printIsSpecificCardInDeckAndWinRatio(getIsSpecificCardInDeckAndWinRatio(ascRange, character, upgradedCardsGrouped))

    printIsSpecificCardInDeckAndWinRatioForRuns(
        "11_is_a_specific_card_in_deck_and_win_ratio_by_characters",
        False,
        "Is a specific card in deck",
    )
    printIsSpecificCardInDeckAndWinRatioForRuns(
        "12_is_a_specific_card_in_deck_upgraded_cards_grouped_and_win_ratio_by_characters",
        True,
        "Is a specific card in deck (upgraded cards grouped)",
    )

    def printNumberOfSpecificCardsAndWinRatioForRuns(fileName, upgradedCardsGrouped, runsString):
        # It doesn't really make sense to show it without specifying a character
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            for character in sorted(characterKeys):
                print(runsString + " and win ratio on character " + character + " on all ascensions:")
                printNumberOfSpecificCardsAndWinRatio(getNumberOfSpecificCardsAndWinRatio(None, character, upgradedCardsGrouped))
                for ascRange in ascRanges:
                    print(runsString + " and win ratio on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                    printNumberOfSpecificCardsAndWinRatio(getNumberOfSpecificCardsAndWinRatio(ascRange, character, upgradedCardsGrouped))

    printNumberOfSpecificCardsAndWinRatioForRuns(
        "13_number_of_specific_cards_and_win_ratio_by_characters",
        False,
        "Number of specific cards",
    )
    printNumberOfSpecificCardsAndWinRatioForRuns(
        "14_number_of_specific_cards_upgraded_cards_grouped_and_win_ratio_by_characters",
        True,
        "Number of specific cards (upgraded cards grouped)",
    )

    def printHasSpecificRelicAndWinRatioForRuns(fileName, sortByPrefix):
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print("Has a specific relic and win ratio on all ascensions (only base game relics):")
            printHasSpecificRelicAndWinRatio(getHasSpecificRelicAndWinRatio(None, None), True, sortByPrefix)
            for ascRange in ascRanges:
                print("Has a specific relic and win ratio on ascensions " + stringFromAscRange(ascRange) + " (only base game relics):")
                printHasSpecificRelicAndWinRatio(getHasSpecificRelicAndWinRatio(ascRange, None), True, sortByPrefix)
            print("Has a specific relic and win ratio on all ascensions:")
            printHasSpecificRelicAndWinRatio(getHasSpecificRelicAndWinRatio(None, None), False, sortByPrefix)
            for ascRange in ascRanges:
                print("Has a specific relic and win ratio on ascensions " + stringFromAscRange(ascRange) + ":")
                printHasSpecificRelicAndWinRatio(getHasSpecificRelicAndWinRatio(ascRange, None), False, sortByPrefix)
            if len(characterKeys) > 1:
                with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                    for character in sorted(characterKeys):
                        print("Has a specific relic and win ratio and win ratio on character " + character + " on all ascensions:")
                        printHasSpecificRelicAndWinRatio(
                            getHasSpecificRelicAndWinRatio(None, character),
                            False,
                            sortByPrefix,
                        )
                        for ascRange in ascRanges:
                            print(
                                "Has a specific relic and win ratio and win ratio on character "
                                + character
                                + " on ascensions "
                                + stringFromAscRange(ascRange)
                                + ":"
                            )
                            printHasSpecificRelicAndWinRatio(
                                getHasSpecificRelicAndWinRatio(ascRange, character),
                                False,
                                sortByPrefix,
                            )

    printHasSpecificRelicAndWinRatioForRuns("15_has_a_specific_relic_and_win_ratio", False)
    printHasSpecificRelicAndWinRatioForRuns("16_has_a_specific_relic_and_win_ratio_sorted_by_prefix", True)

    with open("report/17_average_damage_taken.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Average damage taken on all ascensions:")
        printAverageDamageTaken(getAverageDamageTaken(None, None))
        for ascRange in ascRanges:
            print("Average damage taken on ascensions " + stringFromAscRange(ascRange) + ":")
            printAverageDamageTaken(getAverageDamageTaken(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/17_average_damage_taken_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Average damage taken on character " + character + " on all ascensions:")
                    printAverageDamageTaken(getAverageDamageTaken(None, character))
                    for ascRange in ascRanges:
                        print("Average damage taken on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printAverageDamageTaken(getAverageDamageTaken(ascRange, character))

    with open("report/18_average_combat_length.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Average combat length on all ascensions:")
        printAverageCombatLength(getAverageCombatLength(None, None))
        for ascRange in ascRanges:
            print("Average combat length on ascensions " + stringFromAscRange(ascRange) + ":")
            printAverageCombatLength(getAverageCombatLength(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/18_average_combat_length_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Average combat length on character " + character + " on all ascensions:")
                    printAverageCombatLength(getAverageCombatLength(None, character))
                    for ascRange in ascRanges:
                        print("Average combat length on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printAverageCombatLength(getAverageCombatLength(ascRange, character))

    with open("report/19_killed_by.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Killed by on all ascensions:")
        printKilledBy(getKilledBy(None, None))
        for ascRange in ascRanges:
            print("Killed by on ascensions " + stringFromAscRange(ascRange) + ":")
            printKilledBy(getKilledBy(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/19_killed_by_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Killed by on character " + character + " on all ascensions:")
                    printKilledBy(getKilledBy(None, character))
                    for ascRange in ascRanges:
                        print("Killed by on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printKilledBy(getKilledBy(ascRange, character))

    def printSwappedStarterRelicSortedBy(fileName, keyLambda):
        global swappedDict
        with open("report/" + fileName + ".txt", "w", encoding="utf-8") as f, redirect_stdout(f):
            print("Swapped starter relic on all ascensions:", end=" ")
            printSwappedStarterRelic(getSwappedStarterRelic(None, None))
            print()
            for ascInt in sorted(ascKeysInts):
                asc = str(ascInt)
                swapped = getSwappedStarterRelic(asc, None)
                if swapped["total"] <= CHARACTER_GAMES_THRESHOLD:
                    continue
                print(
                    "Swapped starter relic on ascension " + str(asc) + ":",
                    end=" ",
                )
                printSwappedStarterRelic(swapped)
            print()
            if len(characterKeys) > 1:
                with open("report/" + fileName + "_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                    swappedDict = {}
                    for character in characterKeys:
                        swappedDict[character] = getSwappedStarterRelic(None, character)
                    for character in sorted(characterKeys, key=keyLambda):
                        swapped = swappedDict[character]
                        if swapped["total"] <= CHARACTER_GAMES_THRESHOLD:
                            continue
                        print(
                            "Swapped starter relic on character " + character + " on all ascensions:",
                            end=" ",
                        )
                        printSwappedStarterRelic(swapped)
                        print()
                        for ascInt in sorted(ascKeysInts):
                            asc = str(ascInt)
                            swapped = getSwappedStarterRelic(asc, character)
                            if swapped["total"] == 0:
                                continue
                            print(
                                "Swapped starter relic on character " + character + " on ascension " + str(asc) + ":",
                                end=" ",
                            )
                            printSwappedStarterRelic(swapped)
                        print()
            f.close()

    printSwappedStarterRelicSortedBy(
        "20_swapped_starter_relic_sorted_by_popularity",
        lambda e: -swappedDict[e]["swapped"] / swappedDict[e]["total"],
    )
    printSwappedStarterRelicSortedBy(
        "21_swapped_starter_relic_sorted_by_difference",
        lambda e: -swappedDict[e]["difference"] if swappedDict[e]["difference"] is not None else 0,
    )

    with open("report/22_hosts.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Hosts on all ascensions:")
        printHosts(getHosts(None, None))
        for ascRange in ascRanges:
            print("Hosts on ascensions " + stringFromAscRange(ascRange) + ":")
            printHosts(getHosts(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/22_hosts_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Hosts on character " + character + " on all ascensions:")
                    printHosts(getHosts(None, character))
                    for ascRange in ascRanges:
                        print("Hosts on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printHosts(getHosts(ascRange, character))

    with open("report/23_language.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Language on all ascensions:")
        printLanguage(getLanguage(None, None))
        for ascRange in ascRanges:
            print("Language on ascensions " + stringFromAscRange(ascRange) + ":")
            printLanguage(getLanguage(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/23_language_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Language on character " + character + " on all ascensions:")
                    printLanguage(getLanguage(None, character))
                    for ascRange in ascRanges:
                        print("Language on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printLanguage(getLanguage(ascRange, character))

    with open("report/24_acts_visited.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Acts visited on all ascensions:")
        printActsVisited(getActsVisited(None, None))
        for ascRange in ascRanges:
            print("Acts visited on ascensions " + stringFromAscRange(ascRange) + ":")
            printActsVisited(getActsVisited(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/24_acts_visited_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Acts visited on character " + character + " on all ascensions:")
                    printActsVisited(getActsVisited(None, character))
                    for ascRange in ascRanges:
                        print("Acts visited on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printActsVisited(getActsVisited(ascRange, character))

    with open("report/25_enabled_mods.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
        print("Enabled mods on all ascensions:")
        printEnabledMods(getEnabledMods(None, None))
        for ascRange in ascRanges:
            print("Enabled mods on ascensions " + stringFromAscRange(ascRange) + ":")
            printEnabledMods(getEnabledMods(ascRange, None))
        if len(characterKeys) > 1:
            with open("report/25_enabled_mods_by_characters.txt", "w", encoding="utf-8") as f, redirect_stdout(f):
                for character in sorted(characterKeys):
                    print("Enabled mods on character " + character + " on all ascensions:")
                    printEnabledMods(getEnabledMods(None, character))
                    for ascRange in ascRanges:
                        print("Enabled mods on character " + character + " on ascensions " + stringFromAscRange(ascRange) + ":")
                        printEnabledMods(getEnabledMods(ascRange, character))


except Exception as e:
    print(traceback.format_exc())
    sys.exit(1)

finally:
    if conn:
        conn.close()
