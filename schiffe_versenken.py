#! /usr/bin/python3

import random
import copy


# Zufallsgenerator
RAND = random.Random()

##
## Konventionen
##

# <koor>	tuple()				Koordinaten mit x- und y-Koordinate
# <fields>	set of <koor>		Menge von Koordinaten
# <region>	list of <koor>		Liste von zusammenhängenden Koordinaten
# <regions>	list of <region>	Liste von Regionen
# <status>	{STATUS_SET}		Status eines Feldes, {'none','water','hit',...}
# <result>	tuple()				Resultat: Tupel mit (Koordinate und Status)
#
# shipdef	is a dict()			keys: name, size, num
# ship		is a <region>
# ships		is a <regions>: a list of <region>

##
## Definitionen
##

# Feldgrösse
X_SET = tuple('ABCDEFGHIJ')
Y_SET = tuple( range(1, 11))

# Mögliche Inhalte eines Mapnfeldes
LEGENDE = {
	'none': 	'.',
	'water':	'o',
	'hit':		'+',
	'sunk':		'*',
	'ship':		'#'
}
STATUS_SET = set(LEGENDE.keys())


SCHIFFE = [
	# valid keys: 'num', 'size', 'name'
	{'num': 1, 'size': 5, 'name': 'Schlachtschiff'},
	{'num': 2, 'size': 4, 'name': 'Kreuzer'},
	{'num': 3, 'size': 3, 'name': 'Zerstörer'},
	{'num': 4, 'size': 2, 'name': 'U-Boot'}
]

LEVEL = {
	'leicht': 80,
	'mittel': 50,
	'schwer': 20
}


class Player(object):

	def __init__(self, ki=False, level=50):

		# Interactive or computer player
		self.human		= not ki
		self.ki_level	= level

		# Count all my ships and the foe's ships
		self.ship_count	= 0
		self.foeships	= []

		# The maps for my own ships and the hits
		self.ships	= Map()
		self.hits	= Map()

		# memory for the last turn's result
		self.last_result = None


		## public methods

		## bomb
		## is_all_sunk
		## place_ship
		## turn
		## send_message


	def place_ship(self, shipdef):
		"""
		Randomly set a ship onto ship map and returns the ship region or
		None if no space is left.
		"""
		assert isinstance(shipdef, dict), "'shipdef' must be of type 'dict'"

		what, size = shipdef['name'], shipdef['size']
		map = self.ships

		# chose a free region with minimum size of the ship
		region = RAND.choice(map.regions(size))
		if len(region) == 0: return None

		# get a starting point for the ship
		first = RAND.randint(0,len(region)-size)

		# place the ship
		map.set_fields(region[first:first+size], 'ship')

		# place water around all ship fields
		map.set_fields(
			map.nachbarn(set(region[first:first+size])),
			'water')

		self.ship_count += 1
		return region[first:first+size]


	def cleanup_ships_map(self):
		"""
		Cleanup the ships map of all the water fields.
		"""
		map = self.ships
		map.set_fields(map.get_fields('water'), 'none')


	def save_foes_ships(self, shipdef):
		self.foeships = copy.deepcopy(shipdef)


	def is_all_sunk(self):
		"""
		Returns True when all own ships are sunk.
		"""
		if self.ship_count < 1: return True
		return False


	def turn(self):
		"""
		Play one turn and return a koordninate to bomb the foe's ships.
		Returns None when when player resigns or has no possible turn left.
		"""
		if self.human:
			if self.last_result:
				lkoor,lstat = self.last_result
				if lstat == 'sunk':
					self.hits.surround_with(lkoor, 'water')

				elif lstat == 'hit':
					self._mark_hit_ship(lkoor)

			bomb_map = self.hits
			ship_map = self.ships

			koor = None		# is a tuple()
			while True:
				line = input( "\nCaptain> " )
				token = line.rstrip("\n").split()
				token.append('')	# empty lines fail to pop()
				cmd = token.pop(0).lower()
				if re.match('^(resign|aufgeben|quit|exit|ende|stop)', cmd):
					exit(0)
				elif re.match('^(hilfe|help)', cmd):
					_hilfe()
				elif re.match('^(skip)', cmd):
					break
				elif cmd == '':
					bomb_map.print()
				elif cmd == 'ships':
					ship_map.print()
				elif cmd == 'strategie':
					t_map = self._best_moves()
					Map(t_map).print()
				elif cmd == 'tmap':
					t_map = self._rate_unknown_fields(int(token[0]))
					Map(t_map).print()
				elif cmd == 'tipp':
					t_map = self._best_moves()
