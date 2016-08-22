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
from math import sin, cos, atan2, sqrt, radians
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
		self.neighbors = sorted(self.neighbors,max, key=operator.itemgetter(1))
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

		# add the own station as folder to the analysis path
		self.analysis_path = join(ANALYSIS_PATH, station_to_string(self.id, False).replace(" ", "_").replace(".", "-"))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
		# add the time interval as folder to the analysis path
		self.analysis_path = join(self.analysis_path, str(d_int[0]).replace("-","_")+"-"+str(d_int[1]).replace("-","_"))
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
			# DEBUG: only the specific station
			if(neigh_id == "51d4b5a3-a095-1aa0-e100-80009459e03a"):
				# PRINT: the current station as string
				print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n\n"+station_to_string(neigh_id)+"\n"))
				# get all the pricings out that potentially disrupt the analysis (CURRENTLY: raises)
				rel_idc = self._get_rel_idc(neigh_id)
				# build up the potential rule by investigating the differnet time levels
				self.rule = self._explore_statistics_tree(rel_idc, self.leader_n_idx[neigh_id], neigh_id, split_criteria, 0, [0])
				# PAUSE: after each station investigated
				pause()

	def day_analysis(self, day):
		'''
		Plots the pricings of a day of the station and its neighbors as a timeline

		@param day: day in question
		@dtype day: datetime
		'''

		# add the own station as folder to the analysis path
		self.analysis_path = join(ANALYSIS_PATH, station_to_string(self.id, False).replace(" ", "_").replace(".", "-"))
		if(not(isdir(self.analysis_path))): os.makedirs(self.analysis_path)
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
		self.follower = {} # dict: neigh_id -> List(Tuple(own_idx,fol_idx))
		self.leader_n_idx = {} # dict: neigh_id -> List(Tuple(own_idx,lead_idx,own_cnt,lead_cnt))
		self.leader_p_idx = {} # dict: own_idx -> List(Tuple(neigh_id,lead_idx,own_cnt,lead_cnt))

		# for each neighbor make space the dicts with neigh_id keys
		for (neigh_id, dist) in self.neighbors:
			self.follower[neigh_id] = []
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
					own_set_idx, own_set_alt, own_set_time = self._get_pricings_chain(i, t_int)
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
					# set this as new start index for following iterations
					neigh_pricing_idc[j] = index

					# up_dif is the time difference to the upper own pricing in the chain
					up_dif = 0
					# go up through neighbors pricings until the up_dif is bigger than the threshold
					# pricings over that positive upper threshold are not even an pricing following the own one
					while(up_dif<t_int and index+1<len(neigh.pricing_mat)):
						# get neighbor pricing
						neigh_pricing = neigh.pricing_mat[index]
						# get upper and lower dif
						up_dif = get_time_dif(neigh_pricing, self.pricing_mat[upper_idx])
						low_dif = get_time_dif(neigh_pricing, own_pricing)
						
						# check updif since it just got the current value
						if(up_dif<t_int):
							# if the pricing is past the earliest own it is considered a follower
							if(low_dif>0):
								self.follower[neigh_id].append((i,index))

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
									elif(get_time_dif(neigh.pricing_mat[index],self.pricing_mat[last_raise_idx])<0):
										index += 1
										# check the next possible cause
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
										self._check_leader_multi_multi(neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, own_set_alt, neigh_id, j)


						index+=1

					# endding index for the follower set	
					index -= 1

				if(not(own_single_change)):
					i+=len(own_set_idx)-1

			else:

				"""
				TODO

				Analyse raise data

				"""
				just_raised = True
				last_raise_idx = i
			i+=1

		self._write_first_leader_analysis()

	def _get_pricings_in_span(self, idx, t_span):
		start_idx = idx
		dif = 0

		linked_idx = [idx]
		linked_alt = [self.pricing_mat[idx,pa2i['alt']]]
		linked_times = [str(get_time(self.pricing_mat[idx,pa2i['time']], False))]


		while(dif<t_span and idx<(len(self.pricing_mat)-1)):
			idx += 1
			dif = get_time_dif(self.pricing_mat[idx], self.pricing_mat[start_idx])
			if(dif<t_span and not(is_raise(self.pricing_mat[idx]))):
				linked_idx.append(idx)
				linked_alt.append(self.pricing_mat[idx,pa2i['alt']])
				linked_times.append(str(get_time(self.pricing_mat[idx,pa2i['time']], False)))
			else:
				break

		return linked_idx, linked_alt, linked_times

	def _get_pricings_chain(self, idx, t_span):
		start_idx = idx
		dif = 0

		linked_idx = [idx]
		linked_alt = [self.pricing_mat[idx,pa2i['alt']]]
		linked_times = [str(get_time(self.pricing_mat[idx,pa2i['time']], False))]


		while(dif<t_span and idx<(len(self.pricing_mat)-1)):
			idx += 1
			dif = get_time_dif(self.pricing_mat[idx], self.pricing_mat[start_idx])
			if(dif<t_span and not(is_raise(self.pricing_mat[idx]))):
				start_idx = idx
				linked_idx.append(idx)
				linked_alt.append(self.pricing_mat[idx,pa2i['alt']])
				linked_times.append(str(get_time(self.pricing_mat[idx,pa2i['time']], False)))
			else:
				break

		return linked_idx, linked_alt, linked_times

	def _check_leader_single_single(self, leader_idx, own_idx, neigh_id, j):
		neigh = STATION_DICT[neigh_id]
		own_pricing = self.pricing_mat[own_idx]
		neigh_pricing = neigh.pricing_mat[leader_idx]
		# if the price adjustments are reasonably linked
		n_str = ('\t' + str(j) + '\t' + str(leader_idx) + '\t' + str(neigh_pricing[pa2i['alt']]) + '\t' + str(get_time(neigh_pricing[pa2i['time']], False)) + "\t -> \t " + str([own_idx]))

		if(proper_drop_dif(neigh_pricing, own_pricing)):
			self.leader_n_idx[neigh_id].append((own_idx,leader_idx,0,0))
			self.leader_p_idx[own_idx].append((neigh_id, leader_idx,0,0))
		# 	print(print_bcolors(["BOLD","OKGREEN"],n_str))
		# else:
		# 	print(print_bcolors(["BOLD","FAIL"],n_str))

	def _check_leader_single_multi(self, leader_idx, own_set_idx, own_set_alt, neigh_id, j):
		# the real reaction is the last one that is still a proper adjustment considering the sum of all adjustments up to this point
		# need to take the sum because there is still a need to change after all own adjustments that already occured
		# it is only the last one because it doesn't make sense to adjust twice on the same leader
		# it can however be a couple of single pricings split up 
		neigh = STATION_DICT[neigh_id]
		neigh_pricing = neigh.pricing_mat[leader_idx]

		n_str = ('\t' + str(j) + '\t' + str(leader_idx) + '\t' + str(neigh_pricing[pa2i['alt']]) + '\t' + str(get_time(neigh_pricing[pa2i['time']], False)) + "\t -> \t ")	

		osi = 0
		# first we have to exclude all where the leader is after the own pricing
		while(osi<len(own_set_idx) and get_time_dif(neigh_pricing, self.pricing_mat[own_set_idx[osi]])>0):
			osi+=1

		alt_list = []
		art_pricing = np.zeros((len(pa2i), ))
		art_pricing[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[osi],pa2i['d_diesel']]
		art_pricing[pa2i['d_e5']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e5']]
		art_pricing[pa2i['d_e10']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e10']]

		prop_dist = proper_drop_dif(neigh_pricing, art_pricing)
		osi+=1
		while(osi<len(own_set_idx) and prop_dist):
			art_pricing[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[osi],pa2i['d_diesel']]
			art_pricing[pa2i['d_e5']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e5']]
			art_pricing[pa2i['d_e10']] += self.pricing_mat[own_set_idx[osi],pa2i['d_e10']]
			prop_dist = proper_drop_dif(neigh_pricing, art_pricing)
			if(prop_dist):
				osi+=1
		osi-=1


		if(prop_dist):
			# if the last proper prcing found is a full pricing add it
			take = [own_set_idx[osi]]
			if(own_set_alt[osi]>=21):
				self.leader_n_idx[neigh_id].append((own_set_idx[osi],leader_idx,0,0))
				self.leader_p_idx[own_set_idx[osi]].append((neigh_id, leader_idx,0,0))
				n_str += str(take)
			# else check if it could be combined with previous ones TODO
			else:
				# How to add several as leaded by one TODO
				# right now just add the last
				changes = self.pricing_mat[own_set_idx[osi],[7,9,11]]
				alt = own_set_alt[osi]+own_set_alt[osi-1]
				if(osi>0 and alt <= 21):
					changes_prev =  self.pricing_mat[own_set_idx[osi-1],[7,9,11]]
					comb = [x*y==0 for (x,y) in zip(changes,changes_prev)]
					if(np.sum(comb)==3):
						# print(print_bcolors(["BOLD","WARNING"],"Added several own pricings with the same leader"))
						take.append(own_set_idx[osi-1])

						osi-=1
						changes = [x+y for (x,y) in zip(changes,changes_prev)]
						alt+=own_set_alt[osi-1]
						if(osi>1 and alt<=21):
							changes_prev =  self.pricing_mat[own_set_idx[osi-1],[7,9,11]]
							comb = [x*y==0 for (x,y) in zip(changes,changes_prev)]
							if(np.sum(comb)==3):
								take.append(own_set_idx[osi-1])
								osi-=1

				self.leader_n_idx[neigh_id].append((take[-1],leader_idx,len(take)-1,0))
				self.leader_p_idx[take[-1]].append((neigh_id, leader_idx,len(take)-1,0))
				n_str += str(take)

			# print(print_bcolors(["BOLD","OKGREEN"],n_str))
			return True
		else:
			# print(print_bcolors(["BOLD","FAIL"],n_str))
			return False

	def _check_leader_multi_single(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_idx, neigh_id, j):
		# the leader is the last proper leader
		# because if it was the reaction on a previous one the would have had to be reaction on the following one as well
		neigh = STATION_DICT[neigh_id]
		own_pricing = self.pricing_mat[own_idx]

		if(proper_drop_dif(neigh.pricing_mat[neigh_set_idx[-1]], own_pricing)):
			self.leader_n_idx[neigh_id].append((own_idx,neigh_set_idx[-1],0,0))
			self.leader_p_idx[own_idx].append((neigh_id, neigh_set_idx[-1],0,0))
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[-1]) + '\t' + str(neigh_set_alt[-1]) + '\t' + str(neigh_set_time[-1]) + "\t -> \t " + str([own_idx]))
			# print('')
			# print(print_bcolors(["BOLD","OKGREEN"],n_str))
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[0:-1]) + '\t' + str(neigh_set_alt[0:-1]) + '\t' + str(neigh_set_time[0:-1]) + "\t -> \t " + str([own_idx]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
			# print('')
			return [-1]
		# go back through the leaders and ckeck if combination makes a proper leader
		else:
			# how to add several leaders for one pricing TODO
			art_pricing = np.zeros((len(pa2i), ))
			prop_dist = False
			take_idc = []
			for li in range(1,len(neigh_set_idx)+1):
				art_pricing[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[-li],pa2i['d_diesel']]
				art_pricing[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[-li],pa2i['d_e5']]
				art_pricing[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[-li],pa2i['d_e10']]
				
				take_idc.append(len(neigh_set_idx)-li)

				prop_dist = proper_drop_dif(art_pricing, own_pricing)
				if(prop_dist):											
					self.leader_n_idx[neigh_id].append((own_idx, neigh_set_idx[-li],0,li-1))
					self.leader_p_idx[own_idx].append((neigh_id, neigh_set_idx[-li],0,li-1))
					# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[take_idc[-1]:]) + '\t' + str(neigh_set_alt[take_idc[-1]:]) + '\t' + str(neigh_set_time[take_idc[-1]:]) + "\t -> \t " + str([own_idx]))
					# if(len(take_idc) < len(neigh_set_idx)):
					# 	print('')
					# print(print_bcolors(["BOLD","OKGREEN"],n_str))
					# print(print_bcolors(["BOLD","WARNING"], "Added several leader for one own pricing"))
					# if(len(take_idc) < len(neigh_set_idx)):
					# 	n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[0:take_idc[-1]]) + '\t' + str(neigh_set_alt[0:take_idc[-1]]) + '\t' + str(neigh_set_time[0:take_idc[-1]]) + "\t -> \t " + str([own_idx]))
					# 	print(print_bcolors(["BOLD","FAIL"],n_str))
					# 	print('')
					return take_idc

			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx) + '\t' + str(neigh_set_alt) + '\t' + str(neigh_set_time) + "\t -> \t " + str([own_idx]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
			return []

	def _check_leader_multi_multi(self, neigh_set_idx, neigh_set_alt, neigh_set_time, own_set_idx, own_set_alt, neigh_id, j):
		# TODO
		found_one = False
		nsi = 0
		osi = 0
		neigh = STATION_DICT[neigh_id]

		# print('')

		# exclude all unleaded own pricings
		while(get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) > 0):
			osi += 1

		# as long as there are potential leader sets left
		while(nsi < len(neigh_set_idx) and osi < len(own_set_idx)):
			# take the first leader and initialize the own subset
			cur_n_set = [neigh_set_idx[nsi]]
			cur_n_alt = [neigh_set_alt[nsi]]
			cur_n_time = [neigh_set_time[nsi]]
			nsi += 1
			cur_o_set = []
			cur_o_alt = []
			# as long as there are leaders before the next own add them
			while(nsi < len(neigh_set_idx) and get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) <= 0):
				cur_n_set.append(neigh_set_idx[nsi])
				cur_n_alt.append(neigh_set_alt[nsi])
				cur_n_time.append(neigh_set_time[nsi])
				nsi += 1
			# if nsi is out of bound add all own
			if(nsi==len(neigh_set_idx)):
				cur_o_set.extend(own_set_idx[osi:])
				cur_o_alt.extend(own_set_alt[osi:])
			# else 
			else:
				# as long as there are own pricings before the next leader add them
				while(osi < len(own_set_idx) and get_time_dif(neigh.pricing_mat[neigh_set_idx[nsi]], self.pricing_mat[own_set_idx[osi]]) > 0):
					cur_o_set.append(own_set_idx[osi])
					cur_o_alt.append(own_set_alt[osi])
					osi += 1

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
				# if both set are multi -> check_leader_multi_multi
				else:
					# ckeck for all leader to
					if(cur_n_alt==cur_o_alt):
						self.leader_n_idx[neigh_id].append((cur_o_set[0],cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
						self.leader_p_idx[cur_o_set[0]].append((neigh_id,cur_n_set[0],cur_cnt_o-1,cur_cnt_n-1))
						# n_str = ('\t' + str(j) + '\t' + str(cur_n_set) + '\t' + str(cur_n_alt) + '\t' + str(cur_n_time))
						# print(print_bcolors(["BOLD","OKGREEN"],n_str))
					else:
						# n_str = ('\t' + str(j) + '\t' + str(cur_n_set) + '\t' + str(cur_n_alt) + '\t' + str(cur_n_time))
						# print(print_bcolors(["BOLD","OKBLUE"],n_str))
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
		# the leader is the last proper leader
		# because if it was the reaction on a previous one the would have had to be reaction on the following one as well
		neigh = STATION_DICT[neigh_id]
		osi = 1
		nsi = 1
		neigh_art = np.zeros((len(pa2i), ))
		neigh_art[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_diesel']]
		neigh_art[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e5']]
		neigh_art[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e10']]

		own_art = np.zeros((len(pa2i), ))
		own_art[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_diesel']]
		own_art[pa2i['d_e5']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e5']]
		own_art[pa2i['d_e10']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e10']]

		prop_dif = proper_drop_dif(neigh_art, own_art)

		while(not(prop_dif) and nsi<len(neigh_set_idx)):
			nsi += 1
			neigh_art[pa2i['d_diesel']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_diesel']]
			neigh_art[pa2i['d_e5']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e5']]
			neigh_art[pa2i['d_e10']] += neigh.pricing_mat[neigh_set_idx[-nsi],pa2i['d_e10']]
			prop_dif = proper_drop_dif(neigh_art, own_art)

		if(prop_dif):
			while(prop_dif and osi<len(own_set_idx)):
				osi += 1
				own_art[pa2i['d_diesel']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_diesel']]
				own_art[pa2i['d_e5']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e5']]
				own_art[pa2i['d_e10']] += self.pricing_mat[own_set_idx[-osi],pa2i['d_e10']]
				prop_dif = proper_drop_dif(neigh_art, own_art)
				if(not(prop_dif)):
					osi -= 1
			self.leader_n_idx[neigh_id].append((own_set_idx[-osi],neigh_set_idx[-nsi],osi-1,nsi-1))
			self.leader_p_idx[own_set_idx[-osi]].append((neigh_id, neigh_set_idx[-nsi],osi-1,nsi-1))
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx[-nsi:]) + '\t' + str(neigh_set_alt[-nsi:]) + '\t' + str(neigh_set_time[-nsi:]) + "\t -> \t " + str([own_set_idx[-osi:]]))
			# print(print_bcolors(["BOLD","OKGREEN"],n_str))
			# if(osi > 1 or nsi > 1):
			# 	print(print_bcolors(["BOLD","WARNING"], "Added several pricings"))
			return nsi, osi
		else:
			# n_str = ('\t' + str(j) + '\t' + str(neigh_set_idx) + '\t' + str(neigh_set_alt) + '\t' + str(neigh_set_time) + "\t -> \t " + str([own_set_idx[-osi]]))
			# print(print_bcolors(["BOLD","FAIL"],n_str))
			return 0, osi				

	def _get_rel_idc(self, neigh_id):
		neigh = STATION_DICT[neigh_id]
		# this means all pricings where might be a reason for us to follow
		# start with all pricings
		num_neigh_p = len(neigh.pricing_mat)
		neigh_data_idc = range(0,num_neigh_p)
		# print("num neigh pricings: %d" % num_neigh_p)
		# exclude raises
		raise_idc = neigh._get_raise_idc()
		rel_idc = [x for x in neigh_data_idc if x not in raise_idc]
		# keep all raises but exclude those which are only followers
		# because if they followed us there is no need for us to follow
		# follower_idc = [x[1] for x in self.follower[neigh_id]]
		# leader_idc=[]
		# for (o_idx,n_idx,o_num,n_num) in self.leader_n_idx[neigh_id]:
		# 	leader_idc.append(n_idx)
		# 	if(n_num):
		# 		for i in range(1,n_num+1):
		# 			leader_idc.append(n_idx+i)
		# rel_idc = [x for x in rel_idc if (x not in follower_idc or x in leader_idc )]
		# print("num relevant idc: %d" % len(rel_idc))
		return rel_idc

	def _filter_follower_and_leader(self, neigh_id):
		neigh = STATION_DICT[neigh_id]
		l_idx = 0
		f_idx = 0
		leader = self.leader_n_idx[neigh_id]
		follower = self.follower[neigh_id]
		while(l_idx<len(leader) and f_idx<len(follower)):
			rel = leader[l_idx][0]-follower[f_idx][0]
			if(rel<0):
				l_idx += 1
			elif(rel>0):
				f_idx += 1
			else:
				neigh_lead = leader[l_idx][1]
				neigh_fol = follower[f_idx][1]
				own = leader[l_idx][0]
				if(neigh_lead!=0  and own!=0):
					print('')
					d_dif, e5_dif, e10_dif = get_price_dif(self.pricing_mat[own-1,:], neigh.pricing_mat[neigh_lead-1,:])
					print(print_bcolors(["OKBLUE"], "%d\t%d\t%d" %(d_dif, e5_dif, e10_dif)))
					print(neigh.pricing_to_string(leader[l_idx][1]))
					d_dif, e5_dif, e10_dif = get_price_dif(self.pricing_mat[own-1,:], neigh.pricing_mat[neigh_lead,:])
					print(print_bcolors(["OKBLUE"], "%d\t%d\t%d" %(d_dif, e5_dif, e10_dif)))
					print(self.pricing_to_string(leader[l_idx][0]))
					d_dif, e5_dif, e10_dif = get_price_dif(self.pricing_mat[own,:], neigh.pricing_mat[neigh_lead,:])
					print(print_bcolors(["OKBLUE"], "%d\t%d\t%d" %(d_dif, e5_dif, e10_dif)))
					print(neigh.pricing_to_string(follower[f_idx][1]))
					d_dif, e5_dif, e10_dif = get_price_dif(self.pricing_mat[own,:], neigh.pricing_mat[neigh_fol,:])
					print(print_bcolors(["OKBLUE"], "%d\t%d\t%d" %(d_dif, e5_dif, e10_dif)))
				l_idx += 1
				f_idx += 1
				raw_input("Press Enter to continue...")

	def _get_time_series_data(self):
		berlin = pytz.timezone('Etc/GMT-2')
		init_time = time(0,0,0,0,berlin)
		start_date = datetime.combine(INIT_DATE,init_time)

		len_t_series = int((END_DATE - INIT_DATE).total_seconds()/60) + 1440
		time_series = np.zeros((len_t_series,3))

		idx = 0
		for i in range(0,len(self.pricing_mat)-1):
			d = self.pricing_mat[i,pa2i['diesel']]
			e5 = self.pricing_mat[i,pa2i['e5']]
			e10 = self.pricing_mat[i,pa2i['e10']]
			row = [d,e5,e10]
			fol_d = self.pricing_mat[i+1,pa2i['date']]
			fol_s = self.pricing_mat[i+1,pa2i['time']]
			fol_time = get_timestamp(fol_d,fol_s)
			len_int = int((fol_time - start_date).total_seconds()/60)
			time_series[idx:len_int] = row

		d = self.pricing_mat[-1,pa2i['diesel']]
		e5 = self.pricing_mat[-1,pa2i['e5']]
		e10 = self.pricing_mat[-1,pa2i['e10']]
		row = [d,e5,e10]

		len_int = int((END_DATE - INIT_DATE).total_seconds()/60) + 1440
		time_series[idx:len_int] = row
		return time_series

	def _get_leader_difmat(self):

		if self.leader_n_idx is None:
			print(print_bcolors(['BOLD', 'FAIL'], "Need to get competition first"))
			sys.exit(1)

		num_neigh = len(self.neighbors)
		dif_mat = np.zeros((len(self.pricing_mat),num_neigh,3))

		for (neigh_id, leaders) in self.leader_n_idx:
			neigh = STATION_DICT[neigh_id]
			for (opi, npi) in leaders:
				dif_mat[opi,npi,:] = get_price_dif(self.pricing_mat[opi],neigh.pricing_mat[npi])

		return dif_mat



	def _split_at(self, data_idc, station_id, split_criterium):


		'''
		CAN BE IMPROVED DICTS RATHER THAN LISTS AND JUST ITERATING ONCE OVER 
		ALL INDICES !!!!
		'''


		data = STATION_DICT[station_id].pricing_mat
		try:
			# split data between weekend and weekday
			if(split_criterium=="we"):
				we,wd = [],[]
				for idx in data_idc:
					if(data[idx][pa2i['dow']]>=5):
						we.append(idx)
					else:
						wd.append(idx)
				return [we,wd], ['weekend', 'weekday']

			# split data between different days of the week
			elif(split_criterium=="dow"):
				dow_set = set(map(int, data[data_idc,pa2i['dow']]))
				splits = []
				split_vals = []
				for dow in dow_set:
					split_vals.append(dow)
					splits.append([idx for idx in data_idc if data[idx][pa2i['dow']]==dow])
				return splits, split_vals

			# split data between different times of the day (morning, afternoon, night)
			elif(split_criterium=="tod"):
				m,a,n = [],[],[]
				for idx in data_idc:
					hour = int(data[idx][pa2i['time']]/3600)
					if(hour>=6 and hour<12):
						m.append(idx)
					elif(hour>=12 and hour<22):
						a.append(idx)
					else:
						n.append(idx)
				return [m,a,n], ['morning', 'afternoon', 'night']

			# split data between the different hours of the day
			elif(split_criterium=="hour"):
				hour_set = set(map(int, data[data_idc,pa2i['time']]/3600))
				splits = []
				split_vals = []
				for hour in hour_set:
					split_vals.append(hour)
					splits.append([idx for idx in data_idc if int(data[idx][pa2i['time']]/3600)==hour])
				return splits, split_vals
			else:
				raise ValueError("Wrong split criterium")

		except ValueError:
			traceback.print_exc()
			print("You used %s as split criterium. Please use we, dow, tod or hour only!" % split_criterium)
			sys.exit(1)

	def _explore_statistics_tree(self, rel_idc, leader, neigh_id , split_criteria, split_level, split_vals):

		# rel_idc are the relevant pricings meaning those which are not a raise or leader except they are a leader as well

		# matches are the leader of the current datasplit
		# non_matches are those pricings of neighbors that was not reacted on which were not following on an own pricing

		rule = Rule(self.id, neigh_id, split_criteria, split_level, split_vals, self.analysis_path)
		matches, misses = self._get_matches_and_misses_subsets(rel_idc, leader, neigh_id)
		counts = {'data':len(rel_idc),'match':len(matches),'miss':len(misses)}
		rule.counts.update(counts)

		rule.match_difs, counts = self._get_match_difs(matches, neigh_id)
		rule.miss_difs = self._get_miss_difs(misses, neigh_id)
		rule.counts.update(counts)
		rule._get_stats(matches, misses)

		if(rule.split_further):
			split_level+=1
			if(split_level<len(split_criteria)):
				next_crit = split_criteria[split_level]
				# split the data
				# print(print_bcolors(["BOLD","UNDERLINE"], '\n' + ('Splitting at: ' + next_crit).center(80)))
				data_splits, new_split_vals = self._split_at(rel_idc, neigh_id, next_crit)
				rule.subrules = [None for i in range(0,len(data_splits))]
				rule.sr_idc = range(0,len(data_splits))
				# go one level deeper in the tree
				split_vals.append(0)
				for i in range(0,len(data_splits)):
					split_vals[-1] = new_split_vals[i]
					rule.subrules[i] = self._explore_statistics_tree(data_splits[i], matches, neigh_id, split_criteria, split_level, split_vals)
				sr_idx=0
				while(sr_idx<len(rule.subrules)-1):
					if(rule.subrules[sr_idx]==rule.subrules[sr_idx+1]):
						rule.subrules.pop(sr_idx+1)
						rule.sr_idc[sr_idx+1] = sr_idx
					else:
						sr_idx+=1
				if(len(rule.subrules)==1):
					rule.subrules = None
					rule.sr_idc = None

		return rule
		
	def _get_matches_and_misses_subsets(self, data_idc_sub, leader, neigh_id):
		neigh = STATION_DICT[neigh_id]
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

				'''
				TODO : check if in opening hours:
				FOR NOW check if own index was a raise
				'''
				# add the pair of index
				if(own_idx>=0 and get_time_dif(self.pricing_mat[own_idx+1],neigh.pricing_mat[neigh_idx])>2700 and not(is_raise(self.pricing_mat[own_idx]))):
					non_matches.append((own_idx,neigh_idx))

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
				# print(pricing_to_string(self.pricing_mat[own_idx]))
				# print(pricing_to_string(neigh.pricing_mat[neigh_idx]))
				# print(pricing_to_string(self.pricing_mat[own_idx+1]))
				# pause()

				d_idx += 1

		return matches, non_matches
	
	def _get_mean_and_dev_r_time(self, leader, neigh_id, print_val=True):
		neigh = STATION_DICT[neigh_id]
		time_dif = np.zeros((len(leader), ))
		for i in range(0,len(leader)):
			o = leader[i][0]
			l = leader[i][1]
			own_d = self.pricing_mat[o,pa2i['date']]
			own_s = self.pricing_mat[o,pa2i['time']]
			neigh_d = neigh.pricing_mat[l,pa2i['date']]
			neigh_s = neigh.pricing_mat[l,pa2i['time']]
			time_dif[i] = get_time_dif(neigh.pricing_mat[l], self.pricing_mat[o])
			
		try:
			m = np.mean(time_dif)
			s = np.std(time_dif)
		
		except:
			print(len(time_dif))
			# sys.exit(1)

		if(print_val):
			print('reacted in an average of %f with a std of %f' % (m, s))
		return m, s

	def _get_match_difs(self, matches, neigh_id):
		neigh = STATION_DICT[neigh_id]
		price_dif = np.zeros((len(matches),3,3))

		reset_cnt = 0
		split_cnt = 0
		fuse_cnt = 0

		match_cnt = len(matches)

		for i in range(0,match_cnt):

			# get the matches entry
			(o, l, o_num, l_num) = matches[i]

			if(o_num>l_num):
				split_cnt+=1
			if(o_num<l_num):
				fuse_cnt+=1

			changed = 0
			reset_val = 0

			# get the price differences before, between and after the change
			price_dif[i,0,:] = get_price_dif(self.pricing_mat[o-1],neigh.pricing_mat[l-1])
			price_dif[i,1,:] = get_price_dif(self.pricing_mat[o-1],neigh.pricing_mat[l+l_num])
			price_dif[i,2,:] = get_price_dif(self.pricing_mat[o+o_num],neigh.pricing_mat[l+l_num])

			if(price_dif[i,0,0]!=price_dif[i,1,0]):
				changed+=1
				if(price_dif[i,0,0]==price_dif[i,2,0]):
					reset_val += 1

			if(price_dif[i,0,1]!=price_dif[i,1,1]):
				changed+=4
				if(price_dif[i,0,1]==price_dif[i,2,1]):
					reset_val += 4

			if(price_dif[i,0,2]!=price_dif[i,1,2]):
				changed+=16
				if(price_dif[i,0,2]==price_dif[i,2,2]):
					reset_val += 16

			if(changed==reset_val):
				reset_cnt += 1

		return price_dif, {'reset' : reset_cnt, 'fuse' : fuse_cnt, 'split' : split_cnt}

	def _get_miss_difs(self, misses, neigh_id):
		neigh = STATION_DICT[neigh_id]
		# copy the differences of the non_matches into a numpy array (non_matches*3)
		miss_difs = np.zeros((len(misses),3))
		for i in range(0,len(misses)):
			(own_idx,neigh_idx) = misses[i]
			miss_difs[i,:] = get_price_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])
		return miss_difs



	######### Plotting + Writing ##########

	def _plot_dif_hist(self, dif_mat):
		#
		print("\n Plotting difference histograms for potential neighbors\n")
		def autolabel(rects):
		    # attach some text labels
		    for rect in rects:
		        height = rect.get_height()
		        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
		                '%d' % int(height),
		                ha='center', va='bottom')

		for n in range(0,len(self.neighbors)):
			fig = plt.figure()
			station_str = station_to_string(self.neighbors[n][0])
			fig.suptitle(station_str)
			for fuel in range(0,3):
				unique, counts = np.unique(dif_mat[:,n,fuel], return_counts=True)
				ax = fig.add_subplot(3,1,fuel+1)

				## necessary variables
				width = 0.35
				ind = np.arange(len(unique)-2)
				## the bars
				rects1 = ax.bar(ind, counts[:-2], width, color='red')

				# axes and labels
				ax.set_xlim(-width,len(unique)+width)
				# ax.set_ylim(0,45)
				ax.set_ylabel('counts')
				ax.set_xlabel('dif',ha='right')
				ax.set_title(5*fuel)

				ax.set_xticks(ind + width/2)
				xtickNames = ax.set_xticklabels(unique)
				plt.setp(xtickNames, rotation=60, fontsize=8)
				# plt.gcf().subplots_adjust(bottom=0.15)
				autolabel(rects1)

			## add a legend
			# ax.legend((rects1[0], ), ('pricings month hist', ))
			# plt.show()
			fig.tight_layout()


			filedir = join(self.analysis_path, "neigh_diff_hist")
			if(not(isdir(filedir))): os.makedirs(filedir)
			file_name = station_to_string(self.neighbors[n][0], False).replace(" ", "_")
			file_name = file_name.replace(".", "-")
			fig.savefig(join(filedir,file_name))

	def _write_first_leader_analysis(self):
		real_contenders =  ['8a5b2591-8821-4a36-9c82-4828c61cba29', 'ebc673e0-8359-4ab6-0afa-c31cc35c4bd2',
		'30d8de2f-7728-4328-929f-b45ff1659901', '51d4b54f-a095-1aa0-e100-80009459e03a', '51d4b5a3-a095-1aa0-e100-80009459e03a',
		'f4b31676-e65e-4b60-8851-609c107f5d93']

		HTMLFILE = 'pricings.html'
		f = open(join(self.analysis_path,HTMLFILE), 'w')

		for own_idx, leaders in self.leader_p_idx.items():
			f.write(html_heading(1,pricing_to_string(self.pricing_mat[own_idx])))
			t = HTML.Table(header_row=['t-dif', GAS[0], GAS[1], GAS[2], 'station'])
			for (neigh_id,neigh_idx,o_num,n_num) in leaders:
				neigh = STATION_DICT[neigh_id]
				d_dif_pre, e5_dif_pre, e10_dif_pre = get_price_dif(self.pricing_mat[own_idx-1,:],neigh.pricing_mat[neigh_idx-1,:])
				d_dif_bet, e5_dif_bet, e10_dif_bet = get_price_dif(self.pricing_mat[own_idx-1,:],neigh.pricing_mat[neigh_idx+n_num,:])
				d_dif_post, e5_dif_post, e10_dif_post = get_price_dif(self.pricing_mat[own_idx+o_num,:],neigh.pricing_mat[neigh_idx+n_num,:])

				station_str = station_to_string(neigh_id, False)
				time_dif = "%2d"%(int(get_time_dif(self.pricing_mat[own_idx],neigh.pricing_mat[neigh_idx])/60))
				d_str = "%3d -> %3d -> %3d" % (d_dif_pre, d_dif_bet, d_dif_post)
				e5_str = "%3d -> %3d -> %3d" % (e5_dif_pre, e5_dif_bet, e5_dif_post)
				e10_str = "%3d -> %3d -> %3d" % (e10_dif_pre, e10_dif_bet, e10_dif_post)
				# if(neigh_id in real_contenders):
				# 	attribs[color] = 'green'
				t.rows.append([time_dif, d_str, e5_str, e10_str,station_str])
			htmlcode = str(t)
			f.write(htmlcode)
			f.write('<p>')

		f.close()

		"""
		price wiederhergestellt
		schnelllste
		gleiche abstände
		von pre zu bet dif nach oben
		hövhste abstände
		erstes pricing nach einem raise besonders behandeln
		"""

	def _plot_day_timeline(self, day):

		target_ids = ['ebc673e0-8359-4ab6-0afa-c31cc35c4bd2', '8a5b2591-8821-4a36-9c82-4828c61cba29',
		'30d8de2f-7728-4328-929f-b45ff1659901', '51d4b54f-a095-1aa0-e100-80009459e03a',
		'51d4b5a3-a095-1aa0-e100-80009459e03a', 'f4b31676-e65e-4b60-8851-609c107f5d93',
		'90543baf-7517-43cd-9c59-1a2493c26358']

		weekday = day.weekday()

		colors = get_colors(len(target_ids))
		c_idx = 0

		for (station_id, dif) in self.neighbors:
			if station_id in target_ids:
				neigh = STATION_DICT[station_id]

				st_str = station_to_string(station_id, False)
				time = neigh.pricing_mat[:,pa2i['time']]/3600

				plt.figure(1)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['diesel']], where='post', label=st_str, color=colors[c_idx], ls='-.')
				plt.figure(2)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['e5']], where='post', label=st_str, color=colors[c_idx], ls='-.')
				plt.figure(3)
				plt.subplot(111)
				plt.step(time, neigh.pricing_mat[:,pa2i['e10']], where='post', label=st_str, color=colors[c_idx], ls='-.')

				c_idx += 1

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

		for i in range(1,4):
			plt.figure(i)
			plt.title(GAS[i-1] + '   ' + str(day) + '   dow:' + str(weekday))
			ax = plt.gca()
			ax.set_xticks(range(0,24))
			yticks = ax.get_yticks()
			ax.set_yticks(np.arange(min(yticks), max(yticks)+1, 2.0))
			ax.set_yticklabels(ax.get_yticks()/100)

			ax.set_xlabel('time in hours')
			ax.set_ylabel('price in Euro')

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
			# ax.legend()
			handles, labels = ax.get_legend_handles_labels()
			lgd = ax.legend(handles, labels, loc='upper center')

			dpi = plt.figure(i).get_dpi()
			plt.figure(i).set_size_inches(1920.0/float(dpi),1080.0/float(dpi))

			file_name = GAS[i-1]
			plt.savefig(join(self.analysis_path,file_name), bbox_extra_artists=(lgd,), bbox_inches='tight')

	def _leader_n_idx_to_html_table(self, neigh_id, leader):

		table_data = []
		own_idx,neigh_idx,o_num,n_num = leader[:]
		neigh = STATION_DICT[neigh_id]

		# check out previous pricing
		o_pos = own_idx-1
		n_pos = neigh_idx - 1
		own_p = self.pricing_mat[o_pos]
		neigh_p = neigh.pricing_mat[n_pos]

		d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
		t_dif = get_time_dif(own_p, neigh_p)
		if(t_dif>0):
			table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_time(own_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])
		else:
			table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_time(neigh_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
				neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

		# add the leader set
		while(n_pos<neigh_idx+n_num):
			n_pos+=1
			neigh_p = neigh.pricing_mat[n_pos]
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_time(neigh_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
				neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])

		# add the own set
		while(o_pos<own_idx+o_num):
			o_pos+=1
			own_p = self.pricing_mat[o_pos]
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_time(own_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])

		# check out directly following pricing
		own_p = self.pricing_mat[o_pos+1]
		neigh_p = neigh.pricing_mat[n_pos+1]
		t_dif = get_time_dif(own_p, neigh_p)
		if(t_dif>0):
			own_p = self.pricing_mat[o_pos]
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			table_data.append([HTML.TableCell('neigh', bgcolor='#cc0000'), get_time(neigh_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				neigh_p[pa2i['d_diesel']], neigh_p[pa2i['d_e5']], neigh_p[pa2i['d_e10']],
				neigh_p[pa2i['diesel']], neigh_p[pa2i['e5']], neigh_p[pa2i['e10']]])
		else:
			neigh_p = neigh.pricing_mat[n_pos]
			d_dif, e5_dif, e10_dif = get_price_dif(own_p, neigh_p)
			table_data.append([HTML.TableCell('own', bgcolor='#3bb300'), get_time(own_p[pa2i['time']],False),
				d_dif, e5_dif, e10_dif,
				own_p[pa2i['d_diesel']], own_p[pa2i['d_e5']], own_p[pa2i['d_e10']],
				own_p[pa2i['diesel']], own_p[pa2i['e5']], own_p[pa2i['e10']]])

		htmlcode = HTML.table(table_data,
		    header_row = ['role', 'time',HTML.TableCell('dif', attribs={'colspan':3}),
		    HTML.TableCell('changed', attribs={'colspan':3}), HTML.TableCell('price', attribs={'colspan':3})])
		return htmlcode


	######### Printing ##########
	def print_neighbors(self):
		if(self.neighbors==None): self.get_neighbors(STATION_DICT)

		station_str = station_to_string(self.id)

		print(print_bcolors(["BOLD","OKBLUE"],'\n\n' + 'Neighbors of station:'.center(len(station_str))))
		print(print_bcolors(["BOLD","OKBLUE","UNDERLINE"], station_str + '\n'))

		header = "%s | " % "DIST".center(6)
		header += get_station_header()
		print(header)
		print(("-" * len(header)))

		for neighbor in self.neighbors:
			station_id = neighbor[0]
			station_dist = neighbor[1]
			station_str = station_to_string(station_id)

			row = "%1.4f | "% station_dist
			row += station_to_string(station_id)
			print(row)

		print("\n")

	def _print_leader(self, leader, neigh_id):

		neigh = STATION_DICT[neigh_id]

		d_cnt = 0
		e10_cnt = 0
		e5_cnt = 0
		all_cnt = 0
		all_true = True

		# f = open(join(filedir, "drop_history_" + days + ".txt"),'w+')

		for (own_idx,neigh_idx) in leader:
			all_true = True
			# if(self.pricing_mat[own_idx,pa2i['dow']]>4):
			d_dif_pre = self.pricing_mat[own_idx-1,pa2i['diesel']] - neigh.pricing_mat[neigh_idx-1,pa2i['diesel']]
			d_dif_bet = self.pricing_mat[own_idx-1,pa2i['diesel']] - neigh.pricing_mat[neigh_idx,pa2i['diesel']]
			d_dif_post = self.pricing_mat[own_idx,pa2i['diesel']] - neigh.pricing_mat[neigh_idx,pa2i['diesel']]
			if(d_dif_pre!=d_dif_bet and d_dif_pre==d_dif_post): d_cnt+=1
			else: all_true= False

			e5_dif_pre  = self.pricing_mat[own_idx-1,pa2i['e5']] - neigh.pricing_mat[neigh_idx-1,pa2i['e5']]
			e5_dif_bet = self.pricing_mat[own_idx-1,pa2i['e5']] - neigh.pricing_mat[neigh_idx,pa2i['e5']]
			e5_dif_post = self.pricing_mat[own_idx,pa2i['e5']] - neigh.pricing_mat[neigh_idx,pa2i['e5']]
			if(e5_dif_pre!=e5_dif_bet and e5_dif_pre==e5_dif_post): e5_cnt+=1
			else: all_true= False

			e10_dif_pre = self.pricing_mat[own_idx-1,pa2i['e10']] - neigh.pricing_mat[neigh_idx-1,pa2i['e10']]
			e10_dif_bet = self.pricing_mat[own_idx-1,pa2i['e10']] - neigh.pricing_mat[neigh_idx,pa2i['e10']]
			e10_dif_post = self.pricing_mat[own_idx,pa2i['e10']] - neigh.pricing_mat[neigh_idx,pa2i['e10']]
			if(e10_dif_pre!=e10_dif_bet and e10_dif_pre==e10_dif_post): e10_cnt+=1
			else: all_true= False

			if(all_true): all_cnt+=1

			own_d = self.pricing_mat[own_idx,pa2i['date']]
			own_s = self.pricing_mat[own_idx,pa2i['time']]
			own_tst = get_timestamp(own_d, own_s)

			neigh_d = neigh.pricing_mat[neigh_idx,pa2i['date']]
			neigh_s = neigh.pricing_mat[neigh_idx,pa2i['time']]
			neigh_tst = get_timestamp(neigh_d, neigh_s)

			# t_dif_s = int(86400*(own_d-neigh_d)+(own_s-neigh_s))
			# t_dif_str = "%2d:%2d" % (t_dif_s/60, t_dif_s%60)

			# pre_str = "%s | %2d | %2d | %2d |" % (str("pre " + str(neigh_tst) + " :").center(40),
			# 	d_dif_pre, e10_dif_pre, e5_dif_pre)
			# print(pre_str)

			# bet_str = "%s | %2d | %2d | %2d |" % (str("timedif =  " + t_dif_str + " :").center(40),
			# 	d_dif_bet, e10_dif_bet, e5_dif_bet)
			# print(bet_str)

			# post_str = "%s | %2d | %2d | %2d |" % (str("post " + str(own_tst) + " :").center(40),
			# 	d_dif_post, e10_dif_post, e5_dif_post)
			# print(post_str)
			# print("")

		print("| %5d | %5d | %5d | %5d | %5d |" % (len(leader),
			all_cnt, d_cnt, e10_cnt, e5_cnt))
		print("")


	######### Some visualisations ##########
	def plot_pricing_month_hist(self, date_int):

		year = date_int(0).year
		month = date_int(0).month
		to_year = date_int(1).year
		to_month = date_int(1).month

		month_hist = []
		xTickMarks = []
		while(year<=to_year and month<=to_month):
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
				" WHERE " + PG['STID'] + " AND " + PG['MONTH'] + " AND " + PG['YEAR'] % (self.id, year, month))
			month_hist.append(CURSOR.fetchone()[0])
			mstr = '%d. %d' % (month, year)
			xTickMarks.append(mstr)
			if(month/12==1): year+=1
			month = month%12 + 1 

		fig = plt.figure()
		ax = fig.add_subplot(111)

		## necessary variables
		ind = np.arange(len(month_hist))
		width = 0.35

		## the bars
		rects1 = ax.bar(ind, month_hist[:,1], width, color='red')

		# axes and labels
		ax.set_xlim(-width,len(ind)+width)
		# ax.set_ylim(0,45)
		ax.set_ylabel('pricings')
		ax.set_xlabel('month')
		ax.set_title('pricings month hist')

		ax.set_xticks(ind + width/2)
		xtickNames = ax.set_xticklabels(xTickMarks)
		plt.setp(xtickNames, rotation=60, fontsize=8)
		plt.gcf().subplots_adjust(bottom=0.15)

		## add a legend
		ax.legend((rects1[0], ), ('pricings month hist', ))
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		fig.savefig(join(filedir, ("month_hist")))

	def plot_pricing_hour_hist(self, dow_int, date_int):
		""" Get all price adaptions in the selected interval und and count 
		the occurances for each hour.
		"""	
		pricing_hist = np.zeros((24, ))
		for i in range(0,24):
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history" +
				" WHERE " + PG['STID'] +
				" AND " + PG['DOW_INT'] +
				" AND " + PG['DATE_INT'] +
				" AND " + PG['HOUR'],
				(self.id,)+dow_int+date_int+(i,))
			pricing_hist[i] = CURSOR.fetchone()[0];
		fig = plt.figure()
		ax = fig.add_subplot(111)

		## necessary variables
		ind = np.arange(24)
		width = 0.35

		## the bars
		rects1 = ax.bar(ind, pricing_hist, width, color='red')

		# axes and labels
		ax.set_xlim(-width,len(ind)+width)
		# ax.set_ylim(0,45)
		ax.set_ylabel('pricings')
		ax.set_xlabel('hour')
		ax.set_title('pricing time hist')
		xTickMarks = [i for i in range(0,24)]
		ax.set_xticks(ind + width/2)
		xtickNames = ax.set_xticklabels(xTickMarks)
		plt.setp(xtickNames, rotation=0, fontsize=10)
		plt.gcf().subplots_adjust(bottom=0.15)

		## add a legend
		ax.legend((rects1[0], ), ('pricing time hist', ))
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		fig.savefig(join(filedir,"time_hist_" + d))
		# plt.show()

	def print_pricings_per_time_category(self, dow_int, date_int, time_int):

		CURSOR.execute("SELECT * FROM gas_station_information_history"+
			" WHERE " + PG['STID'] +
			" AND " + PG['DOW_INT'] +
			" AND " + PG['DATE_INT'] +
			" AND " + PG['HOUR_INT'],
			(self.id,)+dow_int+date_int+time_int)
		changes = CURSOR.fetchall();

		textwidth = 60
		print((bcolors.BOLD + bcolors.OKBLUE +
			'Selected station: %s at pos:(%s,%s) \n'\
			%(self.name, self.geo_pos['lat'],
			self.geo_pos['lng'])).center(textwidth)+bcolors.ENDC)

		print(bcolors.BOLD + bcolors.OKBLUE + "Changes on " +  + bcolors.ENDC)

		textwidth_reduced = textwidth - 15
		header = "%s | %s | %s | %s | %s | %s" % ("date".center(10),
                "time".center(10),
                "changed".center(6),
                "diesel".center(6),
                "e5".center(6),
                "e10".center(6))
		print(header)
		print(("-" * textwidth))

		for change in changes:
			c_date = change[5].date()
			c_time = change[5].time()
			c_changed = change[6]
			c_diesel = change[4]
			c_e5 = change[2]
			c_e10 = change[3]
			row = "%s | %s | %s | %s | %s | %s" % (str(c_date).center(10),
				str(c_time).center(10),
				(("%" + str(6) + "d") % c_changed),
                (("%" + str(6) + "d") % c_diesel),
                (("%" + str(6) + "d") % c_e5),
                (("%" + str(6) + "d") % c_e10))
			print(row)


