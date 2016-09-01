# -*- coding: utf-8 -*-
import os, sys, traceback, copy
from os.path import join, realpath, dirname, isdir

# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
# the analysis_docs path is the projects subfolder for outputs to be analysed
ANALYSIS_PATH = join(MODUL_PATH, "analysis_docs")

# python postgres api
import psycopg2
import operator
import collections
# pyhton timezone library
import pytz
from datetime import datetime, timedelta, time
from math import sin, cos, atan2, sqrt, radians, atan, pi
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import colorsys
# python 
from geopy.geocoders import Nominatim

import statsmodels.tsa.stattools as st

import HTML

# import warnings
# warnings.simplefilter("error")

# dict from station_id to station instance
STATION_DICT = None
# postgresql cursor object
CURSOR = None
# Postgresql help dict for querying
PG = {
	'STID' : "stid = %s",
	'DATE' : "date::date = %s",
	'DATE_INT' : "date::date >= %s AND date::date <= %s",
	'MONTH' : "EXTRACT(MONTH FROM date) = %s",
	'YEAR' : "EXTRACT(MONTH FROM date) = %s",
	'HOUR_INT' : "EXTRACT(HOUR FROM date) >= %s AND EXTRACT(HOUR FROM date) <= %s",
	'HOUR' : "EXTRACT(HOUR FROM date) >= %s",
	'DOW' : "EXTRACT(DOW FROM date) = %s",
	'DOW_INT' : "EXTRACT(DOW FROM date) >= %s AND EXTRACT(DOW FROM date) <= %s"
}

SECS_PER_DAY = 86400
dow_to_string = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
# list of gasolines
GAS = ['diesel', 'e5', 'e10']
# start and end date of data
INIT_DATE = datetime(2014,6,8).date()
END_DATE = datetime(2016,4,17).date()

# Pricing attribute to index
pa2i = {
	'id' : 0,
	'date' : 1,
	'dow' : 2,
	'month' : 3,
	'time' : 4,
	'alt' : 5,
	'diesel' : 6,
	'd_diesel' : 7,
	'e5' : 8,
	'd_e5' : 9,
	'e10' : 10,
	'd_e10' : 11,
	'pref'	: 12,
	'we' : 13 
}

