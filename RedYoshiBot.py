import discord
import datetime
import random
import os
import re
import sys
import time
import asyncio
import json
import hashlib
import sqlite3
import struct
from urllib.request import *
from urllib.error import *

current_time_min = lambda: int(round(time.time() / 60))
SELF_BOT_MEMBER = None
SELF_BOT_SERVER = None
db_mng = None
client = discord.Client()
shutdown_watch_running = False
running_State = True
debug_mode = False

class ServerDatabase:
	global debug_mode
	global current_time_min
	#Stores and obtains friend codes using an SQLite 3 database.
	def __init__(self):
		self.recover = sys.argv 
		self.conn = sqlite3.connect('data/fc.sqlite')
		print('Addon "{}" loaded\n'.format(self.__class__.__name__))

	def __del__(self):
		global running_State
		self.conn.commit()
		self.conn.close()
		print('Addon "{}" unloaded\n'.format(self.__class__.__name__))
		if (running_State and not debug_mode):
			print("Unexpected interpreter exit at {}, rebooting.".format(str(datetime.datetime.now())))
			os.execv(sys.executable, ['python3'] + self.recover)
	# based on https://github.com/megumisonoda/SaberBot/blob/master/lib/saberbot/valid_fc.rb
	def verify_fc(self, fc):
		try:
			fc = int(fc.replace('-', ''))
		except ValueError:
			return None
		if fc > 0x7FFFFFFFFF:
			return None
		principal_id = fc & 0xFFFFFFFF
		checksum = (fc & 0xFF00000000) >> 32
		return (fc if hashlib.sha1(struct.pack('<L', principal_id)).digest()[0] >> 1 == checksum else None)

	def fc_to_string(self, fc):
		fc = str(fc).rjust(12, '0')
		return "{}-{}-{}".format(fc[0:4], fc[4:8], fc[8:12])
	async def warn_set(self, memberid, value):
		c = self.conn.cursor()
		if(value == 0):
			c.execute('DELETE FROM usr_warns WHERE userid = ?', (int(memberid),))
			return
		rows = c.execute("SELECT * FROM usr_warns WHERE userid = ?", (int(memberid),))
		for row in rows:
			c.execute("UPDATE usr_warns SET warns = ? WHERE userid = ?", (value, int(memberid)))
			return
		c.execute('INSERT INTO usr_warns VALUES (?,?)', (int(memberid), int(value)))
	async def fact_add(self, memberid, fact):
		c = self.conn.cursor()
		c.execute('INSERT INTO facts VALUES (?,?)', (int(memberid), fact))
	async def fact_delete(self, id):
		c = self.conn.cursor()
		c.execute("DELETE FROM facts WHERE rowid = ?", (id,))
	async def fact_deleteuser(self, memberid):
		c = self.conn.cursor()
		c.execute("DELETE FROM facts WHERE userid = ?", (int(memberid),))
	async def fact_userreg(self, memberid):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM facts WHERE userid = ?", (int(memberid),))
		for row in rows:
			return True
		return False
	async def fact_get(self, withid):
		c = self.conn.cursor()
		rows = []
		if (withid == True):
			rows = c.execute("SELECT rowid,* FROM facts")
		else:
			rows = c.execute("SELECT * FROM facts")
		ret = []
		for row in rows:
			ret.append(row)
		return ret
	async def fact_get_byrow(self, row_id):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM facts WHERE rowid = ?", (row_id,))
		ret = []
		for row in rows:
			ret.append(row)
		return ret
	async def fact_getuser(self, memberid):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM facts WHERE userid = ?", (int(memberid),))
		for row in rows:
			return row[1]
		return None
	async def warn_get(self, memberid):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM usr_warns WHERE userid = ?", (int(memberid),))
		for row in rows:
			return int(row[1])
		return 0
	async def warn_get_all(self):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM usr_warns")
		return rows
	async def mute_apply(self, memberid, amountmin):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM usr_mute WHERE userid = ?", (int(memberid),))
		for row in rows:
			c.execute("UPDATE usr_mute SET start = ?, amount = ? WHERE userid = ?", (current_time_min(), amountmin, int(memberid)))
			return
		c.execute('INSERT INTO usr_mute VALUES (?,?,?)', (int(memberid),current_time_min(), amountmin))
	async def mute_get(self):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM usr_mute")
		return rows
	async def mute_remove(self, memberid):
		c = self.conn.cursor()
		c.execute('DELETE FROM usr_mute WHERE userid = ?', (int(memberid),))
	# Based on kurisu from homebrew discord server https://github.com/ihaveamac/Kurisu
	async def fcregister(self, message, fc, notify):
		"""Add your friend code."""
		fc = self.verify_fc(fc)
		if not fc:
			await client.send_message(message.channel, '{}, that\'s an invalid friend code.'.format(message.author.name))
			return
		if (notify.lower() == "true"):
			notify = True 
		elif (notify.lower() == "false"):
			notify = False
		else:
			await client.send_message(message.channel, '{}, invalid command syntax, `(notify)` must be `true` or `false`.'.format(message.author.name))
			return
		c = self.conn.cursor()
		rows = c.execute('SELECT * FROM friend_codes WHERE userid = ?', (int(message.author.id),))
		for row in rows:
			# if the user already has one, this prevents adding another
			await client.send_message(message.channel, "{}, please delete your current friend code with `@RedYoshiBot fcdelete` before adding another.".format(message.author.name))
			return
		c.execute('INSERT INTO friend_codes VALUES (?,?,?)', (int(message.author.id), fc, notify))
		if notify:
			info_str = ". You will be notified whenever someone requests your code."
		else:
			info_str = ""
		await client.send_message(message.channel, "{}, your friend code has been added to the database: `{}`{}".format(message.author.name, self.fc_to_string(fc), info_str))
		self.conn.commit()

	async def fcquery(self, message):
		global SELF_BOT_MEMBER
		global SELF_BOT_SERVER
		"""Get other user's friend code. You must have one yourself in the database."""
		c = self.conn.cursor()
		member = None
		for m in message.mentions:
			if m != SELF_BOT_MEMBER:
				member = m
		if not member:
			await client.send_message(message.channel, "{}, no user or invalid user specified.".format(message.author.name))
			return
		rows = c.execute('SELECT * FROM friend_codes WHERE userid = ?', (int(message.author.id),))
		for row in rows:
			# assuming there is only one, which there should be
			rows_m = c.execute('SELECT * FROM friend_codes WHERE userid = ?', (int(member.id),))
			for row_m in rows_m:
				if (member.name[-1:] == "s"):
					suffix = "\'"
				else:
					suffix = "\'s"
				await client.send_message(message.channel, "{}{} friend code is `{}`".format(member.name, suffix, self.fc_to_string(row_m[1])))
				try:
					if (row_m[2]):
						await client.send_message(member, "{} in {} server has queried your friend code! Their code is `{}`.".format(message.author.name, SELF_BOT_SERVER.name, self.fc_to_string(row[1])))
				except discord.errors.Forbidden:
					pass  # don't fail in case user has DMs disabled for this server, or blocked the bot
				return
			await client.send_message(message.channel, "{}, looks like {} has no friend code registered.".format(message.author.name, member.name))
			return
		await client.send_message(message.channel, "{}, you need to register your own friend code with `@RedYoshiBot fcregister` before getting others.".format(message.author.name))

	async def fcdelete(self, message):
		#Delete your friend code.
		if (type(message) is discord.Message):
			c = self.conn.cursor()
			c.execute('DELETE FROM friend_codes WHERE userid = ?', (int(message.author.id),))
			await client.send_message(message.channel, "{}, your friend code has been removed from database.".format(message.author.name))
			self.conn.commit()
		elif (type(message) is discord.Member):
			c = self.conn.cursor()
			c.execute('DELETE FROM friend_codes WHERE userid = ?', (int(message.id),))
			self.conn.commit()
	async def get_cookie(self, user):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
		for row in rows:
			return row[1]
		return 0
	async def add_cookie(self, user, amount):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
		for row in rows:
			calc = row[1] + amount 
			if (calc < 0 ):
				calc = 0
			c.execute("UPDATE cookies SET amount = ? WHERE userid = ?", (calc, user))
			return
		if (amount < 0):
			amount = 0
		c.execute('INSERT INTO cookies VALUES (?,?)', (int(user), amount))
		return
	async def set_cookie(self, user, amount):
		c = self.conn.cursor()
		rows = c.execute("SELECT * FROM cookies WHERE userid = ?", (int(user),))
		if (amount <= 0):
			amount = 0
		for row in rows:
			c.execute("UPDATE cookies SET amount = ? WHERE userid = ?", (amount, user))
			return
		c.execute('INSERT INTO cookies VALUES (?,?)', (int(user), amount))
		return
	async def top_ten_cookie(self):
		c = self.conn.cursor()
		return c.execute("SELECT * FROM cookies ORDER BY amount DESC limit 10")
	async def delete_cookie(self, user):
		c = self.conn.cursor()
		c.execute('DELETE FROM cookies WHERE userid = ?', (int(user),))
		return

			

