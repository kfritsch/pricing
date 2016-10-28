# -*- coding: utf-8 -*-
import os, sys, traceback, copy, operator
from os.path import join, realpath, dirname, isdir

# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
SRC_PATH = dirname(realpath(__file__))
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)

# python postgres api
import psycopg2
# pyhton timezone library
import pytz
import numpy as np
from datetime import datetime, timedelta, time
from scipy import stats
# import matplotlib.pyplot as plt

# python 
from geopy.geocoders import Nominatim
import statsmodels.tsa.stattools as st

import codecs, json

import pricing_globals
from helper_functions import *
from pricing_helper_functions import *

import cProfile

# import warnings
# warnings.simplefilter("error")


# Postgresql help dict for querying
PG = pricing_globals.PG

SECS_PER_DAY = pricing_globals.SECS_PER_DAY
dow_to_string = pricing_globals.dow_to_string
# list of gasolines
GAS = pricing_globals.GAS
# start and end date of data
INIT_DATE = pricing_globals.INIT_DATE
END_DATE = pricing_globals.END_DATE

# Pricing attribute to index
pa2i = pricing_globals.pa2i

class Station(object):
	__slots__ = ('id', 'version', 'version_time', 'name', 'brand', 'address', 'geo_pos',
		'neighbors', 'pricing_mat', 'pot_reaction_pn', 'pot_reaction_poi', 'follower', 'no_reaction_pn',
		'rules_pn',
		'json_out')

	def __init__(self, station_data):
		"""
		Initializes a Station.
		Parses the data of the station in the postgresql database into an instance of Station
		@param station_data: the data of the station as it is stored in the postgres database
		@dtype station_data: tuple(pg.gas_station)
		"""
		if(station_data[0]!=None):
			self.id = station_data[0]
		else: self.id = 'NA'

		"""
		@ivar   id: The stations ID
		@dtype  id: C{str}
		"""
		if(station_data[1]!=None):
			self.version = station_data[1]
		else: self.version = 'NA'
		"""
		@ivar   version: The stations version database version count
		@dtype  version: C{str}
		"""
		if(station_data[2]!=None):
			self.version_time = station_data[2]
		else: self.version_time = 'NA'
		"""
		@ivar   version_time: The time when latest version was changed
		@dtype  version_time: C{str}
		"""
		if(station_data[3]!=None):
			self.name = replace_Umlaute(station_data[3])
		else: self.name = 'NA'
		"""
		@ivar   name: The stations name
		@dtype  name: C{str}
		"""
		if(station_data[4]!=None):
			self.brand = replace_Umlaute(station_data[4])
		else: self.brand = ''
		"""
		@ivar   brand: The stations brand
		@dtype  brand: C{str}
		"""

		if(station_data[5]!=None):
			street = replace_Umlaute(station_data[5])
		else: street = 'NA'
		if(station_data[6]!=None):
			hn = station_data[6]
		else: hn = 'NA'
		if(station_data[7]!=None):
			pc = station_data[7]
		else: pc = 'NA'
		if(station_data[8]!=None):
			place = replace_Umlaute(station_data[8])
		else: place = 'NA'

		self.address = {
		'street' : street,
		'house_number' : hn,
		'post_code' : pc,
		'place' : place
		}
		"""
		@ivar   address: The stations address
		@dtype  address: C{dict}
		"""
		self.geo_pos = {
		'lat' : station_data[10],
		'lng' : station_data[11]
		}
		"""
		@ivar   geo_pos: The stations geological position
		@dtype  geo_pos: C{dict}
		"""
		self.neighbors = None
		"""
		@ivar   neighbors: The neighbors of the station. This is based on pure
							distance and the predecessor of the competitors which
							are neighbors with a correlating behavior.
		@dtype  neighbors: C{list}
		"""
		self.pricing_mat = None
		"""
		@ivar   pricing_mat: The matrix containing all the pricing information
							(M:=(pricings x parameters))
							The parameters are listed in the pa2i dict which can
							be used for better readable indexing.
		@dtype  pricing_mat: C{numpy.array}
		"""
		self.pot_reaction_pn = None
		"""
		@ivar   pot_reaction_pn: The potential pricing causes for this station, ordered by neighbors
						It catches every pricing in time window before an own pricing that could semantic wise
						be the cause of the respective pricing. The list gets updated throughout the run.
		@dtype  pot_reaction_pn: dict(neigh_id : list(Tuple(own_idx,neigh_idx,o_num,n_num)))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings
		"""
		self.pot_reaction_poi = None
		"""
		@ivar   pot_reaction_poi: The potential pricing causes for this station, ordered by own pricing index.
						It catches every pricing in time window before an own pricing that could semantic wise
						be the cause of the respective pricing. The list gets updated throughout the run.
		@dtype  pot_reaction_poi: list(Tuple(neigh_id,neigh_idx,o_num,n_num))
						- neigh_id: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings
		"""

		self.no_reaction_pn = {}
		"""
		@ivar   no_reaction_pn: Neighbors pricings that were not reacted on with the respective last
						last own pricing done to get the difference that was created and not reacted on
		@dtype  no_reaction_pn: dict(neigh_id : list(Tuple(own_idx,neigh_idx)))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
		"""


		self.follower = None
		"""
		@ivar   follower: The price followers of this station, meaning stations
						that change its price in reaction to this station.
						Its a dict of lists of tuples: {'neigh_id':[(opi,npi),...],
														...}
						For each neighbor it stores the indeces of those pricing
						pairs where the neighbors pricing closely follows onto an
						own pricing.
							neigh_id:= the id of the respective neighbor
							opi:= the own pricing index
							npi:= neighbor pricing index
		@dtype  follower: C{dict}
		"""

		self.rules_pn = None
	
	def __str__(self):
		"""
		Generates a string for a station containing name and address

		@return s_string: the station's string
		@dtype s_string: string
		"""

		# get the address values
		st_addr = self.address['street'] + " " + self.address['house_number'] + \
		" " + self.address['post_code'] + " " + self.address['place']
		# the name is the brand if given otherwise the name itself
		name = self.brand
		if(len(name)==0):
			name = self.name
		# combine the values
		s_string = name + " " + st_addr
		return s_string

	######### Main public Functions ##########
	def get_pricing(self, d_int, rem_outlier=False):
		'''
		Uses the postgresql CURSOR object to get all the pricings from the station
		and store them in the self.pricing_mat.

		@param d_int: date interval for which to get the pricings
		@dtype d_int: tuple(int,int

		@param rem_outlier: states if outliers are to be removed
		@dtype rem_outlier: boolean
		'''

		# give the date intervals names
		from_date = d_int[0]
		to_date = d_int[1]

		# every pricing need the previous one to checked the differences made
		# so we get the previous pricing if interval starts after initial recording
		prev_price = None
		if(from_date>INIT_DATE):
			first_val_date = from_date - timedelta(1)
			pricing_globals.CURSOR.execute("SELECT * FROM gas_station_information_history"+
				" WHERE " + PG['STID'] + " AND " + PG['DATE_INT'] + " ORDER BY date DESC", (self.id, first_val_date, first_val_date))
			prev_price = pricing_globals.CURSOR.fetchone()

		# get all pricings for the station in the interval
		pricing_globals.CURSOR.execute("SELECT * FROM gas_station_information_history"+
			" WHERE " + PG['STID'] + " AND " + PG['DATE_INT'] + " ORDER BY date", (self.id, from_date, to_date))

		# assign space for the pricing data
		cnt = pricing_globals.CURSOR.rowcount
		if(cnt<=1):
			return
		self.pricing_mat = np.zeros((cnt,len(pa2i)))

		# if the interval starts at the initial we have to neglect the first pricing
		# so te previous is the first pricing
		if prev_price is None:
			prev_price = list(pricing_globals.CURSOR.fetchone())
			# count is reduced by the first one
			cnt -= 1

		p_idx = 0
		# get all pricings
		for i in range(0,cnt):
			# get the next pricing
			fol_price=list(pricing_globals.CURSOR.fetchone())
			# get the date and time
			c_date = fol_price[5].date()
			c_time = fol_price[5].time()
			# get the gas prices
			c_diesel = fol_price[4]
			c_e5 = fol_price[2]
			c_e10 = fol_price[3]
			# get all differences to the previous prices
			d_dif = (c_diesel - prev_price[4])/10
			e5_dif = (c_e5 - prev_price[2])/10
			e10_dif = (c_e10 - prev_price[3])/10
			# check if the prices were changed but not to zero
			diesel_changed = (d_dif!=0) and (c_diesel!=0)
			e5_changed = (e5_dif!=0) and (c_e5!=0)
			e10_changed = (e10_dif!=0) and (c_e10!=0)
			# if any one was changed thsi is a pricing otherwise it is just neglected
			if(diesel_changed or e5_changed or e10_changed):
				# set the id
				self.pricing_mat[i,pa2i['id']] = fol_price[0]
				# set time related values
				self.pricing_mat[i,pa2i['date']] = (c_date - INIT_DATE).days
				self.pricing_mat[i,pa2i['dow']] = int(fol_price[5].weekday())
				self.pricing_mat[i,pa2i['we']] = self.pricing_mat[i,pa2i['dow']]/5
				self.pricing_mat[i,pa2i['month']] = fol_price[5].date().month
				self.pricing_mat[i,pa2i['time']] = c_time.hour*3600 + c_time.minute*60 + c_time.second
				# compute which prices were changed
				c_changed = diesel_changed*1 + e5_changed*4 + e10_changed*16
				self.pricing_mat[i,pa2i['alt']] = c_changed

				# if the value was set to zero take the previous one for all prices
				# otherwise take the new one
				if(c_diesel==0):
					self.pricing_mat[i,pa2i['diesel']] = float(prev_price[4])/10
					self.pricing_mat[i,pa2i['d_diesel']] = 0
					fol_price[4] = prev_price[4]
				else:		
					self.pricing_mat[i,pa2i['diesel']] = float(c_diesel)/10
					self.pricing_mat[i,pa2i['d_diesel']] = d_dif

				if(c_e5==0):
					self.pricing_mat[i,pa2i['e5']] = float(prev_price[2])/10
					self.pricing_mat[i,pa2i['d_e5']] = 0
					fol_price[2] = prev_price[2]
				else:		
					self.pricing_mat[i,pa2i['e5']] = float(c_e5)/10
					self.pricing_mat[i,pa2i['d_e5']] = e5_dif

				if(c_e10==0):
					self.pricing_mat[i,pa2i['e10']] = float(prev_price[4])/10
					self.pricing_mat[i,pa2i['d_e10']] = 0
					fol_price[4] = prev_price[4]
				else:		
					self.pricing_mat[i,pa2i['e10']] = float(c_e10)/10
					self.pricing_mat[i,pa2i['d_e10']] = e10_dif

				# the new previous one is the just added pricing
				prev_price = fol_price
				p_idx+=1

		np.delete(self.pricing_mat, np.arange(p_idx,cnt), 0)

		if(rem_outlier):
			self.remove_outlier_from_pricing()

		return

	def get_neighbors(self, init_range=5, min_cnt=5, max_cnt=20):
		'''
		Compute the distance to all other stations in the STATION_DICT
		and take those located in a certain range
		or a certain amont of the closest ones if there are too many.

		@param init_range: intial range in km in which neighbors are sought
		@dtype init_range: int

		@param min_cnt: the minimum number of neighbors requested
		@dtype min_cnt: int

		@param max_cnt: the maximum number of neighbors allowed
		@dtype max_cnt: int
		'''

		# initialize the list
		self.neighbors = []
		# define own geo position
		lat1 = radians(self.geo_pos['lat'])
		lng1 = radians(self.geo_pos['lng'])
		# R is the radius of the world
		R = 6371000

		# go through all stations
		for station in pricing_globals.STATION_DICT.values():
			# get the stations geo pos
			lat2 = radians(station.geo_pos['lat'])
			lng2 = radians(station.geo_pos['lng'])
			# compute the distance of the stations
			# curvature of the earth is accounted for
			# but not hight differences
			dlng = lng2 - lng1
			dlat = lat2 - lat1
			a = (sin(dlat/2))**2 + cos(lat1) * cos(lat2) * (sin(dlng/2))**2
			c = 2 * atan2( sqrt(a), sqrt(1-a) )
			d = R * c
			d_in_km = float(d)/1000
			# add the station if it is in the initial range
			if(d_in_km<init_range):
				self.neighbors.append((station.id, d_in_km))

		# sort all neighbors at their distance: shortest first
		self.neighbors = sorted(self.neighbors, key=operator.itemgetter(1))
		# delete the own station itself
		del self.neighbors[0]
		# if there are too many stations in the range exclude all up to max_cnt
		if(len(self.neighbors)>max_cnt):
			self.neighbors = self.neighbors[0:max_cnt]
		# if there are too few stations repeat with doubled range
		if(len(self.neighbors)<min_cnt):
			self.get_neighbors(init_range*2, min_cnt, max_cnt)

		return

	def get_competition(self, d_int, lead_t=2700, n_vals=(5,5,20), one_rule=False, com_conf_div=False, hour_min=3, rule_conf=0.5, com_conf=0.03):
		'''
		Gets a stations competitors. A competitor is another station in the neighborhood
		that the stations itself acts upon in a regular rule based fashion.
		The rules are solely derived by the prisings done(!) that means there might be a rule
		which simply does not appear in the data and there might be none but the data
		suggests that there is a dependency

		The function does the following steps:
			- get own pricing
			- get own pricing regularities
			- get all neighbors
			- get their pricings
			- get theor pricing regularities
			- get all related pricing pairs (related means close in time)
			- extract rules out of those pricings
			- TODO: strip the related pricings according to the rules
			- TODO: for pricings with several possible causes try to fing the right one

		@param d_int: the date interval where we search for competition
		@dtype d_int: tuple(date,date)

		@param lead_t: the time previous to an own pricing wherein a neighbors pricing
						is considered a possible cause
		@dtype lead_t: int

		@param split_criteria: the different levels of time intervals
								where different rules might occur
		@dtype split_criteria: list(String)
		'''

		# get the own pricing
		self.get_pricing(d_int)
		if(self.pricing_mat is None):
			print('There are no pricings for this Interval. Please check the date.')
			return False

		# check for the hours of the day where a rule might apply
		drop_hist, raise_hist = self.get_pricing_hour_dist(range(len(self.pricing_mat)), 'mon-sun')
		# take only the consequtive hours with frequent pricings
		rule_hours = self._get_possible_rule_hours(drop_hist)
		# check for the days of the week where a rule might apply
		pricing_hist = self.get_pricing_dow_dist(range(len(self.pricing_mat)))
		# take only the days with frequent pricings
		rule_days = self._get_possible_rule_days(pricing_hist)

		# get all neighbors pricings
		self.get_neighbors(init_range=n_vals[0], min_cnt=n_vals[1], max_cnt=n_vals[2])
		# get the neighbors pricings
		for i in range(len(self.neighbors))[::-1]:
			(neigh_id, dif) = self.neighbors[i]
			neigh = pricing_globals.STATION_DICT[neigh_id]
			neigh.get_pricing(d_int)
			# if the neighbor has not at least a tenth of the own stations pricing
			if(neigh.pricing_mat is None or len(neigh.pricing_mat)<len(self.pricing_mat)/10):
				self.neighbors.pop(i)

		# get all related pricing pairs (related means close in time)
		self._get_neighbor_related_pricings(t_int=lead_t)

		# initilice the rule dict
		self.rules_pn = {}
		# go through neighbors
		for i in range(0,len(self.neighbors)):
			# get neighbor id
			neigh_id = self.neighbors[i][0]
			neigh = pricing_globals.STATION_DICT[neigh_id]
			self.rules_pn[neigh_id] = {}

			# check for the hours of the day where a rule might apply for the neighbor
			neigh_drop_hist, neigh_raise_hist = neigh.get_pricing_hour_dist(range(len(neigh.pricing_mat)), 'mon-sun')
			# take only the consequtive hours with frequent pricings
			neigh_rule_hours = neigh._get_possible_rule_hours(neigh_drop_hist)
			# combine the rule slots of the station pair
			comb_rule_hours = [oh and nh for (oh,nh) in zip(rule_hours, neigh_rule_hours)]

			# check for the days of the week where a rule might apply
			neigh_pricing_hist = neigh.get_pricing_dow_dist(range(len(neigh.pricing_mat)))
			# take only the days with frequent pricings
			neigh_rule_days = neigh._get_possible_rule_days(neigh_pricing_hist)
			# combine the rule slots 
			comb_rule_days = [oh and nh for (oh,nh) in zip(rule_days, neigh_rule_days)]

			# get the neighbor pricings without an own reaction
			self._get_no_reaction_pn(neigh_id)
			
			# get the reactions and ignored pricings for each gastype seperately
			gas_reactions = self._get_gas_specific_reactions(neigh_id)
			gas_ignores = self._get_gas_specific_ignores(gas_reactions, neigh_id)

			# check for and generate rules for each gas type
			for gas in range(len(GAS)):
				valid_rule_count = 0

				gas_matches = 0
				# make new data
				self.rules_pn[neigh_id][GAS[gas]] = {}
				self.rules_pn[neigh_id][GAS[gas]]["rules"] = []

				# get the differences after the reaction
				react_difs = self._get_react_difs(gas_reactions[gas], gas, neigh_id)
				# get the differences after a pricing was ignored
				ignore_difs = self._get_ignore_difs(gas_ignores[gas], gas, neigh_id)
				# if there is no correlation what so ever continue
				if(len(react_difs)==0 and len(ignore_difs)==0):
					continue

				# get the difference distribution and plot the results
				(dist_vals, react_cnts, ignore_cnts) = self._get_match_miss_dif_dists(react_difs, ignore_difs, gas)
				# get the values that support a rule
				support_cnts = react_cnts+ignore_cnts
				# get the total amount of relevant pricings
				total_cnt = np.sum(support_cnts)
				# exceptions cnt
				exceptions = 0

				gas_drop_cnt = len(gas_reactions[gas])+len(gas_ignores[gas])

				# get a copy of the possible rule slots for the gas
				gas_rule_days = comb_rule_days[:]
				gas_rule_hours = comb_rule_hours[:]

				# go through the possible rule distances starting from behind
				dist_idx = len(dist_vals)-1
				while((any(gas_rule_days) or any(gas_rule_hours)) and dist_idx>0):
					# get the distance
					dist_val = dist_vals[dist_idx]
					# get the relevant pricing pairs
					dist_reacts = [gas_reactions[gas][j] for j in range(len(gas_reactions[gas])) if react_difs[j]==dist_val]
					dist_ignores = [gas_ignores[gas][j] for j in range(len(gas_ignores[gas])) if ignore_difs[j]==dist_val]
					# get its support
					support = support_cnts[dist_idx]
					# compute the confidence value that this is a rule based reaction
					confidence = comp_conf(support,total_cnt)

					# if it is unlikely to be a rule
					if(confidence<rule_conf):
						rule_data = [dist_val,
						confidence,
						len(dist_reacts),
						len(dist_ignores),
						0,
						exceptions,
						gas_drop_cnt]

						# add those to the exception count
						exceptions += support

					# otherwise create a rule out of the distance
					else:
						valid_rule_count += 1
						# while there are possible rules left
						rule = Rule(owner=self.id,
							competitor=neigh_id,
							gas_type=GAS[gas],
							date_int=d_int,
							max_p_dist=dist_val,
							confidence = confidence,
							reactions=len(dist_reacts),
							ignores=len(dist_ignores),
							exceptions=exceptions,
							total=gas_drop_cnt)

						exceptions+=rule.get_time_windows(dist_reacts,
							dist_ignores,
							gas_rule_days,
							gas_rule_hours,
							neigh_drop_hist,
							neigh_pricing_hist,
							min_hours=hour_min,
							one_rule=one_rule)
						self.rules_pn[neigh_id][GAS[gas]]["rules"].append(rule)

						rule.check_automatism(dist_reacts)

						# get overall matches for the neighbor
						gas_matches+=rule.matches

					dist_idx-=1


				# the confidence value deciding if it is an competitor or not
				competitor_conf = (float(gas_matches)/gas_drop_cnt) if(gas_matches>0) else 0
				# decides if the confidence value is to be divided by the number of chosen rules
				if(com_conf_div and valid_rule_count>0): competitor_conf=competitor_conf/valid_rule_count

				self.rules_pn[neigh_id][GAS[gas]]["competitor"] = int(competitor_conf>com_conf)
				self.rules_pn[neigh_id][GAS[gas]]["confidence"] = competitor_conf

		return True

	def c_profile_competition(self, d_int, lead_t=2700, n_vals=(5,5,20), one_rule=False, com_conf_div=False, hour_min=3, rule_conf=0.5, com_conf=0.03):
		success = cProfile.runctx('self.get_competition(d_int, lead_t, n_vals, one_rule, com_conf_div, hour_min, rule_conf, com_conf)', globals(), locals())
		return success

	def save_json(self, file_dir):
		if(not(isdir(file_dir))): os.makedirs(file_dir)
		if(self.rules_pn is None):
			raise ValueError('No rules generated yet. Get competition first!!!')
		j=json.dumps(self.rules_pn,cls=RuleJSONEncoder,indent=4)
		f=open(join(file_dir,self.id+'.json'),"w")
		f.write(j)
		f.close()

	def get_json(self):
		if(self.rules_pn is None):
			raise ValueError('No rules generated yet. Get competition first!!!')
		j=json.dumps(self.rules_pn,cls=RuleJSONEncoder,indent=4)
		return j



	######### Main privat Functions ##########
	def _remove_outlier_from_pricing(self):
		"""
		Removes the outlier from the pricing_mat.
		It checkes if the deviation from the median is higher than 30% of the
		median itself for every gas respectively. If an outlier is deteted take
		the next last value as the current one.
		"""

		# get the medians for outlier detection
		md_diesel = np.median(self.pricing_mat[:,pa2i['diesel']])
		md_e5 = np.median(self.pricing_mat[:,pa2i['e5']])
		md_e10 = np.median(self.pricing_mat[:,pa2i['e10']])

		# since we always take the previous value if an outlier is detected
		# we have to make sure the previous index has an appropriate value.
		# that means the first value has to be appropriate 

		# for every gas check the first value
		# if it is an outlier take the next pricings that isn't

		# diesel
		if(np.abs(self.pricing_mat[0,pa2i['diesel']]-md_diesel)>0.3*md_diesel):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['diesel']]-md_diesel)>0.3*md_diesel):
				idx += 1
			self.pricing_mat[0,pa2i['diesel']] = self.pricing_mat[idx,[pa2i['diesel']]]
		# e5
		if(np.abs(self.pricing_mat[0,pa2i['e5']]-md_e5)>0.3*md_e5):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['e5']]-md_e5)>0.3*md_e5):
				idx += 1
			self.pricing_mat[0,pa2i['e5']] = self.pricing_mat[idx,[pa2i['e5']]]
		# e10
		if(np.abs(self.pricing_mat[0,pa2i['e10']]-md_e10)>0.3*md_e10):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['e10']]-md_e10)>0.3*md_e10):
				idx += 1
			self.pricing_mat[0,pa2i['e10']] = self.pricing_mat[idx,[pa2i['e10']]]

		# make sure every following index has an appropriate value
		for i in range(1,len(self.pricing_mat)):
			pricing = self.pricing_mat[i,:]
			# diesel
			if(np.abs(pricing[pa2i['diesel']]-md_diesel)>0.3*md_diesel):
				pricing[pa2i['diesel']] = self.pricing_mat[i-1,[pa2i['diesel']]]
			# e5
			if(np.abs(pricing[pa2i['e5']]-md_e5)>0.3*md_e5):
				pricing[pa2i['e5']] = self.pricing_mat[i-1,[pa2i['e5']]]
			# e10
			if(np.abs(pricing[pa2i['e10']]-md_e10)>0.3*md_e10):
				pricing[pa2i['e10']] = self.pricing_mat[i-1,[pa2i['e10']]]
		return

	# DEP:
	def _get_raise_idc(self):
		"""
		Gets all the indices of the pricing_mat where the change was a raise.
		A pricing is CURRENTLY a raise if at least one of gas prices has been raised

		@ return: the raise indices
		@ dtype: list(Int)
		"""

		raise_idc = []
		# go thrugh all pricings
		for i in range(0,len(self.pricing_mat)):
			pricing = self.pricing_mat[i,:]
			# if the pricing is a raise append it
			if(is_raise(pricing)):
				raise_idc.append(i)

		return raise_idc

	def _get_neighbor_related_pricings(self, t_int=2700):
		"""
		Checks for every own pricing if it has a possible causing pricing beneath its neighbors.
		A problem that has to be accounted for is that pricings a sometimes semantically connected,
		so there could be three consequtive price adjustments, where only one of the three gas types
		has been changed. This functions considers 4 different scenarios of causation:
			- single cause -> single reaction
			- single cause -> multiple reactions
			- multiple causes -> single reaction
			- multiple causes -> multiple reactions
		So the first thing that is done is to check for a consequtive chain after the own pricing.
		For this chain we get all possible causes and then classify the type of the relationship.

		@param t_int: the time interval in which a pricing is a cause
		@dtype t_int: int
		"""

		# initialze the dictionaries
		# self.follower = {} # dict: neigh_id -> List(Tuple(own_idx,fol_idx))
		self.pot_reaction_pn = {} # dict: neigh_id -> List(Tuple(own_idx,lead_idx,own_cnt,lead_cnt))
		self.pot_reaction_poi = {} # dict: own_idx -> List(Tuple(neigh_id,lead_idx,own_cnt,lead_cnt))

		# for each neighbor make space the dicts with neigh_id keys
		for (neigh_id, dist) in self.neighbors:
			# self.follower[neigh_id] = []
			self.pot_reaction_pn[neigh_id] = []

		# get counts
		num_neigh = len(self.neighbors)
		p_cnt = len(self.pricing_mat)

		# the function keeps track of where the last cause for each neighbor has been
		# since a following pricing can only have causes from there on
		neigh_pricing_idc = np.zeros((num_neigh, ))

		# get a just raised flag because pricing behavior after a raise might be different
		# get the index of the last raise to check if enough time has passed after a raise
		# for everything oto be normal again
		just_raised = False
		last_raise_idx = 0
		# the pricing index
		i=0

		own_set_idx = []

		while(i < p_cnt):
			# get the own pricing
			own_pricing = self.pricing_mat[i,:]

			# exclude raises from investigation
			if(not(is_raise(own_pricing))):
				# check is the pricing might be linked to others and get them
				own_set_idx, own_set_alt, own_set_time = self._get_pricings_in_span(i, t_int, chain=True)

				# # make space in the dict with pricing_idx key
				for lf in own_set_idx:
					self.pot_reaction_poi[lf] = []

				# get the index of the last own pricing that is linked to the currently investigated one
				upper_idx = own_set_idx[-1]

				# go through all neighbors
				for j in range(0,num_neigh):
					# copy the own set index they might get changed later on
					c_own_set_idx = own_set_idx[:]
					# get the neighbor
					neigh_id = self.neighbors[j][0]
					neigh = pricing_globals.STATION_DICT[neigh_id]
					# get the current index for the earliest posssible cause out of the list
					index = int(neigh_pricing_idc[j])

					# make sure we get in the while loop
					dif = -t_int-1
					# go up through neighbor pricings until the cause threshold was reached
					while(dif<-t_int and index+1<len(neigh.pricing_mat)):
						dif = get_time_dif(neigh.pricing_mat[index], own_pricing)
						# index is set to the next pricing
						index+=1
					# the last index is the one where the threshold was breached
					index-=1

					# get neighbor pricing
					neigh_pricing = neigh.pricing_mat[index]

					# up_dif is the time difference to the uppermost own pricing in the chain
					up_dif = get_time_dif(neigh_pricing, self.pricing_mat[upper_idx])


					# # low_dif is the time difference to the first own pricing in the chain
					# low_dif = get_time_dif(neigh_pricing, own_pricing)
						
					# if the neighbor pricing is at most t_int minutes after the last own pricing
					# it is a potential leader or follower
					if(up_dif<t_int):

						# # if the pricing is past the earliest own it is considered a follower
						# if(low_dif>0):)
						# 	self.follower[neigh_id].append((i,index))

						'''
						IF ITS A CAUSE
						'''
						if(up_dif<0):

							# check if there has just been a raise because in the intervall following a raise pricing is a little different
							if(just_raised):

								# if  the time interval has already passed again after an raise the justed raised flag is over
								if(get_time_dif(self.pricing_mat[i], self.pricing_mat[last_raise_idx])>t_int):
									just_raised = False


								# if the leader is before the raise dont consider it since the raise makes a cause impossible
								else:
									while(get_time_dif(neigh.pricing_mat[index],self.pricing_mat[last_raise_idx])<0 and
										index+1<len(neigh.pricing_mat) and up_dif<0):
										index += 1
										# get neighbor pricing
										neigh_pricing = neigh.pricing_mat[index]
										# up_dif is the time difference to the uppermost own pricing in the chain
										up_dif = get_time_dif(neigh_pricing, self.pricing_mat[upper_idx])
									# if the cause threshold is broken continue
									if(up_dif>=0):
										# set this as new start index for following iterations
										neigh_pricing_idc[j] = index
										continue

							# set a flag if the neighbor pricing stands alone
							# alone means there is now own one that follows in the interval and is not a raise
							# neigh_single_change = get_time_dif(neigh.pricing_mat[index+1], neigh_pricing)>=(-1)*up_dif or is_raise(neigh.pricing_mat[index+1])
							if(len(c_own_set_idx)>1):
								od = len(c_own_set_idx)-1
								while(od>=0):
									if(get_time_dif(self.pricing_mat[c_own_set_idx[od]], neigh.pricing_mat[index])<0):
										c_own_set_idx.pop(od)
									od-=1

							# get the whole set of leaders beeing all princings of this neighbor in the span
							# from the first cause being the current index to the last own pricing which is up_dif mins apart
							# since up_dif is negative we need the positive value
							neigh_set_idx, neigh_set_alt, neigh_set_time = neigh._get_pricings_in_span(index, (-1)*up_dif, chain=False, exc_raise=False)


							if(len(neigh_set_idx)==1):
								'''
								IF THERE IS ONLY ONE LEADER
								'''
								if(len(c_own_set_idx)==1):
									'''
									IF THERE IS ONLY ONE OWN
									'''
									self._check_leader_single_single(index, i, neigh_id, j)
								else:
									'''
									IF THERE ARE SEVERAL OWN
									'''
									self._check_leader_single_multi(index, c_own_set_idx,own_set_alt, neigh_id, j)
							else:
								'''
								IF THERE IS A SET OF LEADERS
								'''
								# the index has to be raised by the number of additional causes
								index+=len(neigh_set_idx)-1
								if(len(c_own_set_idx)==1):
									'''
									IF THERE IS ONLY ONE OWN
									'''
									self._check_leader_multi_single(neigh_set_idx, neigh_set_alt, neigh_set_time, c_own_set_idx[0], neigh_id, j)
								else:
									'''
									IF THERE ARE SEVERAL OWN
									'''
									self._check_leader_multi_multi2(neigh_set_idx, neigh_set_alt, neigh_set_time, c_own_set_idx[:], own_set_alt, neigh_id, j, t_int)
						# the potential cause has been treated and is not relevant any further
						index+=1
					# set this as new start index for following iterations
					neigh_pricing_idc[j] = index	

				# if there was a chain of own pricings increase the index by the amount of additional pricings
				i+=len(own_set_idx)-1

			# if it is a raise do some other investigation
			else:

				"""
				TODO

				Analyse raise data

				"""
				# set the just raised flag and value
				just_raised = True
				last_raise_idx = i
			# increase the own index that has been just treated 
			i+=1

	def _get_pricings_in_span(self, idx, t_span, chain=False, exc_raise=True):
		"""
		Get a list of all pricings in a time interval set by a pricing and a time span

		@param idx: the index of the first pricing in the list
		@dytpe idx: int

		@param t_span: the span in which pricings are included
		@dytpe t_span: int

		@return linked_idx: the index of the pricings in the span
		@dtype list(Int)

		@return linked_alt: the chnaged values of those pricings
		@dtype list(Int)

		@return linked_times: the timestmaps of those values
		@dtype list(Datetime)
		"""

		# save the first index for reference
		start_idx = idx

		# create index alt and time lists with the first pricing
		linked_idx = [idx]
		linked_alt = [self.pricing_mat[idx,pa2i['alt']]]
		linked_times = [str(get_time(self.pricing_mat[idx,pa2i['time']], False))]

		# while we are in the span at not at the end of pricings procede
		dif = 0
		while(dif<t_span and idx<(len(self.pricing_mat)-1)):
			# get next pricing and append if in span and not a raise
			idx += 1
			dif = get_time_dif(self.pricing_mat[idx], self.pricing_mat[start_idx])
			if(dif<t_span):
				if(exc_raise and is_raise(self.pricing_mat[idx])):
					break
				if(chain):
					start_idx = idx
				linked_idx.append(idx)
				linked_alt.append(self.pricing_mat[idx,pa2i['alt']])
				linked_times.append(str(get_time(self.pricing_mat[idx,pa2i['time']], False)))
			# as soon as we break the span or reach a raise stop
			else:
				break
		# return the created lists
		return linked_idx, linked_alt, linked_times

	def _check_leader_single_single(self, leader_idx, own_idx, neigh_id, j):
		"""
		Check if the single leader is the cause for a single own pricing.
		The only relevant feature is the appropriate adjustment of the prices.
		In a reaction it only makes sense to change something that has been changed itself
		and the changed value of the reaction should be the changed value of the cause at most

		@param leader_idx: the index of the potentially causing pricing
		@dytpe leader_idx: int

		@param own_idx: the index of the potentially causéd pricing
		@dytpe own_idx: int

		@param neigh_id: the identifier of the station of the leading pricing
		@dytpe neigh_id: string

		@param j: the number of the neighbor in the list
		@dytpe j: int
		"""

		# get neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# get the relevant pricings
		own_pricing = self.pricing_mat[own_idx]
		neigh_pricing = neigh.pricing_mat[leader_idx]

		# if the changes made in the pricings allow for a causal relaionship
		if(proper_drop_dif(neigh_pricing, own_pricing)):
			self.pot_reaction_pn[neigh_id].append((own_idx,leader_idx,0,0))
			self.pot_reaction_poi[own_idx].append((neigh_id, leader_idx,0,0))
			return True
		else:
			return False

	def _check_leader_single_multi(self, leader_idx, own_set_idx, own_set_alt, neigh_id, j):
		"""
		There are several own consecutive pricings but just one leader. Check which one or which subsection, was caused by this pricing.
		We take the last one that is still a proper adjustment considering the sum of all adjustments up to this point although it could
		have been the earlier one as well. This is because if we take the former one that will make for a higher difference after
		the pricing in comparison. This stat however will be th crucial one in the actual rule building, so we don't want exceptions
		there if there is a possible other reason. 
		It could be some of those pricings split up so we have to check for possibly 3 prcings all checking only one gas.

		@param leader_idx: the index of the potentially causing pricing
		@dytpe leader_idx: int

		@param own_set_idx: all the own pricings possibly caused by the leading pricing
		@dytpe own_set_idx: list(Int)

		@param own_set_alt: all the own pricings alt values
		@dytpe own_set_alt: list(Int)

		@param neigh_id: the identifier of the station of the leading pricing
		@dytpe neigh_id: string

		@param j: the number of the neighbor in the list
		@dytpe j: int

		@return take: the list of reactions on the leader
		@dtype take: list(Int)
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		neigh_pricing = neigh.pricing_mat[leader_idx]

		take = []

		# create a string with all relevant information except the list of reactions
		n_str = ('\t' + str(j) + '\t' + str(leader_idx) + '\t' + str(neigh_pricing[pa2i['alt']]) + '\t' + str(get_time(neigh_pricing[pa2i['time']], False)) + "\t -> \t ")	

		osi = 0
		# first we have to exclude all where the leader is after the own pricing
		while(osi<len(own_set_idx) and get_time_dif(neigh_pricing, self.pricing_mat[own_set_idx[osi]])>0):
			osi+=1
		if(osi==len(own_set_idx)):
			return take

		# crate an artificial pricing to add up the changed value. A proper reactive pricing still needs
		# to be lower or equal to its cause 
		art_pricing = np.zeros((len(pa2i), ))
		art_pricing[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[osi],pa2i['d_diesel']]
		art_pricing[pa2i['d_e5']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e5']]
		art_pricing[pa2i['d_e10']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e10']]

		# check for the first if its is a proper reaction
		prop_dist = proper_drop_dif(neigh_pricing, art_pricing)
		# as long as there are more possible reactions left and the last one was still proper
		while(osi+1<len(own_set_idx) and prop_dist):
			# add the next pricing to the artificial
			osi+=1
			art_pricing[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[osi],pa2i['d_diesel']]
			art_pricing[pa2i['d_e5']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e5']]
			art_pricing[pa2i['d_e10']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e10']]
			# check its validity
			prop_dist = proper_drop_dif(neigh_pricing, art_pricing)
			# if this not proper decrease the index to the last proper one
			if(not(prop_dist)):
				osi-=1
				prop_dist = True
				break

		# if there has been one proper one
		if(prop_dist):
			# if the last proper pricing is the first one or if it changes all of the leaders gases add it
			if(osi==0 or own_set_alt[osi]==neigh_pricing[pa2i['alt']]):
				take = [own_set_idx[osi]]
				self.pot_reaction_pn[neigh_id].append((own_set_idx[osi],leader_idx,0,0))
				self.pot_reaction_poi[own_set_idx[osi]].append((neigh_id, leader_idx,0,0))
				# add the reaction to the output string
				n_str += str(take)
			# else check if it could be combined with previous ones
			else:
				# get the single changed values in the leader
				changes = [val for (alt,val) in zip(neigh.pricing_mat[leader_idx,[7,9,11]],[1,4,16]) if alt!=0]
				# go back through own pricings 
				while(osi>0 and len(changes)>0):
					# get the single changed values in the own pricing
					own_changes = [val for (alt,val) in zip(self.pricing_mat[own_set_idx[osi],[7,9,11]],[1,4,16]) if alt!=0]
					# remove all own values from the leader
					for val in own_changes:
						if(val in changes):
							changes.remove(val)
						# if they can not be removed the change is to much and can not be combined
						else:
							break
					# add the index
					take.append(own_set_idx[osi])
					osi-=1
				self.pot_reaction_pn[neigh_id].append((take[-1],leader_idx,len(take)-1,0))
				self.pot_reaction_poi[take[-1]].append((neigh_id, leader_idx,len(take)-1,0))
				# add the list of reactions to the output string
				n_str += str(take)

		else:
			return take

	def _check_leader_multi_single(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_idx, neigh_id, j):
		"""
		There are several leading pricings but just one reaction. Check which one was caused the possible cause for the reaction.
		The cause is the last proper leader, because if it was the reaction on a previous pricing, there would have had
		to be an reaction on the following ones as well. If the last one is no proper cause then there are actually two scenarios.
		Either the leader didn't change anything that the own pricing changed, which makes it possible for a previous one to be the cause.
		Or the leader did change at least one same gas. Then it must be part of the cause if there is one coming from this neighbor at all.
		Then we need to check if it could be combined with previous ones to form a proper cause.

		@param neigh_set_idx: the indices of the potentially causing pricings
		@dytpe neigh_set_idx: list(Int)

		@param neigh_set_alt: the alt values of the potentially causing pricings
		@dytpe neigh_set_alt: list(Int)

		@param neigh_set_time: the time strings of the potentially causing pricings
		@dytpe neigh_set_time: list(Int)

		@param own_idx: the own pricing index
		@dytpe own_idx: int

		@param neigh_id: the identifier of the station of the leading pricing
		@dytpe neigh_id: string

		@param j: the number of the neighbor in the list
		@dytpe j: int

		@return take: the list of causing pricings found
		@dtype take: list(Int)
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		#get the own pricing
		own_pricing = self.pricing_mat[own_idx]
		n_idx = len(neigh_set_idx)-1

		take = []

		share_change = False
		# get own changes
		own_changes = [alt<0 for alt in self.pricing_mat[own_idx,[7,9,11]]]
		# go back through the possible causes until we either find a possible cause or a pricing
		# that changed one of the gases changed by the own pricing while neglecting all pricings
		# where there were no related gas changes
		while(n_idx>=0 and not(share_change)):
			if(proper_drop_dif(neigh.pricing_mat[neigh_set_idx[n_idx]], own_pricing)):
				self.pot_reaction_pn[neigh_id].append((own_idx,neigh_set_idx[n_idx],0,0))
				self.pot_reaction_poi[own_idx].append((neigh_id,neigh_set_idx[n_idx],0,0))

				take.append(neigh_set_idx[n_idx])
				return take
			else:
				# get neigh changes
				changes = [alt<0 for alt in neigh.pricing_mat[neigh_set_idx[n_idx],[7,9,11]]]
				# check for shared changes
				for i in range(len(GAS)):
					if(own_changes[i] and changes[i]):
						share_change = True
						break

			n_idx-=1
		# if none was related to the own pricing
		if(n_idx < 0):
			return take

		# else we reached a related pricing which is not proper but is related to the own pricing
		# check if it can be combined with previous one to get a proper one
		else:
			# reset index to the last proper
			n_idx+=1
			take = [neigh_set_idx[n_idx]]
			# crate an artificial pricing to add up the changed value from the leaders. A proper reactive pricing still needs
			# to be lower or equal to its cause

			art_pricing = np.zeros((len(pa2i), ))
			art_pricing[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[n_idx],pa2i['d_diesel']]
			art_pricing[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[n_idx],pa2i['d_e5']]
			art_pricing[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[n_idx],pa2i['d_e10']]
			# go back while combining was possible

			#go to the next idx
			n_idx -= 1
			comb = True
			while(n_idx>=0 and comb):
				# combine each gas_change if the artificial gas_change is still zero for this gas
				for d_gas in ['d_diesel', 'd_e5', 'd_e10']:
					# get the change index
					d_idx = pa2i[d_gas]
					if(art_pricing[d_idx]==0):
						art_pricing[d_idx] += neigh.pricing_mat[neigh_set_idx[n_idx],d_idx]
					# otherwise combining is not possible
					else:
						comb = False
						break
				if(comb and proper_drop_dif(art_pricing, own_pricing)):
					take.append(neigh_set_idx[n_idx])
					self.pot_reaction_pn[neigh_id].append((own_idx,neigh_set_idx[n_idx],0,len(take)-1))
					self.pot_reaction_poi[own_idx].append((neigh_id,neigh_set_idx[n_idx],0,len(take)-1))

					return take
				n_idx -= 1

			# # if there was no possible combination
			take.pop()
			return take

	def _check_leader_multi_multi2(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, own_set_alt, neigh_id, j, t_int):
		"""
		There are several leading pricings as well as several own reactions. Check which leader is the possible cause for which
		own reaction:
			- Start with the last reaction
			- Go back through the leaders and collect those in the right time frame
			- Do the multi_single check
			- remove the match if there is one else only remove the reaction
			- repeat until each reaction is treated
		If none was found the multi_single condition, that it can not be a earlier pricing because then there would have had to be
		another reaction on the other later one, still hold although there is a potential later one because the later was already
		proven to be no potential reaction.
		Removing the cause for the following analysis has the same intention as in the single multi condition. The removed cause could
		have been the cause for a previous one as well but in regard to further analysis it is saver to assume the later one to be the
		real reaction at first.
		TODO: look a differences to the other approach

		@param neigh_set_idx: the indices of the potentially causing pricings
		@dytpe neigh_set_idx: list(Int)

		@param neigh_set_alt: the alt values of the potentially causing pricings
		@dytpe neigh_set_alt: list(Int)

		@param neigh_set_time: the time strings of the potentially causing pricings
		@dytpe neigh_set_time: list(Int)

		@param own_set_idx: the list of own reactions
		@dytpe own_set_idx: list(Int)

		@param own_set_alt: the list of the alt values of the own reactions
		@dytpe own_set_alt: list(Int)

		@param neigh_id: the identifier of the station of the leading pricing
		@dytpe neigh_id: string

		@param j: the number of the neighbor in the list
		@dytpe j: int
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# as long as there are own pricings left
		while(len(own_set_idx)>0):
			# take the last and remove it
			osi = own_set_idx.pop()
			own_pricing = self.pricing_mat[osi]
			# the neighbor start index for each reaction is always the last
			nsi = len(neigh_set_idx)-1

			# get tmep lists
			cur_n_set = []
			cur_n_time = []
			cur_n_alt = []
			# get potential leaders as long as there are potential leaders
			while(nsi>=0):
				# get the time difference
				dif = get_time_dif(own_pricing, neigh.pricing_mat[neigh_set_idx[nsi]])
				# if the own pricing is at most the threshold after the leader
				if(dif<t_int):
					# if the pricing is after the leader at all			
					if(dif>=0):
						cur_n_set.append(neigh_set_idx[nsi])
						cur_n_alt.append(neigh_set_alt[nsi])
						cur_n_time.append(neigh_set_time[nsi])
					# if it is before the leader
					else:
						neigh_set_idx.pop(nsi)
						neigh_set_alt.pop(nsi)
						neigh_set_time.pop(nsi)

					nsi-=1
				else:
					break
			# if there was one leader found, do the single single check
			if(len(cur_n_set)==1):
				rem_n = self._check_leader_single_single(cur_n_set[0], osi, neigh_id, j)
				if(rem_n):
					rem_idx = neigh_set_idx.index(cur_n_set[0])
					neigh_set_idx.pop(rem_idx)
					neigh_set_alt.pop(rem_idx)
					neigh_set_time.pop(rem_idx)

			# if there were several leader found, do the multi single check
			elif(len(cur_n_set)>1):
				to_rem = self._check_leader_multi_single(cur_n_set, cur_n_alt, cur_n_alt, osi, neigh_id, j)
				#TODO: kreiere aus den Auslösern ein einzelnes Pricing und überprüfe ob von allen potenteill nachfolgenden
				#Änderungen noch welche zusammengenommen werden können
				for r_nsi in to_rem:
					rem_idx = neigh_set_idx.index(r_nsi)
					neigh_set_idx.pop(rem_idx)
					neigh_set_alt.pop(rem_idx)
					neigh_set_time.pop(rem_idx)
			# if there is no possible leader for this reaction
			else:
				n_str = ('\t' + str(j) + '\t' + str(cur_n_set) + '\t' + str(cur_n_alt) + '\t' + str(cur_n_time) + "\t -> \t " + str([osi]))
		
	def _get_no_reaction_pn(self, neigh_id):
		"""
		For all the neighbors pricings check if it is a raise or a leader. If not there was no reaction
		so we add it to the list

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return ignores: a list of those pricings without reaction
		@dtype ignores: list(Tuple(own_idx,neigh_idx))
						- own_idx: the own pricing index just before the neighbors pricing
						- neigh_idx: the neighbor pricing index
		"""

				# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# prepare the list
		ignores = []

		reactions = self.pot_reaction_pn[neigh_id]
		# index for the list of neighbor pricings 
		n_idx = 0
		# index for the leader list
		r_idx = 0
		# index for next potential onw pricing before a ignored neighbor pricing
		own_idx = 0		
		# go until end of one list reached
		while(n_idx < len(neigh.pricing_mat) and r_idx < len(reactions)):
			# if the neighbor pricing is a raise neglect it
			if(is_raise(neigh.pricing_mat[n_idx])):
				n_idx+=1
			else:
				# if the neighbor is a leader increase both indices
				# the data index has to be increased according to the number of leaders in this leader set
				if(n_idx == reactions[r_idx][1]):
					own_idx = reactions[r_idx][0]
					n_idx += 1+reactions[r_idx][3]
					r_idx += 1		
				# if the data neigh index is below the next leader index add it to non matches and increase only the data index
				elif(n_idx < reactions[r_idx][1]):

					# go back through the own pricings until the pricing is directly before the neighbors pricing (time related)
					# we want this pricing to know the price difference generated by the neighbor
					# be carefull not to go in the negativ index area 
					while(own_idx<len(self.pricing_mat) and get_time_dif(neigh.pricing_mat[n_idx],self.pricing_mat[own_idx])>=0):
						own_idx+=1
					# stop if last index was reached
					if(own_idx == len(self.pricing_mat)):
						break
					# go back to last index before neigh
					own_idx -= 1
					# TODO: check if in opening hours:
					# CURRENTLY: check if own index was a raise
					# add the pair of index if it is no raise
					if(get_time_dif(self.pricing_mat[own_idx+1],neigh.pricing_mat[n_idx])>2700
						and not(is_raise(self.pricing_mat[own_idx]))):
						ignores.append((own_idx,n_idx))

					n_idx += 1

				# if the leader index is lower go to the next leader
				else:
					r_idx += 1

		# if there are still neighbor pricings left but no leader the rest are non matches
		while(n_idx< len(neigh.pricing_mat)):
			# if the neighbor pricing is a raise neglect it
			if(is_raise(neigh.pricing_mat[n_idx])):
				n_idx+=1
			else:
				# go up through own pricing until we are above the neighbor (time related)
				while(own_idx<len(self.pricing_mat) and get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[n_idx])<=0):
					own_idx+=1
					# if we reach the end break 
				if(own_idx == len(self.pricing_mat)):
					break
				# go one back so we have the last own index before the neighbor pricing
				own_idx-=1
				if(get_time_dif(self.pricing_mat[own_idx+1],neigh.pricing_mat[n_idx])>2700
					and not(is_raise(self.pricing_mat[own_idx]))):
					ignores.append((own_idx,n_idx))

				n_idx += 1

		self.no_reaction_pn[neigh_id]=ignores

	def _get_gas_specific_ignores(self, gas_reactions, neigh_id):
		"""
		For a specific neighbor and each gas respectively get all neighbor pricings that were not reacted on.
		For all the neighbors pricings check if it is a raise or a leader. If not there was no reaction
		so we add it to the list

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@param gas_reactions: the reactions for every gas type
		@dtype gas_reactions: list(list(tuple(own_idx,neigh_idx))) 

		@return gas_ignores: the pricing pairs where the station ignored a gas change fro the neighbor
		@dtype gas_ignores: list(list(tuple(own_idx,neigh_idx))) 
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# prepare the list
		gas_ignores = [[],[],[]]

		for gas in range(len(GAS)):
			gas_specific_reactions = gas_reactions[gas]
			# index for the list of neighbor pricings 
			n_idx = 0
			# index for the leader list
			r_idx = 0
			# index for next potential onw pricing before a ignored neighbor pricing
			own_idx = 0		
			# go until end of one list reached
			while(n_idx < len(neigh.pricing_mat) and r_idx < len(gas_specific_reactions)):
				# if the neighbor pricing is a raise neglect it
				if(is_raise(neigh.pricing_mat[n_idx])):
					n_idx+=1
				elif(neigh.pricing_mat[n_idx,pa2i[GAS[gas]]+1]==0):
					n_idx+=1
				else:
					# if the neighbor is a leader increase both indices
					# the data index has to be increased according to the number of leaders in this leader set
					if(n_idx == gas_specific_reactions[r_idx][1]):
						own_idx = gas_specific_reactions[r_idx][0]
						n_idx += 1
						r_idx += 1				
					# if the data neigh index is below the next leader index add it to non matches and increase only the data index
					elif(n_idx < gas_specific_reactions[r_idx][1]):

						# go back through the own pricings until the pricing is directly before the neighbors pricing (time related)
						# we want this pricing to know the price difference generated by the neighbor
						# be carefull not to go in the negativ index area 
						while(own_idx<len(self.pricing_mat) and get_time_dif(neigh.pricing_mat[n_idx],self.pricing_mat[own_idx])>=0):
							own_idx+=1
						# stop if last index was reached
						if(own_idx == len(self.pricing_mat)):
							break
						# go back to last index before neigh
						add_idx = own_idx-1
						while(own_idx<len(self.pricing_mat) and self.pricing_mat[own_idx,pa2i[GAS[gas]]+1]==0):
							own_idx+=1
						if(own_idx == len(self.pricing_mat)):
							break
						# TODO: check if in opening hours:
						# CURRENTLY: check if own index was a raise
						# add the pair of index if it is no raise
						if(get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[n_idx])>2700
							and not(is_raise(self.pricing_mat[add_idx]))):
							gas_ignores[gas].append((add_idx,n_idx))

						n_idx += 1

					# if the leader index is lower go to the next leader
					else:
						r_idx += 1

			# go through all neighbor pricings left and add them as non matches
			while(n_idx< len(neigh.pricing_mat)):
				# if the neighbor pricing is a raise neglect it
				if(is_raise(neigh.pricing_mat[n_idx])):
					n_idx+=1
				elif(neigh.pricing_mat[n_idx,pa2i[GAS[gas]]+1]==0):
					n_idx+=1
				else:
					# go up through own pricing until we are above the neighbor (time related)
					while(own_idx<len(self.pricing_mat) and get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[n_idx])<=0):
						own_idx+=1
						# if we reach the end break 
					if(own_idx == len(self.pricing_mat)):
						break
					# go one back so we have the last own index before the neighbor pricing
					add_idx = own_idx-1
					while(own_idx<len(self.pricing_mat) and self.pricing_mat[own_idx,pa2i[GAS[gas]]+1]==0):
						own_idx+=1
					if(own_idx == len(self.pricing_mat)):
						break
					if(get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[n_idx])>2700
						and not(is_raise(self.pricing_mat[add_idx]))):
						gas_ignores[gas].append((add_idx,n_idx))

					n_idx += 1

		return gas_ignores

	def _get_react_difs(self, gas_reactions, gas, neigh_id):
		"""
		Gets a difference matrix for pricings and their possible causes.
		The matrix contains all prices after the own reaction on a possibly causing pricing

		@param gas_reactions: the list of the all reactions
		@dtype gas_reactions: list(Tuple(own_idx,neigh_idx))
							- own_idx: the own pricing index
							- neigh_idx: the neighbor pricing index

		@param gas: the gas type identifier
		@dtype gas: int

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return price_dif: the difference list for all the reactions
		@dtype price_dif: numpy.array
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# intialize the matrix
		price_dif = np.zeros((len(gas_reactions), ))

		gas_idx = pa2i[GAS[gas]]

		#go through all gas_reactions
		for i in range(len(gas_reactions)):
			(o, l) = gas_reactions[i]
			# get the price after the change
			price_dif[i] = int(self.pricing_mat[o,gas_idx]-neigh.pricing_mat[l,gas_idx])

		return price_dif

	def _get_ignore_difs(self, gas_ignores, gas, neigh_id):
		"""
		Gets a difference matrix for all nieghbor pricings without reaction for a gas type.

		@param gas_ignores: the list of the ignored pricings for one gas type
		@dtype gas_ignores: list(Tuple(own_idx,neigh_idx))
							- own_idx: the own pricing index
							- neigh_idx: the neighbor pricing index

		@param gas: the gas type identifier
		@dtype gas: int

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return price_dif: the difference list for all the reactions
		@dtype price_dif: numpy.array
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# intialize the matrix
		price_dif = np.zeros((len(gas_ignores), ))

		gas_idx = pa2i[GAS[gas]]

		#go through all gas_reactions
		for i in range(len(gas_ignores)):
			(o, l) = gas_ignores[i]
			# get the price after the change
			price_dif[i] = int(self.pricing_mat[o,gas_idx]-neigh.pricing_mat[l,gas_idx])

		return price_dif	

	def _get_gas_specific_reactions(self, neigh_id):
		"""
		Generates a list with pricing pairs where the neighboring pricing caused the own
		one with regard to this gas only. Just go through all reactions for this neighbor
		and check which gas was changed where(or if at all) and add the indices.

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return gas_specific_reactions: the list of lists
		@dtype gas_specific_reactions: list(list(tuple(own_idx,neigh_idx)))

		"""

		# get the neighbor station
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# get the pot_reactions for this station
		pot_reaction = self.pot_reaction_pn[neigh_id]

		# mae space for gas specific reactions
		gas_specific_reactions = [[],[],[]]
		# go through all reactions
		for (o_idx, n_idx, o_num, n_num) in pot_reaction:
			# there shoulf be only several pricings from one side maximum
			assert(not(o_num and n_num)), 'Several own and neighbor pricings'
			# check if the own station has only one pricing
			if(o_num==0):
				# get this pricing
				o_p = self.pricing_mat[o_idx]
				# check if the neighbor station has only one pricing
				if(n_num==0):
					# go through all gases
					for gas in range(len(GAS)):
						# get the gas changed idx
						gas_alt = pa2i[GAS[gas]]+1
						# if the own station changed the gas the cause has to have done it as well
						if(o_p[gas_alt]<0):
							gas_specific_reactions[gas].append((o_idx,n_idx))
				else:
					# go through all gases
					for gas in range(len(GAS)):
						# get the gas changed idx
						gas_alt = pa2i[GAS[gas]]+1
						# if the own station changed the gas
						if(o_p[gas_alt]<0):
							# go through all neighbors pricings
							c_n = 0
							while(c_n<=n_num):
								n_p = neigh.pricing_mat[n_idx+c_n]
								# if it changed the gas add it and stop
								if(n_p[gas_alt]<0):
									gas_specific_reactions[gas].append((o_idx,n_idx+c_n))
									break
								c_n+=1
			else:
				# go through all own pricings
				c_o = 0
				while(c_o<=o_num):
					o_p = self.pricing_mat[o_idx+c_o]
					# go through all gases
					for gas in range(len(GAS)):
						# get the gas changed idx
						gas_alt = pa2i[GAS[gas]]+1
						# if this own pricing changed the gas the cause has to have done it as well
						if(o_p[gas_alt]<0):
							gas_specific_reactions[gas].append((o_idx+c_o,n_idx))
							break
					c_o+=1

		return gas_specific_reactions

	def _get_possible_rule_hours(self, drop_dist):
		"""
		We want a day interval where pricings occur regularly.
		For this we compute the mean of the times where pricings occur at all.
		Regularly means then it should have at least a tenth of this value pricings

		Furhtermore we want to exclude singular irregularities.
		So we look at the three next values on each side take make a final decision.

		We only consider drops because raises occur at the borders of opening hours and
		might add a hour where there is no rule possible

		@param drop_dist: The distribution of price drops of this station over the hours of a day
		@dtype drop_dist: numpy.array

		@return rule_hours: A boolean for each hour stating if there could be a rule or not
		@dtype rule_hours: list(Boolean)
		"""
		drops_occure = drop_dist[np.where(drop_dist>0)]
		mean_drop_per_hour = np.sum(drops_occure)/len(drops_occure)
		threshold = int((mean_drop_per_hour/10)+1)
		# get those times where pricings occur regularly as candidaes for rules
		rule_hours = [drop_cnt>=threshold for drop_cnt in drop_dist]

		# create a list with enlarged ends
		tmp_rule_hours = rule_hours[-3:]+rule_hours[:]+rule_hours[0:3]
		# go through the rule_hours
		for i in range(3,len(rule_hours)+3):
			# get the sum of the top and the bottom
			bot = sum(tmp_rule_hours[i-3:i])
			top = sum(tmp_rule_hours[i+1:i+1+3])
			# if the the hour itself was candidate
			if(tmp_rule_hours[i]):
				# we consider the maximum the two sides
				rule_hours[i-3] = max(bot,top)>=2
			else:
				# otherwise the minimum
				rule_hours[i-3] = min(bot,top)>=2

		# fill in holes
		tmp_rule_hours = [rule_hours[-1]] + rule_hours + [rule_hours[0]]
		for i in range(1, len(rule_hours)+1):
			if(not(rule_hours[i-1]) and (tmp_rule_hours[i-1] and tmp_rule_hours[i+1])):
				rule_hours[i-1] = True

		return rule_hours

	def _get_possible_rule_days(self, pricing_dist):
		"""
		We want a hour interval where pricings occur regularly.
		For this we compute the mean of the times where pricings occur at all.
		Regularly means then it should have at least a tenth of this value pricings

		@param pricing_dist: The distribution of pricings of this station over the days in a week
		@dtype pricing_dist: numpy.array

		@return rule_houres: A boolean for each day stating if there could be a rule or not
		@dtype rule_houres: list(Boolean)
		"""
		pricings_occure = pricing_dist[np.where(pricing_dist>0)]
		mean_drop_per_day = np.sum(pricings_occure)/len(pricings_occure)
		threshold = int((mean_drop_per_day/10)+1)
		# get those times where pricings occur regularly as candidaes for rules
		rule_days = [pricing_cnt>=threshold for pricing_cnt in pricing_dist]
		return rule_days

	def get_pricing_hour_dist(self, pricings, title):
		"""
		For all indexed pricings get the hour distribution.

		@param pricings: the pricing for which a distribution needs to be done
		@dtype pricings: list(Int)

		@return hist: the distribution values
		@dtype date_int: list(int)
		"""	

		pricing_hist = np.zeros((24, ))
		raise_hist = np.zeros((24, ))
		for p_idx in pricings:
			own_p = self.pricing_mat[p_idx]
			p_time = int(own_p[pa2i['time']]/3600)
			if(is_raise(own_p)):
				raise_hist[p_time]+=1
			else:
				pricing_hist[p_time]+=1

		return pricing_hist, raise_hist

	def get_pricing_dow_dist(self, pricings):
		"""
		For all indexed pricings get a day of the week distribution.

		@param pricings: the pricing for which a distribution needs to be done
		@dtype pricings: list(Int)

		@return hist: the distribution values
		@dtype date_int: list(int)
		"""	

		pricing_hist = np.zeros((7, ))
		for p_idx in pricings:
			own_p = self.pricing_mat[p_idx]
			if(not(is_raise(own_p))):
				p_time = int(own_p[pa2i['dow']])
				pricing_hist[p_time]+=1

		return pricing_hist

	def _get_match_miss_dif_dists(self, match_difs, miss_difs, gas):
		"""
		Generate a preis difference distribution indicating possible rules differences supported by reactions
		and pricings where no reaction happend. This is important because the maximal values indicate
		the boundary where a difference is okay or where it needs to be changed, if the values
		are no extremes.

		@param match_difs: the difference list for all the matches of this gas
		@dtype match_difs: numpy.array

		@param miss_difs: the difference list for all the misses of this gas
		@dtype miss_difs: numpy.array

		@param gas: the id of the gas type
		@dtype gas: int

		@return hists: the values and their distributions
		@dtype hists: tuple(unique_match, counts_match, unique_miss, counts_miss)
						- unique_match: the difference values after a reaction
						- counts_match: the difference counts after a reaction
						- unique_miss: the difference values after a ignored pricing
						- counts_miss: the difference counts after a ignored pricing
		"""

		# get the match and miss differences and their counts
		unique_match, counts_match = np.unique(match_difs, return_counts=True)
		unique_miss, counts_miss = np.unique(miss_difs, return_counts=True)
		unique_comb = np.unique(np.concatenate((unique_match,unique_miss),axis=0))

		# we need to have a value for each difference appearing in one of the lists
		# therefore we need to fuse the unique values and update the counts
		u_ma = 0
		u_mi = 0
		match_c = np.zeros((len(unique_comb),))
		miss_c = np.zeros((len(unique_comb),))
		i = 0
		while(u_ma<len(unique_match)):
			if(unique_comb[i]==unique_match[u_ma]):
				match_c[i] = counts_match[u_ma]
				u_ma+=1
			i+=1
		i = 0
		while(u_mi<len(unique_miss)):
			if(unique_comb[i]==unique_miss[u_mi]):
				miss_c[i] = counts_miss[u_mi]
				u_mi+=1
			i+=1

		hists = (unique_comb, match_c, miss_c)
		return hists