class Station(object):
	__slots__ = ('id', 'version', 'version_time', 'name', 'brand', 'address', 'geo_pos',
		'neighbors', 'pricing_mat', 'leader_n_idx', 'leader_p_idx', 'follower', 'analysis_path',
		'rule')

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
		self.leader_n_idx = None
		"""
		@ivar   leader: The price leaders of this station, meaning stations that
						cause this station to change its price.
						Its a dict of lists of tuples: {'neigh_id':[(opi,npi),...],
														...}
						For each neighbor it stores the indeces of those pricing
						pairs where the own pricing closely follows onto a
						neighbor pricing.
							neigh_id:= the id of the respective neighbor
							opi:= the own pricing index
							npi:= neighbor pricing index
		@dtype  leader: C{dict}
		"""
		self.leader_p_idx = None
		"""
		@ivar   leader_p_idx: The price leaders of this station, meaning stations that
						cause this station to change its price.
						Its a dict assigning each indexed pricing a lists of tuples: {'opi':[(neigh_id,npi,dif),...],
														...}
						For each neighbor it stores the indeces of those pricing
						pairs where the own pricing closely follows onto a
						neighbor pricing.
							neigh_id:= the id of the respective neighbor
							opi:= the own pricing index
							npi:= neighbor pricing index
							dif.=the time difference to the opi
		@dtype  leader_p_idx: C{dict}
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

		self.analysis_path = ANALYSIS_PATH
		self.rule = None
	
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
			CURSOR.execute("SELECT * FROM gas_station_information_history"+
				" WHERE " + PG['STID'] + " AND " + PG['DATE_INT'] + " ORDER BY date DESC", (self.id, first_val_date, first_val_date))
			prev_price = CURSOR.fetchone()

		# get all pricings for the station in the interval
		CURSOR.execute("SELECT * FROM gas_station_information_history"+
			" WHERE " + PG['STID'] + " AND " + PG['DATE_INT'] + " ORDER BY date", (self.id, from_date, to_date))

		# assign space for the pricing data
		cnt = CURSOR.rowcount
		self.pricing_mat = np.zeros((cnt,len(pa2i)))

		# if the interval starts at the initial we have to neglect the first pricing
		# so te previous is the first pricing
		if prev_price is None:
			prev_price = CURSOR.fetchone()
			# count is reduced by the first one
			cnt -= 1

		# get all pricings
		for i in range(0,cnt):
			fol_price=CURSOR.fetchone()

			self.pricing_mat[i,pa2i['id']] = fol_price[0]
			c_date = fol_price[5].date()
			self.pricing_mat[i,pa2i['date']] = (c_date - INIT_DATE).days
			c_time = fol_price[5].time()
			self.pricing_mat[i,pa2i['dow']] = int(fol_price[5].weekday())
			self.pricing_mat[i,pa2i['we']] = self.pricing_mat[i,pa2i['dow']]/5
			self.pricing_mat[i,pa2i['month']] = fol_price[5].date().month
			self.pricing_mat[i,pa2i['time']] = c_time.hour*3600 + c_time.minute*60 + c_time.second
			c_changed = fol_price[6]
			self.pricing_mat[i,pa2i['alt']] = c_changed
			c_diesel = fol_price[4]
			self.pricing_mat[i,pa2i['diesel']] = float(c_diesel)/10
			c_e5 = fol_price[2]
			self.pricing_mat[i,pa2i['e5']] = float(c_e5)/10
			c_e10 = fol_price[3]
			self.pricing_mat[i,pa2i['e10']] = float(c_e10)/10

			d_dif = (c_diesel - prev_price[4])/10
			self.pricing_mat[i,pa2i['d_diesel']] = d_dif
			e5_dif = (c_e5 - prev_price[2])/10
			self.pricing_mat[i,pa2i['d_e5']] = e5_dif
			e10_dif = (c_e10 - prev_price[3])/10
			self.pricing_mat[i,pa2i['d_e10']] = e10_dif

			# the new previous one is the just added pricing
			prev_price = fol_price

		if(rem_outlier):
			self.remove_outlier_from_pricing()

		return

	def get_neighbors(self, init_range=5, min_cnt=2, max_cnt=20):
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
		for station in STATION_DICT.values():
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

	def get_competition(self, d_int, lead_t=2700, split_criteria=['all','we','dow']):
		'''
		Gets a stations competitors. A competitor is another station in the neighborhood
		that the stations itself acts upon in a regular rule based fashion.
		The rules are solely derived by the prisings done(!) that means there might be a rule
		which simply does not appear in the data and there might be none but the data
		suggests that there is a dependency

		The function does the following steps:
			- get own pricing
			- get all neighbors
			- get their pricings
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
		self.analysis_path = join(self.analysis_path, str(d_int[0]).replace("-","_")+"-"+str(d_int[1]).replace("-","_"))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
		self.analysis_path = join(self.analysis_path, str(self).replace(" ", "_").replace(".", "-"))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)

		# get the own pricing
		self.get_pricing(d_int)
		# get all neighbors pricings
		self.get_neighbors()
		# get the neighbors pricings
		for (neigh_id, dif) in self.neighbors:
			neigh = STATION_DICT[neigh_id]
			neigh.get_pricing(d_int)
		
		# get all related pricing pairs (related means close in time)
		self._get_neighbor_related_pricings(t_int=lead_t)

		# go through neighbors
		for i in range(0,len(self.neighbors)):
			# get neighbor id
			neigh_id = self.neighbors[i][0]
			neigh = STATION_DICT[neigh_id]
			# PRINT: the current station as string
			print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n\n"+str(neigh)+"\n"))
			# get all the pricings out that potentially disrupt the analysis (CURRENTLY: raises)
			rel_idc = self._get_rel_idc(neigh_id)
			# build up the potential rule by investigating the differnet time levels
			self.rule = self._explore_time_tree(rel_idc, self.leader_n_idx[neigh_id], neigh_id, split_criteria, [0])
			# # PAUSE: after each station investigated
			# pause()

	def day_analysis(self, day):
		'''
		Plots the pricings of a day of the station and its neighbors as a timeline

		@param day: day in question
		@dtype day: datetime
		'''

		# add the day to the as folder analysis path
		self.analysis_path = join(self.analysis_path, str(day))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)

		# get the pricing for the day only
		self.get_pricing((day,day))
		# get the neighbors
		self.get_neighbors()
		# get their pricings
		for (neigh_id, dif) in self.neighbors:
			neigh = STATION_DICT[neigh_id]
			neigh.get_pricing((day,day))

		# get all related pricing pairs (related means close in time)
		self._get_neighbor_related_pricings(t_int=3600)

		# plot timeline
		self._plot_day_timeline(day)
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
			neigh = STATION_DICT[neigh_id]
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
		self.leader_n_idx = {} # dict: neigh_id -> List(Tuple(own_idx,lead_idx,own_cnt,lead_cnt))
		self.leader_p_idx = {} # dict: own_idx -> List(Tuple(neigh_id,lead_idx,own_cnt,lead_cnt))

		# for each neighbor make space the dicts with neigh_id keys
		for (neigh_id, dist) in self.neighbors:
			# self.follower[neigh_id] = []
			self.leader_n_idx[neigh_id] = []

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
		while(i < p_cnt):
			# get the own pricing
			own_pricing = self.pricing_mat[i,:]
			# # PRINT: the pricings date and changed value
			# print(str(get_timestamp(own_pricing[pa2i['date']], own_pricing[pa2i['time']])) + "\t%d" % (own_pricing[pa2i['alt']]))

			# exclude raises from investigation
			if(not(is_raise(own_pricing))):

				# set a flag if the pricing changed all gas price
				own_all_changed = own_pricing[pa2i['alt']]==21
				# set a flag if the own pricing stands alone
				# alone means there is now own one that follows in the interval and is not a raise
				own_single_change = get_time_dif(self.pricing_mat[i+1], own_pricing)>t_int or is_raise(self.pricing_mat[i+1])

				#if it is not alone
				if(not(own_single_change)):
					# get the full chain of consecutive pricings
					own_set_idx, own_set_alt, own_set_time = self._get_pricings_in_span(i, t_int, chain=True)
					# # PRINT: the indices, changes and times for the whole chain 
					# print('\n' + str(own_set_idx) + '\t' + str(own_set_alt) + '\t' + str(own_set_time))
					# # PAUSE: after own print
					# pause()

					# make space in the dict with pricing_idx key
					for lf in own_set_idx:
						self.leader_p_idx[lf] = []
					# set the uppder index of the set
					upper_idx = i+len(own_set_idx)-1
				
				# if the pricing is alone
				else:
					# # PRINT: the indices, changes and times for the single pricing 
					# print('\n' + str(i) + '\t' + str(own_pricing[pa2i['alt']]) + '\t' + str(get_time(own_pricing[pa2i['time']], False)))
					# # PAUSE: after own print
					# pause()

					# make space in the dict with pricing_idx key
					self.leader_p_idx[i] = []
					# set the uppder index of the set to the index itself
					upper_idx = i

				# go through all neighbors
				for j in range(0,num_neigh):
					# get the neighbor
					neigh_id = self.neighbors[j][0]
					neigh = STATION_DICT[neigh_id]
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

						# if the pricing is before the last own it is considered a leader
						'''
						IF ITS A LEADER
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
									if(up_dif>=0):
										# set this as new start index for following iterations
										neigh_pricing_idc[j] = index
										continue

							# set a flag if the neighbor pricing changed all gas prices
							neigh_all_changed = neigh_pricing[pa2i['alt']]==21
							# set a flag if the neighbor pricing stands alone
							# alone means there is now own one that follows in the interval and is not a raise
							neigh_single_change = get_time_dif(neigh.pricing_mat[index+1], neigh_pricing)>=(-1)*up_dif

							if(neigh_single_change):
								'''
								IF THERE IS ONLY ONE LEADER
								'''
								if(own_single_change):
									'''
									IF THERE IS ONLY ONE OWN
									'''
									self._check_leader_single_single(index, i, neigh_id, j)
								else:
									'''
									IF THERE ARE SEVERAL OWN
									''' 
									self._check_leader_single_multi(index, own_set_idx,own_set_alt, neigh_id, j)
							else:
								'''
								IF THERE IS A SET OF LEADERS
								'''
								# get the whole set of leaders beeing all princings of this neighbor in the span
								# from the first cause being the current index to the last own pricing which is up_dif mins apart
								# since up_dif is negative we need the positive value
								neigh_set_idx, neigh_set_alt, neigh_set_time = neigh._get_pricings_in_span(index, (-1)*up_dif)
								# the index has to be raised by the number if additional causes
								index+=len(neigh_set_idx)-1
								if(own_single_change):
									'''
									IF THERE IS ONLY ONE OWN
									'''
									self._check_leader_multi_single(neigh_set_idx, neigh_set_alt, neigh_set_time, i, neigh_id, j)	
								else:
									'''
									IF THERE ARE SEVERAL OWN
									'''
									self._check_leader_multi_multi2(neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, own_set_alt, neigh_id, j, t_int)

						# the potential cause has been treated and is not relevant any further
						index+=1
					# set this as new start index for following iterations
					neigh_pricing_idc[j] = index	

				# if there was a chain of own pricings increase the index by the amount of additional pricings
				if(not(own_single_change)):
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

		# # get a html output stating all causes for each pricing respectiely
		# self._write_first_leader_analysis()

	def _get_pricings_in_span(self, idx, t_span, chain=False):
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
			if(dif<t_span and not(is_raise(self.pricing_mat[idx]))):
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
		neigh = STATION_DICT[neigh_id]
		# get the relevant pricings
		own_pricing = self.pricing_mat[own_idx]
		neigh_pricing = neigh.pricing_mat[leader_idx]
		# a print string printing the relevant information of a leader
		n_str = ('\t' + str(j) + '\t' + str(leader_idx) + '\t' + str(neigh_pricing[pa2i['alt']]) + '\t' + str(get_time(neigh_pricing[pa2i['time']], False)) + "\t -> \t " + str([own_idx]))

		# if the changes made in the pricings allow for a causal relaionship
		if(proper_drop_dif(neigh_pricing, own_pricing)):
			self.leader_n_idx[neigh_id].append((own_idx,leader_idx,0,0))
			self.leader_p_idx[own_idx].append((neigh_id, leader_idx,0,0))
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
		neigh = STATION_DICT[neigh_id]
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
				self.leader_n_idx[neigh_id].append((own_set_idx[osi],leader_idx,0,0))
				self.leader_p_idx[own_set_idx[osi]].append((neigh_id, leader_idx,0,0))
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
				self.leader_n_idx[neigh_id].append((take[-1],leader_idx,len(take)-1,0))
				self.leader_p_idx[take[-1]].append((neigh_id, leader_idx,len(take)-1,0))
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
		neigh = STATION_DICT[neigh_id]
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
				self.leader_n_idx[neigh_id].append((own_idx,neigh_set_idx[n_idx],0,0))
				self.leader_p_idx[own_idx].append((neigh_id,neigh_set_idx[n_idx],0,0))
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
					self.leader_n_idx[neigh_id].append((own_idx,neigh_set_idx[n_idx],0,len(take)-1))
					self.leader_p_idx[own_idx].append((neigh_id,neigh_set_idx[n_idx],0,len(take)-1))
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
		neigh = STATION_DICT[neigh_id]
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
		neigh = STATION_DICT[neigh_id]

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
						self.leader_n_idx[neigh_id].append((cur_o_set[0],cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
						self.leader_p_idx[cur_o_set[0]].append((neigh_id,cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
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
		neigh = STATION_DICT[neigh_id]
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
			self.leader_n_idx[neigh_id].append((own_set_idx[osi],neigh_set_idx[nsi],num_own-1,num_neigh-1))
			self.leader_p_idx[own_set_idx[-osi]].append((neigh_id, neigh_set_idx[-nsi],num_own-1,num_neigh-1))
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
		neigh = STATION_DICT[neigh_id]
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

	def _split_at(self, data_idc, station_id, split_criterium):
		"""
		Split a list of pricings regarding to a specific value (e.g. seperate the data according to the day of the week

		@param data_idc: all the data that is to split as indices
		@dytpe data_idc: list(Int)

		@param station_id: the identifier of the station which did the pricings
		@dytpe station_id: string

		@param split_criterium: a keyword identifying how to split the data
		@dytpe split_criterium: int

		@return splits: the generated sets of data as indeces
		@dtype splits: list(list(Int))

		@return split_vals: the different values at which was splitted
		@dtype split_vals: list(Int)
		"""

		# get the stations data
		data = STATION_DICT[station_id].pricing_mat
		try:
			# split data between weekend and weekday
			if(split_criterium=="we"):
				# create the two empty sets
				we,wd = [],[]
				# check for the relevant indices if the dow value is 5 or above
				for idx in data_idc:
					if(data[idx][pa2i['dow']]>=5):
						we.append(idx)
					else:
						wd.append(idx)
				splits = [wd,we]
				# the values are 1(True) for weekend and 0(False) for weekday
				spit_vals = [0,1]
				return splits, spit_vals

			# split data between different days of the week
			elif(split_criterium=="dow"):
				# create a set for all the different days of the week appearing in the relevant data
				dow_set = set(map(int, data[data_idc,pa2i['dow']]))
				# create empty list for the return values
				splits = []
				split_vals = []
				# for each different day of the week get all the respective data
				for dow in dow_set:
					# append the day of the week value and the data
					split_vals.append(dow)
					splits.append([idx for idx in data_idc if data[idx][pa2i['dow']]==dow])
				return splits, split_vals

			# split data between the different hours of the day
			elif(split_criterium=="hour"):
				# create a set for all the different hours of the week appearing in the relevant data
				hour_set = set(map(int, data[data_idc,pa2i['time']]/3600))
				# create empty list for the return values
				splits = []
				split_vals = []
				# for each different hour get all the respective data
				for hour in hour_set:
					# append the hour value and the data
					split_vals.append(hour)
					splits.append([idx for idx in data_idc if int(data[idx][pa2i['time']]/3600)==hour])
				return splits, split_vals
			else:
				raise ValueError("Wrong split criterium")

		except ValueError:
			traceback.print_exc()
			print("You used %s as split criterium. Please use we, dow, tod or hour only!" % split_criterium)
			sys.exit(1)

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
		neigh = STATION_DICT[neigh_id]
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
		neigh = STATION_DICT[neigh_id]
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
		neigh = STATION_DICT[neigh_id]
		# copy the differences of the non_matches into a numpy array (non_matches*3)
		miss_difs = np.zeros((len(misses),3))
		# go through all misses
		for i in range(0,len(misses)):
			# get the relevant indices
			(own_idx,neigh_idx) = misses[i]
			# add the difference
			miss_difs[i,:] = get_price_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])
		return miss_difs


	######### Printing and Visualizing##########
	def print_neighbors(self):
		"""
		Prints information about all the neighbors of this station like the station informations itself
		and the distance
		"""

		# get neighbors if not done
		if self.neighbors is None: self.get_neighbors(STATION_DICT)

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
			station = STATION_DICT[station_id]
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
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
				" WHERE " + PG['STID'] + " AND " + PG['MONTH'] + " AND " + PG['YEAR'] % (self.id, month, year))
			# add the count to the chart data
			month_hist.append(CURSOR.fetchone()[0])
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

	def plot_pricing_hour_hist(self, dow_int, date_int):
		"""
		Get all price adaptions for this station in the selected interval und and count 
		the occurances for each hour.

		@param dow_int: specifies the day of the week or an consequtive interval (e.g. weekend) for which we want the statistics
		@dtype dow_int: tuple(Int,Int)

		@param date_int: specifies the date interval for which we want the statistics
		@dtype date_int: tuple(datetime.date,datetime.date)
		"""	

		# initialze the hour data
		pricing_hist = np.zeros((24, ))
		# get the count for every hour
		for i in range(0,24):
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history" +
				" WHERE " + PG['STID'] +
				" AND " + PG['DOW_INT'] +
				" AND " + PG['DATE_INT'] +
				" AND " + PG['HOUR'],
				(self.id,)+dow_int+date_int+(i,))
			pricing_hist[i] = CURSOR.fetchone()[0];
		# create a figure
		fig = plt.figure()
		ax = fig.add_subplot(111)

		# set the positions and width of the bars
		ind = np.arange(24)
		width = 0.35

		# create the bars
		rects1 = ax.bar(ind, pricing_hist, width, color='red')

		label_barchart_rects(rects1, ax)

		# set the labels
		ax.set_ylabel('pricings')
		ax.set_xlabel('hour')
		ax.set_title('pricing activity - hour history')
		# create and set the xticks
		xTickMarks = [i for i in range(0,24)]
		ax.set_xticks(ind + width/2)
		xtickNames = ax.set_xticklabels(xTickMarks)
		plt.setp(xtickNames, rotation=0, fontsize=10)
		plt.gcf().subplots_adjust(bottom=0.15)
		# save the figure
		fig.savefig(join(self.analysis_path,'pricing_activity-hour_history'))

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


	######### Some visualization helpers ##########
	def _plot_day_timeline(self):
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
				neigh = STATION_DICT[station_id]
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
			plt.savefig(join(self.analysis_path,file_name), bbox_extra_artists=(lgd,), bbox_inches='tight')

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
		neigh = STATION_DICT[neigh_id]
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
			neigh = STATION_DICT[neigh_id]
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



class Rule(object):
	__slots__ = ('owner', 'competitor',
		'split_criteria', 'split_vals', 'split_further',
		'max_p_dist', 'conf', 'consistent', 'mean_rtime', 'dev_rtime',
		'match_difs', 'miss_difs', 'counts',
		'subrules', 'sr_idc',
		'analysis_path')

	def __init__(self, owner, competitor, split_criteria, split_vals, analysis_path):
		"""
		Initializes a rule.

		@param owner: the station's id that owns the rule
		@dtype owner: string

		@param competitor: the competitor's id the rule is applied to
		@dtype competitor: string

		@param split_criteria: the criteria of the specifiaction of the time interval in which the rule is applied
		@dtype split_criteria: list(String)

		@param split_level: the deepness of the rule in the rule tree
		@dtype split_level: int

		@param split_vals: the values of the specifiaction of the time interval in which the rule is applied
		@dtype split_vals: list(Int)

		@param analysis_path: parent path where output should be saved to
		@dtype analysis_path: string
		"""
		self.owner = owner
		self.competitor = competitor

		self.split_criteria = split_criteria
		self.split_vals = split_vals

		self.match_difs = None
		self.miss_difs = None
		self.counts = {}

		self.max_p_dist = [None,None,None]
		self.conf = [None,None,None]
		self.consistent = [None,None,None]
		self.mean_rtime = [None,None,None]
		self.dev_rtime = [None,None,None]

		self.subrules =None
		self.sr_idc = None

		self.analysis_path = analysis_path

	def __str__(self):
		"""
		Generates a string for a rule containing the time interval criteria and their values

		@return rule_str: the rule's string
		@dtype rule_str: string
		"""
		rule_str = self.split_criteria[0]+':'+str(self.split_vals[0])
		for i in range(1,len(self.split_vals)):
			rule_str += ('_'+self.split_criteria[i]+str(self.split_vals[i]))
		return rule_str

	def __eq__(self, other):
		eq = self.max_p_dist == other.max_p_dist
		return eq

	def _write_stats_analysis(self):
		# TODO
		pass

	def _get_stats(self, matches, misses):
		"""
		Computes the stats of the rule meaning the maximal price distances that are allowed for the gases.
		It uses the difference information after a reaction and those there no reaction happened.
		The maximal values of those differences depict the threshold where a difference is accepted or
		where a adapion needs to happen. After a reaction the price should be adjusted so that the difference
		is the maximal difference the station wants to a competitor. When no reaction accured the difference
		needs to be allowed so the maximum value indicates the threshold as well.

		The difficulty is to make a distinction between extreme values that happened because the rule was
		not followed 100% and just few instances where a real reaction occurs.
		Thats why a html file is generated to print the outlier pricings to be able to check for inconsistencies.

		@param matches: the leaders that are in this time interval
		@dtype matches: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@param misses: the unreacted pricings in this time interval
		@dtype misses: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index right before the unreacted neighbors pricing
						- neigh_idx: the neighbor pricing index where no reaction occured
		"""

		# get the owning station
		own_station = STATION_DICT[self.owner]
		neigh = STATION_DICT[self.competitor]

		# plot the dif barcharts
		self._plot_match_miss_dif_hists()

		# go into the competitors directory
		filedir = join(self.analysis_path, str(neigh).replace(" ", "_"))
		# create it if it doesn't exist
		if(not(isdir(filedir))): os.makedirs(filedir)
		# go into the difs_oulier directory where information about infrequent high values is stored.
		filedir = join(filedir, "difs_outlier")
		# create the directory if it doesn't exist
		if(not(isdir(filedir))): os.makedirs(filedir)
		# open a file with the name of the rule
		file_name = str(self) + '.html'
		f = open(join(filedir,file_name), 'w')

		# write a header
		f.write(html_intro("difs_outlier in rule: " + str(self)))

		# initialize list for the maximal and modal values
		max_tup_after_react = []
		max_tup_after_unreacted = []
		mod_tup_after_react = []
		mod_tup_after_unreacted  = []

		# treat each gas seperatedly
		for gas in range(0,len(GAS)):
			# write the gas into the file
			f.write(html_heading(1, GAS[gas]))
			# get the match dif values and counts
			unique, counts = np.unique(self.match_difs[:,2,gas], return_counts=True)
			# the maximal value is at the end
			r_idx = len(unique)-1
			max_tup_after_react.append((unique[r_idx], counts[r_idx]))
			# get the modal value 
			mod_idx = np.argmax(counts)
			mod_tup_after_react.append((unique[mod_idx], counts[mod_idx]))

			# do the same for the pricings without reaction
			unique2, counts2 = np.unique(self.miss_difs[:,gas], return_counts=True)
			unr_idx = len(unique2)-1
			max_tup_after_unreacted.append((unique2[unr_idx], counts2[unr_idx]))
			mod_idx2 = np.argmax(counts2)
			mod_tup_after_unreacted.append((unique2[mod_idx], counts2[mod_idx]))

			f.write(html_heading(2, "After own reset"))
			for ext_idx in range(mod_idx+1,len(unique)):
				f.write(html_heading(3, "dif: " + str(unique[ext_idx]) + "\tcount: " + str(counts[ext_idx])))
				outlier = [i for i in range(0,self.counts['match']) if self.match_difs[i,2,gas]==unique[ext_idx]]
				for idx in outlier:
					f.write(own_station._get_leader_env_as_html_table(self.competitor, matches[idx]))
					f.write('<br>')

			f.write(html_heading(2, "After unreacted pricing"))
			for ext_idx in range(mod_idx2+1,len(unique2)):
				f.write(html_heading(3, "dif: " + str(unique2[ext_idx]) + "\tcount: " + str(counts2[ext_idx])))
				outlier = [i for i in range(0,self.counts['miss']) if self.miss_difs[i,gas]==unique2[ext_idx]]
				for idx in outlier:
					f.write(own_station._get_leader_env_as_html_table(self.competitor, (misses[idx][0]+1, misses[idx][1],0,0)))
					f.write('<br>')

			f.write(html_end())
			# get the combined confidence value of the maxvalues with good single confidence values
			# comb_conf = 0
			# while(comb_conf<0.5 and (r_idx>=mod_idx or unr_idx>=mod_idx)):

			# 	# compute the single confidence values
			# 	react_conf = self._comp_conf(max_tup_after_react[gas][1],self.counts['match'])
			# 	unreac_conf = self._comp_conf(max_tup_after_unreacted[gas][1],self.counts['miss'])

			# 	# while react max value is higher than the unreact value and the confidence value is too low
			# 	# take the next value
			# 	while(react_conf<0.5 and max_tup_after_unreacted[gas][0]<max_tup_after_react[gas][0] and r_idx>mod_idx):
			# 		# write the outliers to file
			# 		# f.write(html_heading(2, "After own reset"))
			# 		# f.write(html_heading(3, "dif: " + str(unique[r_idx]) + "\tcount: " + str(counts[r_idx]) + "\tconf: " + str(react_conf)))
			# 		# outlier = [i for i in range(0,self.counts['match']) if self.match_difs[i,2,gas]==unique[r_idx]]
			# 		# for idx in outlier:
			# 		# 	f.write(own_station._leader_n_idx_to_html_table(self.competitor, matches[idx]))
			# 		# 	f.write('<br>')

			# 		# get the next conf value
			# 		r_idx-=1
			# 		max_tup_after_react[gas] = (unique[r_idx], counts[r_idx])
			# 		react_conf = self._comp_conf(max_tup_after_react[gas][1],self.counts['match'])

			# 	# the other way around
			# 	while(unreac_conf<0.5 and max_tup_after_unreacted[gas][0]>max_tup_after_react[gas][0] and unr_idx>mod_idx2):
			# 		# write the outliers to file
			# 		# f.write(html_heading(2, "After unreacted pricing"))
			# 		# f.write(html_heading(3, "dif: " + str(unique2[unr_idx]) + "\tcount: " + str(counts2[unr_idx]) + "\tconf: " + str(unreacted_conf)))
			# 		# outlier = [i for i in range(0,self.counts['miss']) if self.miss_difs[i,gas]==unique2[unr_idx]]
			# 		# for idx in outlier:
			# 		# 	f.write(own_station._leader_n_idx_to_html_table(self.competitor, (misses[idx][0], misses[idx][1],0,0)))
			# 		# 	f.write('<br>')

			# 		# get the next conf value
			# 		unr_idx-=1
			# 		max_tup_after_unreacted[gas] = (unique2[unr_idx], counts2[unr_idx])
			# 		unreac_conf = self._comp_conf(max_tup_after_unreacted[gas][1],self.counts['miss'])

			# 	# if the maximum values match compute the combined confidence value
			# 	if(max_tup_after_unreacted[gas][0]==max_tup_after_react[gas][0]):
			# 		comb_cnt = max_tup_after_react[gas][1]+max_tup_after_unreacted[gas][1]
			# 		comb_conf = math.tanh(float(math.pow(comb_cnt,3))/(self.counts['match']+self.counts['miss']))
			# 		# if the value is higher than 50% set the stats and finish
			# 		if(comb_conf>0.5):
			# 			# set the threshold
			# 			self.max_p_dist[gas] = max_tup_after_react[gas][0]
			# 			# the thresholds match
			# 			consistent[gas] = True
			# 			# set the conf value
			# 			self.conf[gas] = comb_conf
			# 			self.counts['conf_count'] = comb_cnt
			# 			self.mean_rtime[gas], self.dev_rtime[gas] = self._get_mean_and_dev_r_time(matches,gas):
			# 			break
			# 		else:
			# 			# if we can not take the rule proceed and decrease each value if the confidence value isn't sufficient
			# 			if(unreac_conf<0.5):
			# 				unr_idx-=1
			# 				max_tup_after_unreacted[gas] = (unique2[unr_idx], counts2[unr_idx])
			# 			if(react_conf<0.5):
			# 				r_idx-=1
			# 				max_tup_after_react[gas] = (unique[r_idx], counts[r_idx])
			# 	# otherwise
			# 	else:
			# 		if(max_tup_after_unreacted[gas][0]>max_tup_after_react[gas][0]):
			# 			count = max_tup_after_unreacted[gas][1]]
			# 			conf = unreac_conf
			# 		else:
			# 			count = max_tup_after_react[gas][1]
			# 			conf = react_conf
			# 		if(conf>0.5):
			# 			# there is no consistent threshold
			# 			self.max_p_dist[gas] = None
			# 			# the thresholds do not match
			# 			consistent[gas] = False
			# 			# set the conf value
			# 			self.conf[gas] = comb_conf
			# 			self.counts['conf_count'] = comb_cnt
			# 			break
			# 		else:
			# 			# 
			# 			if(max_tup_after_unreacted[gas][0]>max_tup_after_react[gas][0]):
			# 				unr_idx-=1
			# 				max_tup_after_unreacted[gas] = (unique2[unr_idx], counts2[unr_idx])
			# 			else:
			# 				r_idx-=1
			# 				max_tup_after_react[gas] = (unique[r_idx], counts[r_idx])

			# 	# if we reach this position there was no 
			# 	if(max_tup_after_unreacted[gas][0]>max_tup_after_react[gas][0]):
			# 		unr_idx-=1
			# 		max_tup_after_unreacted[gas] = (unique2[unr_idx], counts2[unr_idx])
			# 	else:
			# 		r_idx-=1
			# 		max_tup_after_react[gas] = (unique[r_idx], counts[r_idx])

			# f.write(html_end())
		return

	def _get_mean_and_dev_r_time(self, matches, gas):
		"""
		Get the mean and standard deviation of the reaction time in the matches for the respective gas type.
		So we only consider the reaction time when each party of the match changed the respective gas price.
		The reaction time is the time between the pricings where this specific gas was changed.

		@param matches: the list of leaders that apply to this rules category
		@dtype matches: list(Tuple(own_idx,neigh_idx,o_num,n_num))
						- own_idx: the own pricing index
						- neigh_idx: the neighbor pricing index
						- o_num: the number of own additional pricings
						- n_num: the number of the neighbors additional pricings

		@param gas: the index of the gas type
		@dtype gas: int

		@return m: the mean reaction time in minutes
		@dtype m: int

		@return s: the standard deviation of the reaction time in minutes
		@dtype s: int
		"""

		# get the own and the competitors station
		neigh = STATION_DICT[self.competitor]
		own_station = STATION_DICT[self.owner]
		# get the gas changed index for the pricing mat
		gmi = GAS[gas]+1
		# initialize the time difference list
		time_dif = []
		# go through all matches
		for i in range(len(matches)):
			# get all fields
			(own_idx, neigh_idx, o_num, n_num) = matches[i]
			o = own_idx
			n = neigh_idx
			# go until index is reached where the own station changed the gas price
			while(own_station.pricing_mat[o,gmi]>=0 and o<=o_num):
				o+=1
			# if the own station did change the gas price
			if(o<=o_num):
				# go until index is reached where the other station changed the gas price
				while(neigh.pricing_mat[n,gmi]>=0 and n<=n_num):
					n+=1
				# if the other station did change the gas price
				if(n<=n_num):
					# get the respective pricings where the gas price was changed
					o_pr = own_station.pricing_mat[o]
					n_pr = eigh.pricing_mat[n]
					# get the time difference between those to pricings
					time_dif.append(float(get_time_dif(o_pr,n_pr))/60)
			
		m = int(np.mean(time_dif) + 0.5)
		s = int(np.std(time_dif) + 0.5)
		
		return m, s

	def _plot_match_miss_dif_hists(self):
		"""
		Generate a barchart for this rule visualizing the price differences after a reaction
		and when no reaction happend. This is important because the maximal values indicate
		the boundary where a difference is okay or where it needs to be changed, if the values
		are no extremes.
		"""
		# generate a afigure
		fig = plt.figure()
		# add the rule as subtitle
		fig.suptitle(str(self),fontsize=20, weight='bold')

		# go through all gases
		for gas in range(0,3):
			#add a sublot
			ax = fig.add_subplot(1,3,gas+1)
			# get the match and miss differences and their counts
			unique_match, counts_match = np.unique(self.match_difs[:,2,gas], return_counts=True)
			unique_miss, counts_miss = np.unique(self.miss_difs[:,gas], return_counts=True)
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

			x_labels = unique_comb



			# # indices for the lists
			# u_ma = 0
			# u_mi = 0
			# # new counts
			# match_c = []
			# miss_c = []
			# # new differences
			# x_labels = []


			# # go through the lists until one end is reached
			# while(u_ma<len(unique_match) and u_mi<len(unique_miss)):
			# 	# if the differences match add the values of both
			# 	if(unique_match[u_ma]==unique_miss[u_mi]):
			# 		match_c.append(counts_match[u_ma])
			# 		miss_c.append(counts_miss[u_mi])
			# 		x_labels.append(unique_match[u_ma])
			# 		u_ma+=1
			# 		u_mi+=1
			# 	# if match is lower add the match and a zero for miss
			# 	elif(unique_match[u_ma]<unique_miss[u_mi]):
			# 		match_c.append(counts_match[u_ma])
			# 		miss_c.append(0)
			# 		x_labels.append(unique_match[u_ma])
			# 		u_ma+=1
			# 	# if miss is lower add the miss and a zero for match
			# 	else:
			# 		miss_c.append(counts_miss[u_mi])
			# 		match_c.append(0)
			# 		x_labels.append(unique_miss[u_mi])
			# 		u_mi+=1
			# # when there are matches left add them and zeros for misses
			# while(u_ma<len(unique_match)):
			# 	match_c.append(counts_match[u_ma])
			# 	miss_c.append(0)
			# 	x_labels.append(unique_match[u_ma])
			# 	u_ma+=1
			# # when there are misses left add them and zeros for matches
			# while(u_mi<len(unique_miss)):
			# 	miss_c.append(counts_miss[u_mi])
			# 	match_c.append(0)
			# 	x_labels.append(unique_miss[u_mi])
			# 	u_mi+=1

			# set title of the axe
			ax.set_title(GAS[gas],fontsize=20, position=(0.5,1.0), weight='bold')

			# widt of a bar
			width = 0.4
			# x position of the bars
			ind = np.arange(len(match_c))+(width/2)
			if(len(match_c)<=3):
				ax.set_xlim(0,5)
				ind+=1.0
			# generate the bars with (x position, height, width, color)
			rects1 = ax.bar(ind, match_c, width, color='red')
			rects2 = ax.bar(ind+width, miss_c, width, color='green')

			# setup and format the x axis
			# give it a label
			ax.set_xlabel('price_dif',fontsize=16, position=(1.05,-0.1))
			# give it ticks and names
			ax.set_xticks(ind + width)
			xtickNames = ax.set_xticklabels(x_labels)
			# format the ticks
			plt.setp(xtickNames, fontsize=16, weight='bold')

			# setup and format the y axis
			# give it a label
			ax.set_ylabel('counts',fontsize=16, position=(0,1.0))
			#reevaluate the ytick positions
			max_val = max(max(miss_c), max(match_c))
			ytickpos = ax.get_yticks()
			if(len(ytickpos)-2>4):
				ytickpos = ytickpos[::2]
				ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
			if(max_val/ytickpos[-1]>0.95):
				ytickpos = np.append(ytickpos,[ytickpos[-1]+ytickpos[1]])
			ax.set_yticks(ytickpos)
			# format the y ticks
			plt.setp(ax.get_yticklabels(), fontsize=16, weight='bold')

			# label the bars
			label_barchart_rects(rects1,ax)
			label_barchart_rects(rects2,ax)

		
		# add a legend
		legend = plt.figlegend((rects1[0], rects2[0]), ('dif after reaction', 'dif not reacted'), loc='lower center')
		for label in legend.get_texts():
			label.set_fontsize(20)
			label.set_weight('bold')

		# save the figure
		station = STATION_DICT[self.competitor]
		# go into the directory of the competitor
		filedir = join(self.analysis_path, str(station).replace(" ", "_"))
		# create it if it doesn't exist
		if(not(isdir(filedir))): os.makedirs(filedir)
		# go into the directory for rule difference barcharts
		filedir = join(filedir, "rule_dif_hists")
		# create it if it doesn't exist
		if(not(isdir(filedir))): os.makedirs(filedir)
		# create a file for the barchart with the name of the rule
		file_name = str(self)
		dpi = fig.get_dpi()
		fig.set_size_inches(1920.0/float(dpi),1080.0/float(dpi))
		plt.subplots_adjust(top=0.85, bottom=0.12, left= 0.05, right=0.95, hspace=0.2, wspace=0.2)
		fig.savefig(join(filedir,file_name))
		plt.close(fig)

		return

	def _comp_conf(self,x,y):
		"""
		Computes the confidence value for for a rule. It compares the pricings that support this exact rule
		to the total amount of pricings in this time category.
		As confidence value we want something like the percentage of the maximal difference from all
		matches or misses respectively. However this should not be a linear function. The amount of the maximal
		difference should be weighted much higher. For moderately high values of occurances there should
		be a high total number to neglect this value as extreme values. Or to put it in slighly different way
		the percentage needed to accept a value decreases with the total amount. 
		Additionally we want to scale the value into the range of 0 to 1 to express the condifence as a percentage.
		Function: 2/pi*atan(2* (x²/y))


		@param x: the supporting fraction
		@dtype x: int

		@param y: the total amount
		@dtype y: int

		@return conf: the confidence value as percentage
		@dtype conf: float
		"""

		conf = (2/pi)*atan(float(pow(x,2))/y)
		return conf


######### Pricing related helping-functions ##########
def get_station_dict():
	"""
	Generate a dictionary with id -> station for each station.

	@return	The dictionary containing all gas stations indexed by their id
	@rtype	dict
	"""

	STATION_DICT = {}
	# get the station data from the postgres database pointed to by the CURSOR
	CURSOR.execute('SELECT * from gas_station')
	station_data = CURSOR.fetchall()
	# for each station generate a station instance and add it to the dict
	for i in range(0,len(station_data)):
		STATION_DICT[station_data[i][0]] = Station(station_data[i])
	return STATION_DICT

def pricing_to_string(pricing, dow=False):
	"""
	Generates a string from the pricing with the relevant information

	@param pricing: the pricing in question
	@dtype pricing: numpy.array

	@param dow: indicating whether the day of the week should be added
	@dtype dow: boolean

	@return p_string: the pricing's string
	@dtype p_string: string
	"""

	# generate a substring for each gas type with the price and the difference from the previous value
	d_str = "%s"% pricing[pa2i['diesel']]
	d_dif = pricing[pa2i['d_diesel']]
	if(d_dif>0):
		d_str += " +%3d" % d_dif
	else:
		d_str += " %3d" % d_dif

	e5_str = "%s"% pricing[pa2i['e5']]
	e5_dif = pricing[pa2i['d_e5']]
	if(e5_dif>0):
		e5_str += " +%3d" % e5_dif
	else:
		e5_str += " %3d" % e5_dif

	e10_str = "%s"% pricing[pa2i['e10']]
	e10_dif = pricing[pa2i['d_e10']]
	if(e10_dif>0):
		e10_str += " +%3d" % e10_dif
	else:
		e10_str += " %3d" % e10_dif

	# get the time and date
	date = get_date(pricing[pa2i['date']])
	time = get_time(pricing[pa2i['time']], tz=False)

	# combine al those values to a string
	p_string = "%s | %s | %s | %s | %s | %s" % (str(date).center(10),
		str(time).center(10),
		(("%" + str(6) + "d") % pricing[pa2i['alt']]),
        d_str,
        e5_str,
        e10_str)

	# add the day of the week if wanted
	if(dow):
		p_string += " | %s" %(dow_to_string(pricing[pa2i['dow']]),)

	return p_string

def get_timestamp(days, secs):
	"""
	Computes the datetime from the days value anf the time value of a pricing.

	@param days: the passed since the initial pricngs day
	@dtype days: int

	@param secs: the seconds value in seconds passed in a day
	@dtype secs: int

	@return c_time: the full datetime instance
	@dtype c_time: datetime.datetime
	"""
	# combine the computed day and time values
	c_date = get_date(days)
	c_time = get_time(secs)
	c_datetime = datetime.combine(c_date,c_time)
	return c_datetime

def get_date(days):
	"""
	Computes the date from the days value of a pricing.

	@param days: the passed since the initial pricngs day
	@dtype days: int

	@return c_time: the date of the day
	@dtype c_time: datetime.date
	"""
	# add as many days to the initial day
	c_date = (INIT_DATE + timedelta(days=days))
	return c_date

def get_time(secs, tz=True):
	"""
	Computes the time of the day from the seconds value.
	CURRENTLY its possible to choose wether the timezone berlin should be added

	@param secs: the seconds value in seconds passed in a day
	@dtype secs: int

	@param tz: indicating whether a timezone should be added
	@dtype tz: boolean

	@return c_time: the time of the day
	@dtype c_time: datetime.time
	"""

	# compute the minutes passed and the remaining seconds
	m, s = divmod(secs, 60)
	# compute the hours passed and the remaining minutes
	h, m = divmod(m, 60)
	# comnie those values to a time instance with or witout timezone
	if(tz):
		# timezone berlin
		berlin = pytz.timezone('Etc/GMT-2')
		c_time = time(int(h),int(m),int(s),0,berlin)
	else:
		c_time = time(int(h),int(m),int(s),0)
	return c_time

def get_price_dif(p1,p2):
	"""
	Computes the price difference for all gases between the two pricings

	@param p1: pricing from from which the other one's prices get substracted
	@dtype p1: numpy.array

	@param p2: substract
	@dtype p2: numpy.array

	@return d_dif: the diesel price difference
	@dtype d_dif: int

	@return e5_dif: the e5 price difference
	@dtype e5_dif: int

	@return e10_dif: the e10 price difference
	@dtype e10_dif: int
	"""

	# compute the three differences and return
	d_dif = int(p1[pa2i['diesel']] - p2[pa2i['diesel']])
	e5_dif = int(p1[pa2i['e5']] - p2[pa2i['e5']])
	e10_dif = int(p1[pa2i['e10']] - p2[pa2i['e10']])
	return d_dif, e5_dif, e10_dif

def get_time_dif(p1,p2):
	"""
	Computes the time difference in seconds between the two pricings

	@param p1: pricing from from which the other one's time gets substracted
	@dtype p1: numpy.array

	@param p2: substract
	@dtype p2: numpy.array

	@return t_dif: the time difference seconds
	@dtype t_dif: int
	"""

	# get the two pricings day and time vals
	# time val is the seconds passed in this day
	# day val is days passed from the initial day
	p1_s = p1[pa2i['time']]
	p1_d = p1[pa2i['date']]
	p2_s = p2[pa2i['time']]
	p2_d = p2[pa2i['date']]
	# the difference is the day difference times seconds per day
	# plus the difference in seconds in days 
	t_dif = SECS_PER_DAY*(p1_d-p2_d)+(p1_s-p2_s)
	return t_dif

def is_raise(p):
	"""
	Check if a pricing is a raise.
	CURRENTLY a pricing is a raise when at least one gas price was raised

	@param p: the pricing in question
	@dtype p: list(Int)

	@return proper: True if it is a proper adjustment
	@dtype proper: boolean
	"""

	if(p[pa2i['d_diesel']]>0 or p[pa2i['d_e5']]>0 or p[pa2i['d_e10']]>0):
		return True
	else:
		return False

def proper_drop_dif(l_p, f_p):
	"""
	Check if a cause and a reaction have the right changed values to justify their relation.
	The reactions chnages must be lower or equal to the cause, because the distance would not
	have been right before the cause.

	@param l_p: the leading pricing
	@dtype l_p: list(Int)

	@param f_p: the following pricing
	@dtype f_p: list(Int)

	@return proper: True if it is a proper adjustment
	@dtype proper: boolean
	"""
	proper = True
	if(not(is_raise(l_p))):
		proper = (l_p[pa2i['d_diesel']]<=f_p[pa2i['d_diesel']] and l_p[pa2i['d_e5']]<=f_p[pa2i['d_e5']] and l_p[pa2i['d_e10']]<=f_p[pa2i['d_e10']])
	return proper



######### Plotting-functions ##########
def plot_pricing_month_hist():
	"""
	Plot the pricing activity in germany as a month histogram.
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
		CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
			" WHERE " + PG['MONTH'] + " AND " + PG['YEAR'] % (month, year))
		# add the count to the chart data
		month_hist.append(CURSOR.fetchone()[0])
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
	fig.savefig(join(ANALYSIS_PATH, ('pricing_activity-month_history')))