def get_retry_times ():
	try:
		with open("data/retry.flag", "r") as f:
			data = f.read()
			ret = int(data)
			return ret
	except:
		set_retry_times(0)
		return 0

def set_retry_times(amount):
	with open("data/retry.flag", "w") as f:
		f.write(str(amount))

def is_channel(message, ch_id):
	return (message.channel.id == ch_id)

def get_role(roleid):
	global SELF_BOT_SERVER
	roles = SELF_BOT_SERVER.roles
	for rol in roles:
		if(rol.id == roleid):
			return rol
	return None
def get_from_mention(mention):
	global SELF_BOT_SERVER
	global SELF_BOT_MEMBER
	memberid = re.sub("\D", "", mention)
	return client.get_server(SERVER_ID()).get_member(memberid)

def int_to_emoji(num):
	num = int(num)
	eml = NUMBER_EMOJI();
	if (num == 0):
		return eml[0]
	retstr = ""
	while (num != 0):
		retstr = eml[num % 10] + retstr
		num = int(num/10)
	return retstr

def int_to_rps(num):
	num = num % 3
	if (num == 0):
		return ":punch:"
	elif (num == 1):
		return ":hand_splayed:"
	return ":v:"

async def game_numberguess(user, machine, diff, message):
	global db_mng
	mach1 = int_to_emoji(int(machine/10))
	mach2 = int_to_emoji(machine % 10)
	i = 0
	game_message = await client.send_message(message.channel, "{}, you guessed: {} , I guessed: :question::question:".format(message.author.name, int_to_emoji(user)))
	randsec = random.randint(1, 3)
	while (i < randsec):
		await asyncio.sleep(1)
		i = i + 1 
	game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}:question:".format(message.author.name, int_to_emoji(user), mach1))
	randsec = random.randint(1, 3)
	while (i < randsec):
		await asyncio.sleep(1)
		i = i + 1
	game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}{}".format(message.author.name, int_to_emoji(user), mach1, mach2))
	if (user == machine):
		if diff == 0:
			game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}{} . **You won 10 <:yoshicookie:416533826869657600>!**".format(message.author.name, int_to_emoji(user), mach1, mach2))
			await db_mng.add_cookie(message.author.id, 10)
		elif diff == 1:
			game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}{} . **You won 50 <:yoshicookie:416533826869657600>!**".format(message.author.name, int_to_emoji(user), mach1, mach2))
			await db_mng.add_cookie(message.author.id, 50)
		elif diff == 2:
			game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}{} . **You won 100 <:yoshicookie:416533826869657600>!**".format(message.author.name, int_to_emoji(user), mach1, mach2))
			await db_mng.add_cookie(message.author.id, 100)
	else:
		game_message = await client.edit_message(game_message, "{}, you guessed: {} , I guessed: {}{} . **You lost 1 <:yoshicookie:416533826869657600>.**".format(message.author.name, int_to_emoji(user), mach1, mach2))
		await db_mng.add_cookie(message.author.id, -1)
	return
async def game_rps(bot_ch, usr_ch, message):
	##0 - rock; 1 - paper; 2 - scissors
	state = 0 #0 lose; 1 match; 2 win
	bot_ch = bot_ch + 3
	usr_ch = usr_ch + 3
	winstr = "**You lost 1 <:yoshicookie:416533826869657600>.**"
	if (bot_ch == usr_ch):
		state = 1
		winstr = "**That's a match.**"
	elif (bot_ch % 3) == (usr_ch - 1) % 3:
		state  = 2
		winstr = "**You won 2 <:yoshicookie:416533826869657600>.**"
		await db_mng.add_cookie(message.author.id, 2)
	else:
		await db_mng.add_cookie(message.author.id, -1)
	await client.send_message(message.channel, "{}, your choice: {} , my choice: {} . {}".format(message.author.name, int_to_rps(usr_ch), int_to_rps(bot_ch), winstr))
	return