class Rule(object):
	__slots__ = ('owner', 'competitor',
		'split_criteria', 'split_vals', 'split_further', 'rule_str',
		'max_p_dist', 'conf', 'consistent',
		'match_difs', 'miss_difs', 'counts',
		'subrules', 'sr_idc',
		'analysis_path')

	def __init__(self, owner, competitor, split_criteria, split_level, split_vals, analysis_path):
		self.owner = owner
		self.competitor = competitor

		self.split_criteria = split_criteria[0:split_level+1]
		self.split_vals = split_vals
		self.split_further = False
		self.rule_str = split_criteria[0]+':'+str(split_vals[0])
		for i in range(1,split_level+1):
			self.rule_str += split_criteria[i]+':'+str(split_vals[i])

		self.match_difs = None
		self.miss_difs = None
		self.counts = {}

		self.max_p_dist = None
		self.conf = None
		self.consistent = True

		self.subrules =None
		self.sr_idc = None

		self.analysis_path = analysis_path

	def __str__(self):
		# TODO
		pass

	def _stats_to_string(self):
		# print(print_bcolors(["OKGREEN","BOLD"], "\n" + node_label.center(textwidth)))
		# print('contains %d pricings' %(data_cnt,))
		# print('\t with %d leader matches, making %f' %  (match_cnt, float(match_cnt)/data_cnt))
		# print('\t and %d leader matches, making %f' % (non_match_cnt, float(non_match_cnt)/data_cnt))

		# print('The same prices where changed %d times all prices making %f' % (same_alt, float(same_alt)/match_cnt))
		# print('the own pricing resettet %d times all prices making %f' % (all_cnt, float(all_cnt)/match_cnt))
		# print('the own pricing resettet %d times the appropriate prices making %f' % (prop_cnt, float(prop_cnt)/match_cnt))
		# zipped = zip(modes,counts,(counts/float(match_cnt)))

		# print(print_bcolors(["UNDERLINE"], "stat".center(20) + "diesel".center(23) + "e5".center(23) + "e10".center(23)))
		# stats_str = ['mod_dif_before', 'mod_dif_between', 'mod_dif_after']
		# for i in range(0,3):
		# 	row = stats_str[i].center(20)
		# 	row += "| %2d\t%2d\t%.3f | " %(int(zipped[i][0]), zipped[i][1], zipped[i][2])
		# 	row += "%2d\t%2d\t%.3f | " %(int(zipped[i+3][0]), zipped[i+3][1], zipped[i+3][2])
		# 	row += "%2d\t%2d\t%.3f" %(int(zipped[i+6][0]), zipped[i+6][1], zipped[i+6][2])
		# 	print(row)

		# print('')
		# row = "max_dif_m_after".center(20)
		# row += "| %2d\t%2d\t%.3f | " %(max_val[2], d_max_cnt, d_max_cnt/float(match_cnt))
		# row += "%2d\t%2d\t%.3f | " %(max_val[5], e5_max_cnt, e5_max_cnt/float(match_cnt))
		# row += "%2d\t%2d\t%.3f" %(max_val[8], e10_max_cnt, e10_max_cnt/float(match_cnt))
		# print(row)


		# if(data_cnt>0):
		# 	if(match_cnt>0):
		# 		if(len(split_criteria)==0):

		# 			# get values for this interval
		# 			split
		# 			mean_r_time, std_r_time = self._get_mean_and_dev_r_time(matches, neigh_id) 
		# 			all_r, prop_r, modes, counts, max_val = self._get_price_dif_stats(matches, neigh_id)

		# 			# get the max price distance for neighbor pricings which were not reacted on
		# 			# indicate the max allowed distance
		# 			non_match_cnt = len(non_matches_difs)

		# 			if(non_match_cnt>0):
		# 				max_vals = np.amax(non_matches_difs,axis=0)

		# 				max_counts = [np.sum(non_matches_difs[:,i]==max_vals[i]) for i in range(0,3)]
		# 				max_cnt_perc = [max_counts[i]/float(non_match_cnt) for i in range(0,3)]

		# 				print('')
		# 				row = "max_dif_nm_after".center(20)
		# 				row += "| %2d\t%2d\t%.3f | " %(max_vals[0], max_counts[0], max_cnt_perc[0])
		# 				row += "%2d\t%2d\t%.3f | " %(max_vals[1], max_counts[1], max_cnt_perc[1])
		# 				row += "%2d\t%2d\t%.3f" %(max_vals[2], max_counts[2], max_cnt_perc[2])
		# 				print(row)

		# 				for i in range(0,3):
		# 					if(max_cnt_perc[i]<=0.1):
		# 						print(print_bcolors(["FAIL","BOLD"], "\nUnexpected value in non_match maximal difference: " + str(GAS[i])))
		# 						extremes = np.nonzero(non_matches_difs[:,i]==max_vals[i])[0]
		# 						neigh = STATION_DICT[neigh_id]
		# 						for idx in extremes:
		# 							(own_idx, neigh_idx) = non_matches[idx]
		# 							print(pricing_to_string(self.pricing_mat[own_idx]))
		# 							print(print_bcolors(["FAIL","BOLD"],pricing_to_string(neigh.pricing_mat[neigh_idx])))
		# 							print(pricing_to_string(self.pricing_mat[own_idx+1]))
		# 							print(pricing_to_string(self.pricing_mat[own_idx+2]))
		# 			else:
		# 				print('\n No non matches found')


		# 	else:
		# 		print(print_bcolors(["WARNING"], 'no MATCHES in this intervall!!!'))
		# else:
		# 	print(print_bcolors(["WARNING"], 'no DATA in this intervall!!!'))
		pass

	def _get_stats(self, matches, misses):

		own_station = STATION_DICT[self.owner]

		filedir = join(self.analysis_path, station_to_string(self.competitor, False).replace(" ", "_"))
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, "difs_outlier")
		if(not(isdir(filedir))): os.makedirs(filedir)
		file_name = self.rule_str + '.html'
		f = open(join(filedir,file_name), 'w')

		f.write(html_intro("difs_outlier in rule: " + self.rule_str))
		# get the dif_histogram, maximum value and modal value after own pricing
		# get the dif histogram, maximum value and modal value after unreacted neighbor pricings
		max_tup_after_own = []
		max_tup_after_unreacted = []
		mod_tup_after_own = []
		mod_tup_after_unreacted  = []
		# (additional) get the dif_histogram, minimum value and modal value after the leading pricing
		# min_tup_after_leader

		self._plot_match_miss_dif_hists()
		for gas in range(0,len(GAS)):
			f.write(html_heading(1, GAS[gas]))
			unique, counts = np.unique(self.match_difs[:,2,gas], return_counts=True)
			r_idx = -1
			max_tup_after_own.append((unique[r_idx], counts[r_idx]))
			mod_idx = np.argmax(counts)
			mod_tup_after_own.append((unique[mod_idx], counts[mod_idx]))

			unique2, counts2 = np.unique(self.miss_difs[:,gas], return_counts=True)
			unr_idx = -1
			max_tup_after_unreacted.append((unique2[unr_idx], counts2[unr_idx]))
			mod_idx = np.argmax(counts2)
			mod_tup_after_unreacted.append((unique2[mod_idx], counts2[mod_idx]))


			comb_cnt = max_tup_after_own[gas][1]+max_tup_after_unreacted[gas][1]
			comb_conf = comb_cnt*(comb_cnt/(self.counts['match']+self.counts['miss']))

			own_conf = max_tup_after_own[gas][1]*(float(max_tup_after_own[gas][1])/self.counts['match'])
			f.write(html_heading(2, "After own reset"))
			while(own_conf<1.5 and -r_idx<len(unique)):
				f.write(html_heading(3, "dif: " + str(unique[r_idx]) + "\tcount: " + str(counts[r_idx]) + "\tconf: " + str(own_conf)))
				outlier = [i for i in range(0,self.counts['match']) if self.match_difs[i,2,gas]==unique[r_idx]]
				for idx in outlier:
					f.write(own_station._leader_n_idx_to_html_table(self.competitor, matches[idx]))
					f.write('<br>')

				r_idx-=1
				max_tup_after_own[gas] = ((unique[r_idx], counts[r_idx]))
				own_conf = max_tup_after_own[gas][1]*(float(max_tup_after_own[gas][1])/self.counts['match'])
			f.write('<br>')

			unreacted_conf = max_tup_after_unreacted[gas][1]*(float(max_tup_after_unreacted[gas][1])/self.counts['miss'])
			f.write(html_heading(2, "After unreacted pricing"))
			while(unreacted_conf<1.5 and -unr_idx<len(unique2)):
				f.write(html_heading(3, "dif: " + str(unique2[unr_idx]) + "\tcount: " + str(counts2[unr_idx]) + "\tconf: " + str(unreacted_conf)))
				outlier = [i for i in range(0,self.counts['miss']) if self.miss_difs[i,gas]==unique2[unr_idx]]
				for idx in outlier:
					f.write(own_station._leader_n_idx_to_html_table(self.competitor, (misses[idx][0], misses[idx][1],0,0)))
					f.write('<br>')

				unr_idx-=1
				max_tup_after_unreacted[gas] = ((unique2[unr_idx], counts2[unr_idx]))
				unreacted_conf = max_tup_after_unreacted[gas][1]*(float(max_tup_after_unreacted[gas][1])/self.counts['miss'])

			comb_cnt = max_tup_after_own[gas][1]+max_tup_after_unreacted[gas][1]
			comb_conf = comb_cnt*(comb_cnt/(self.counts['match']+self.counts['miss']))

			if(comb_conf>=0.5):
				if(max_tup_after_own[gas][0]==max_tup_after_unreacted[gas][0]):
					self.max_p_dist = max_tup_after_own[gas][0]
					consistent = True
					self.conf = comb_conf
				
				else:
					consistent = False
					self.conf = comb_conf

				split_further = True
		f.write(html_end())

		return

	def _plot_match_miss_dif_hists(self):

		def autolabel(rects, ax):
			# attach some text labels
			for rect in rects:
				height = rect.get_height()
				ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
						'%d' % int(height),
						ha='center', va='bottom')
		
		fig = plt.figure()
		station_str = station_to_string(self.owner)
		fig.suptitle(self.rule_str)

		for gas in range(0,3):
			unique, counts = np.unique(self.match_difs[:,2,gas], return_counts=True)
			ax = fig.add_subplot(2,3,gas+1)
			## necessary variables
			width = 0.35
			ind = np.arange(len(unique))
			## the bars
			rects1 = ax.bar(ind, counts[:], width, color='red')

			# axes and labels
			ax.set_xlim(-width,len(unique)+width)
			# ax.set_ylim(0,45)
			ax.set_ylabel('counts')
			ax.set_xlabel('dif',ha='right')
			ax.set_title(GAS[gas] + ' reset')

			ax.set_xticks(ind + width/2)
			xtickNames = ax.set_xticklabels(unique)
			plt.setp(xtickNames, rotation=60, fontsize=8)
			# plt.gcf().subplots_adjust(bottom=0.15)
			autolabel(rects1,ax)

			unique2, counts2 = np.unique(self.miss_difs[:,gas], return_counts=True)
			ax2 = fig.add_subplot(2,3,3+gas+1)
			## the bars
			ind = np.arange(len(unique2))
			rects2 = ax2.bar(ind, counts2[:], width, color='green')

			# axes and labels
			ax2.set_xlim(-width,len(unique2)+width)
			# ax.set_ylim(0,45)
			ax2.set_ylabel('counts')
			ax2.set_xlabel('dif',ha='right')
			ax2.set_title(GAS[gas] + ' unreacted')

			ax2.set_xticks(ind + width/2)
			xtickNames = ax2.set_xticklabels(unique2)
			plt.setp(xtickNames, rotation=60, fontsize=8)
			# plt.gcf().subplots_adjust(bottom=0.15)
			autolabel(rects2,ax2)

		## add a legend
		# ax.legend((rects1[0], ), ('pricings month hist', ))
		# plt.show()
		fig.tight_layout()


		filedir = join(self.analysis_path, station_to_string(self.competitor, False).replace(" ", "_"))
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, "rule_dif_hists")
		if(not(isdir(filedir))): os.makedirs(filedir)
		file_name = self.rule_str
		fig.savefig(join(filedir,file_name))
		plt.close(fig)

		return