#					Map(t_map).print()
					best_rate = max(t_map.values())
					best_moves= [k for k,v in t_map.items() if v == best_rate]
					print('Mmmm..vieleicht auf {}'.format(as_xy(RAND.choice(best_moves))))
				elif re.match('[a-z]\d+', cmd):
					koor = as_koor(cmd)
					if koor == None:
						print( "-- Gib ein Feld bitte mit einem Buchstaben und " \
							"einer Zahl ein.\n-- Zum Beispiel: {0}{1}"\
							.format(RAND.choice(X_SET),RAND.choice(Y_SET)) )
						continue
					elif bomb_map.get(koor) != 'none':
						feld = bomb_map.get(koor)
						print( "-- Oh, Captain!")
						print( "-- Im Feld {0} ist doch schon '{1}'".format(
							X_SET[koor[0]] + str(Y_SET[koor[1]]),
							feld
						))
						continue
					break
				else:
					print( "-- Häh? Versuche es mal mit 'hilfe'.")
			return koor

		# KI move
		target_map = self._best_moves()
		best_rate  = max(target_map.values())
		best_moves = [xy for xy,val in target_map.items() if val == best_rate]

		f =  RAND.choice(best_moves)
		print('foes turn: {} with {} points'.format(f, target_map[f]))
		return f


	def bomb(self, koor):
		"""Bomb a field on the ship map and return the result."""
		assert isinstance(koor, tuple), "Need a tuple as field coordinate."

		map = self.ships
		result = None
		status = map.get(koor)
		if status == 'ship' or status == 'hit':
			map.set(koor, 'hit')

			# check for sunken ship
			ship = map.nachbarn(
				{koor}, status={'ship', 'hit'}, include=True, recursive=True
			)
			hits = map.nachbarn(
				{koor}, status='hit', include=True, recursive=True
			)
