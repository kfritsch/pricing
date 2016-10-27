# -*- coding: utf-8 -*-
import os, sys, traceback, copy, operator
from os.path import join, realpath, dirname, isdir

# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
SRC_PATH = dirname(realpath(__file__))
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
# the analysis_docs path is the projects subfolder for outputs to be analysed
ANALYSIS_PATH = join(MODUL_PATH, "tmp")
if(not(isdir(ANALYSIS_PATH))): os.makedirs(ANALYSIS_PATH)

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

import HTML, codecs, json

import pricing_globals
from helper_functions import *
from pricing_helper_functions import *

import cProfile

# import warnings
# warnings.simplefilter("error")

# the targets for the testing data
TARGET_DATA = {
	"90543baf-7517-43cd-9c59-1a2493c26358":{ # Q1 Kurt
		"8a5b2591-8821-4a36-9c82-4828c61cba29":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*17+[0]*1]).T
		], # Aral Kurt
		"51d4b5a3-a095-1aa0-e100-80009459e03a":[
		np.array([1,
			0]).T,
		np.array([[1]*7,
			[1]*7]).T,
		np.array([[0]*5+[1]*2+[0]*7+[1]*9+[0]*1,
			[0]*7+[1]*7+[0]*10]).T
		], # Jet Hansa
		"51d4b54f-a095-1aa0-e100-80009459e03a":[
		np.array([1]).T,
		np.array([[1]*7]).T,
		np.array([[0]*5+[1]*18+[0]*1]).T
		], # Jet Iburger
		"30d8de2f-7728-4328-929f-b45ff1659901":[
		np.array([2]).T,
		np.array([[1]*7]).T,
		np.array([[0]*9+[1]*14+[0]*1]).T
		], # Ratio Kaufland Kurt 52
		"ebc673e0-8359-4ab6-0afa-c31cc35c4bd2":[
		np.array([1]).T,
		np.array([[1]*7]).T,
		np.array([[0]*7+[1]*16+[0]*1]).T
		], # Score Kurt 2
		"f4b31676-e65e-4b60-8851-609c107f5d93":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*17+[0]*1]).T
		] # Shell Leng Land
	},
	"886cb311-3a0f-4bcb-814a-86bf7e25d4b0":{ # Tankstelle Haster
		"51d4b6e0-a095-1aa0-e100-80009459e03a":[
		np.array([-1]).T,
		np.array([[1]*7]).T,
		np.array([[0]*8+[1]*14+[0]*2]).T
		] # Jet Bremer 100
	},
	"58243ea3-d98c-48b2-bc6c-a9cd71869935":{ # Q1 Chaussee
		"1e28be99-06c9-4886-9b8a-51ce4b23d5fe":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		], # Agip Magde
		"9daee97e-ef5c-4a4a-ab11-3aa6c5f5d281":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		], # Shell Magde
		"e4e4d522-6f9a-44c3-9d75-25fc8466d9a7":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		] # Shell Breiter 
	},
	"72afdc97-915d-45b5-a2ae-9a045bd03e6b":{ # Q1 Weimarer
		"7cf6a222-2443-4b36-b454-e99227f105c7":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*14+[0]*4]).T
		], # Shell Hollaendische 268
		"51d4b47b-a095-1aa0-e100-80009459e03a":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*14+[0]*4]).T
		] # Jet Hollaendische 210
	},
	"49d0dc5d-5663-4f4f-be33-a341ecb9ceb1":{ # Q1 Bahnhofstrasse
		"f8d69252-c4e2-4ec5-8d85-de7dd0e23a07":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*5+[1]*17+[0]*2]).T
		], # Esso Blanken
		"51d4b648-a095-1aa0-e100-80009459e03a":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*5+[1]*17+[0]*2]).T
		] # Jet Lütmarser
	},
	"61939c88-130e-4a83-8931-5e7723e0b2b3":{ # Q1 Heinrich-Heine-Strasse
		"ca59821d-9be3-4716-81e8-9aba1bca33d5":[
		np.array([3]).T,
		np.array([[1]*7]).T,
		np.array([[0]*5+[1]*17+[0]*2]).T
		], # Aral Friedenstr
		"cf2f67eb-2295-4ac0-986e-5222be15b0dd":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*5+[1]*17+[0]*2]).T
		] # Aral Kummersdorfer
	},
	"4b48fc6f-fe5c-4660-aa24-ec07cc77faac":{ # bft Dattelner
		"51d4b6c5-a095-1aa0-e100-80009459e03a":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*15+[0]*3]).T
		], # Jet Heinrichenburger
		"86cac7b9-6008-4e6d-9542-f07396ae42bb":[
		np.array([-1]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*15+[0]*3]).T
		], # Shell Hebewerkstr 25
		"005056ba-7cb6-1ed2-bceb-7966ed5a4d26":[
		np.array([0,
			-1]).T,
		np.array([[1]*7,
			[1]*7]).T,
		np.array([[0]*6+[1]*1+[0]*7+[1]*7+[0]*3,
			[0]*7+[1]*7+[0]*10]).T
			], # Star Hebewerkstr 18
		"5f2a28c7-f0c2-4454-9562-cd9f94b0a29b":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*15+[0]*3]).T
		] # Freie Tanke Wittener Strasse 96
	},
	"c7565063-01dd-4181-82a9-a9012f2380ae":{ # bft Blankenburger
		"308786e0-9dfd-4f90-b0a3-dd6ab1ce9f97":[
		np.array([-1]).T,
		np.array([[1]*7]).T,
		np.array([[1]*24]).T
		], # Aral Pasewalker Strasse 110
		"de2e2b16-448e-439a-a544-b45c685431ae":[
		np.array([-1]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		] # Total Wackenberg
	},
	"21f995f7-2556-4817-b7b5-744db37ddb69":{ # bft Sebastianstrasse
		"f2d21709-e795-4596-8992-61250d7b5225":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		], # Aral Sebastianstrasse 158
		"b1d8fc89-8404-43b5-bd89-7ce2dacc95c9":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*15+[0]*3]).T
		], # ED Schmittmannstrasse 2
		"7f9fe251-ede1-4443-a077-3c001d6d7c44":[
		np.array([0]).T,
		np.array([[1]*7]).T,
		np.array([[0]*6+[1]*16+[0]*2]).T
		] # Markant Heerstr. 166
	}
}
# the results of the classified data
TESTING_DATA = {
}
# random results to get a general idea
RANDOM_DATA = {
}

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
		'analysis_path',
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

		self.analysis_path = join(ANALYSIS_PATH, str(self).replace(" ", "_").replace(".", "-"))

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

		# add the time interval as folder to the analysis path
		tmp_path = self.analysis_path
		self.analysis_path = join(self.analysis_path, str(d_int[0]).replace("-","_")+"-"+str(d_int[1]).replace("-","_"))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)

		# get the own pricing
		self.get_pricing(d_int)

		# check for the hours of the day where a rule might apply
		drop_hist, raise_hist = self.plot_pricing_hour_hist(range(len(self.pricing_mat)), 'mon-sun')
		# take only the consequtive hours with frequent pricings
		rule_hours = self._get_possible_rule_hours(drop_hist)
		# check for the days of the week where a rule might apply
		pricing_hist = self.plot_pricing_dow_hist(range(len(self.pricing_mat)))
		# take only the days with frequent pricings
		rule_days = self._get_possible_rule_days(pricing_hist)

		# plot pricing hists for opening hour analysis
		splits, titles = split_at(range(len(self.pricing_mat)), self.id, 'dow')
		for dow in range(7):
			day_drop_hist, day_raise_hist = self.plot_pricing_hour_hist(splits[dow], dow_to_string[titles[dow]])

		# depending if we have test results for the station open a new dict in the accordig dict
		if(self.id in TARGET_DATA):
			TESTING_DATA[self.id] = {}
		else:
			RANDOM_DATA[self.id] = {}



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

		# # PRINT:
		# print("loaded all data")

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

			# make a new entry in the according dict for the 
			if(self.id in TARGET_DATA):
				TESTING_DATA[self.id][neigh.id]=[None,None,None]
			else:
				RANDOM_DATA[self.id][neigh.id]=[None,None,None]

			# if(neigh_id!="30d8de2f-7728-4328-929f-b45ff1659901"): continue

			# # PRINT: the current station as string
			# print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n"+str(neigh)+"\n"))
			# get the pricings without reaction of this station

			# reset the anaylis_path and add the competitor first before adding the time interval again
			self.analysis_path = join(tmp_path, str(neigh).replace(" ", "_").replace(".", "-"))
			if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
			self.analysis_path = join(self.analysis_path, str(d_int[0]).replace("-","_")+"-"+str(d_int[1]).replace("-","_"))
			if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)

			# change the neigh analysis_path
			n_tmp_path = neigh.analysis_path
			neigh.analysis_path = self.analysis_path

			# check for the hours of the day where a rule might apply for the neighbor
			neigh_drop_hist, neigh_raise_hist = neigh.plot_pricing_hour_hist(range(len(neigh.pricing_mat)), 'mon-sun')
			# take only the consequtive hours with frequent pricings
			neigh_rule_hours = neigh._get_possible_rule_hours(neigh_drop_hist)
			# combine the rule slots of the station pair
			comb_rule_hours = [oh and nh for (oh,nh) in zip(rule_hours, neigh_rule_hours)]

			# check for the days of the week where a rule might apply
			neigh_pricing_hist = neigh.plot_pricing_dow_hist(range(len(neigh.pricing_mat)))
			# take only the days with frequent pricings
			neigh_rule_days = neigh._get_possible_rule_days(neigh_pricing_hist)
			# combine the rule slots 
			comb_rule_days = [oh and nh for (oh,nh) in zip(rule_days, neigh_rule_days)]
			# reset the path
			neigh.analysis_path = n_tmp_path

			# get the neighbor pricings without an own reaction
			self._get_no_reaction_pn(neigh_id)
			
			# get the reactions and ignored pricings for each gastype seperately
			gas_reactions = self._get_gas_specific_reactions(neigh_id)
			gas_ignores = self._get_gas_specific_ignores(gas_reactions, neigh_id)

			# check for and generate rules for each gas type
			for gas in range(len(GAS)):
				gas_matches = 0
				# make new data
				eval_data = [None,np.empty((0, 7)),[],[]]
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
				(dist_vals, react_cnts, ignore_cnts) = self._plot_match_miss_dif_hists(react_difs, ignore_difs, gas)
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

				# # PLOT:
				# # create a file to save irregularities
				# file_name = GAS[gas] + "_rule_outlier" + '.html'
				# f = open(join(self.analysis_path,file_name), 'w')
				# f.write(html_intro(GAS[gas] + " rule exceptions"))
				# f.write("<style>\n")
				# f.write(".floating-box {display: inline-block;margin-top: 20px;margin-bottom: 20px;border: 3px solid #000000;}\n")
				# f.write("</style>\n")
				# f.write("<center>\n")

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
						# if it is classified station and the value is a rule take the data for analysis
						# if(self.id in TARGET_DATA and neigh.id in TARGET_DATA[self.id] and TARGET_DATA[self.id][neigh.id][0][0]>=dist_val):
						rule_data = [dist_val,
						confidence,
						len(dist_reacts),
						len(dist_ignores),
						0,
						exceptions,
						gas_drop_cnt]
						eval_data[1] = np.append(eval_data[1], [rule_data], axis=0)
						eval_data[2].append(np.zeros((7,6)))
						eval_data[3].append(np.zeros((24,7)))

						# add those to the exception count
						exceptions += support
						# write the pricings to a file for later checking
						# write a intro

						# # PLOT:
						# self._write_exception_table(f, neigh_id, dist_val, dist_reacts, dist_ignores, lead_t)

					# otherwise create a rule out of the distance
					else:
						# while there are possible rules left
						rule = Rule(owner=self.id,
							competitor=neigh_id,
							gas_type=GAS[gas],
							date_int=d_int,
							analysis_path=self.analysis_path,
							max_p_dist=dist_val,
							confidence = confidence,
							reactions=len(dist_reacts),
							ignores=len(dist_ignores),
							exceptions=exceptions,
							total=gas_drop_cnt)


						# # PRINT: rule hours to fill
						# print(print_bcolors(['BOLD', 'FAIL'],str([i for i in range(len(gas_rule_hours)) if gas_rule_hours[i]])))
						exceptions+=rule.get_time_windows(dist_reacts,
							dist_ignores,
							gas_rule_days,
							gas_rule_hours,
							neigh_drop_hist,
							neigh_pricing_hist,
							min_hours=hour_min,
							one_rule=one_rule)
						self.rules_pn[neigh_id][GAS[gas]]["rules"].append(rule)
						# # PRINT: rule hours to fill
						# print(print_bcolors(['BOLD', 'OKGREEN'],str([i for i in range(len(rule.hour_rule)) if rule.hour_rule[i]])))
						rule.check_automatism(dist_reacts)

						# # PLOT:
						# rule.write_stats_analysis()
						# add the evaluation data
						# general rule data
						eval_data[1] = np.append(eval_data[1], [rule.rule_data], axis=0)
						# day values
						eval_data[2].append(np.concatenate((np.array([rule.day_rule]).T,rule.day_data),axis=1))
						# hpur values
						eval_data[3].append(np.concatenate((np.array([rule.hour_rule]).T,rule.hour_data),axis=1))
						# get overall matches for the neighbor
						gas_matches+=rule.matches

					dist_idx-=1

				# # PLOT:
				# f.write("</center>\n")
				# f.write(html_end())
				# f.close()

				# the confidence value deciding if it is an competitor or not
				competitor_conf = (float(gas_matches)/gas_drop_cnt) if(gas_matches>0) else 0
				# decides if the confidence value is to be divided by the number of chosen rules
				valid_rule_count = sum(eval_data[1][:,1]>=rule_conf)
				if(com_conf_div and valid_rule_count>0): competitor_conf=competitor_conf/valid_rule_count

				eval_data[0]=[int(competitor_conf>com_conf),competitor_conf]
				self.rules_pn[neigh_id][GAS[gas]]["competitor"] = int(competitor_conf>com_conf)
				self.rules_pn[neigh_id][GAS[gas]]["confidence"] = competitor_conf

				if(self.id in TARGET_DATA):
					TESTING_DATA[self.id][neigh.id][gas] = eval_data
				else:
					RANDOM_DATA[self.id][neigh.id][gas] = eval_data
			# # PAUSE: after each station investigated
			# pause()

		# reset the analsis path
		self.analysis_path = tmp_path

	def c_profile_competition(self, d_int, lead_t=2700, n_vals=(5,5,20), one_rule=False, com_conf_div=False, hour_min=3, rule_conf=0.5, com_conf=0.03):
		cProfile.runctx('self.get_competition(d_int, lead_t, n_vals, one_rule, com_conf_div, hour_min, rule_conf, com_conf)', globals(), locals())

	def day_analysis(self, day):
		'''
		Plots the pricings of a day of the station and its neighbors as a timeline

		@param day: day in question
		@dtype day: datetime
		'''

		# add the day to the as folder analysis path
		directory = join(self.analysis_path, str(day))
		if(not(isdir(directory))): os.makedirs(directory)

		# get the pricing for the day only
		self.get_pricing((day,day))
		# get the neighbors
		self.get_neighbors()
		# get their pricings
		for (neigh_id, dif) in self.neighbors:
			neigh = pricing_globals.STATION_DICT[neigh_id]
			neigh.get_pricing((day,day))

		# get all related pricing pairs (related means close in time)
		self._get_neighbor_related_pricings(t_int=3600)

		# plot timeline
		self._plot_day_timeline(day, directory)

		return

	def check_granger_causality(self, date_int):
		'''
		Uses the granger causality test to infer if a neighbor has a causal influence
		on the station itself. As test data we use the pricing timeline beeing the price
		at every minute for a single gasline type.

		The Granger causaltity test compares if the prediction of the own time serieses next value
		is improved by adding the other time series as predictive variable

		@param date_int: date interval for which the data is analysed
		@dtype date_int: tuple(date,date)
		'''
		# get the own pricing
		self.get_pricing(date_int, rem_outlier=True)
		# get the neighbors
		self.get_neighbors()
		num_neigh = len(self.neighbors)

		# get the own price time series matrice: dims(min,gas)
		own_time_series_data = self.get_time_series_data()
		len_series = len(own_time_series_data)
		granger_data = np.zeros((len_series,2))

		# go through neighbors
		for i in range(0,num_neigh):
			# get neighbor
			neigh_id = self.neighbors[i][0]
			neigh = pricing_globals.STATION_DICT[neigh_id]
			# PRINT: the station investigated
			print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n\n"+station_to_string(neigh_id)+"\n"))
			# get the neighbors pricing
			neigh.get_pricing()
			# create its time series
			neigh_time_series_data = neigh.get_time_series_data()
			# go through every gas type
			for j in range(0,len(GAS)):
				# extract the relevant data
				granger_data[:,0] = own_time_series_data[:,j]
				granger_data[:,1] = neigh_time_series_data[:,j]
				# do the test
				res_dict = st.grangercausalitytests(granger_data, maxlag=30, addconst=True, verbose=True)
				# PRINT: the result of the test
				print(res_dict[1][0])

	def save_json(self, file_dir=None):
		if(file_dir is None): file_dir=self.analysis_path
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

		# # PLOT
		# # create a file to explore larger reaction combinations for tha ba
		# file_dir = join(ANALYSIS_PATH,"TESTING_DATA")
		# if(not(isdir(file_dir))): os.makedirs(file_dir)
		# file_name = "complex_reaction_table" + '.html'
		# f = open(join(file_dir,file_name), 'w')
		# f.write(html_intro("Complex Reactions"))
		# f.write("<style>\n")
		# f.write(".floating-box {display: inline-block;margin-top: 20px;margin-bottom: 20px;border: 3px solid #000000;}\n")
		# f.write("</style>\n")
		# f.write("<center>\n")
		# f.write(html_heading(1, "Complex Reactions"))

		own_set_idx = []

		while(i < p_cnt):
			# get the own pricing
			own_pricing = self.pricing_mat[i,:]
			# # PRINT: the pricings date and changed value
			# print(str(get_timestamp(own_pricing[pa2i['date']], own_pricing[pa2i['time']])) + "\t%d" % (own_pricing[pa2i['alt']]))

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

					# # DEBUG:
					# if(len(c_own_set_idx)>1):
					# 	print("action: " + pricing_to_string(neigh.pricing_mat[index]))
					# 	print("reaction: " + pricing_to_string(self.pricing_mat[i]))
					# 	print("")
					# 	print("last reaction: " + pricing_to_string(self.pricing_mat[c_own_set_idx[-1]]))
					# 	pause()
					# get neighbor pricing
					neigh_pricing = neigh.pricing_mat[index]

					# up_dif is the time difference to the uppermost own pricing in the chain
					up_dif = get_time_dif(neigh_pricing, self.pricing_mat[upper_idx])

					# # DEBUG:
					# if(len(c_own_set_idx)>1):
					# 	print("up_dif: "+ str(up_dif))

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
								# # DEBUG:
								# print('justed raised')
								# print(pricing_to_string(self.pricing_mat[last_raise_idx]))
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
										# # DEBUG:
										# print('need to continue')
										continue

							# set a flag if the neighbor pricing stands alone
							# alone means there is now own one that follows in the interval and is not a raise
							# neigh_single_change = get_time_dif(neigh.pricing_mat[index+1], neigh_pricing)>=(-1)*up_dif or is_raise(neigh.pricing_mat[index+1])
							if(len(c_own_set_idx)>1):
								# print(len(c_own_set_idx))
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
									# # DEBUG:
									# print('single_single')
									# pause()
								else:
									'''
									IF THERE ARE SEVERAL OWN
									'''
									# # DEBUG:
									# print("single_mult")
									# print(pricing_to_string(neigh.pricing_mat[neigh_set_idx[0]]))
									# print("")
									# for odx in range(len(c_own_set_idx)):
									# 	print(pricing_to_string(self.pricing_mat[c_own_set_idx[odx]]))
									# pause()
									self._check_leader_single_multi(index, c_own_set_idx,own_set_alt, neigh_id, j)

									# # PLOT:
									# # write to file for ba
									# f.write(html_heading(3, "single action multiple reactions"))
									# f.write("<div class=\"floating-box\">\n")
									# f.write(self._reaction_html_table_single(neigh_id, [c_own_set_idx[-1], index], t_int, ["last_reaction", "action", "reaction", "bet"]))
									# f.write("</div>\n")
									# f.write('<br>\n')
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
									# # DEBUG:
									# print("mult_single")
									# for ndx in range(len(neigh_set_idx)):
									# 	print(pricing_to_string(neigh.pricing_mat[neigh_set_idx[ndx]]))
									# print("")
									# print(pricing_to_string(self.pricing_mat[c_own_set_idx[0]]))
									# pause()
									self._check_leader_multi_single(neigh_set_idx, neigh_set_alt, neigh_set_time, c_own_set_idx[0], neigh_id, j)

									# # PLOT:
									# # write to file for ba
									# f.write(html_heading(3, "multiple actions single reaction"))
									# f.write("<div class=\"floating-box\">\n")
									# f.write(self._reaction_html_table_single(neigh_id, [c_own_set_idx[0],neigh_set_idx[0]], t_int, ["reaction", "first_action", "bet", "action"]))
									# f.write("</div>\n")
									# f.write('<br>\n')
								else:
									'''
									IF THERE ARE SEVERAL OWN
									'''
									# # DEBUG:
									# print("mult_mult")
									# for ndx in range(len(neigh_set_idx)):
									# 	print(pricing_to_string(neigh.pricing_mat[neigh_set_idx[ndx]]))
									# print("")
									# for odx in range(len(c_own_set_idx)):
									# 	print(pricing_to_string(self.pricing_mat[c_own_set_idx[odx]]))
									# pause()

									# # PLOT:
									# # write to file for ba
									# f.write(html_heading(3, "multiple actions multiple reactions"))
									# f.write("<div class=\"floating-box\">\n")
									# f.write(self._reaction_html_table_single(neigh_id, [c_own_set_idx[-1], neigh_set_idx[0]], t_int, ["last_reaction", "first_action", "reaction", "action"]))
									# f.write("</div>\n")
									# f.write('<br>\n')
									# self._check_leader_multi_multi2(neigh_set_idx, neigh_set_alt, neigh_set_time, c_own_set_idx[:], own_set_alt, neigh_id, j, t_int)
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

		# # PLOT
		# f.close()
		# # get a html output stating all causes for each pricing respectiely
		# self._write_first_leader_analysis()

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
		# a print string printing the relevant information of a leader
		n_str = ('\t' + str(j) + '\t' + str(leader_idx) + '\t' + str(neigh_pricing[pa2i['alt']]) + '\t' + str(get_time(neigh_pricing[pa2i['time']], False)) + "\t -> \t " + str([own_idx]))

		# if the changes made in the pricings allow for a causal relaionship
		if(proper_drop_dif(neigh_pricing, own_pricing)):
			self.pot_reaction_pn[neigh_id].append((own_idx,leader_idx,0,0))
			self.pot_reaction_poi[own_idx].append((neigh_id, leader_idx,0,0))
			return True
		# 	# PRINT: the leader information in green for succeed
		# 	print(print_bcolors(["BOLD","OKGREEN"],n_str))
		# # otherwise
		else:
			# # PRINT: the leader information in red for fail
			# print(print_bcolors(["BOLD","FAIL"],n_str))
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
		# 	# PRINT: the relevant information red if not succeded
			# print(print_bcolors(["BOLD","FAIL"],n_str))
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

				# # PRINT: the relevant information green if succeded
				# print(print_bcolors(["BOLD","OKGREEN"],n_str))
				# return take
		else:
		# 	# PRINT: the relevant information red if not succeded
			# print(print_bcolors(["BOLD","FAIL"],n_str))
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
				# # PRINT: the relevant information in their success related color
				# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[n_idx]) + '\t' + str(neigh_set_alt[n_idx]) + '\t' + str(neigh_set_time[n_idx]) + "\t -> \t " + str([own_idx]))
				# print(print_bcolors(["BOLD","OKGREEN"],n_str))
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
			# # PRINT: the relevant information red for fail
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[:]) + '\t' + str(neigh_set_alt[:]) + '\t' + str(neigh_set_time[:]) + "\t -> \t " + str([own_idx]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
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
					# # PRINT: the relevant information in their success related color
					# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[n_idx:n_idx+len(take)]) + '\t' + str(neigh_set_alt[n_idx:n_idx+len(take)]) + '\t' + str(neigh_set_time[n_idx:n_idx+len(take)1]) + "\t -> \t " + str([own_idx]))
					# print(print_bcolors(["BOLD","OKGREEN"],n_str))
					return take
				n_idx -= 1

			# # if there was no possible combination
			# # PRINT: the relevant information red for fail
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[:]) + '\t' + str(neigh_set_alt[:]) + '\t' + str(neigh_set_time[:]) + "\t -> \t " + str([own_idx]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
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
				# PRINT: the relevant information red for fail
				n_str = ('\t' + str(j) + '\t' + str(cur_n_set) + '\t' + str(cur_n_alt) + '\t' + str(cur_n_time) + "\t -> \t " + str([osi]))
				# print(print_bcolors(["BOLD","FAIL"],n_str))

	def _check_leader_multi_multi(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, own_set_alt, neigh_id, j):
		"""
		There are several leading pricings as well as several own reactions. Check which leader is the possible cause for which
		own reaction.
			- Divide the both sets into subparts
				- Start with the first leader
				- collect all leaders up to the first reaction
				- collect all reactions until the next leader comes before the next reaction
			- investigate those both subsets
				- the two subsets might fit one of the other categories (multi-single,...)
				- if there are still multiple in both sets try a different rule
			- start over until there are no further pricings

		CURRENTLY there is no treatment for cases like [n, n, o ,n, o, o]

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

		# initialze indeces
		nsi = 0
		osi = 0
		# 
		neigh = pricing_globals.STATION_DICT[neigh_id]

		# exclude all unleaded own pricings
		while(get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) > 0):
			osi += 1

		# as long as there are potential leader sets left
		while(nsi < len(neigh_set_idx)):
			# take the first leader and initialize the own subset
			cur_n_set = [neigh_set_idx[nsi]]
			cur_n_alt = [neigh_set_alt[nsi]]
			cur_n_time = [neigh_set_time[nsi]]
			# next index
			nsi += 1
			# as long as there are leaders before the next own add them
			while(nsi < len(neigh_set_idx) and get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) <= 0):
				cur_n_set.append(neigh_set_idx[nsi])
				cur_n_alt.append(neigh_set_alt[nsi])
				cur_n_time.append(neigh_set_time[nsi])
				nsi += 1

			# initialize the reaction set
			cur_o_set = []
			cur_o_alt = []
			# if nsi is out of bound add all reactions
			if(nsi==len(neigh_set_idx)):
				cur_o_set.extend(own_set_idx[osi:])
				cur_o_alt.extend(own_set_alt[osi:])
			else:
				# as long as there are own pricings before the next leader add them
				while(osi < len(own_set_idx) and get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) > 0):
					cur_o_set.append(own_set_idx[osi])
					cur_o_alt.append(own_set_alt[osi])
					osi += 1
			# get the sets counts
			cur_cnt_n = len(cur_n_set)
			cur_cnt_o = len(cur_o_set)

			if(cur_cnt_n==1):
				# if both set are one -> check_leader_single_single
				if(cur_cnt_o==1):
					self._check_leader_single_single(cur_n_set[0], cur_o_set[0], neigh_id, j)
				# if only own set is multi -> check_leader_single_multi
				else:
					self._check_leader_single_multi(cur_n_set[0], cur_o_set, cur_o_alt, neigh_id, j)
			else:
				# if only neigh set is multi -> check_leader_multi_single
				if(cur_cnt_o==1):
					self._check_leader_multi_single(cur_n_set, cur_n_alt, cur_n_time, cur_o_set[0], neigh_id, j)
				# if both set are multi -> do a new check
				else:
					# if they changed the same prices add the whole sets
					if(cur_n_alt==cur_o_alt):
						self.pot_reaction_pn[neigh_id].append((cur_o_set[0],cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
						self.pot_reaction_poi[cur_o_set[0]].append((neigh_id,cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
						# # PRINT: relevant information in respective color for success
						# n_str = ('\t' + str(j) + '\t' + str(cur_n_set) + '\t' + str(cur_n_alt) + '\t' + str(cur_n_time))
						# print(print_bcolors(["BOLD","OKGREEN"],n_str))
					else:
						# otherwise go from the bacl to the front and find causes for own pricing
						# while deleting the found matches
						while(len(cur_n_set)>0 and len(cur_o_set)>0):
							rem_n, rem_o = self._check_leader_multi_multi_single(cur_n_set, cur_n_alt, cur_n_time, cur_o_set, neigh_id, j)
							while(rem_o>0):
								cur_o_set.pop()
								rem_o -= 1
							while(rem_n>0):
								cur_n_set.pop()
								cur_n_alt.pop()
								cur_n_time.pop()
								rem_n -= 1

		# print('')

	def _check_leader_multi_multi_single(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, neigh_id, j):
		"""
		At this point we have a group of possible causes followed by a group of possible reactions.
		We start at the last own pricing and try to find a cause. We start from the back for the same
		reason as in the single multi condition.  A found cause for the last reaction could have been the cause for a previous
		one as well but in regard to further analysis it is saver to assume the later one to be the
		real reaction at first.

		CURRENTLY there is no treatment for cases like [n, n, o ,n, o, o]

		@param neigh_set_idx: the indices of the potentially causing pricings
		@dytpe neigh_set_idx: list(Int)

		@param neigh_set_alt: the alt values of the potentially causing pricings
		@dytpe neigh_set_alt: list(Int)

		@param neigh_set_time: the time strings of the potentially causing pricings
		@dytpe neigh_set_time: list(Int)

		@param own_set_idx: the list of own reactions
		@dytpe own_set_idx: list(Int)

		@param neigh_id: the identifier of the station of the leading pricing
		@dytpe neigh_id: string

		@param j: the number of the neighbor in the list
		@dytpe j: int

		@return num_own: the number of own elements for which a cause was found
		@dtype num_own: int

		@return num_neigh: the number of causing elements
		@dtype num_neigh: int
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# start at the last indexes
		osi = len(own_set_idx)-1
		nsi = len(neigh_set_idx)-1
		# there could still be a multi-single or single-multi reaction as subset
		# so we nelen(neigh_set_idx)-1d to create an artificial pricing for both parts
		neigh_art = np.zeros((len(pa2i), ))
		neigh_art[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[nsi],pa2i['d_diesel']]
		neigh_art[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[nsi],pa2i['d_e5']]
		neigh_art[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[nsi],pa2i['d_e10']]

		own_art = np.zeros((len(pa2i), ))
		own_art[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[osi],pa2i['d_diesel']]
		own_art[pa2i['d_e5']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e5']]
		own_art[pa2i['d_e10']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e10']]

		# while  the leader can not account for the last pricing add earlier ones
		prop_dif = proper_drop_dif(neigh_art, own_art)

		while(not(prop_dif) and nsi>0):
			nsi-=1
			neigh_art[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_diesel']]
			neigh_art[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e5']]
			neigh_art[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e10']]
			prop_dif = proper_drop_dif(neigh_art, own_art)

		# if a point was reached where the reaction could be explained
		if(prop_dif):
			# check if the cause could explain several reactions together
			while(prop_dif and osi>0):
				osi -= 1
				own_art[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_diesel']]
				own_art[pa2i['d_e5']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e5']]
				own_art[pa2i['d_e10']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e10']]
				prop_dif = proper_drop_dif(neigh_art, own_art)
				if(not(prop_dif)):
					osi += 1
			num_own = len(own_set_idx)-osi
			num_neigh = len(neigh_set_idx)-nsi
			self.pot_reaction_pn[neigh_id].append((own_set_idx[osi],neigh_set_idx[nsi],num_own-1,num_neigh-1))
			self.pot_reaction_poi[own_set_idx[-osi]].append((neigh_id, neigh_set_idx[-nsi],num_own-1,num_neigh-1))
			# # PRINT relevant information 
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[nsi:]) + '\t' + str(neigh_set_alt[nsi:]) + '\t' + str(neigh_set_time[nsi:]) + "\t -> \t " + str([own_set_idx[osi:]]))
			# print(print_bcolors(["BOLD","OKGREEN"],n_str))
			# return the number of elements to remove
			return num_neigh, num_own
		else:
			num_own = len(own_set_idx)-osi
			num_neigh = 0
			# # PRINT relevant information 
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx) + '\t' + str(neigh_set_alt) + '\t' + str(neigh_set_time) + "\t -> \t " + str([own_set_idx[osi]]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
			# return the of elements to remove
			return num_neigh, num_own		

	#DEP:
	def _get_rel_idc(self, neigh_id):
		"""
		We only want to analyse those pricings, where it is possible to infer something from the statistiks.
		While pricings with reactions are quite important, those where no reaction occurs are nearly as important
		as well. However we just want those unreacted pricings of a neighbor, where the own station didn't react
		because itdidn't have to according to the rule. Any other reason should be excluded because it could harm
		the further analysis. Excluded are CURRENTLY:
			- raises
			- (follower which are no leader as well)

		@param neigh_id: the identifier of the station in question
		@dytpe neigh_id: string

		@return rel_idc: the list of relevant pricings pricings
		@dtype rel_idc: list(Int)
		"""
		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# start with all pricings of this neighbor
		num_neigh_p = len(neigh.pricing_mat)
		neigh_data_idc = range(0,num_neigh_p)
		# exclude raises
		raise_idc = neigh._get_raise_idc()
		rel_idc = [x for x in neigh_data_idc if x not in raise_idc]

		# # keep all raises but exclude those which are only followers
		# # because if they followed us there is no need for us to follow
		# follower_idc = [x[1] for x in self.follower[neigh_id]]
		# leader_idc=[]
		# for (o_idx,n_idx,o_num,n_num) in self.leader_n_idx[neigh_id]:
		# 	leader_idc.append(n_idx)
		# 	if(n_num):
		# 		for i in range(1,n_num+1):
		# 			leader_idc.append(n_idx+i)
		# rel_idc = [x for x in rel_idc if (x not in follower_idc or x in leader_idc )]

		return rel_idc

	def _get_time_series_data(self):
		"""
		Create a minute wise time series from the data in the pricing_mat for all gas types

		@return time_series: the time_series
		@dtype time_series: numpy.array
		"""

		# set the start date of the data
		berlin = pytz.timezone('Etc/GMT-2')
		time_zero = ime(0,0,0,0,berlin)
		init_time = time_zero+timedelta(secs=self.pricing_mat[0,pa2i['time']])
		init_date = INIT_DATE+timedelta(days=self.pricing_mat[0,pa2i['date']])
		start_date = datetime.combine(init_date,init_time)
		# set the stop date of the data
		end_time = init_time+timedelta(secs=self.pricing_mat[-1,pa2i['time']])
		end_date = INIT_DATE+timedelta(days=self.pricing_mat[-1,pa2i['date']])
		stop_date = datetime.combine(end_date, end_time)

		# compute the number of minutes in the interval.
		# we round up for cases where the last change is not on a exact minute
		len_t_series = int(math.ceil((stop_date - start_date).total_seconds()/60))
		# make place for the data
		time_series = np.zeros((len_t_series,3))

		# remember the index where the next value has to go
		idx = 0
		# go through the pricings up to the last one
		for i in range(0,len(self.pricing_mat)-1):
			# get prices
			d = self.pricing_mat[i,pa2i['diesel']]
			e5 = self.pricing_mat[i,pa2i['e5']]
			e10 = self.pricing_mat[i,pa2i['e10']]
			row = [d,e5,e10]
			# get the datetime of the next pricig
			fol_d = self.pricing_mat[i+1,pa2i['date']]
			fol_s = self.pricing_mat[i+1,pa2i['time']]
			fol_time = get_timestamp(fol_d,fol_s)
			# get the minutes from the start up to this next pricings datetime
			len_int = int(math.ceil((fol_time - start_date).total_seconds()/60))
			# set the values from next to set index up to this length
			time_series[idx:len_int] = row
			# set the next index
			idx = len_int

		# set the values of the last pricingon the last line
		d = self.pricing_mat[-1,pa2i['diesel']]
		e5 = self.pricing_mat[-1,pa2i['e5']]
		e10 = self.pricing_mat[-1,pa2i['e10']]
		row = [d,e5,e10]

		return time_series

	#DEP:
	def _explore_time_tree(self, rel_idc, leader, neigh_id , split_criteria, split_vals):
		"""
		There might not be one rule concerning one competitor for the whole time. THere might be different rules for different
		time categories (e.g. weekend vs weekday, morning vs afternoon and many more).
		This funtion iteratively splits up the pricings into ever smaller time intervals. It then generates the rules for the small
		time intervalls and puts neighboring intervalls back together if they have the same rules. at the end it returns the top rule
		which splits up into subrules up to the lowest level where there different rules.

		@param rel_idc: all for the rule relevant pricings (as indices) at this time level
		@dytpe rel_idc: list(Int)

		@param leader: a list of relevant leaders for this time level
		@dtype leader: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@param neigh_id: the identifier for the neighbor
		@dytpe neigh_id: string

		@param split_criteria: a list of keywords identifying how to split the data
		@dytpe split_criteria: list(String)

		@param split_level: the current level of the time tree
		@dytpe split_level: int

		@param split_vals: a list of values identifying the past values for the branches to get to this level
		@dytpe split_vals: list(Int)

		@return split_criteria: the toprule concerning this neighbor
		@dtype splits: Rule
		"""
		if(len(rel_idc)<10):
			return None
		# initialize the new rule for this level
		rule = Rule(self.id, neigh_id, split_criteria[0:len(split_vals)], split_vals, self.analysis_path)
		# get the matching leaders for this level as well as the unreacted pricings
		matches, misses = self._get_matches_and_misses_subsets(rel_idc, leader, neigh_id)
		# pass some values to the count dict of the rule
		counts = {'data':len(rel_idc),'match':len(matches),'miss':len(misses)}
		rule.counts.update(counts)

		# get the match difs
		rule.match_difs, counts = self._get_match_difs(matches, neigh_id)
		# get the miss difs
		rule.miss_difs = self._get_miss_difs(misses, neigh_id)
		# update some counts conderning the matches
		rule.counts.update(counts)
		# get the rules stats
		rule._get_stats(matches, misses)

		# if there are enough pricings in this category that splitting up might be sensible 
		if(len(matches)>=10):
			# check if there are further splits possible
			if(len(split_vals)<len(split_criteria)):
				# get the next split criterium
				next_crit = split_criteria[len(split_vals)]
				# split the data
				data_splits, new_split_vals = self._split_at(rel_idc, neigh_id, next_crit)
				# generate a list of subrules one for each split
				rule.subrules = [None for i in range(0,len(data_splits))]

				# initialize a list of indices, each one points to the respective subrule and stands for a time interval
				rule.sr_idc = []

				# go one level deeper in the tree
				split_vals.append(0)
				for i in range(0,len(data_splits)):
					# add the new split value and get the next rule
					update_s_v = split_vals[:]
					update_s_v[-1] = new_split_vals[i]
					rule.subrules[i] = self._explore_time_tree(data_splits[i], matches, neigh_id, split_criteria, update_s_v)

				# go through all subrules and combine the intervals with equal rules

				# if the first subrule had to few data
				# get the first subrule that is not None because to few data
				# and take those rules values
				# TODO:
				# sr_idx=0
				# rule.sr_idc.append(0)
				# while(sr_idx<len(rule.subrules)-1):
				# 	if(rule.subrules[sr_idx]==rule.subrules[sr_idx+1]):
				# 		rule.subrules.pop(sr_idx+1)
				# 		rule.sr_idc.append(sr_idx)
				# 	else:
				# 		sr_idx+=1
				# 		rule.subrules.pop(sr_idx+1)

				# # if all subrules are the some 
				# if(len(rule.subrules)==1):
				# 	if(rule==rule.subrules[0]):
				# 		rule.subrules = None
				# 		rule.sr_idc = None
				# 	else:

		return rule
		
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

					# # PRINT: the unreacted pricing with the own previous and following pricing
					# print(pricing_to_string(self.pricing_mat[own_idx]))
					# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
					# print(pricing_to_string(self.pricing_mat[own_idx+1]))
					# pause()

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
				# # PRINT: the unreacted pricing with the own previous and following pricing
				# print(pricing_to_string(self.pricing_mat[own_idx]))
				# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
				# print(pricing_to_string(self.pricing_mat[own_idx+1]))
				# pause()

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

						# # PRINT: the unreacted pricing with the own previous and following pricing
						# print(pricing_to_string(self.pricing_mat[own_idx]))
						# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
						# print(pricing_to_string(self.pricing_mat[own_idx+1]))
						# pause()

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
					# # PRINT: the unreacted pricing with the own previous and following pricing
					# print(pricing_to_string(self.pricing_mat[own_idx]))
					# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
					# print(pricing_to_string(self.pricing_mat[own_idx+1]))
					# pause()

					n_idx += 1

		return gas_ignores

	#DEP:
	def _get_matches_and_misses_subsets(self, data_idc_sub, leader, neigh_id):
		"""
		For a list of the neighbors pricings (those which happened in a specific time category) check if a specific
		if the own station reacted on those, meaning check if it is in the respective ńeighbors leader list.
		While doing this generate two lists, one with the leaders which matched a neighbors pricing and one for those where
		there was no own reaction to the neighbors pricing.

		@param data_idc_sub: the list of relevant pricing indeces of the neighbor
		@dtype data_idc_sub: list(Int)

		@param leader: a list of relevant leaders for this time category
		@dtype leader: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return matches: a list of the matching leaders
		@dtype matches: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@return non_matches: a list of those pricings without reaction
		@dtype non_matches: list(Tuple(own_idx,neigh_idx))
						- own_idx: the own pricing index just before the neighbors pricing
						- neigh_idx: the neighbor pricing index
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# prepare the lists
		matches = []
		non_matches = []

		# index for the list of relevant neighbor pricings (data_idc_sub)
		d_idx = 0
		# index for the leader list
		l_idx = 0
		# go until end of one list reached
		while(d_idx < len(data_idc_sub) and l_idx < len(leader)):

			# if the neighbor is a leader add it to the matches and increase both indices
			# the data index has to be increased according to the number of leaders in this leader set
			if(data_idc_sub[d_idx] == leader[l_idx][1]):
				matches.append(leader[l_idx])
				d_idx += 1+leader[l_idx][3]
				l_idx += 1
			
			# if the data neigh index is below the next leader index add it to non matches and increase only the data index
			elif(data_idc_sub[d_idx] < leader[l_idx][1]):
				# get the own_index(meaning of the station in question) from the leader entry
				own_idx = leader[l_idx][0]
				# get neigh index
				neigh_idx = data_idc_sub[d_idx]

				# go back through the own pricings until the pricing is directly before the neighbors pricing (time related)
				# we want this pricing to know the price difference generated by the neighbor
				# be carefull not to go in the negativ index area 
				while(get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])>0 and own_idx>=0):
					own_idx-=1
				# TODO: check if in opening hours:
				# CURRENTLY: check if own index was a raise
				# add the pair of index if it is no raise
				if(own_idx>=0 and get_time_dif(self.pricing_mat[own_idx+1],neigh.pricing_mat[neigh_idx])>2700 and not(is_raise(self.pricing_mat[own_idx]))):
					non_matches.append((own_idx,neigh_idx))

				# # PRINT: the unreacted pricing with the own previous and following pricing
				# print(pricing_to_string(self.pricing_mat[own_idx]))
				# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
				# print(pricing_to_string(self.pricing_mat[own_idx+1]))
				# pause()

				d_idx += 1

			# if the leader index is lower go to the next leader
			else:
				l_idx += 1

		# if there are still neighbor pricings left but no leader the rest are non matches
		if(d_idx < len(data_idc_sub)):
			#get the last leader index of the stations own pricing
			own_idx = leader[l_idx-1][0]
			# go through all neighbor pricings left and add them as non matches
			while(d_idx<len(data_idc_sub)):
				# get neighbor pricing index
				neigh_idx = data_idc_sub[d_idx]
				# go up through own pricing until we are above the neighbor (time related)
				while(get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])<=0):
					own_idx+=1
					# if we reach the end break 
					if(own_idx == len(self.pricing_mat)):
						break
				# go one back so we have the last own index before the neighbor pricing
				own_idx-=1
				if(own_idx+1<len(self.pricing_mat) and get_time_dif(self.pricing_mat[own_idx+1],neigh.pricing_mat[neigh_idx])>2700 and not(is_raise(self.pricing_mat[own_idx]))):
					non_matches.append((own_idx,neigh_idx))
				# # PRINT: the unreacted pricing with the own previous and following pricing
				# print(pricing_to_string(self.pricing_mat[own_idx]))
				# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
				# print(pricing_to_string(self.pricing_mat[own_idx+1]))
				# pause()

				d_idx += 1

		return matches, non_matches

	#DEP:
	def _get_match_difs(self, matches, neigh_id):
		"""
		Gets a difference matrix for pricings and their possible causes.
		The matrix contains all prices after the own reaction on a possibly causing pricing

		@param matches: the list of the all leaders
		@dtype matches: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return price_dif: the difference matrix for all the matches dims(matches,gas)
		@dtype price_dif: numpy.array

		@return counts: dict containing values for number of own pricings that:
							- reset: resetted the previous price difference
							- fuse: fused multiple prcings of the leader to one own
							- split: splitted up a larger leader pricing in several own
		@dtype counts: dict
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# intialize the matrix
		price_dif = np.zeros((len(matches),3,3))

		# set the counts to zero
		reset_cnt = 0
		split_cnt = 0
		fuse_cnt = 0

		#go through all matches
		for i in range(len(matches)):

			# get the matches entry
			(o, l, o_num, l_num) = matches[i]

			# check if the own pricing was a fuse or a split
			if(o_num>l_num):
				split_cnt+=1
			if(o_num<l_num):
				fuse_cnt+=1

			# counters for which prices the leader changed and which the own resetted
			changed = 0
			reset_val = 0

			# get the price differences before, between and after the change
			price_dif[i,0,:] = get_price_dif(self.pricing_mat[o-1],neigh.pricing_mat[l-1])
			price_dif[i,1,:] = get_price_dif(self.pricing_mat[o-1],neigh.pricing_mat[l+l_num])
			price_dif[i,2,:] = get_price_dif(self.pricing_mat[o+o_num],neigh.pricing_mat[l+l_num])

			# for each gas check
			for gas in range(len(GAS)):
				# price dif before the neighbors pricings and after those has changed
				if(price_dif[i,0,gas]!=price_dif[i,1,gas]):
					# add the gas respective value
					changed+=pow(4,gas)
					# check further if the own pricing reseted the previous difference
					if(price_dif[i,0,gas]==price_dif[i,2,gas]):
						# add the gas respective value
						reset_val += pow(4,gas)

			# if all the prices that have been changed are resetted as well
			if(changed==reset_val):
				reset_cnt += 1

		# create the dict of the counts
		counts = {'reset' : reset_cnt, 'fuse' : fuse_cnt, 'split' : split_cnt}
		return price_dif, counts

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

	#DEP
	def _get_miss_difs(self, misses, neigh_id):
		"""
		Gets a difference matrix for pricings without reactions

		@param misses: the pricings without reactions
		@dtype misses: list(Tuple(own_idx,neigh_idx))
						- own_idx: the last own pricing before the neighbors
						- neigh_idx: the index of the neighbors pricing that was not reacted on

		@param neigh_id: the identifier of the neighbor
		@dtype neigh_id: string

		@return miss_difs: the difference matrix for all the misses dims(misses,gas)
		@dtype miss_difs: numpy.array
		"""

		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# copy the differences of the non_matches into a numpy array (non_matches*3)
		miss_difs = np.zeros((len(misses),3))
		# go through all misses
		for i in range(0,len(misses)):
			# get the relevant indices
			(own_idx,neigh_idx) = misses[i]
			# add the difference
			miss_difs[i,:] = get_price_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])
		return miss_difs

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


	######### Printing and Visualizing##########
	def print_neighbors(self):
		"""
		Prints information about all the neighbors of this station like the station informations itself
		and the distance
		"""

		# get neighbors if not done
		if self.neighbors is None: self.get_neighbors(pricing_globals.STATION_DICT)

		# get the header for the list
		header = "%s | " % "DIST".center(6)
		header +=  "%s | %s | %s" % ("BRAND".center(20),
        "ID".center(36),
        "ADDRESS".center(60))

		# print information about what is done
		print(print_bcolors(["BOLD","OKBLUE"],'\nPRINTING NEIGHBORS OF STATION:\n'.center(len(header))))
		print(print_bcolors(["BOLD","OKBLUE"], str(self).center(len(header))))
		print('')

		# print the header for the list
		print(header)
		print(("-" * len(header)))

		# print the information for each neighbor
		for neighbor in self.neighbors:
			station_id = neighbor[0]
			station = pricing_globals.STATION_DICT[station_id]
			station_dist = neighbor[1]
			st_addr = station.address['street'] + " " + station.address['house_number'] + \
				" " + station.address['post_code'] + " " + station.address['place']
			name = station.brand
			if(len(name)==0):
				name = station.name

			row = "%1.4f | "% station_dist
			row += "%s | %s | %s" % (name.center(20),
	        station.id.center(36),
	        st_addr.center(60))
			print(row)

		print("\n")

	def plot_pricing_month_hist(self, date_int):
		"""
		Plot the pricing activity for this station as a month histogram.
		It shows the amount of pricings made in each month from the initial recoding date until now
		"""

		# get the month and the year of the start and end date
		year = INIT_DATE.year
		month = INIT_DATE.month
		to_year = END_DATE.year
		to_month = END_DATE.month

		# initialize barchart data and labels
		month_hist = []
		xTickMarks = []
		# proceed chronilogically until the end date is reach
		while(year<=to_year and month<=to_month):
			# get the count of all pricings in this month
			pricing_globals.CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
				" WHERE " + PG['STID'] + " AND " + PG['MONTH'] + " AND " + PG['YEAR'] % (self.id, month, year))
			# add the count to the chart data
			month_hist.append(pricing_globals.CURSOR.fetchone()[0])
			# create and add the labell for the month
			mstr = '%d. %d' % (month, year)
			xTickMarks.append(mstr)
			# if we are in december go to january and next year
			if(month==12):
				year+=1
				month = 1
			# otherwise to the next month
			else:
				month+=1

		# complete the outer month data 
		month_hist[0] *= (30/INIT_DATE.day)
		month_hist[-1] *= (30/END_DATE.day)

		# create a plot 
		fig = plt.figure()
		ax = fig.add_subplot(111)

		# get the positions and the width of the bars
		ind = np.arange(len(month_hist))
		width = 0.35

		# create the bars
		rects1 = ax.bar(ind, month_hist[:,1], width, color='red')

		label_barchart_rects(rects1, ax)

		# set the labels and title
		ax.set_ylabel('pricings')
		ax.set_xlabel('month')
		ax.set_title('pricing activity - month history')

		# set the x ticks and format them
		ax.set_xticks(ind + width/2)
		xtickNames = ax.set_xticklabels(xTickMarks)
		plt.setp(xtickNames, rotation=60, fontsize=8)
		plt.gcf().subplots_adjust(bottom=0.15)

		# save the figure
		fig.savefig(join(self.analysis_path, 'pricing_activity-month_history'))

	def plot_pricing_hour_hist(self, pricings, title):
		"""
		For all indexed pricings plot a hour historgram.

		@param pricings: the pricing for which a histogram needs to be done
		@dtype pricings: list(Int)

		@return hist: the histogram values
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

		# # PLOT:
		# fig = plt.figure()
		# ax = fig.add_subplot(111)
		# ax.set_title(title,fontsize=20, position=(0.5,1.0), weight='bold')

		# # widt of a bar
		# width = 1
		# # x position of the bars
		# ind = np.arange(len(pricing_hist))

		# # generate the bars with (x position, height, width, color)
		# rects1 = ax.bar(ind, pricing_hist, width, color='blue')
		# rects2 = ax.bar(ind, raise_hist, width, color='red', bottom=pricing_hist)

		# # setup and format the x axis
		# # give it a label
		# ax.set_xlabel('time',fontsize=16, position=(1.05,-0.1))
		# # give it ticks and names
		# ax.set_xticks(ind + width/2)
		# xtickNames = ax.set_xticklabels(ind)
		# # format the ticks
		# plt.setp(xtickNames, fontsize=16, weight='bold')

		# # setup and format the y axis
		# # give it a label
		# ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
		# #reevaluate the ytick positions
		# max_val = max(pricing_hist)
		# ytickpos = ax.get_yticks()
		# if(len(ytickpos)-2>4):
		# 	ytickpos = ytickpos[::2]
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# if(max_val/ytickpos[-1]>0.95):
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# ax.set_yticks(ytickpos)
		# # format the y ticks
		# plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

		# # label the bars
		# label_barchart_rects2(rects1, pricing_hist+raise_hist, ax)

		# # add a legend
		# legend = plt.figlegend((rects1[0], rects2[0]), ('decline', 'raise'), loc='lower center')
		# for label in legend.get_texts():
		# 	label.set_fontsize(20)
		# 	label.set_weight('bold')

		# filedir = join(self.analysis_path, 'hour_distribution')
		# if(not(isdir(filedir))): os.makedirs(filedir)
		# file_name = title
		# dpi = fig.get_dpi()
		# fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		# plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95)
		# fig.savefig(join(filedir,file_name))
		# plt.close(fig)

		return pricing_hist, raise_hist

	def plot_pricing_dow_hist(self, pricings):
		"""
		For all indexed pricings plot a hour historgram.

		@param pricings: the pricing for which a histogram needs to be done
		@dtype pricings: list(Int)

		@return hist: the histogram values
		@dtype date_int: list(int)
		"""	

		pricing_hist = np.zeros((7, ))
		for p_idx in pricings:
			own_p = self.pricing_mat[p_idx]
			if(not(is_raise(own_p))):
				p_time = int(own_p[pa2i['dow']])
				pricing_hist[p_time]+=1


		# # PLOT:
		# fig = plt.figure()
		# ax = fig.add_subplot(111)
		# ax.set_title("dow_distribution", fontsize=20, position=(0.5,1.0), weight='bold')

		# # widt of a bar
		# width = 1
		# # x position of the bars
		# ind = np.arange(len(pricing_hist))

		# # generate the bars with (x position, height, width, color)
		# rects1 = ax.bar(ind, pricing_hist, width, color='blue')

		# # setup and format the x axis
		# # give it a label
		# ax.set_xlabel('dow',fontsize=16, position=(1.05,-0.1))
		# # give it ticks and names
		# ax.set_xticks(ind + width/2)
		# xtickNames = ax.set_xticklabels(ind)
		# # format the ticks
		# plt.setp(xtickNames, fontsize=16, weight='bold')

		# # setup and format the y axis
		# # give it a label
		# ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
		# #reevaluate the ytick positions
		# max_val = max(pricing_hist)
		# ytickpos = ax.get_yticks()
		# if(len(ytickpos)-2>4):
		# 	ytickpos = ytickpos[::2]
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# if(max_val/ytickpos[-1]>0.95):
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# ax.set_yticks(ytickpos)
		# # format the y ticks
		# plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

		# # label the bars
		# label_barchart_rects(rects1, ax)

		# file_name = "dow_distribution"
		# dpi = fig.get_dpi()
		# fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		# plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95)
		# fig.savefig(join(self.analysis_path,file_name))
		# plt.close(fig)

		return pricing_hist

	def write_first_leader_analysis(self):
		"""
		Write down the potential leaders for all pricings 
		"""

		HTMLFILE = 'first_leader_analysis.html'
		f = open(join(self.analysis_path,HTMLFILE), 'w')

		f.write(html_intro('first_leader_analysis'))
		f.write(html_heading(1, 'Analysis all leaders for each pricing:'))

		for own_idx, leaders in self.leader_p_idx.items():
			f.write(html_heading(2,'PRICING INDEX: %d' %(own_idx,)))
			htmlcode = self.leader_per_pricing_as_html_table(own_idx, leaders)
			f.write(htmlcode)
			f.write('<p>')

		f.close()

	def _plot_match_miss_dif_hists(self, match_difs, miss_difs, gas):
		"""
		Generate a barchart indicating possible rules by visualizing the price differences after a reaction
		and when no reaction happend. This is important because the maximal values indicate
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

		# # PLOT:
		# # generate a a figure
		# fig = plt.figure()
		# ax = fig.add_subplot(111)

		# x_labels = unique_comb

		# # set title of the axe
		# ax.set_title(GAS[gas]+'_price_differences',fontsize=20, position=(0.5,1.0), weight='bold')

		# # widt of a bar
		# width = 0.4
		# # x position of the bars
		# ind = np.arange(len(match_c))+(width/2)
		# if(len(match_c)<=3):
		# 	ax.set_xlim(0,5)
		# 	ind+=1.0
		# # generate the bars with (x position, height, width, color)
		# rects1 = ax.bar(ind, match_c, width, color='red')
		# rects2 = ax.bar(ind+width, miss_c, width, color='green')

		# # setup and format the x axis
		# # give it a label
		# ax.set_xlabel('price_dif',fontsize=16, position=(1.05,-0.1))
		# # give it ticks and names
		# ax.set_xticks(ind + width)
		# xtickNames = ax.set_xticklabels(x_labels)
		# # format the ticks
		# plt.setp(xtickNames, fontsize=16, weight='bold')

		# # setup and format the y axis
		# # give it a label
		# ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
		# #reevaluate the ytick positions
		# max_val = max(max(miss_c), max(match_c))
		# ytickpos = ax.get_yticks()
		# if(len(ytickpos)-2>4):
		# 	ytickpos = ytickpos[::2]
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# if(max_val/ytickpos[-1]>0.95):
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# ax.set_yticks(ytickpos)
		# # format the y ticks
		# plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

		# # label the bars
		# label_barchart_rects(rects1,ax)
		# label_barchart_rects(rects2,ax)
		
		# # add a legend
		# legend = plt.figlegend((rects1[0], rects2[0]), ('dif after reaction', 'dif not reacted'), loc='lower center')
		# for label in legend.get_texts():
		# 	label.set_fontsize(20)
		# 	label.set_weight('bold')

		# # save the figure
		# # create a file for the barchart with the name of the rule
		# file_name = '%s_price_differences'%(GAS[gas])
		# dpi = fig.get_dpi()
		# fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		# plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95, hspace=0.2, wspace=0.2)
		# fig.savefig(join(self.analysis_path,file_name))
		# plt.close(fig)

		hists = (unique_comb, match_c, miss_c)
		return hists


	######### Some visualization helpers ##########
	def _plot_day_timeline(self, directory):
		"""
		Plots the pricings of this station and its neighbors for the day for which the data is currently in the pricing
		matice as a timeline
		"""

		# CURRENTLY soecify the ids of the real competitors of the Q1 KSD
		target_ids = ['ebc673e0-8359-4ab6-0afa-c31cc35c4bd2', '8a5b2591-8821-4a36-9c82-4828c61cba29',
		'30d8de2f-7728-4328-929f-b45ff1659901', '51d4b54f-a095-1aa0-e100-80009459e03a',
		'51d4b5a3-a095-1aa0-e100-80009459e03a', 'f4b31676-e65e-4b60-8851-609c107f5d93',
		'90543baf-7517-43cd-9c59-1a2493c26358']

		# get different colors for all neighbors
		colors = get_colors(len(target_ids))
		# set a color index
		c_idx = 0
		# go through all neighbors
		for (station_id, dif) in self.neighbors:
			# CURRENTLY check if it is in the real competitors
			if station_id in target_ids:
				# get the neighbor
				neigh = pricing_globals.STATION_DICT[station_id]
				st_str = str(neigh)
				# get the pricings hour value
				time = neigh.pricing_mat[:,pa2i['time']]/3600
				# for each gas type there is a figure
				# a line for the neighbor to each figure
				plt.figure(1)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['diesel']], where='post', label=st_str, color=colors[c_idx], ls='-.')
				plt.figure(2)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['e5']], where='post', label=st_str, color=colors[c_idx], ls='-.')
				plt.figure(3)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['e10']], where='post', label=st_str, color=colors[c_idx], ls='-.')
				# increase the color index
				c_idx += 1

		# add the own station
		st_str = station_to_string(self.id, False)
		time = self.pricing_mat[:,pa2i['time']]/3600

		plt.figure(1)
		plt.subplot(111)
		plt.step(time, self.pricing_mat[:,pa2i['diesel']], where='post', label=st_str, color=colors[c_idx], ls='-.')
		plt.figure(2)
		plt.subplot(111)
		plt.step(time, self.pricing_mat[:,pa2i['e5']], where='post', label=st_str, color=colors[c_idx], ls='-.')
		plt.figure(3)
		plt.subplot(111)
		plt.step(time, self.pricing_mat[:,pa2i['e10']], where='post', label=st_str, color=colors[c_idx], ls='-.')

		day = get_date(self.pricing_mat[0,pa2i['date']])
		w_day = dow_to_string[self.pricing_mat[0,pa2i['dow']]]
		# go through the figures
		for i in range(len(GAS)):
			# get the figure
			plt.figure(i+1)
			# set the title
			plt.title(GAS[i] + '   ' + str(day) + '   ' + w_day)
			# set x and y ticks
			ax = plt.gca()
			ax.set_xticks(range(0,24))
			yticks = ax.get_yticks()
			ax.set_yticks(np.arange(min(yticks), max(yticks)+1, 2.0))
			ax.set_yticklabels(ax.get_yticks()/100)

			# set the labels
			ax.set_xlabel('time in hours')
			ax.set_ylabel('price in Euro')
			# make a grid for easier reference in the plot
			ax.grid(b = True, 
	          which = 'both', 
	          axis = 'y', 
	          color = 'Gray', 
	          linestyle = '--', 
	          alpha = 0.5,
	          linewidth = 1)
			ax.grid(b = True, 
	          which = 'both', 
	          axis = 'x', 
	          color = 'Gray', 
	          linestyle = '--', 
	          alpha = 0.5,
	          linewidth = 1)

			# located the labels
			handles, labels = ax.get_legend_handles_labels()
			lgd = ax.legend(handles, labels, loc='upper center')
			# generate a hd figure
			dpi = plt.figure(i).get_dpi()
			plt.figure(i).set_size_inches(1920.0/float(dpi),1080.0/float(dpi))

			# safe the figure with the gas as name
			file_name = GAS[i]
			plt.savefig(join(directory,file_name), bbox_extra_artists=(lgd,), bbox_inches='tight')

	def _get_leader_env_as_html_table(self, neigh_id, leader):
		"""
		Parses the information about a leader tuple into an html table. It adds the previous and posterior pricing as well.
		A pricing in this table consist of an owner identifier, the time, the diffences to the competitor, the changed values
		and the prices themselves

		@param neigh_id: the id of the station of the leading pricing
		@dtype neigh_id: string

		@param leader: the leader tuple that needs to be printed
		@dtype leader: tuple(own_idx,neigh_idx,o_num,n_num)
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@return htmlcode: the leader pricings enviroment as a html table
		@dtype htmlcode: string
		"""

		# get the leader fields
		own_idx,neigh_idx,o_num,n_num = leader[:]
		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# initialize the table data
		table_data = []

		# get the previous pricings for checking which to print 
		o_pos = own_idx-1
		n_pos = neigh_idx-1
		own_p = self.pricing_mat[o_pos]
		neigh_p = neigh.pricing_mat[n_pos]

		# get the price difference of the created by the next pricing to print
		# so the difference is between the current printing pricing and the last one of the other side
		d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)

		# get the time difference of the two previous pricings
		t_dif = get_time_dif(own_p, neigh_p)
		# if the own one is nearer to the leader append the own one
		if(t_dif>0):
			# add it to the table
			table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_date(own_p[pa2i['date']]), get_time(own_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])

		# if the neighbors is nearer append this one
		else:
			# add it to the table
			table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_date(neigh_p[pa2i['date']]), get_time(neigh_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
				neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

		# add the neigbors set
		while(n_pos<neigh_idx+n_num):
			# get the next neighbor pricing
			n_pos+=1
			neigh_p = neigh.pricing_mat[n_pos]
			# get the price difference to the last own
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			# add it to the table
			table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_date(neigh_p[pa2i['date']]), get_time(neigh_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
				neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

		# add the own set
		while(o_pos<own_idx+o_num):
			# get the own neighbor pricing
			o_pos+=1
			own_p = self.pricing_mat[o_pos]
			# get the price difference to the last neighbor
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			# add it to the table
			table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_date(own_p[pa2i['date']]), get_time(own_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])

		# check out directly following pricing
		# get both next prcings
		if(o_pos+1<len(self.pricing_mat) and n_pos+1<len(neigh.pricing_mat)):
			own_p = self.pricing_mat[o_pos+1]
			neigh_p = neigh.pricing_mat[n_pos+1]
			# get the time difference
			t_dif = get_time_dif(own_p, neigh_p)
			# if the neighbor has the next pricing
			if(t_dif>0):
				# get the last own pricing
				own_p = self.pricing_mat[o_pos]
				# get the price difference
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				# add the neighbor to the table
				table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_date(neigh_p[pa2i['date']]), get_time(neigh_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
					neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

			# if the next pricing is an own one
			else:
				# get the previous neighbors pricing
				neigh_p = neigh.pricing_mat[n_pos]
				# get the price difference
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				# add the own one to the table
				table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_date(own_p[pa2i['date']]), get_time(own_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
					own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])

		# print the tabel with header to html table code
		htmlcode = HTML.table(table_data,
		    header_row = ['role', 'date', 'time',HTML.TableCell('dif', attribs={'colspan':3}),
		    HTML.TableCell('changed', attribs={'colspan':3}), HTML.TableCell('price', attribs={'colspan':3})])
		return htmlcode

	def _leader_per_pricing_as_html_table(self, o_idx, leaders):
		"""
		Generate a html table for all the different leaders of an own pricing.
		Start with the own pricings and then add all the others seperated by an empty line.
		A row contains the role of the pricing's owner, the time, the changed values and the current prices

		CURRENTLY it highlights the real concurrence

		@param o_idx: the index of the own pricing
		@dtype o_idx: int

		@param leader: the list of leaders of this pricing
		@dtype leader: list(Tuple(neigh_id,neigh_idx,o_num,n_num))
						- neigh_id: the identifier of the respetive competitor
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@return htmlcode: the leader pricings enviroment as a html table
		@dtype htmlcode: string
		"""

		# this is the list of the current competitors of the Q1_KSD
		competitors =  ['8a5b2591-8821-4a36-9c82-4828c61cba29', 'ebc673e0-8359-4ab6-0afa-c31cc35c4bd2',
		'30d8de2f-7728-4328-929f-b45ff1659901', '51d4b54f-a095-1aa0-e100-80009459e03a', '51d4b5a3-a095-1aa0-e100-80009459e03a',
		'f4b31676-e65e-4b60-8851-609c107f5d93']

		# a list with a readable identifier
		com_to_str = ['ARAL', 'SCORE', 'RATIO', 'JET_IB', 'JET_HA', 'SHELL']
		# the rows for the table
		table_data = []
		# add all own pricings
		for i in range(o_num+1):
			own_p = self.pricing_mat[o_idx+i]
			table_data.append([HTML.TableCell('own', bgcolor='black'), get_time(own_p[pa2i['time']],False),
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])
		# add an empty row
		table_data.append(HTML.TableCell('', attribs={'colspan':8, 'height':'10px'}))

		# add the prcings of each leader
		for (neigh_id,neigh_idx,o_num,n_num) in leaders:
			# get the neighbor
			neigh = pricing_globals.STATION_DICT[neigh_id]
			neigh_p = neigh.pricing_mat[neigh_idx]
			# clarify the role
			if(neigh_id in competitors):
				com = com_to_str[competitors.index(neigh_id)]
				first_cell = HTML.TableCell(con, bgcolor='#3bb300')
			else:
				first_cell = HTML.TableCell('NO_CON', bgcolor='#cc0000')
			# add all prcings
			for j in range(n_num+1):
				neigh_p = neigh.pricing_mat[neigh_idx+j]
				table_data.append([first_cell, get_time(neigh_p[pa2i['time']],False),
					neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
					neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])
			# add a free row after each leader
			table_data.append(HTML.TableCell('', attribs={'colspan':8, 'height':'10px'}))

		htmlcode = HTML.table(table_data,
		    header_row = ['role', 'time', HTML.TableCell('changed', attribs={'colspan':3}), HTML.TableCell('price', attribs={'colspan':3})])
		return htmlcode

	def _reaction_html_table_single(self, neigh_id, reaction, lead_t, hit_role):
		"""
		Parses the information about a reaction into an html table. It adds the previous and posterior pricing as well.
		A pricing in this table consist of an owner identifier, the time, the diffences to the competitor, the changed values
		and the prices themselves

		@param neigh_id: the id of the station of the leading pricing
		@dtype neigh_id: string

		@param reaction: the reaction tuple that needs to be printed
		@dtype reaction: tuple(own_idx,neigh_idx)
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index

		@return htmlcode: the leader pricings enviroment as a html table
		@dtype htmlcode: string
		"""

		# get the leader fields
		own_idx,neigh_idx = reaction[:]
		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# initialize the table data
		table_data = []

		action = neigh.pricing_mat[neigh_idx]
		reaction = self.pricing_mat[own_idx]

		# get the own and neigh index the reaction interval before and after the pricing
		own_first = own_idx
		dif = 0
		while(own_first>0 and dif>-lead_t):
			own_first -=1
			own_p = self.pricing_mat[own_first]
			dif = get_time_dif(own_p, action)

		own_last = own_idx
		while(own_last<len(self.pricing_mat)-1 and dif<lead_t):
			own_last +=1
			own_p = self.pricing_mat[own_last]
			dif = get_time_dif(own_p, reaction)

		neigh_first = neigh_idx
		dif = 0
		while(neigh_first>0 and dif>-lead_t):
			neigh_first -=1
			neigh_p = neigh.pricing_mat[neigh_first]
			dif = get_time_dif(neigh_p, action)

		neigh_last = neigh_idx
		while(neigh_last<len(neigh.pricing_mat)-1 and dif<lead_t):
			neigh_last +=1
			neigh_p = neigh.pricing_mat[neigh_last]
			dif = get_time_dif(neigh_p, reaction)

		# go to the pricings before ones that get printed
		cur_own = own_first
		cur_neigh = neigh_first
		own_role = 'prev_hour'
		neigh_role = 'prev_hour'

		# print all pricings
		while(cur_own<own_last-1 or cur_neigh<neigh_last-1):
			if(cur_own==len(self.pricing_mat)-2 or cur_neigh==len(neigh.pricing_mat)-2):
				break
			own_p = self.pricing_mat[cur_own+1]
			neigh_p = neigh.pricing_mat[cur_neigh+1]
			time_dif = get_time_dif(own_p, neigh_p)
			if(time_dif<0):
				cur_own += 1
				neigh_p = neigh.pricing_mat[cur_neigh]
				if(cur_own==own_idx):
					own_role = hit_role[0]
					neigh_role = 'post_hour'
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				table_data.append([HTML.TableCell(own_role, bgcolor='#3bb300'), get_date(own_p[pa2i['date']]), get_time(own_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
					own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])
				if(cur_own==own_idx):
					own_role = 'post_hour'
			else:
				cur_neigh += 1
				own_p = self.pricing_mat[cur_own]
				if(cur_neigh==neigh_idx):
					neigh_role = hit_role[1]
					own_role = hit_role[2]
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				table_data.append([HTML.TableCell(neigh_role, bgcolor='#cc0000'), get_date(neigh_p[pa2i['date']]), get_time(neigh_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
					neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])
				if(cur_neigh==neigh_idx):
					neigh_role = hit_role[3]

		# print the tabel with header to html table code
		htmlcode = HTML.table(table_data,
		    header_row = ['role', 'date', 'time',HTML.TableCell('dif', attribs={'colspan':3}),
		    HTML.TableCell('changed', attribs={'colspan':3}), HTML.TableCell('price', attribs={'colspan':3})])
		# # DEBUG:
		# pause()
		return htmlcode

	def _ignore_html_table_single(self, neigh_id, ignore, lead_t):
		"""
		Parses the information about a reaction into an html table. It adds the previous and posterior pricing as well.
		A pricing in this table consist of an owner identifier, the time, the diffences to the competitor, the changed values
		and the prices themselves

		@param neigh_id: the id of the station of the leading pricing
		@dtype neigh_id: string

		@param ignore: the ignore tuple that needs to be printed
		@dtype ignore: tuple(own_idx,neigh_idx)
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index

		@return htmlcode: the leader pricings enviroment as a html table
		@dtype htmlcode: string
		"""

		# get the leader fields
		own_idx,neigh_idx = ignore[:]
		# get the neighbor
		neigh = pricing_globals.STATION_DICT[neigh_id]
		# initialize the table data
		table_data = []

		action = neigh.pricing_mat[neigh_idx]
		prev_action = self.pricing_mat[own_idx]

		# get the own and neigh index the reaction interval before and after the pricing
		own_first = own_idx
		dif = 0
		while(own_first>0 and dif>-lead_t):
			own_first -=1
			own_p = self.pricing_mat[own_first]
			dif = get_time_dif(own_p, prev_action)

		own_last = own_idx
		while(own_last<len(self.pricing_mat)-1 and dif<lead_t):
			own_last +=1
			own_p = self.pricing_mat[own_last]
			dif = get_time_dif(own_p, action)

		neigh_first = neigh_idx
		dif = 0
		while(neigh_first>0 and dif>-lead_t):
			neigh_first -=1
			neigh_p = neigh.pricing_mat[neigh_first]
			dif = get_time_dif(neigh_p, prev_action)

		neigh_last = neigh_idx
		while(neigh_last<len(neigh.pricing_mat)-1 and dif<lead_t):
			neigh_last +=1
			neigh_p = neigh.pricing_mat[neigh_last]
			dif = get_time_dif(neigh_p, action)

		# go to the pricings before ones that get printed
		cur_own = own_first
		cur_neigh = neigh_first
		own_role = 'prev_hour'
		neigh_role = 'prev_hour'

		# print all pricings
		while(cur_own<own_last-1 or cur_neigh<neigh_last-1):
			own_p = self.pricing_mat[cur_own+1]
			neigh_p = neigh.pricing_mat[cur_neigh+1]
			time_dif = get_time_dif(own_p, neigh_p)
			if(time_dif<0):
				cur_own += 1
				neigh_p = neigh.pricing_mat[cur_neigh]
				if(cur_own==own_idx):
					own_role = 'prev_action'
				elif(cur_own>own_idx):
					own_role = 'post_hour'
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				table_data.append([HTML.TableCell(own_role, bgcolor='#3bb300'), get_date(own_p[pa2i['date']]), get_time(own_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
					own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])
			else:
				cur_neigh += 1
				own_p = self.pricing_mat[cur_own]
				if(cur_neigh==neigh_idx):
					neigh_role = 'action'
				elif(cur_neigh>neigh_idx):
					neigh_role = 'post_hour'
				d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
				table_data.append([HTML.TableCell(neigh_role, bgcolor='#cc0000'), get_date(neigh_p[pa2i['date']]), get_time(neigh_p[pa2i['time']],False),
					d_dif, e5_dif, e10_dif,
					neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
					neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

		# print the tabel with header to html table code
		htmlcode = HTML.table(table_data,
		    header_row = ['role', 'date', 'time',HTML.TableCell('dif', attribs={'colspan':3}),
		    HTML.TableCell('changed', attribs={'colspan':3}), HTML.TableCell('price', attribs={'colspan':3})])
		return htmlcode

	def _write_exception_table(self, f, neigh_id, dist_val, dist_reacts, dist_ignores, lead_t):
		# write a header for the distance
		f.write(html_heading(1, "DISTANCE: " + str(dist_val)))
		# write a header for the reaction type
		f.write(html_heading(2, "AFTER OWN REACTION:"))
		# write the outlier as html table
		for react in dist_reacts:
			f.write("<div class=\"floating-box\">\n")
			f.write(self._reaction_html_table_single(neigh_id, react, lead_t, ["reaction","action","bet", "bet"]))
			f.write("</div>\n")
			f.write('<br>\n')
			f.write('<br>\n')
		# write a header for the reaction type
		f.write(html_heading(2, "AFTER IGNORED PRICINGS:"))
		# write the outlier as html table
		for ignore in dist_ignores:
			f.write("<div class=\"floating-box\">\n")
			f.write(self._ignore_html_table_single(neigh_id, ignore, lead_t))
			f.write("</div>\n")
			f.write('<br>\n')
			f.write('<br>\n')




class Rule(object):
	__slots__ = ('owner', 'competitor','gas_type',
		'max_p_dist', 'conf', 'support', 'exceptions', 'matches', 'total',
		'rule_data',
		'day_distrib', 'hour_distrib',
		'day_rule', 'hour_rule',
		'day_data', 'hour_data',
		'mean_rtime', 'dev_rtime',
		'from_date', 'to_date',
		'analysis_path')

	def __init__(self, owner, competitor, gas_type, date_int, analysis_path, max_p_dist, confidence, reactions, ignores, exceptions, total):
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
		@ivar   analysis_path: The directory where to save generated output
		@dtype  analysis_path: string
		"""
		self.analysis_path = join(analysis_path, gas_type + "_rules")
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
		print(max_p_dist)
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

	def write_stats_analysis(self):
		"""
		Generate a html page for this rule based on its valus.
		"""
		# get the strings for the stations
		own_str = str(pricing_globals.STATION_DICT[self.owner])
		neigh_str = str(pricing_globals.STATION_DICT[self.competitor])
		# get maximal linewidth
		linewidth = max(len(own_str),len(neigh_str)) + 10

		# go to the directory of the difference of the rule
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
		# create a file to save irregularities
		file_name = self.gas_type + "_dist_" + str(self.max_p_dist) + '.html'
		f = open(join(self.analysis_path,file_name), 'w')

		# write a intro
		f.write(html_intro(self.gas_type + "_dist_" + str(self.max_p_dist)))
		# the gastype distance is the header
		head_str = (self.gas_type + ':' + str(self.max_p_dist)).center(linewidth)
		f.write(html_heading(2, head_str))

		# timespans in days comes next
		f.write(html_heading(3, "Timespan:"))
		f.write("<p style=\"font-size:14px; font-style:italic;\">\n")
		f.write((str(self.from_date) + " - " + str(self.to_date) + "\n").center(linewidth))
		f.write("</p>\n")

		# then the two stations
		f.write(html_heading(3, "Between:"))
		f.write("<p style=\"font-size:14px; font-style:italic;\">\n")
		f.write((own_str + "\n<br>\n").center(linewidth))
		f.write(("and" + "\n<br>\n").center(linewidth))
		f.write((neigh_str + "\n<br>\n").center(linewidth))
		f.write("</p>\n")

		# the day days as a list
		day_str = ""
		for i in range(0,len(self.day_rule)):
			if(self.day_rule[i]):
				day_str+=dow_to_string[i].center(linewidth) + "\n<br>\n"
		if(len(day_str)==0):
			day_str = "no days"

		f.write(html_heading(3, "Time:"))
		f.write("<p style=\"font-size:14px; font-weight:bold;\">\n")
		f.write(day_str)
		f.write("</p>\n")

		# then the hours
		hour_str = ""
		start=0
		end=0
		i=0
		while(i<len(self.hour_rule)):
			while(i<len(self.hour_rule) and not(self.hour_rule[i])):
				i+=1
			start=i
			if(i==len(self.hour_rule)):
				break
			while(i<len(self.hour_rule) and self.hour_rule[i]):
				i+=1
			end=i
			hour_str += ("%d:00 - %d:00 Uhr"%(start,end)).center(linewidth) + "\n<br>\n"

		if(len(hour_str)==0):
			hour_str = "no hours"


		f.write(hour_str)
		f.write("</p>\n")

		# Reaktionstimes
		f.write(html_heading(3, "Reaktiontime:"))
		f.write("<p style=\"font-size:14px; font-weight:bold;\">\n")
		f.write(("mean: %d"%(self.mean_rtime, )).center(linewidth) + "\n<br>\n")
		f.write(("st_dev: %d"%(self.dev_rtime, )).center(linewidth) + "\n<br>\n")
		f.write("</p>\n")

		# all the rule related stats
		f.write(html_heading(3, "Stats:"))
		f.write("<p style=\"font-size:14px; font-weight:bold;\">\n")
		f.write(("confidence: %1.4f"%(self.conf, )).center(linewidth) + "\n<br>\n")
		f.write(("support: %d"%(self.support, )).center(linewidth) + "\n<br>\n")
		f.write(("matches: %d"%(self.matches, )).center(linewidth) + "\n<br>\n")
		f.write(("exceptions: %d"%(self.exceptions, )).center(linewidth) + "\n<br>\n")
		f.write(("influence: %1.4f"%(float(self.matches)/self.total, )).center(linewidth) + "\n<br>\n")
		f.write("</p>\n")


		# write the end
		f.write(html_end())
		f.close()
		
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
		ig_hour_hist, re_hour_hist = self._plot_pricing_hour_hist(reactions, ignores)
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
		ig_day_hist, re_day_hist = self._plot_pricing_day_hist(reactions, ignores)
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

	def _plot_pricing_hour_hist(self, reactions, ignores):
		"""
		For all the pricings supporting this rule make a time histogram.

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

		# # PLOT:
		# fig = plt.figure()
		# ax = fig.add_subplot(111)
		# ax.set_title('dist_%d-hour_distribution' %(self.max_p_dist,),fontsize=20, position=(0.5,1.0), weight='bold')

		# # widt of a bar
		# width = 1
		# # x position of the bars
		# ind = np.arange(len(ignored_hist))

		# # generate the bars with (x position, height, width, color)
		# rects1 = ax.bar(ind, match_hist, width, color='red')
		# rects2 = ax.bar(ind, ignored_hist, width, color='green', bottom=match_hist)
		# # setup and format the x axis
		# # give it a label
		# ax.set_xlabel('time',fontsize=16, position=(1.05,-0.1))
		# # give it ticks and names
		# ax.set_xticks(ind + width/2)
		# xtickNames = ax.set_xticklabels(ind)
		# # format the ticks
		# plt.setp(xtickNames, fontsize=16, weight='bold')

		# # setup and format the y axis
		# # give it a label
		# ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
		# #reevaluate the ytick positions
		# comb_hist = ignored_hist+match_hist
		# max_val = max(comb_hist)
		# ytickpos = ax.get_yticks()
		# if(len(ytickpos)-2>4):
		# 	ytickpos = ytickpos[::2]
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# if(max_val/ytickpos[-1]>0.95):
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# ax.set_yticks(ytickpos)
		# # format the y ticks
		# plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

		# # label the bars
		# label_barchart_rects2(rects1,match_hist+ignored_hist,ax)

		# if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
		# # create a file for the barchart with the name of the rule
		# file_name = "dist_%d-hour_distribution"%(self.max_p_dist,)
		# dpi = fig.get_dpi()
		# fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		# plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95)
		# fig.savefig(join(self.analysis_path,file_name))
		# plt.close(fig)

		return ignored_hist,match_hist

	def _plot_pricing_day_hist(self, reactions, ignores):
		"""
		For all the pricings supporting this rule make a day histogram.

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


		# # PLOT:
		# fig = plt.figure()
		# ax = fig.add_subplot(111)
		# ax.set_title('dist_%d-day_distribution' %(self.max_p_dist,),fontsize=20, position=(0.5,1.0), weight='bold')

		# # widt of a bar
		# width = 1
		# # x position of the bars
		# ind = np.arange(len(ignored_hist))

		# # generate the bars with (x position, height, width, color)
		# rects1 = ax.bar(ind, match_hist, width, color='red')
		# rects2 = ax.bar(ind, ignored_hist, width, color='green', bottom=match_hist)
		# # setup and format the x axis
		# # give it a label
		# ax.set_xlabel('dow',fontsize=16, position=(1.05,-0.1))
		# # give it ticks and names
		# ax.set_xticks(ind + width/2)
		# xtickNames = ax.set_xticklabels([dow_to_string[dow] for dow in range(len(ignored_hist))])
		# # format the ticks
		# plt.setp(xtickNames, fontsize=16, weight='bold')

		# # setup and format the y axis
		# # give it a label
		# ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
		# #reevaluate the ytick positions
		# comb_hist = ignored_hist+match_hist
		# max_val = max(comb_hist)
		# ytickpos = ax.get_yticks()
		# if(len(ytickpos)-2>4):
		# 	ytickpos = ytickpos[::2]
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# if(max_val/ytickpos[-1]>0.95):
		# 	ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
		# ax.set_yticks(ytickpos)
		# # format the y ticks
		# plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

		# # label the bars
		# label_barchart_rects(rects2,ax)

		# if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
		# # create a file for the barchart with the name of the rule
		# file_name = "dist_%d-day_distribution"%(self.max_p_dist,)
		# dpi = fig.get_dpi()
		# fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		# plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95)
		# fig.savefig(join(self.analysis_path,file_name))
		# plt.close(fig)

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

class NumpyAwareJSONEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, np.ndarray):
			return {'__np.ndarray__': True, 'items': obj.tolist()}
		try:
			return json.JSONEncoder.default(self, obj)
		except TypeError:
			if(isinstance(obj,np.bool_)):
				return int(obj)
			else:
				print("Encountered not json compatible obj")
				print(obj)
				sys.exit()

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

def json_object_hook(obj):
    if '__np.ndarray__' in obj:
    	return np.array(obj['items'])
    else:
        return obj

def safe_test_dict(obj, filename):
	file_dir = join(ANALYSIS_PATH,"TESTING_DATA")
	if(not(isdir(file_dir))): os.makedirs(file_dir) 
	j=json.dumps(obj,cls=NumpyAwareJSONEncoder,indent=4)
	f=open(join(file_dir,filename),"w")
	f.write(j)
	f.close()

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

	ana_day = datetime(2016,7,11).date()

	try:
		con = psycopg2.connect(database='pricing_31_8_16', user='kai', password='Sakral8!')
		# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
		pricing_globals.CURSOR = con.cursor()
		pricing_globals.STATION_DICT = get_station_dict()

		# plot_pricing_month_hist()
		test_stations_plz = ['49078','49191', '39291', '34314', '37688', '15859',
		'44577', '13156', '53474']
		test_station_city = ['Osnabrück', 'Belm', 'Möser', 'Espenau', 'Beverungen', 'Storkow',
		'Castrop-Rauxel', 'Berlin', 'Bad Neuenahr-Ahrweiler']
		test_station_street = ['Kurt-Schuhmacher-Damm', 'Haster Str', 'Chaussee', 'Weimarer Weg', 'Bahnhofstr', 'Heinrich-Heine-Str',
		'Dattelner Str', 'Blankenburger Str', 'Sebastianstr']
		test_station_brand = ['Q1', 'Tankstelle', 'Q1', 'Q1', 'Q1', 'Q1',
		'bft', 'bft', 'bft']

		run_modes = {
			"default" : [2700, (5,5,20),False,False,3,0.5,0.03],
			"lead_t" : [1800, (5,5,20),False,False,3,0.5,0.03],
			"n_vals" : [2700, (5,10,20),False,False,3,0.5,0.03],
			"one_rule" : [2700, (5,5,20),True,False,3,0.5,0.03],
			"com_conf_div" : [2700, (5,5,20),False,True,3,0.5,0.03],
			"hour_min" : [2700, (5,5,20),False,False,5,0.5,0.03],
			"rule_conf" : [2700, (5,5,20),False,False,3,0.99,0.03],
			"com_conf" : [2700, (5,5,20),False,False,3,0.5,0.1]}
		for run_mode in run_modes.keys():
			run_vals = run_modes[run_mode]
			print("running in mode: " + run_mode)

			for i in range(0,len(test_stations_plz)):
				pricing_globals.CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(test_stations_plz[i],test_station_brand[i]))
				gas_station_id = pricing_globals.CURSOR.fetchall()[0][0]
				station = pricing_globals.STATION_DICT[gas_station_id]

				# print station details
				print('analysing station:')
				print(str(station) + ' ' + station.id) 

				# get the stations competition
				print('getting the stations competition')
				station.get_competition(d_int=(from_date,to_date),lead_t=run_vals[0],n_vals=run_vals[1], one_rule=run_vals[2], com_conf_div=run_vals[3], hour_min=run_vals[4], rule_conf=run_vals[5], com_conf=run_vals[6])

				print('saving the json file')
				station.save_json(join(join(ANALYSIS_PATH,"TESTING_DATA"),run_mode))

				# station.check_Granger_Causality()

			safe_test_dict(TESTING_DATA,run_mode+".json")
			TESTING_DATA = {}



	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()