######### Pricing related helping-functions ##########

def get_station_dict():
    ''' Get the station data from the postgres database pointed to by the CURSORsor
    and create a dictionary of ID -> Station for each station.

    @param  CURSOR: The postgres CURSORsor on the gas station data
    @type   CURSOR: C{psycopg2.CURSORsor}

    @return	The dictionary containing all gas stations indexed by their id
    @rtype	C{dict}
    '''
    STATION_DICT = {}
    CURSOR.execute('SELECT * from gas_station')
    station_data = CURSOR.fetchall()
    for i in range(0,len(station_data)):
    	STATION_DICT.update({station_data[i][0] : Station(station_data[i])})
    return STATION_DICT

def pricing_to_string(pricing):
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

	tst = get_timestamp(pricing[pa2i['date']],pricing[pa2i['time']])
	date = tst.date()
	time = tst.time()
	# date = INIT_DATE+timedelta(r[pa2i['date']])
	# time = get_timestamp_from_sec(r[pa2i['time']])

	row = "%s | %s | %s | %s | %s | %s" % (str(date).center(10),
		str(time).center(10),
		(("%" + str(6) + "d") % pricing[pa2i['alt']]),
        d_str,
        e5_str,
        e10_str)

	return row

def station_to_string(station_id, format=True):
	station = STATION_DICT[station_id]
	st_addr = station.address['street'] + " " + station.address['house_number'] + \
	" " + station.address['post_code'] + " " + station.address['place']

	name = station.brand
	if(len(name)==0):
		name = station.name

	if(format):
		row = "%s | %s | %s" % (name.center(20),
	        station.id.center(36),
	        st_addr.center(60))
	else:
		row = name + " " + st_addr
	return row