#			print('SHIP:',ship,'HITS:',hits)

			if len(ship-hits) < 1:
				map.set_fields(ship, 'sunk')
				self.ship_count -= 1
				result =  (koor, 'sunk')
			else:
				result =  (koor, 'hit')

		elif status == 'none' or status == 'water':
			map.set(koor, 'water')
			result =  (koor, 'water')

		if result == None:
			raise Exception("sync error in protocol", (koor, status))

		self.send_message('foe_has_' + result[1], result)
		return result


	def handle_result(self, result):
		"""
		Behandle alle möglichen Ergebnisse eines Bombardments des Gegeners.
		"""
		assert isinstance(result, tuple), "<result> must be an tuple (koor,status)"

		koor,status = result
		assert status in STATUS_SET, "no valid <status> in <result>"

		map = self.hits
		if status == 'sunk':
			map.set(koor, status)
			ship = map.nachbarn( {koor}, {'hit','sunk'}, True, True)

			# mark sunken ship in my map
			map.set_fields(ship, 'sunk')

			# delete ship from the list of foe's ships
			name = None
			for s in self.foeships:
				if s['size'] == len(ship):
					s['num'] -= 1
					name = s['name']
					break
			if name == None:
				raise Exception("Not existing ship sunk", [result,ship,len(ship)])

			self.send_message('result_sunk', name, ship)

		elif status == 'hit':
			map.set(koor, status)
			self.send_message( 'result_' + status, result )

		elif status == 'water':
			map.set(koor, status)
			self.send_message( 'result_' + status, result )

		else:
			raise Exception("unable to handle result", result)

		self.last_result = result
		return


	def send_message(self, msgid, *args):
		"""
		Send message to the player (only for interactive mode).
		"""
		if not self.human: return

		name = 'Kapitän'
		if msgid == 'ships_distributed':
			print("{}! Es wurden {} Schiffe verteilt.".format(
				name, args[0]
			))

		elif msgid == 'result_sunk':
			print("{}! Wir haben ein {} versenkt!".format(
				name, args[0]
			))

		elif msgid == 'result_hit':
			print("{}! Wir haben auf Feld {} ein Schiff getroffen!".format(
				name, as_xy(args[0][0])
			))

		elif msgid == 'result_water':
			print("{}! Wasser.".format(
				name, args[0]
			))

		elif msgid == 'foe_has_sunk':
			print("{}! Unser Gegner hat unser Schiff bei {} versenkt!".format(
				name, as_xy(args[0][0])
			))

		elif msgid == 'foe_has_hit':
			print("{}! Unser Gegner hat unser Schiff bei {} getroffen!".format(
				name, as_xy(args[0][0])
			))

		elif msgid == 'foe_has_water':
			print("{}! Unser Gegner macht Wellen bei {}.".format(
				name, as_xy(args[0][0])
			))

		elif msgid == 'you_win':
			print("{}! DU HAST GEWONNEN!".format(name))

		elif msgid == 'you_lost':
			print("{}! DU HAST LEIDER VERLOREN!".format(name))

		else:
			print("UNKNOWN MESSAGE:", msgid, '>>', args)

		return


	def _mark_hit_ship(self, field):
		"""
		Markiert die Felder diagonal, da hier kein Schiff liegen darf.
		"""
		assert isinstance(field, tuple), "field must be a tuple"
		assert field[0] in range(len(X_SET)) and field[1] in range(len(Y_SET)),\
			"field must be element of (X_SET, Y_SET)"

		self.hits.set_fields(
			self.hits.nachbarn({field}, filter='odd'),
			'water'
		)

		return


	def _best_moves(self):
		"""
		Calculate the best move and return the coordinate.
		"""

		# Level (0-100), set to maximum if human request a good move
		level = self.ki_level
		if self.human: level = 100

		## we create a map with a rate for each field. the field with the
		## highest rate will be bombed...

		rate_map = dict()

		## mark some fields from the last turn
		if self.last_result != None:
			field, status = self.last_result

			# mark_hit_ship (level hard)
			if status == 'hit' and RAND.randint(0,100) <= level + LEVEL['leicht']:
				self._mark_hit_ship(field)
				#print('level:',level,'mark_hit_ship_at:',field)

			# mark_sunken_ship (level easy)
			if status == 'sunk' and RAND.randint(0,100) <= level + LEVEL['leicht']:
				self.hits.surround_with(field, 'water')
				#print('level:',level,'ship_is_sunk')

			# rate unknown fields (level intermediate)
			if RAND.randint(0,100) <= level + LEVEL['leicht']:
				# what is the maximum ship size?
				maximum = max(
					[shipdef['size'] for shipdef in self.foeships \
					if shipdef['num'] > 0]
				)
				rmap = self._rate_unknown_fields(size=maximum)
				for f in rmap.keys():
					rate_map[f] = rate_map.get(f,0) + rmap[f]
				#print('level:',level,'rate_fields_size:',maximum)

			# rate best fields to detroy a ship which was hit
			hits = self.hits.get_fields('hit')
			if len(hits) > 0 and RAND.randint(0,100) <= level + LEVEL['leicht']:
				#print('level:', level, 'destroy_ship:',hits, end=' ')

				# get one field, get the ship and find all empty neighbours
				field = hits.pop()
				fields = self.hits.nachbarn(
					self.hits.get_region(field),
					status='none'
				)

				# add rate to all empty fields
				for f in fields:
					rate_map[f] = rate_map.get(f,0) + 20

		# fall-back
		if self.last_result == None or len(rate_map) < 1:
			rate_map = {koor:1 for koor in self.hits.get_fields('none')}
			#print('LEVEL', level, 'random_field')
		#print('LEVEL', level, 'RATED MAP IS:')
		#Map(rate_map).print()

		return rate_map


	def _rate_unknown_fields(self, size=1, rate=1):
		"""
		Bewertet unbekannte Felder der Map und gibt eine <target map> zurück.
		Der Parameter 'size' gibt dabei die minimale Regionengrösse an
		(default: 1).
		Der Parameter 'rate' gibt die Basis zur Berechung der <target map>
		(default: 1).
		"""

		t_map = dict()
		regions = self.hits.regions(size)
		for region in regions:
			val_list = calc_points(region, rate)
			for k,v in val_list.items():
				t_map[k] = t_map.get(k, 0) + v

		return t_map