def plot_pricing_hour_hist(dow_int, date_int):
	"""
	Get all price adaptions in the selected interval und and count 
	the occurances for each hour.

	@param dow_int: specifies the day of the week or an consequtive interval (e.g. weekend) for which we want the statistics
	@dtype dow_int: tuple(Int,Int)

	@param date_int: specifies the date interval for which we want the statistics
	@dtype date_int: tuple(datetime.date,datetime.date)
	"""	

	# initialze the hour data
	pricing_hist = np.zeros((24, ))
	# get the count for every hour
	for i in range(0,24):
		CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history" +
			" WHERE " + PG['DOW_INT'] +
			" AND " + PG['DATE_INT'] +
			" AND " + PG['HOUR'],
			dow_int+date_int+(i,))
		pricing_hist[i] = CURSOR.fetchone()[0];
	# create a figure
	fig = plt.figure()
	ax = fig.add_subplot(111)

	# set the positions and width of the bars
	ind = np.arange(24)
	width = 0.35

	# create the bars
	rects1 = ax.bar(ind, pricing_hist, width, color='red')

	label_barchart_rects(rects1, ax)

	# set the labels
	ax.set_ylabel('pricings')
	ax.set_xlabel('hour')
	ax.set_title('pricing activity - hour history')
	# create and set the xticks
	xTickMarks = [i for i in range(0,24)]
	ax.set_xticks(ind + width/2)
	xtickNames = ax.set_xticklabels(xTickMarks)
	plt.setp(xtickNames, rotation=0, fontsize=10)
	plt.gcf().subplots_adjust(bottom=0.15)
	# save the figure
	fig.savefig(join(ANALYSIS_PATH,'pricing_activity-hour_history'))