def get_station_header():
	return "%s | %s | %s" % ("BRAND".center(20),
        "ID".center(36),
        "ADDRESS".center(60))

def get_timestamp(days, secs):
	c_date = get_date(days)
	c_time = get_time(secs)
	return datetime.combine(c_date,c_time)

def get_date(days):

	return (INIT_DATE + timedelta(days=days))

def get_time(secs, tz=True):
	m, s = divmod(secs, 60)
	h, m = divmod(m, 60)
	if(tz):
		berlin = pytz.timezone('Etc/GMT-2')
		c_time = time(int(h),int(m),int(s),0,berlin)
	else:
		c_time = time(int(h),int(m),int(s),0)
	return c_time

def set_global_d_int(from_date, to_date):
	global INIT_DATE
	global END_DATE
	INIT_DATE = from_date
	END_DATE = to_date

def get_price_dif(p1,p2):
	d_dif = int(p1[pa2i['diesel']] - p2[pa2i['diesel']])
	e5_dif = int(p1[pa2i['e5']] - p2[pa2i['e5']])
	e10_dif = int(p1[pa2i['e10']] - p2[pa2i['e10']])
	return d_dif, e5_dif, e10_dif

def get_time_dif(p1,p2):
	p1_s = p1[pa2i['time']]
	p1_d = p1[pa2i['date']]
	p2_s = p2[pa2i['time']]
	p2_d = p2[pa2i['date']]
	return SECS_PER_DAY*(p1_d-p2_d)+(p1_s-p2_s)