async def game_coin(bot_ch, usr_ch, message):
	choice_str = "head"
	if (usr_ch == 1):
		choice_str = "tails"
	bot_str = "head"
	if (bot_ch % 2 == 1):
		bot_str = "tails"
	if (bot_ch == 145):
		await client.send_message(message.channel, "{}, you guessed: **{}** , the coin landed on its **side**. **How lucky! You won 500 <:yoshicookie:416533826869657600>.**".format(message.author.name, choice_str))
		await db_mng.add_cookie(message.author.id, 500)
	elif(bot_ch % 2 == usr_ch):
		await client.send_message(message.channel, "{}, you guessed: **{}** , the coin landed on its **{}**. **You won 1 <:yoshicookie:416533826869657600>.**".format(message.author.name, choice_str, bot_str))
		await db_mng.add_cookie(message.author.id, 1)
	else:
		await client.send_message(message.channel, "{}, you guessed: **{}** , the coin landed on its **{}**. **You lost 1 <:yoshicookie:416533826869657600>.**".format(message.author.name, choice_str, bot_str))
		await db_mng.add_cookie(message.author.id, -1)	
	return

def help_array():
	return {
		"fcregister": ">@RedYoshiBot fcregister (friendcode) (notify)\r\nAdds your friend code to the server database. If notify is \"true\", you will be notified whenever someone queries your friend code, otherwise set it to \"false\".", 
		"fcquery": ">@RedYoshiBot fcquery (user)\r\nGets the friend code from the specified user (you need to have your own friend code registered). If the specified user has the notify option enabled, your friend code will be sent to them as well.",
		"fcdelete": ">@RedYoshiBot fcdelete\r\nRemoves your friend code from the server database.",
		"ping": ">@RedYoshiBot ping\r\nPings the bot.",
		"membercount": ">@RedYoshiBot membercount\r\nDisplays the member count of the server.",
		"rules": ">@RedYoshiBot rules\r\nShows the server rules.",
		"getwarn": ">@RedYoshiBot getwarn\nSends your warning amount in a DM.",
		"getmute": ">@RedYoshiBot getmute\nSends your muted time in a DM.",
		"fact": ">@RedYoshiBot fact (factID)\nDisplays a random fact. If factID is specified, the fact with that id will be displayed. (Use listfact to get all fact IDs.)",
		"addfact": ">@RedYoshiBot addfact (fact)\nAdds a fact (only one per user). The format is the following: base;opt1, opt2, etc; opt1, opt2, etc; etc... any instance of {} will be replaced by a random choice. You must have the same amount of {} as ; otherwise it won't work properly.\n\nExamples:\n{} is number {}; Mario, Luigi, Yoshi; NUMBER:1:3\nI {} {} {}; hate, love; cheese, apples, USER; :wink:, :weary:\n\nNUMBER:X:Y -> Random number between X and Y\nUSER -> Random server member.",
		"delfact": ">@RedYoshiBot delfact\nRemoves your own fact.",
		"listfact": ">@RedYoshiBot listfact\nDisplays all facts.",
		"communities": ">@RedYoshiBot communities\nShows the main CTGP-7 communities.",
		"game": ">@RedYoshiBot game (gamemode) (options)\nPlays a game."
	}
def staff_help_array():
	return {
		"say": ">@RedYoshiBot say (channel/user) (text)\r\nSends a message in the specified channel or a DM if it is a user.",
		"edit": ">@RedYoshiBot edit (messageid) (text)\r\nEdits the specified message. Can only edit recent bot messages in the server.",
		"release": ">@RedYoshiBot release (version) (tag)\r\nAnnounces the release of the specified version (data taken from github) in #announcements. If (tag) is 1, it will tag @everyone (only tag everyone for major releases)",
		"restart": ">@RedYoshiBot restart\r\nRestarts the bot.",
		"stop": ">@RedYoshiBot stop\r\nStops the bot, once stopped is has to be manually started again from a terminal, so no way to start it from discord.",
		"mute": ">@RedYoshiBot mute (user) (amount)\r\nMutes an user for a certain amount. The amount can be m (minutes), h (hours), d (days) and y (years). For example: 2h, 12m, 7d, etc",
		"unmute": ">@RedYoshiBot unmute (user)\r\nUnmutes a muted user.",
		"warn": ">@RedYoshiBot warn (user) [Reason]\nGives a warning to an user. Reason is optional.",
		"setwarn": ">@RedYoshiBot setwarn (user) (amount) [Reason]\nSets the warning amount of an user. Reason is optional.",
		"getwarn": ">@RedYoshiBot getwarn\nGets all the warned users.",
		"getmute": ">@RedYoshiBot getmute\nGets all the muted users.",
		"delfact": ">@RedYoshiBot delfact (id)\nDeletes specified fact.",
		"change_game": ">@RedYoshiBot change_game\nChanges the current playing game to a new random one."
	}
def game_help_array():
	return {
		"guessanumber": ">@RedYoshiBot game guessanumber (easy/normal/hard) (number)\nGuess a number game.\n\neasy: Guess a number between 0 and 10 (Win: +10 yoshi cookies).\nnormal: Guess a number between 0 and 50 (Win: +50 yoshi cookies).\nhard: Guess a number between 0 and 99 (Win: +100 yoshi cookies).\nLose: -1 yoshi cookies.",
		"rps": ">@RedYoshiBot game rps (rock/paper/scissors)\nRock-Paper-Scissors.\n\nWin: +2 yoshi cookies.\nMatch: nothing.\nLose: -1 yoshi cookies.",
		"coin": ">@RedYoshiBot game coin (head/tails)\nFlip a coin.\n\nWin: +1 yoshi cookies.\nLose: -1 yoshi cookies.",
		"showcookie": ">@RedYoshiBot game showcookie\nShows your amount of yoshi cookies.",
		"top10": ">@RedYoshiBot game top10\nShows the top 10 users with the highest amount of yoshi cookies."
	}
def staff_game_help_array():
	return {
		"showcookie":">@RedYoshiBot game showcookie (user)\nShows the amount of yoshi cookies of the specified user.",
		"setcookie": ">@RedYoshiBot game setcookie (user) (amount)\nSets the amount of yoshi cookies of the specified user."
	}
#All the ids
def ch_list():
	return {
		"ANN": "163072540061728768",
		"STAFF": "382885324575211523",
		"FRIEND": "163333095725072384",
		"DOORSTEP": "339476078244397056",
		"BOTCHAT": "324672297812099093"
	}