class Rule(object):
	__slots__ = ('owner', 'competitor','gas_type',
		'max_p_dist', 'conf', 'support', 'exceptions', 'matches', 'total',
		'rule_data',
		'day_distrib', 'hour_distrib',
		'day_rule', 'hour_rule',
		'day_data', 'hour_data',
		'mean_rtime', 'dev_rtime',
		'from_date', 'to_date')

	def __init__(self, owner, competitor, gas_type, date_int, max_p_dist, confidence, reactions, ignores, exceptions, total):
		"""
		Initializes a rule.
		"""

		"""
		@ivar   owner: The station's ID, who has this rule
		@dtype  owner: string
		"""
		self.owner = owner
		"""
		@ivar   competitor: The competing station's ID, that the rule is applied on
		@dtype  competitor: string
		"""
		self.competitor = competitor
		"""
		@ivar   gas_type: The gas type of the rule
		@dtype  gas_type: string
		"""
		self.gas_type = gas_type
		"""
		@ivar   from_date: The starting date for which this rule was generated
		@dtype  from_date: datetime.date
		"""
		self.from_date = date_int[0]
		"""
		@ivar   to_date: The starting date for which this rule was generated
		@dtype  to_date: datetime.date
		"""
		self.to_date = date_int[1]
		"""
		@ivar   max_p_dist: The maximally allowed threshold. So if the price distance surpasses this value the owner reacts
		@dtype  max_p_dist: int
		"""
		self.max_p_dist = max_p_dist
		"""
		@ivar   conf: The confidence value with which we claim this rule exists
		@dtype  conf: int
		"""
		self.conf = confidence
		"""
		@ivar   support: The number of pricings that support this rule
		@dtype  support: int
		"""
		self.support = reactions + ignores
		"""
		@ivar   exceptions: The number of pricings that mark an exception of this rule
		@dtype  exceptions: int
		"""
		self.exceptions = exceptions
		"""
		@ivar   matches: The number of pricings that that happened accoring to this rule
		@dtype  matches: int
		"""
		self.matches = 0
		"""
		@ivar   total: The number of price drops of the owner
		@dtype  total: int
		"""
		self.total = total

		self.rule_data = np.array([max_p_dist, confidence, reactions, ignores, 0, 0, total])


		"""
		@ivar   day_distrib: The distribution of pricings with this max_p_dist over the days of the week
		@dtype  day_distrib: numpy.array
		"""
		self.day_distrib = None
		"""
		@ivar   hour_distrib: The distribution of pricings with this max_p_dist over the hours of a day
		@dtype  hour_distrib: numpy.array
		"""
		self.hour_distrib = None
		"""
		@ivar   day_rule: A list stating on which days of the week this rule holds
		@dtype  day_rule: list(boolean)
		"""
		self.day_rule = None
		"""
		@ivar   hour_rule:  A list stating on which hours of the day this rule holds
		@dtype  hour_rule: list(boolean)
		"""
		self.hour_rule = None
		"""
		@ivar   day_data: A list stating on which days of the week this rule holds
		@dtype  day_data: list(boolean)
		"""
		self.day_data = np.zeros((7,5))
		"""
		@ivar   hour_data:  A list stating on which hours of the day this rule holds
		@dtype  hour_data: list(boolean)
		"""
		self.hour_data = np.zeros((24,6))

		"""
		@ivar   mean_rtime:  The mean reaction time of the pricings in accordance with this rule
		@dtype  mean_rtime: int
		"""
		self.mean_rtime = 0
		"""
		@ivar   dev_rtime: The standard deviation of the pricings in accordance with this rule
		@dtype  dev_rtime: int
		"""
		self.dev_rtime = 0

	def __str__(self):
		"""
		Generates a string for a rule containing the time interval criteria and their values

		@return rule_str: the rule's string
		@dtype rule_str: string
		"""
		#TODO:
		pass
		
	def get_time_windows(self, reactions, ignores, day_slots, hour_slots, hour_totals, day_totals, min_hours, one_rule):
		"""
		Get the rules time windows where it holds

		@param reactions: list of index of the reaction list for this competitor
		@dtype reactions: list(Int)

		@param ignores: list of index of the ignored pricings list for this competitor
		@dtype ignores: list(Int)

		@param day_slots: the available days for a rule
		@dtype day_slots: list(Boolean)

		@param hour_slots: the available houres for a rule
		@dtype hour_slots: list(Boolean)

		@param hour_totals: for every hour the total value of the neighbor
		@dtype hour_totals: list(Int)

		@param day_totals: for every day the total value of the neighbor
		@dtype day_totals: list(Int)

		@param min_hours: the minimum amout of consecutive hours for a rule
		@dtype min_hours: int

		@param one_rule: if there is just one rule allowed per competitor
		@dtype one_rule: bool

		@return outlier: sum up those reactions in still available slots they are new exceptions
		@dtype outlier: string
		"""

		# get and set hour distribution for this rule
		ig_hour_hist, re_hour_hist = self._get_pricing_hour_dist(reactions, ignores)
		comb_hour_hist = ig_hour_hist+re_hour_hist
		self.hour_distrib = comb_hour_hist

		# fill hour data for analysis
		# reactions
		self.hour_data[:,0] = re_hour_hist
		# ignores
		self.hour_data[:,1] = ig_hour_hist
		# support
		self.hour_data[:,2] = comb_hour_hist
		# totals
		self.hour_data[:,3] = hour_totals
		# occupied
		self.hour_data[:,4] = hour_slots
		# changed
		self.hour_data[:,5] = [False]*24

		# if there are any hour slots left
		if(any(hour_slots)):

			# if just one rule is allowed take all slots
			if(one_rule):
				rule_hours = hour_slots[:]
			else:
				# get those times where pricings occur regularly as candidaes for rules
				# regular means it reaches 10 percent of the own pricings in this hour
				rule_hours = [pricing_cnt>=(own_cnt/10) for (pricing_cnt,own_cnt) in zip(comb_hour_hist,hour_totals)]

				# check for slots that are supposed to be taken out and considered for further rules
				# if they are at least 3 hours long
				# add the beginning to the end to be able to check all slots
				tmp_h_rule = rule_hours+rule_hours
				# get the first and last available slots
				first_avail = hour_slots.index(True)
				last_avail = len(hour_slots)-hour_slots[::-1].index(True)-1
				# start at the first available
				i = first_avail
				# throw all failed slots out that are smaller than 3
				while(i<=last_avail):
					if(not(rule_hours[i])):
						cnt = 0
						while(i<=last_avail and not(tmp_h_rule[i])):
							i+=1
							cnt+=1
						if(cnt<min_hours):
							while(cnt>0):
								rule_hours[i-cnt] = True
								self.hour_data[i-cnt,5] = True
								cnt-=1
					else:
						i+=1

				tmp_h_rule = rule_hours+rule_hours

				i = first_avail
				# start at the first slot that is different from the last
				# that is to exclude fails at the start

				# in general get only those rules with at least 3 slots
				while(i<last_avail and rule_hours[i+1]==rule_hours[i]):
					i+=1
				i+=1
				while(i<=last_avail-2):
					if(rule_hours[i]):
						cnt = 0
						while(i<=last_avail and tmp_h_rule[i]):
							i+=1
							cnt+=1
						if(cnt<min_hours):
							while(cnt>0):
								rule_hours[i-cnt] = False
								self.hour_data[i-cnt,5] = True
								cnt-=1
					else:
						i+=1

				# check if those slots are available
				rule_hours = [(rh and hs) for (rh,hs) in zip(rule_hours,hour_slots)]


			# set the new taken slots
			for i in range(len(hour_slots)):
				hour_slots[i] = not(rule_hours[i]) and hour_slots[i]

			# set hour rule
			self.hour_rule = rule_hours
			self.matches = sum([re_hour_hist[i] for i in range(len(rule_hours)) if rule_hours[i]])
			self.rule_data[4] = self.matches

		else:
			# there are no hours left
			self.hour_rule = 24*[False]
			self.matches = 0
			self.rule_data[4] = self.matches

		# get and set day distribution for this rule
		ig_day_hist, re_day_hist = self._get_pricing_day_dist(reactions, ignores)
		comb_day_hist = ig_day_hist+re_day_hist
		self.day_distrib = comb_day_hist

		# fill day data for analysis
		# reactions
		self.day_data[:,0] = re_day_hist
		# ignores
		self.day_data[:,1] = ig_day_hist
		# support
		self.day_data[:,2] = comb_day_hist
		# totals
		self.day_data[:,3] = day_totals
		# occupied
		self.day_data[:,4] = day_slots

		# if there are any day slots left
		if(any(day_slots)):

			# if just one rule is allowed take all slots
			if(one_rule):
				rule_days = day_slots[:]
			else:

				# check for the days of the week where a rule might apply
				pricings_occure = comb_day_hist[np.where(comb_day_hist>0)]
				mean_drop_per_day = np.sum(pricings_occure)/len(pricings_occure)
				threshold = int((mean_drop_per_day/10)+1)
				# get those times where pricings occur regularly as candidaes for rules
				rule_days = [pricing_cnt>=threshold for pricing_cnt in comb_day_hist]
				# check if those slots are available
				rule_days = [rd and ds for (rd,ds) in zip(rule_days,day_slots)]
				# set the new taken slots

			for i in range(len(day_slots)):
				day_slots[i] = not(rule_days[i]) and day_slots[i]

			# set day rule
			self.day_rule = rule_days
		else:
			self.day_rule = 7*[False]

		# update the outlier
		outlier = sum([comb_hour_hist[i] for i in range(len(hour_slots)) if hour_slots[i]])
		self.exceptions+=outlier
		self.rule_data[5] = self.exceptions
		return outlier

	def check_automatism(self, reactions):
		"""
		Generate the the Reaktiontime and standarddeviation thereof to check for automatism

		@param reactions: the list of reactions in this rule
		@dtype reactions: list(tuple(own_idx, neigh_idx))
		"""
		if(len(reactions)>0):
			# only get the real reactions
			rule_reactions = self._get_reactions_in_rule(reactions)
			if(len(rule_reactions)>0):
				# get the values
				mean, st_dev = self._get_mean_and_dev_r_time(rule_reactions)
				self.mean_rtime = mean
				self.dev_rtime = st_dev
				# TODO: some checking at what point there is automatic behavior

	def _get_reactions_in_rule(self, reactions):
		"""
		get all the reactions that really apply to the rules slots

		@param reactions: the list of reactions in this rule
		@dtype reactions: list(tuple(own_idx, neigh_idx))

		@return rule_reactions: the list of reactions that apply to the slotss
		@dtype rule_reactions: list(tuple(own_idx, neigh_idx))
		"""
		station = pricing_globals.STATION_DICT[self.owner]
		rule_reactions = []
		for reaction in reactions:
			pricing = station.pricing_mat[reaction[0]]
			if(self.day_rule[int(pricing[pa2i['dow']])] and self.hour_rule[int(pricing[pa2i['time']]/3600)]):
				rule_reactions.append(reaction)
		return rule_reactions

	def _get_mean_and_dev_r_time(self, rule_reactions):
		"""
		Get the mean and standard deviation of the reaction time in the matches for the respective gas type.
		So we only consider the reaction time when each party of the match changed the respective gas price.
		The reaction time is the time between the pricings where this specific gas was changed.

		@return m: the mean reaction time in minutes
		@dtype m: int

		@return s: the standard deviation of the reaction time in minutes
		@dtype s: int
		"""

		# get the own and the competitors station
		neigh = pricing_globals.STATION_DICT[self.competitor]
		own_station = pricing_globals.STATION_DICT[self.owner]
		# initialize the time difference list
		time_dif = []
		# go through all matches
		for i in range(len(rule_reactions)):
			# get all fields
			(own_idx, neigh_idx) = rule_reactions[i]
			# get the respective pricings where the gas price was changed
			o_pr = own_station.pricing_mat[own_idx]
			n_pr = neigh.pricing_mat[neigh_idx]
			# get the time difference between those to pricings
			time_dif.append(float(get_time_dif(o_pr,n_pr))/60)
			
		m = int(np.mean(time_dif) + 0.5)
		s = int(np.std(time_dif) + 0.5)
		
		return m, s

	def _get_pricing_hour_dist(self, reactions, ignores):
		"""
		For all the pricings supporting this rule make a time distribution over.

		@return hist: the histogram values
		@dtype date_int: list(int)
		"""	
		station = pricing_globals.STATION_DICT[self.owner]
		neigh = pricing_globals.STATION_DICT[self.competitor]

		ignored_hist = np.zeros((24, ))
		for (o_idx, n_idx) in ignores:
			neigh_p_time = int(neigh.pricing_mat[n_idx,pa2i['time']]/3600)
			ignored_hist[neigh_p_time]+=1

		match_hist = np.zeros((24, ))
		for (o_idx, n_idx) in reactions:
			own_p_time = int(station.pricing_mat[o_idx,pa2i['time']]/3600)
			match_hist[own_p_time]+=1

		return ignored_hist,match_hist

	def _get_pricing_day_dist(self, reactions, ignores):
		"""
		For all the pricings supporting this rule make a day distribution.

		@return hist: the histogram values
		@dtype date_int: list(int)
		"""	
		station = pricing_globals.STATION_DICT[self.owner]
		neigh = pricing_globals.STATION_DICT[self.competitor]

		ignored_hist = np.zeros((7, ))
		for (o_idx, n_idx) in ignores:
			neigh_p_time = int(neigh.pricing_mat[n_idx,pa2i['dow']])
			ignored_hist[neigh_p_time]+=1

		match_hist = np.zeros((7, ))
		for (o_idx, n_idx) in reactions:
			own_p_time = int(station.pricing_mat[o_idx,pa2i['dow']])
			match_hist[own_p_time]+=1

		return ignored_hist,match_hist

	def _get_days(self):
		day_list = []
		for i in range(len(self.day_rule)):
			if(self.day_rule[i]):
				current_day = {}
				current_day['day'] = i
				current_day['total'] = self.day_data[i,3]
				current_day['support'] = self.day_data[i,2]
				current_day['reactions'] = self.day_data[i,0]
				current_day['ignores'] = self.day_data[i,1]
				day_list.append(current_day)
		return day_list

	def _get_times(self):
		hour_list = []
		i=0
		while i < len(self.hour_rule):
			if(self.hour_rule[i]):
				start_idx = i
				i+=1
				while(self.hour_rule[i]):
					i+=1
				i+=1
				end_idx = i
				current_hour = {}
				stats = np.sum(self.hour_data[start_idx:end_idx,:], axis=0)
				current_hour['start_time'] = start_idx
				current_hour['end_time'] = end_idx
				current_hour['total'] = stats[3]
				current_hour['support'] = stats[2]
				current_hour['reactions'] = stats[0]
				current_hour['ignores'] = stats[1]
				current_hour['exceptions'] = stats[5]
				hour_list.append(current_hour)
			else:
				i+=1
		return hour_list


class RuleJSONEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Rule):
			return {
			'difference': obj.max_p_dist,
			'confidence': obj.conf,
			'total': obj.total,
			'support': obj.support,
			'correlations': obj.rule_data[2],
			'ignores': obj.rule_data[3],
			'reactions': obj.matches,
			'exceptions': obj.exceptions,
			'days': obj._get_days(),
			'times': obj._get_times(),
			}
		try:
			return json.JSONEncoder.default(self, obj)
		except TypeError:
			if(isinstance(obj,np.bool_)):
				return int(obj)
			else:
				print("Encountered not json compatible obj")
				print(obj)
				sys.exit()

def get_station_dict():
	"""
	Generate a dictionary with id -> station for each station.

	@return	The dictionary containing all gas stations indexed by their id
	@rtype	dict
	"""

	pricing_globals.STATION_DICT = {}
	# get the station data from the postgres database pointed to by the CURSOR
	pricing_globals.CURSOR.execute('SELECT * from gas_station')
	station_data = pricing_globals.CURSOR.fetchall()
	# for each station generate a station instance and add it to the dict
	for i in range(0,len(station_data)):
		pricing_globals.STATION_DICT[station_data[i][0]] = Station(station_data[i])
	return pricing_globals.STATION_DICT

if __name__ == "__main__":
	berlin = pytz.timezone('Etc/GMT-2')

	from_date = datetime(2016,6,1).date()
	to_date = datetime(2016,8,31).date()

	try:
		con = psycopg2.connect(database='pricing_31_8_16', user='kai', password='Sakral8!')
		# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
		pricing_globals.CURSOR = con.cursor()
		pricing_globals.STATION_DICT = get_station_dict()

		test_station_plz = '49078'
		test_station_city = 'Osnabrück'
		test_station_street = 'Kurt-Schuhmacher-Damm'
		test_station_brand = 'Q1'

		run_vals = [2700, (5,5,20),False,False,3,0.5,0.03]

		pricing_globals.CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(test_station_plz,test_station_brand))
		gas_station_id = pricing_globals.CURSOR.fetchall()[0][0]
		station = pricing_globals.STATION_DICT[gas_station_id]

		# print station details
		print('analysing station:')
		print(str(station) + ' ' + station.id) 

		# get the stations competition
		print('getting the stations competition')
		station.get_competition(d_int=(from_date,to_date),lead_t=run_vals[0],n_vals=run_vals[1], one_rule=run_vals[2], com_conf_div=run_vals[3], hour_min=run_vals[4], rule_conf=run_vals[5], com_conf=run_vals[6])

		print('saving the json file')
		station.save_json(join(MODUL_PATH,"test_json"))

	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()