######### General helping-functions ##########
bcolors = {
    "HEADER" : '\033[95m',
    "OKBLUE" : '\033[94m',
    "OKGREEN" : '\033[92m',
    "WARNING" : '\033[93m',
    "FAIL" : '\033[91m',
    "ENDC" : '\033[0m',
    "BOLD" : '\033[1m',
    "UNDERLINE" : '\033[4m' 
}

def print_bcolors(formats, text):
	"""
	Add console formatting identifer to strings.

	@param formats: a list of formats for the string (has to be in the dict bcolors)
	@dtype formats: list(String)

	@param text: the string should be formatted
	@dtype text: string

	@return formated_text: the formatted string
	@dtype formated_text: string
	"""
	formated_text = ''
	for format in formats:
		formated_text += bcolors[format]
	formated_text += text + bcolors["ENDC"]
	return formated_text

def replace_Umlaute(r_str):
	"""
	Replace the umlaute in a String.

	@param r_str: the string to check for umlaute
	@dtype r_str: string

	@return r_str: the replaced string
	@dtype r_str: string
	"""
	r_str = r_str.replace('ä', 'ae')
	r_str = r_str.replace('ö', 'oe')
	r_str = r_str.replace('ü', 'ue')
	r_str = r_str.replace('Ä', 'Ae')
	r_str = r_str.replace('Ö', 'Oe')
	r_str = r_str.replace('Ü', 'Ue')
	r_str = r_str.replace('ß', 'ss')
	return r_str