def is_raise(p):
	if(p[pa2i['d_diesel']]>0 or p[pa2i['d_e5']]>0 or p[pa2i['d_e10']]>0):
		return True
	else:
		return False

def proper_drop_dif(l_p, f_p):
	if(not(is_raise(l_p))):
		return (l_p[pa2i['d_diesel']]<=f_p[pa2i['d_diesel']] and l_p[pa2i['d_e5']]<=f_p[pa2i['d_e5']] and l_p[pa2i['d_e10']]<=f_p[pa2i['d_e10']])
	else:
		return True



######### Pricing related plotting-functions ##########

def plot_pricing_hour_hist(d=None, from_date=None, to_date=None):
	"""Get all price adaptions in the selected interval und and count 
	the ocCURSORances for each hour.
	"""
	tup = ()
	time_str = " WHERE "
	if(d!=None):
		time_str += (day[d])
	else:
		print('Please specify day')
		sys.exit(1)
	if(from_date!=None):
		time_str += (" AND date::date>=%s")
		tup += (from_date, )
	if(to_date!=None):
		time_str += (" AND date::date<=%s")
		tup += (to_date, )
	
	pricing_hist = np.zeros((24, ))
	CURSOR.execute("SELECT COUNT(date_part('hour',date)) FROM gas_station_information_history" +
		time_str + " GROUP BY date_part('hour',date) ORDER BY date_part('hour',date)", tup)
	for i in range(0,24):
		pricing_hist[i] = CURSOR.fetchone()[0];

	fig = plt.figure()
	ax = fig.add_subplot(111)

	## necessary variables
	ind = np.arange(24)
	width = 0.35

	## the bars
	rects1 = ax.bar(ind, pricing_hist, width, color='red')

	# axes and labels
	ax.set_xlim(-width,len(ind)+width)
	# ax.set_ylim(0,45)
	ax.set_ylabel('changes')
	ax.set_xlabel('hour')
	ax.set_title('changes per hour of day')
	xTickMarks = [i for i in range(0,24)]
	ax.set_xticks(ind + width/2)
	xtickNames = ax.set_xticklabels(xTickMarks)
	plt.setp(xtickNames, rotation=0, fontsize=10)

	## add a legend
	ax.legend((rects1[0], ), ('changes per hour of day', ))
	filedir = join(ANALYSIS_PATH, 'all_' + d)
	fig.savefig(filedir)
	# plt.show()