class Map(object):
	def __init__(self, dict=None):
		if dict == None:
			self.map = {}
		else:
			self.map = dict


	def get(self, koor):
		"""
		Returns status of a field.
		"""
		assert isinstance(koor,tuple),	"request tuple for coordinates"
		assert len(koor) == 2,			"need two coordinates"

		return self.map.get(koor, 'none')


	def get_fields(self, status=None):
		"""
		Berechnet alle Felder, die den den Status 'status' haben.
		Ist 'status' nicht gesetzt (default), werden alle Felder zurück
		gegeben, zu denen *kein* Status bekannt ist.

		Returns fields with 'status' (default: unknown status)
		"""

		# set 'status' to None if 'none' is given
		if status == 'none': status = None

		list = set()
		if status == None:
			for x in range(len(X_SET)):
				for y in range(len(Y_SET)):
					if (x,y) not in self.map: list.add((x,y))
			return list

		for k,s in self.map.items():
			if status == s: list.add(k)
		return list


	def set(self, koor, status):
		"""
		Set status of a field.
		"""
		assert isinstance(koor,tuple),	"request tuple for coordinates"
		assert len(koor) == 2,			"need two coordinates"
		assert status in STATUS_SET,	"status must be STATUS_SET element"

		self.map[koor] = status
		return


	def set_fields(self, fields, status):
		"""
		Setze die Liste der Felder auf iden Feldstatus 'status'.
		Set a list of fields to given status
		"""
		assert isinstance(fields, (set,list,tuple)), \
			"'fields' must be a list or tuple of coordinates eg. '[(1,4)]'"

		for (x,y) in fields:
			self.map[(x,y)] = status
		return


	def print(self):
		# print coodinates from X_SET (A..Z)
		print( "    ", end="" )
		for x in range(len(X_SET)):
			print( X_SET[x], end=" ")
		print()
		print( "  +", len(X_SET) * '--', sep="")

		for y in range(len(Y_SET)):
			print( "{0:2}|".format(Y_SET[y]), end="")
			for x in range(len(X_SET)):
				val = self.map.get((x,y), 'none')
				if isinstance(val, (int,float)):
					print("{0:>2}".format(int(val)), end='')
				else:
					print("{0:>2}".format(LEGENDE[val]), end='')
			print()


	def nachbarn(self, fields, status=None, include=False, recursive=False, filter=None):
		"""
		Returns all neighbour fields of the given field list.
		If 'status' is not None, only fields which status is 'status' will be
		returned.
		If 'include' is True, fields will be included into the result.
		If 'recursive' is True, nachbarn() will be called recursivly onto
		the result until all reachable fields are found.
		"""
		assert isinstance(fields, set), "'fields' must be set of coordinates"
		assert filter == None or filter != None and len(fields) == 1,\
			"filter only supported for single fields yet"
		assert filter == None or filter == 'odd' or filter == 'even',\
			"filter only supports values: None, odd, even"

		# set 'status' to None if 'none' is given
		if status != None and not isinstance(status, set):
			status = {status}

		# koor_last holds last neighbour set,
		# needed for recursive final condition
		koor_last = fields

		result_set = set()
		for koor in fields:
			(x, y) = koor
			pot_x = (x,)
			pot_y = (y,)

			# calculate all possible x and y coordinates
			# left and right
			if x-1 in range(len(X_SET)):
				pot_x = pot_x + (x-1,)
			if x+1 in range(len(X_SET)):
				pot_x = pot_x + (x+1,)

			# up and down
			if y-1 in range(len(Y_SET)):
				pot_y = pot_y + (y-1,)
			if y+1 in range(len(Y_SET)):
				pot_y = pot_y + (y+1,)

			# add all possible coordinates
			for xi in pot_x:
				for yi in pot_y:
					stat = self.get((xi,yi))
					if status == None or stat in status:
						result_set.add( (xi,yi) )

			# recursive: final condition: neighbour set has not changed
			if recursive and len(result_set - koor_last) > 0:
				result_set = self.nachbarn(
					result_set, status, recursive=True, include=True
				)

		# delete original coordinates if 'include' is not set
		if not include:
			for koor in fields:
				if koor in result_set: result_set.remove(koor)

		# apply filter to the target set
		if filter != None:
			field = fields.pop()
			# QSUM is defined as (x + y) % 2
			#   field is even: QSUM differs
			#   field is odd:  QSUM does not differ
			qsum = (field[0] + field[1]) % 2
			if filter == 'even':
				qsum = (field[0] + field[1] + 1) % 2

			# delete all coordinates which QSUM differs
			result_set = set([k for k in result_set
				if (k[0] + k[1]) % 2 == qsum
			])

		return result_set


	def surround_with(self, field, status, what=None):
		"""
		Set the surrounding fields of a region. The region is calculated from
		one fields and all neighbored fields with equal status.
		"""

		# get all neighbours of region containing 'field' and set them
		# to 'what' (defaults to field status unless set).
		self.set_fields(
			self.nachbarn(self.get_region(field), status=what),
			status
		)

		return


	def regions(self, size=1, status=None):
		"""
		Returns a list of regions of a minimal size with fields status
		(default :None).
		"""
		assert size >  0, "size must be > 0"
		assert size <= max(len(X_SET), len(Y_SET)), \
			"size must not be greater then Y_SET and X_SET"

		positions = []
		# get all vertical regions
		for x in range(len(X_SET)):
			pos = []
			for y in range(len(Y_SET)):
				if status == None:
					if (x,y) not in self.map:
						pos.append((x,y))
					else:
						if len(pos) >= size:
							positions.append(pos)
						else:
							pass
						pos = []

				else:
					if status == self.get((x,y)):
						pos.append((x,y))
					else:
						if len(pos) >= size:
							positions.append(pos)
						pos = []
			if len(pos) >= size:
				positions.append(pos); #print(x,y, 'got region', pos)

		# horizontal regions
		for y in range(len(Y_SET)):
			pos = []
			for x in range(len(X_SET)):
				if status == None:
					if (x,y) not in self.map:
						pos.append((x,y))
					else:
						if len(pos) >= size:
							positions.append(pos)
						else:
							pass
						pos = []

				else:
					if status == self.get((x,y)):
						pos.append((x,y))
					else:
						if len(pos) >= size:
							positions.append(pos)
						pos = []
			if len(pos) >= size:
				positions.append(pos)

		return positions


	def get_region(self, field, what=None):
		"""
		Returns a region containing 'field' and all fields with equal
		status surrounding it.
		If 'what' is set surrounding fields must have field status 'what'.
		"""

		# set default field status to search for
		if what == None:
			what = self.get(field)

		# get all neighbours of 'field' with equal field status
		region = self.nachbarn(
			{field}, what, include=True, recursive=True
		)

		return region