def pause():
	"""
	Pause the execution until Enter gets pressed
	"""
	raw_input("Press Enter to continue...")
	return

def get_colors(color_num):
	"""
	Use the HSV color spectrum to get a number of colors that look different.

	@param corlor_num: the number of different colors wanted
	@dtype corlor_num: int

	@return colors: the color values returned
	@dtype colors: list(String)
	"""
	
	colors=[]
	# divide 360 by the number of colors and go in those steps from 0 to 360
	for i in np.arange(0., 360., 360. / color_num):
		# get the percentage value of the hue
		hue = i/360.
		# get a random lightness value higher than 50
		lightness = (50 + np.random.rand() * 10)/100.
		# get a random saturation value higher than 90
		saturation = (90 + np.random.rand() * 10)/100.
		# get rbg value ffrom the values above and append it
		colors.append(colorsys.hls_to_rgb(hue, lightness, saturation))
	return colors

def html_intro(page_title):
	"""
	Create the top of an html page with a page title

	@param page_title: the page title
	@dtype page_title: string

	@return intro: the html intro with the title
	@dtype intro: string
	"""
	intro = "<!DOCTYPE html><br><html><br><head><br><title>%s</title><br></head><br><body>" %(page_title)
	return intro

def html_end():
	"""
	Create a html ending

	@return end: the html ending
	@dtype end: string
	"""
	end = "</body><br></html>"
	return end