def plot_pricing_month_hist():
	
	CURSOR.execute("SELECT COUNT(date_trunc('month',date))" +
		" FROM gas_station_information_history" +
		" GROUP BY date_trunc('month',date) ORDER BY date_trunc('month',date)")
	cnt = CURSOR.rowcount
	counts = np.zeros((cnt,))
	for i in range(0,len(counts)):
		counts[i] = CURSOR.fetchone()[0]
	fig = plt.figure()
	ax = fig.add_subplot(111)

	## necessary variables
	ind = np.arange(len(counts))
	width = 0.35

	## the bars
	rects1 = ax.bar(ind, counts, width, color='red')

	# axes and labels
	ax.set_xlim(-width,len(ind)+width)
	# ax.set_ylim(0,45)
	ax.set_ylabel('pricings')
	ax.set_xlabel('month')
	ax.set_title('pricings month hist')
	xTickMarks = []
	for i in range(0,len(counts)):
		m = ((5+i)%12)+1
		y = 14+(5+i)/12
		mstr = '%d. %d' % (m, y)
		xTickMarks.append(mstr)
	ax.set_xticks(ind + width/2)
	xtickNames = ax.set_xticklabels(xTickMarks)
	plt.setp(xtickNames, rotation=60, fontsize=8)
	plt.gcf().subplots_adjust(bottom=0.15)

	## add a legend
	ax.legend((rects1[0], ), ('pricings month hist', ))
	fig.savefig(join(ANALYSIS_PATH, ("month_hist_all")))



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
	formated_text = ''
	for format in formats:
		formated_text += bcolors[format]
	formated_text += text + bcolors["ENDC"]
	return formated_text