## classmethods

def _hilfe():
	print( """
ende  - Du gibst auf und beendest das Spiel.
skip  - Du verzichtest auf Deinen Zug.
ships - Schau auf Deine geheime Karte.
tipp  - Ich gebe Dir einen Tipp.
hilfe - Ich zeige Dir die Befehle, die ich verstehe.

Gibst Du mir keine Eingabe, zeige ich Dir Deine Karte.
Gibst Du mir einen Buchstaben und eine Zahl, wie A4, oder D10
schießt Du auf dieses Feld.

Was soll ich tun?
""")
	return


def calc_points(region, rate=1):
	"""
	Returns <target map> of the given region.
	Parameter 'rate' gives the base rate (default: 1).
	"""

	values = {}
	n = len(region)
	for i in range(n//2):
		val = rate*(i+1) + n
		values[region[i]] = val
		values[region[-(i+1)]] = val
	if n%2 != 0:
		i = n//2
		values[region[i]] = rate*(i+1) + n

	return values


def as_xy(koor):
	return X_SET[koor[0]] + str(Y_SET[koor[1]])


def as_koor(string):
	if len(string) < 2: return None

	xs = string[0:1].upper()
	ys = int(string[1:])
	try:
		x = X_SET.index(string[0:1].upper())
		y = Y_SET.index(int(string[1:]))
	except:
		return None

	return (x,y)


##
##  MAIN
##

if __name__ == '__main__':

	import re

	ship_count = 0
	sunk_count = 0

	# Set computer ships
	p1 = Player()
	p2 = Player(ki=True, level=99)
	for ship in SCHIFFE:
		num = ship['num']
		for n in range(num):
			p1.place_ship(ship)
			p2.place_ship(ship)

	p1.cleanup_ships_map()
	p1.send_message('ships_distributed', p1.ship_count)
	p2.save_foes_ships(SCHIFFE)

	p2.cleanup_ships_map()
	p2.send_message('ships_distributed', p2.ship_count)
	p1.save_foes_ships(SCHIFFE)

	# initialze turn counter
	turn = 0

	# create a player's list
	player = list()
	player.append(p1)
	player.append(p2)

	# save number of players
	num_player = len(player)

	# Nobody has won or loose, yet
	winner	= None
	loser	= None
	while True:
		print('turn',turn,'num_player',num_player)

		# calculate which player is active or passive
		active  = player[turn   % num_player]
		passive = player[(turn+1) % num_player]

		if active.is_all_sunk():
			loser	= active
			winner	= passive
			break
		koor = active.turn()
		if koor == None:
			# skip this turn
			pass
		else:
			# take turn and handle result
			active.handle_result(passive.bomb(koor))

		turn += 1

	# END OF GAME
	winner.send_message('you_win')
	loser.send_message('you_lost')
	exit(0)

#EOF