def html_heading(num, heading):
	"""
	Create different headings for a html page

	@param num: the thickness level of the heading
	@dtype num: int

	@param heading: the heading text
	@dtype heading: string

	@return heading: the html heading
	@dtype heading: string
	"""
	heading = "<h%d>%s</h%d>"% (num,heading,num)
	return heading

def label_barchart_rects(rects, ax):
	"""
	Label each rectangle in the bar chart with its value

	@param rects: the bars of a bar chart
	@dtype rects: list(rectangle)
	"""
	for rect in rects:
		# get the height
		height = rect.get_height()
		# add the label at right above the center of the rect
		ax.text(rect.get_x() + rect.get_width()/2., 1.0*height,
				'%d' % int(height),
				ha='center', va='bottom', fontsize=16)

# def set_date_span():
# 	# get the first and the last date in the pricing history
# 	CURSOR.execute('SELECT date from gas_station_information_history ORDER BY date')
# 	INIT_DATE = CURSOR.fetchone()[0]
# 	CURSOR.execute('SELECT date from gas_station_information_history ORDER BY date DESC')
# 	END_DATE = CURSOR.fetchone()[0]

# 	print(INIT_DATE)
# 	print(END_DATE)

if __name__ == "__main__":
	con = None
	geolocator = Nominatim()
	plz_nordhorn = '48529'
	plz_osnabrueck = '49078'

	berlin = pytz.timezone('Etc/GMT-2')

	yesterday = datetime.now().date()-timedelta(days=1)
	three_month_ago = datetime.now().date()-timedelta(days=91)

	from_date = three_month_ago
	to_date = yesterday

	ana_day = datetime(2016,2,24).date()
	# set_global_d_int(from_date, to_date)
	try:
		con = psycopg2.connect(database='pricing_31_8_16', user='kai', password='Sakral8!')
		# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
		CURSOR = con.cursor()
		STATION_DICT = get_station_dict()

		# plot_pricing_month_hist()

		CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(plz_osnabrueck,"Q1"))
		gas_station_id = CURSOR.fetchall()[0][0]
		station = STATION_DICT[gas_station_id]

		# station.get_neighbors()
		# station.print_neighbors()


		# station.day_analysis(ana_day)
		# pause()

		station.get_competition(d_int=(from_date,to_date),lead_t=2700,split_criteria=['all'])

		# station.check_Granger_Causality()


	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()