def replace_Umlaute(r_str):
	r_str = r_str.replace('ä', 'ae')
	r_str = r_str.replace('ö', 'oe')
	r_str = r_str.replace('ü', 'ue')
	r_str = r_str.replace('Ä', 'AE')
	r_str = r_str.replace('Ö', 'OE')
	r_str = r_str.replace('Ü', 'UE')
	r_str = r_str.replace('ß', 'ss')
	return r_str

def pause():
	raw_input("Press Enter to continue...")
	return

def get_colors(color_num):
    colors=[]
    for i in np.arange(0., 360., 360. / color_num):
        hue = i/360.
        lightness = (50 + np.random.rand() * 10)/100.
        saturation = (90 + np.random.rand() * 10)/100.
        colors.append(colorsys.hls_to_rgb(hue, lightness, saturation))
    return colors

def html_intro(page_title):
	return "<!DOCTYPE html>\n<html>\n<head>\n<title>%s</title>\n</head>\n<body>" %(page_title)

def html_end():
	return "</body>\n</html>"

def html_heading(num, heading):
	return "<h%d>%s</h%d>"% (num,heading,num)


if __name__ == "__main__":
	con = None
	geolocator = Nominatim()
	plz_nordhorn = '48529'
	plz_osnabrueck = '49078'

	berlin = pytz.timezone('Etc/GMT-2')

	from_date = datetime(2016,1,1).date()
	to_date = datetime(2016,4,10).date()

	ana_day = datetime(2016,2,24).date()
	# set_global_d_int(from_date, to_date)
	try:
		con = psycopg2.connect(database='pricing', user='kai', password='Sakral8!')
		CURSOR = con.cursor()
		STATION_DICT = get_station_dict()
		# plot_pricing_month_hist(CURSOR)

		CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(plz_osnabrueck,"Q1"))
		gas_station_id = CURSOR.fetchall()[0][0]
		station = STATION_DICT[gas_station_id]

		# station.get_neighbors()
		# station.print_neighbors()


		# station.day_analysis(ana_day)
		# pause()

		station.get_competition(d_int=(from_date,to_date),lead_t=2700,split_criteria=['all','we','dow'])

		# station.check_Granger_Causality()


	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()