def NUMBER_EMOJI():
	return [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:"]

def PLAYING_GAME():
	return ["Yoshi's Story", "Yoshi's Cookie", "Yoshi's Island", "Super Smash Bros.", "Mario Party 8", "Yoshi's Woolly World", "Mario Kart 7", "CTGP-R", "Yoshi Touch & Go"]

def MUTEROLE_ID():
	return "385544890030751754"

def SERVER_ID():
	return "163070769067327488"

COMMUNITIES_TEXT = "```Here are the main CTGP-7 communities:\n\nCustom Tracks: 29-1800-5228-2361\nCustom Tracks, 200cc: 52-3127-4613-8641\nNormal Tracks: 02-5770-2485-4638\nNormal Tracks, 200cc: 54-0178-4815-8814\n\nMake sure you are in 0.17.1 or greater to play in those communities.```"

async def send_rules(user, newusr):
	global client
	try:
		with open("data/rules.txt", "r") as f:
			if (newusr):
				await client.send_message(user, "Welcome to the CTGP-7 server! :3\nHere are the rules: ``` {} ```".format(f.read()))
			else:
				await client.send_message(user, "Here are the rules: ``` {} ```".format(f.read()))
	except:
		print("Failed opening rules file.")


async def shutdown_watch():
	global db_mng
	global client
	global shutdown_watch_running
	global running_State
	if (shutdown_watch_running):
		return
	shutdown_watch_running = True
	while True:
		await asyncio.sleep(5)
		if os.path.isfile("data/stop.flag"):
			running_State = False
			os.remove("data/stop.flag")
			print("Manually stopping by terminal.")
			del db_mng
			await client.close()
			with open("data/stopped.flag", "w") as f:
				f.write("dummy")
			try:
				sys.exit(0)
			except:
				pass

async def parsetime(timestr):
	try:
		basenum = int(timestr[0:-1])
		unit = timestr[-1:]
	except:
		return [-1, -1, " "]
	if(unit == "m"):
		return [basenum, basenum, "minutes"]
	elif(unit == "h"):
		return [basenum * 60, basenum, "hours"]
	elif(unit == "d"):
		return [basenum * 60 * 24, basenum, "days"]
	elif(unit == "y"):
		return [basenum * 60 * 24 * 365, basenum, "years"]
	else:
		return [-1, -1, " "]

async def punish(member, amount):
	global client
	if(amount == 2):
		try:
			await client.send_message(member, "**CTGP-7 server:** You have been muted for 2 hours.")
		except:
			pass
		await mute_user(member.id, 120)
	elif(amount == 3):
		try:
			await client.send_message(member, "**CTGP-7 server:** You have been kicked and muted 7 days, you may join again.")
		except:
			pass
		await mute_user(member.id, 7*24*60)
		try:
			await client.kick(member)
		except:
			pass
	elif(amount >= 4):
		try:
			await client.send_message(member, "**CTGP-7 server:** You have been banned.")
		except:
			pass
		try:
			await client.ban(member, 7)
		except:
			pass

async def mute_user(memberid, amount):
	global db_mng
	global client
	global SELF_BOT_SERVER
	muted_user = get_from_mention(memberid)
	await db_mng.mute_apply(muted_user.id, amount)
	mute_role = get_role(MUTEROLE_ID())
	await client.add_roles(muted_user, mute_role)

async def unmute_user(memberid):
	global db_mng
	global client
	global SELF_BOT_SERVER
	muted_user = get_from_mention(memberid)
	await db_mng.mute_remove(muted_user.id)
	mute_role = get_role(MUTEROLE_ID())
	try:
		await client.send_message(muted_user, "**CTGP-7 server:** You have been unmuted.")
	except:
		pass
	await client.remove_roles(muted_user, mute_role)

async def parse_fact(s1):
	global SELF_BOT_SERVER
	s2 = re.split("[;]", s1)
	base = s2[0]
	del s2[0]
	final = []
	for rep in s2:
		final.append(re.split("[,]", rep))
	for f in final:
		id = random.randint(0, len(f) - 1)
		f[id] = f[id].strip()
		f[id] = f[id].replace("==", " ")
		foundNum = 0
		foundUsr = 0
		while (foundNum != -1 or foundUsr != -1):
			foundNum = f[id].find("NUMBER")
			foundUsr = f[id].find("USER")
			random.seed()
			if (foundNum != -1):
				special = f[id][foundNum:]
				special = special.split()[0]
				special = re.split("[:]", special)
				try:
					replacement = str(random.randint(int(special[1]),int(special[2])))
				except:
					replacement = ""
				f[id] = f[id].replace(special[0]+":"+ special[1]+":"+special[2], replacement, 1)
			elif (foundUsr != -1):
				memberlist = list(SELF_BOT_SERVER.members)
				replacement = memberlist[random.randint(0,len(memberlist) - 1)].name
				replacement.replace("USER", "user")
				f[id] = f[id].replace("USER", replacement, 1)
		base = base.replace("{}", f[id], 1)
	return base

async def isfact_dynamic(s1):
	s2 = re.split("[;]", s1)
	if (len(s2) == 1):
		return False
	else:
		return True
async def muted_task():
	global db_mng
	global current_time_min
	while True:
		await asyncio.sleep(60)
		rows = await db_mng.mute_get()
		for row in rows:
			timeleft = (row[1] + row[2]) - current_time_min()
			if(timeleft <= 0):
				await unmute_user(str(row[0]))

async def perform_game_change():
	names = PLAYING_GAME()
	name = names[random.randint(0, len(names) - 1)]
	await client.change_presence(game=discord.Game(name=name))
	return name

async def change_game():
	while True:
		await perform_game_change()
		await asyncio.sleep(600)

@client.event
async def on_ready():
	print("\n-------------------------\n")
	global db_mng
	global SELF_BOT_SERVER
	global SELF_BOT_MEMBER
	global debug_mode
	if(os.path.isfile("debug.flag")):
		print("Debug mode enabled.")
		debug_mode = True
	SELF_BOT_SERVER = client.get_server(SERVER_ID())
	SELF_BOT_MEMBER = SELF_BOT_SERVER.get_member(client.user.id)
	db_mng = ServerDatabase()
	asyncio.ensure_future(shutdown_watch())
	asyncio.ensure_future(muted_task())
	asyncio.ensure_future(change_game())
	print("Bot running: {}".format(str(datetime.datetime.now())))
	print('Logged in as: {} in server: {}'.format(SELF_BOT_MEMBER.name,SELF_BOT_SERVER.name))
	print('------\n')
	set_retry_times(0)

@client.event
async def wait_until_login():
    await client.change_presence(game=discord.Game(name='something goes here'))


@client.event
async def on_member_join(member):
	global SELF_BOT_SERVER
	global client
	global db_mng
	door_chan = SELF_BOT_SERVER.get_channel(ch_list()["DOORSTEP"])
	await client.send_message(door_chan, "Everybody welcome {} to the server! Make sure to check the rules I've sent to you in a direct message.\nWe are now {} members.".format(member.mention, SELF_BOT_SERVER.member_count))
	await send_rules(member, True)
	rows = await db_mng.mute_get()
	for row in rows:
		if (row[0] == int(member.id)):
			timeleft = (row[1] + row[2]) - current_time_min()
			if (timeleft > 0):
				await mute_user(member.id, timeleft)

@client.event
async def on_member_remove(member):
	global SELF_BOT_SERVER
	global db_mng
	global client
	door_chan = SELF_BOT_SERVER.get_channel(ch_list()["DOORSTEP"])
	await client.send_message(door_chan, "See ya **{}**. We are now {} members.".format(member.name, SELF_BOT_SERVER.member_count))
	await db_mng.fcdelete(member)
	
@client.event
async def on_message(message):
	global db_mng
	global SELF_BOT_SERVER
	global SELF_BOT_MEMBER
	global COMMUNITIES_TEXT
	global client
	global running_State
	global debug_mode
	global current_time_min
	if (client.user == None) or (SELF_BOT_SERVER == None) or (SELF_BOT_MEMBER == None):
		print("Error, some variable is None")
		return None
	try:
		random.seed()
		bot_mtn = message.content.split()[0]
		if (get_from_mention(bot_mtn) == client.user) and (message.author != client.user): #@RedYoshiBot
			try:
				bot_cmd = message.content.split()[1]
				if bot_cmd == 'mute':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split()
						if (len(tag) != 4):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["mute"] + "```")
							return
						muted_member = get_from_mention(tag[2])
						if(muted_member != None):
							mutemin = await parsetime(tag[3])
							if (mutemin[0] == -1):
								await client.send_message(message.channel, "{}, invalid time amount.".format(message.author.name))
								return
							await mute_user(tag[2], mutemin[0])
							await client.send_message(message.channel, "{} was muted for {} {}.".format(muted_member.name, mutemin[1], mutemin[2]))
							try:
								await client.send_message(muted_member, "**CTGP-7 server:** You have been muted for {} {}.".format(mutemin[1], mutemin[2]))
							except:
								pass
							return
						else:
							await client.send_message(message.channel, "{}, invalid member.".format(message.author.name))
							return
				elif bot_cmd == 'unmute':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split()
						if (len(tag) != 3):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["unmute"] + "```")
							return
						muted_member = get_from_mention(tag[2])
						if(muted_member != None):
							await unmute_user(tag[2])
							await client.send_message(message.channel, "{} was unmuted.".format(muted_member.name))
						else:
							await client.send_message(message.channel, "{}, invalid member.".format(message.author.name))
				elif bot_cmd == 'getmute':
					tag = message.content.split()
					if is_channel(message, ch_list()["STAFF"]):
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["getmute"] + "```")
							return
						rows = await db_mng.mute_get()
						retstr = "--------------------- \n"
						for row in rows:
							retstr += "{}: {}m\n".format(get_from_mention(str(row[0])).name, (row[1] + row[2]) - current_time_min())
						retstr += "---------------------"
						await client.send_message(message.channel, "Muted users:\n```{}```".format(retstr))
					else:
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["getmute"] + "```")
							return
						await client.send_message(message.channel, "{}, I've sent your muted time in a DM".format(message.author.name))
						rows = await db_mng.mute_get()
						for row in rows:
							if (str(row[0]) == message.author.id):
								try:
									await client.send_message(message.author, "**CTGP-7 server:** You are muted for {} minutes.".format((row[1] + row[2]) - current_time_min()))
								except:
									pass
								return
						try:
							await client.send_message(message.author, "**CTGP-7 server:** You are not muted.")
						except:
							pass
				elif bot_cmd == 'communities' or bot_cmd == 'community':
					tag = message.content.split(None)
					if (len(tag) != 2):
						await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["communities"] + "```")
						return
					await client.send_message(message.channel, COMMUNITIES_TEXT)
				elif bot_cmd == 'change_game':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split(None)
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["change_game"] + "```")
							return
						retgame = await perform_game_change()
						await client.send_message(message.channel, "{}, changed current playing game to: `{}`".format(message.author.name, retgame))
				elif bot_cmd == 'warn':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split(None, 3)
						if (len(tag) < 3):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["warn"] + "```")
							return
						warn_member = get_from_mention(tag[2])
						warnreason = ""
						if(len(tag) == 3):
							warnreason = "No reason given."
						else:
							warnreason = tag[3]
						if(warn_member != None):
							warncount = await db_mng.warn_get(warn_member.id)
							warncount += 1
							await db_mng.warn_set(warn_member.id, warncount)
							await client.send_message(message.channel, "{} got a warning. {} warnings in total.".format(warn_member.name, warncount))
							try:
								await client.send_message(warn_member, "**CTGP-7 server:** You got a warning. Toatal warnings: {}.\nReason:\n```{}```".format(warncount, warnreason))
							except:
								pass
							await punish(warn_member, warncount)
						else:
							await client.send_message(message.channel, "{}, invalid member.".format(message.author.name))
				elif bot_cmd == 'setwarn':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split(None, 4)
						if (len(tag) < 4):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["setwarn"] + "```")
							return
						warn_member = get_from_mention(tag[2])
						warnreason = ""
						try:
							warncount = int(tag[3])
						except:
							await client.send_message(message.channel, "{}, invalid amount.".format(message.author.name))
							return
						if(len(tag) == 4):
							warnreason = "No reason given."
						else:
							warnreason = tag[4]
						if(warn_member != None):
							await db_mng.warn_set(warn_member.id, warncount)
							await client.send_message(message.channel, "Set {} warnings to {}.".format(warn_member.name, warncount))
							try:
								await client.send_message(warn_member, "**CTGP-7 server:** You now have {} warnings.\nReason:\n```{}```".format(warncount, warnreason))
							except:
								pass
							await punish(warn_member, warncount)
						else:
							await client.send_message(message.channel, "{}, invalid member.".format(message.author.name))
				elif bot_cmd == 'getwarn':
					tag = message.content.split()
					if is_channel(message, ch_list()["STAFF"]):
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["getwarn"] + "```")
							return
						rows = await db_mng.warn_get_all()
						retstr = "--------------------- \n"
						for row in rows:
							retstr += "{}: {}\n".format(get_from_mention(str(row[0])).name, row[1])
						retstr += "---------------------"
						await client.send_message(message.channel, "Users with warnings:\n```{}```".format(retstr))
					else:
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["getwarn"] + "```")
							return
						await client.send_message(message.channel, "{}, I've sent your amount of warnings in a DM".format(message.author.name))
						warncount = await db_mng.warn_get(message.author.id)
						try:
							await client.send_message(message.author, "**CTGP-7 server:** You have {} warnings.".format(warncount))
						except:
							pass
				elif bot_cmd == 'release':
					if is_channel(message, ch_list()["STAFF"]): 
						tag = message.content.split()
						try:
							d = urlopen("https://api.github.com/repos/mariohackandglitch/CTGP-7updates/releases/tags/" + tag[2])
						except HTTPError as err:
							await client.send_message(message.channel, "Release tag invalid. (Example: v0.14-1)\r\nError: " + str(err.code))
						else:
							json_data = json.loads(d.read().decode("utf-8"))
							ch = client.get_channel(ch_list()["ANN"]) #announcements
							try:
								if tag[3] == "1":
									await client.send_message(ch, "@everyone\r\n" + json_data["name"] +" (" + json_data["tag_name"] + ") has been released! Here is the changelog:\r\n```" + json_data["body"] + "```")
							except IndexError:
								await client.send_message(ch, json_data["name"] +" (" + json_data["tag_name"] + ") has been released! Here is the changelog:\r\n```" + json_data["body"] + "```")
				elif bot_cmd == 'say':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split(None, 3)
						channel_id = tag[2][2:-1]
						channel_obj = client.get_channel(channel_id)
						try:
							if (channel_obj != None):
								await client.send_message(channel_obj, tag[3])
								await client.send_message(message.channel, "Message successfully sent in {}.".format(channel_obj.name))
							else:
								member_obj = get_from_mention(tag[2])
								if (member_obj != None):
									try:
										await client.send_message(member_obj, tag[3])
										await client.send_message(message.channel, "Message successfully sent to {}.".format(member_obj.name))
									except:
										await client.send_message(message.channel, "Can't send message to member (not in the server or blocked the bot).")
								else:
									await client.send_message(message.channel, "Invalid channel or member specified.")
						except IndexError:
							await client.send_message(message.channel, "Nothing to say.")
				elif bot_cmd == 'edit':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split(None, 3)
						if (len(tag) != 4):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["edit"] + "```")
							return
						for chan in SELF_BOT_SERVER.channels:
							try:
								msg = await client.get_message(chan, tag[2])
								if (msg.author == client.user):
									try:
										old_content = msg.content
										new_msg = await client.edit_message(msg, tag[3])
										await client.send_message(message.channel, "**Edited successfully:**\nOld: ```{}```New:```{}```".format(old_content, new_msg.content))
										return
									except:
										await client.send_message(message.channel, "**Couldn't edit message:** Internal error.")
										return
								else:
									await client.send_message(message.channel, "**Couldn't edit message:** Not a bot message.")
									return
							except:
								pass
						await client.send_message(message.channel, "**Couldn't edit message:** Message not found (may be too old).")
						return
				elif bot_cmd == 'restart':
					if is_channel(message, ch_list()["STAFF"]):
						await client.send_message(message.channel, "The bot is now restarting.")
						print("Manually restarting by {} ({})".format(message.author.id, message.author.name))
						running_State = False
						del db_mng
						await client.close()
						os.execv(sys.executable, ['python3'] + sys.argv)
				elif bot_cmd == 'stop':
					if is_channel(message, ch_list()["STAFF"]):
						await client.send_message(message.channel, "The bot is now stopping, see ya.")
						print("Manually stopping by {} ({})".format(message.author.id, message.author.name))
						running_State = False
						del db_mng
						await client.close()
						try:
							sys.exit(0)
						except:
							pass
				elif bot_cmd == 'ping':
					tag = message.content.split()
					if (len(tag) != 2):
						await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["ping"] + "```")
						return
					msg_time = message.timestamp
					now_dt = datetime.datetime.utcnow()
					delay_time = now_dt - msg_time
					await client.send_message(message.channel, "Pong! ({}s, {}ms)".format(delay_time.seconds, delay_time.microseconds / 1000))
				elif bot_cmd == 'membercount':
					if not (message.channel.is_private):
						await client.send_message(message.channel, "We are now {} members.".format(SELF_BOT_SERVER.member_count))
					else:
						await client.send_message(message.channel, "This command cannot be used here.")
				elif bot_cmd == 'fcregister':
					if is_channel(message, ch_list()["FRIEND"]):
						tag = message.content.split()
						if not (len(tag) == 3 or len(tag) == 4):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["fcregister"] + "```")
							return
						if (len(tag) == 4):
							await db_mng.fcregister(message, tag[2], tag[3])
						else:
							await db_mng.fcregister(message, tag[2], "true")
					else:
						await client.send_message(message.channel, "{}, friend code related commands can only be used in {}".format(message.author.name,SELF_BOT_SERVER.get_channel(ch_list()["FRIEND"]).mention))
				elif bot_cmd == 'fcquery':
					if is_channel(message, ch_list()["FRIEND"]):
						tag = message.content.split()
						if (len(tag) != 3):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["fcquery"] + "```")
							return
						await db_mng.fcquery(message)
					else:
						await client.send_message(message.channel, "{}, friend code related commands can only be used in {}".format(message.author.name,SELF_BOT_SERVER.get_channel(ch_list()["FRIEND"]).mention))
				elif bot_cmd == 'fcdelete':
					if is_channel(message, ch_list()["FRIEND"]):
						tag = message.content.split()
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["fcdelete"] + "```")
							return
						await db_mng.fcdelete(message)
					else:
						await client.send_message(message.channel, "{}, friend code related commands can only be used in {}".format(message.author.name,SELF_BOT_SERVER.get_channel(ch_list()["FRIEND"]).mention))
				elif bot_cmd == 'rules':
					await client.send_message(message.channel, "{}, I've sent you the rules in a private message.".format(message.author.name))
					await send_rules(message.author, False)
				elif bot_cmd == 'fact':
					tag = message.content.split()
					if not (len(tag) == 2 or len(tag) == 3):
						await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["fact"] + "```")
						return
					final_text = ""
					if (len(tag) == 2):
						fact_text = await db_mng.fact_get(False)
						fact_id = fact_text[random.randint(0, len(fact_text) - 1)][1]
						try:
							final_text = await parse_fact(fact_id)
						except:
							print("Error parsing: " + fact_id)
							raise
							return
					else:
						try:
							fact_text = await db_mng.fact_get_byrow(int(tag[2]))
							fact_id = fact_text[0][1]
						except:
							await client.send_message(message.channel, "Invalid id specified.")
							return
						try:
							final_text = await parse_fact(fact_id)
						except:
							print("Error parsing: " + fact_id)
							raise
							return
					await client.send_message(message.channel, "```" + final_text + "```")
				elif bot_cmd == 'listfact':
					tag = message.content.split()
					if (len(tag) != 2):
						await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["listfact"] + "```")
						return
					fact_text = await db_mng.fact_get(True)
					retstr = "```\n----------\n"
					if is_channel(message, ch_list()["STAFF"]):
						for row in fact_text:
							retstr += str(row[0]) + " - " + get_from_mention(str(row[1])).name + " - " + row[2] + "\n----------\n"
						retstr += "```"
						await client.send_message(message.channel, retstr)
					else:
						for row in fact_text:
							try:
								final_text = await parse_fact(row[2])
								text_isdyn = "(dynamic)" if await isfact_dynamic(row[2]) else "(static)"
								retstr += str(row[0]) + " - " + text_isdyn +  " - " + final_text + "\n----------\n"
							except:
								print("Error parsing: " + fact_id)
						retstr += "```"
						await client.send_message(message.channel, "{}, I sent you all the facts in a DM.".format(message.author.name))
						await client.send_message(message.author, retstr)
				elif bot_cmd == 'delfact':
					if is_channel(message, ch_list()["STAFF"]):
						tag = message.content.split()
						if (len(tag) != 3):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_help_array()["delfact"] + "```")
							return
						try:
							await db_mng.fact_delete(int(tag[2]))
						except:
							await client.send_message(message.channel, "{}, invalid id.".format(message.author.name))
							return
						await client.send_message(message.channel, "Fact {} deleted.".format(tag[2]))
					else:
						tag = message.content.split()
						if (len(tag) != 2):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["delfact"] + "```")
							return
						await db_mng.fact_deleteuser(message.author.id)
						await client.send_message(message.channel, "{}, your fact has been removed.".format(message.author.name))
				elif bot_cmd == 'addfact':
					if not is_channel(message, ch_list()["STAFF"]):
						if(await db_mng.fact_userreg(message.author.id)):
							await client.send_message(message.channel, "{}, you can only have one fact registered. Use `@RedYoshiBot delfact` to delete the existing one.".format(message.author.name))
							return
					tag = message.content.split(None, 2)
					if (len(tag) != 3):
						await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["addfact"] + "```")
						return
					try:
						dummy = await parse_fact(tag[2])
					except:
						await client.send_message(message.channel, "{}, error parsing fact, correct usage:\r\n```".format(message.author.name) + help_array()["addfact"] + "```")
						return
					await db_mng.fact_add(int(message.author.id), tag[2])
					await client.send_message(message.channel, "Fact added: \n```{}```".format(await parse_fact(tag[2])))						
				elif bot_cmd == 'help':
					if is_channel(message, ch_list()["BOTCHAT"]) or is_channel(message, ch_list()["STAFF"]) or message.channel.is_private:
						tag = message.content.split()
						if (len(tag) > 2):
							if tag[2] == "game":
								if (len(tag) == 3):
									help_str = "Here is the help for the specified command:\r\n```" + help_array()["game"] + "```"
									help_str += "Here is a list of all the available game modes:\n\n"
									for index, content in game_help_array().items():
										help_str += "`" + index + "`, "
									help_str = help_str[:-2]
									help_str += "\n\nUse `@RedYoshiBot help game (gamemode)` to get help of a specific command."
									await client.send_message(message.channel, help_str)
									if is_channel(message, ch_list()["STAFF"]):
										help_str = "\nHere is a list of all the available game staff commands:\n\n"
										for index, content in staff_game_help_array().items():
											help_str += "`" + index + "`, "
										help_str = help_str[:-2]
										help_str += "\n\nUse `@RedYoshiBot help game (gamemode)` to get help of a specific command."
										await client.send_message(message.channel, help_str)
									return
								else:
									if is_channel(message, ch_list()["STAFF"]):
										if tag[3] in staff_game_help_array():
											await client.send_message(message.channel, "Here is the help for the specified game mode:\r\n```" + staff_game_help_array()[tag[3]] + "```")
											return
									if tag[3] in game_help_array():
										await client.send_message(message.channel, "Here is the help for the specified game mode:\r\n```" + game_help_array()[tag[3]] + "```")
									else:
										await client.send_message(message.channel, "Unknown game mode, use `@RedYoshiBot help game` to get a list of all the available game modes.")
									return
							if is_channel(message, ch_list()["STAFF"]):
								if tag[2] in staff_help_array():
									await client.send_message(message.channel, "Here is the help for the specified command:\r\n```" + staff_help_array()[tag[2]] + "```")
									return
							if tag[2] in help_array():
								await client.send_message(message.channel, "Here is the help for the specified command:\r\n```" + help_array()[tag[2]] + "```")
							else:
								await client.send_message(message.channel, "Unknown command, use `@RedYoshiBot help` to get a list of all the available commands.")
						else:
							help_str = "Here is a list of all the available commands:\n\n"
							for index, content in help_array().items():
								help_str += "`" + index + "`, "
							help_str = help_str[:-2]
							help_str += "\n\nUse `@RedYoshiBot help (command)` to get help of a specific command."
							await client.send_message(message.channel, help_str)
							if is_channel(message, ch_list()["STAFF"]):
								help_str = "\nHere is a list of all the available staff commands:\n\n"
								for index, content in staff_help_array().items():
									help_str += "`" + index + "`, "
								help_str = help_str[:-2]
								help_str += "\n\nUse `@RedYoshiBot help (command)` to get help of a specific command."
								await client.send_message(message.channel, help_str)
					else:
						await client.send_message(message.channel, "`@RedYoshiBot help` can only be used in <#324672297812099093> or DM.")
						return
				elif bot_cmd == "game":
					if (is_channel(message, ch_list()["BOTCHAT"]) or is_channel(message, ch_list()["STAFF"])):
						tag = message.content.split()
						if (len(tag) < 3):
							await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + help_array()["game"] + "```")
							return
						if (tag[2] == "guessanumber"):
							if (len(tag) != 5):
								await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + game_help_array()["guessanumber"] + "```")
								return
							if (tag[3] == "easy"):
								try:
									guessed = int(tag[4])
									if not guessed in range(0, 11):
										raise ValueError("Number out of range.")
								except:
									await client.send_message(message.channel, "{}, invalid number specified. (Must be between 0 and 10)".format(message.author.name))
									return
								result = random.randint(0, 10)
								await game_numberguess(guessed, result, 0, message)
								return
							elif (tag[3] == "normal"):
								try:
									guessed = int(tag[4])
									if not guessed in range(0, 51):
										raise ValueError("Number out of range.")
								except:
									await client.send_message(message.channel, "{}, invalid number specified. (Must be between 0 and 50)".format(message.author.name))
									return
								result = random.randint(0, 50)
								await game_numberguess(guessed, result, 1, message)
								return
							elif (tag[3] == "hard"):
								try:
									guessed = int(tag[4])
									if not guessed in range(0, 100):
										raise ValueError("Number out of range.")
								except:
									await client.send_message(message.channel, "{}, invalid number specified. (Must be between 0 and 99)".format(message.author.name))
									return
								result = random.randint(0, 99)
								await game_numberguess(guessed, result, 2, message)
								return
							else:
								await client.send_message(message.channel, "{}, invalid difficulty specified. (easy/normal/hard)".format(message.author.name))
								return
						elif (tag[2] == "rps"):
							if (len(tag) != 4):
								await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + game_help_array()["rps"] + "```")
								return
							bot_ch = random.randint(0, 2)
							usr_ch = 0
							if (tag[3] == "rock" or tag[3] == "r"):
								usr_ch = 0
							elif (tag[3] == "paper" or tag[3] == "p"):
								usr_ch = 1
							elif (tag[3] == "scissors" or tag[3] == "s"):
								usr_ch = 2
							else:
								await client.send_message(message.channel, "{}, invalid choice (rock/paper/scissors).".format(message.author.name))
								return
							await game_rps(bot_ch, usr_ch, message)
							return
						elif (tag[2] == "coin"):
							if (len(tag) != 4):
								await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + game_help_array()["coin"] + "```")
								return
							bot_ch = random.randint(1, 500)
							usr_ch = 0
							if (tag[3] == "head" or tag[3] == "h"):
								usr_ch = 0
							elif (tag[3] == "tails" or tag[3] == "t" or tag[3] == "tail"):
								usr_ch = 1
							else:
								await client.send_message(message.channel, "{}, invalid choice (head/tails).".format(message.author.name))
								return
							await game_coin(bot_ch, usr_ch, message)
							return
						elif (tag[2] == "showcookie"):
							if is_channel(message, ch_list()["STAFF"]):
								if (len(tag) != 4):
									await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_game_help_array()["showcookie"] + "```")
									return
								cookie_member = get_from_mention(tag[3])
								if (cookie_member != None):
									cookie_amount = await db_mng.get_cookie(cookie_member.id)
									await client.send_message(message.channel, "{} has {} <:yoshicookie:416533826869657600> .".format(cookie_member.name, cookie_amount))
									return
								else:
									await client.send_message(message.channel, "{}, invalid member specified.".format(message.author.name))
							else:
								if (len(tag) != 3):
									await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + game_help_array()["showcookie"] + "```")
									return
								cookie_amount = await db_mng.get_cookie(message.author.id)
								await client.send_message(message.channel, "{}, you have {} <:yoshicookie:416533826869657600> .".format(message.author.name, cookie_amount))
								return
						elif (tag[2] == "top10"):
							if (len(tag) != 3):
								await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + game_help_array()["top10"] + "```")
								return
							rows = await db_mng.top_ten_cookie()
							retstr = "Users with most <:yoshicookie:416533826869657600> .\n\n---------------------------------\n"
							for row in rows:
								cookie_member = get_from_mention(str(row[0]))
								if cookie_member != None:
									retstr += "**{}** = **{}** <:yoshicookie:416533826869657600>\n---------------------------------\n".format(cookie_member.name, row[1])
								else:
									await db_mng.delete_cookie(row[0])
							await client.send_message(message.channel, "{}".format(retstr))
						elif (tag[2] == "setcookie"):
							if is_channel(message, ch_list()["STAFF"]):
								if (len(tag) != 5):
									await client.send_message(message.channel, "{}, invalid syntax, correct usage:\r\n```".format(message.author.name) + staff_game_help_array()["setcookie"] + "```")
									return
								cookie_member = get_from_mention(tag[3])
								try:
									amount = int(tag[4])
								except:
									await client.send_message(message.channel, "{}, invalid amount specified.".format(message.author.name))
									return
								if (cookie_member != None):
									await db_mng.set_cookie(cookie_member.id, amount)
									await client.send_message(message.channel, "Set {} <:yoshicookie:416533826869657600> to {} .".format(cookie_member.name, amount))
									return
								else:
									await client.send_message(message.channel, "{}, invalid user specified.".format(message.author.name))
									return
						else:
							await client.send_message(message.channel, "{}, invalid game mode specified. Use `@RedYoshiBot help game` to get a list of game modes.".format(message.author.name))
							return
						return
					else:
						await client.send_message(message.channel, "`@RedYoshiBot game` can only be used in <#324672297812099093>.")
						return
				else:
					await client.send_message(message.channel, 'Hi {}! :3\r\nTo get the list of all the available commands use `@RedYoshiBot help`'.format(message.author.name))	
			except IndexError:
				await client.send_message(message.channel, 'Hi {}! :3\r\nTo get the list of all the available commands use `@RedYoshiBot help`'.format(message.author.name))
		elif (message.channel.is_private and not message.author == client.user):
			staff_chan = SELF_BOT_SERVER.get_channel(ch_list()["STAFF"])
			await client.send_message(staff_chan, "{} sent me the following in a DM:\n```{}```".format(message.author.mention, message.content))
	except:
		if(debug_mode):
			raise
		else:
			pass
try:
	client.run(sys.argv[1])
except:
	if (running_State):
		print("Got exception at {}, restarting bot in a while.".format(str(datetime.datetime.now())))
		retryam = get_retry_times()
		if(retryam < 30):
			time.sleep(30)
		elif(retryam < 180):
			time.sleep(300)
		else:
			print("Retried too many times, exiting.")
			running_State = False
			del db_mng
			raise
		print("Retry count: {}\n".format(retryam))
		set_retry_times(retryam + 1)
		running_State = False
		del db_mng
		os.execv(sys.executable, ['python3'] + sys.argv)
	else:
		pass