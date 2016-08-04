# -*- coding: utf-8 -*-
import os, sys, traceback, copy
from os.path import join, realpath, dirname, isdir

MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
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


STATION_DICT = None
CURSOR = None
SECS_PER_DAY = 86400
GAS = ['diesel', 'e5', 'e10']

INIT_DATE = datetime(2014,6,8).date()
END_DATE = datetime(2016,4,17).date()

PG_STDI = "stid=%s"
# Change to from and to dates
PG_D_INT = "date::date>=%s AND date::date<=%s"
PG_MONTH = "EXTRACT(MONTH FROM date) = %s"
PG_YEAR = "EXTRACT(MONTH FROM date) = %s"

day = {
	# weekday
	'wd' : "EXTRACT(ISODOW FROM date) < 6",
	# saturday
	'sat' : "EXTRACT(ISODOW FROM date) = 6",
	# sunday
	'sun' : "EXTRACT(ISODOW FROM date) = 7"
}

d_time = {
	# morning reset
	'5to10' : "EXTRACT(HOUR FROM date) >= 5 AND EXTRACT(HOUR FROM date) <= 10",
	# midday raise
	'11to14' : "EXTRACT(HOUR FROM date) >= 11 AND EXTRACT(HOUR FROM date) <= 14",
	# afternoon + evening drop
	'15to21' : "EXTRACT(HOUR FROM date) >= 15 AND EXTRACT(HOUR FROM date) <= 21",
	# night reset
	'22to4' : "(data::time::hour >= 22 OR data::time::hour <=4"
}

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
	'pref'	: 12
}

class Station(object):
	__slots__ = ('id', 'version', 'version_time', 'name', 'brand', 'address',
		'geo_pos', 'neighbors', 'pricing_mat', 'leader', 'follower')

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
		self.leader = None
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
	
	######### Main Functions ##########
	def get_pricing(self, from_date=None, to_date=None):

		# get default values if no date interval specifiec
		if(from_date==None): from_date = INIT_DATE
		if(to_date==None): to_date = END_DATE

		# get the previous pricing if interval starts after initial recording
		prev_price = None
		if(from_date>INIT_DATE):
			first_val_date = from_date - timedelta(1)
			CURSOR.execute("SELECT * FROM gas_station_information_history"+
				" WHERE " + PG_STDI + " AND " + PG_D_INT + " ORDER BY date DESC", (self.id, first_val_date, first_val_date))
			prev_price = CURSOR.fetchone()

		# get all pricings for the station in the interval
		CURSOR.execute("SELECT * FROM gas_station_information_history"+
			" WHERE " + PG_STDI + " AND " + PG_D_INT + " ORDER BY date", (self.id, from_date, to_date))

		# assign space for the pricing data
		cnt = CURSOR.rowcount
		self.pricing_mat = np.zeros((cnt,len(pa2i)))

		# if the interval starts at the initial value take the first as previous pricing
		if prev_price is None:
			prev_price = CURSOR.fetchone()
			cnt -= 1

		# get all pricings
		for i in range(0,cnt):
			fol_price=CURSOR.fetchone()

			self.pricing_mat[i,pa2i['id']] = fol_price[0]
			c_date = fol_price[5].date()
			self.pricing_mat[i,pa2i['date']] = (c_date - INIT_DATE).days
			c_time = fol_price[5].time()
			self.pricing_mat[i,pa2i['dow']] = fol_price[5].weekday()
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

			prev_price = fol_price

		# get the medians for outlier detection
		md_diesel = np.median(self.pricing_mat[:,pa2i['diesel']])
		md_e5 = np.median(self.pricing_mat[:,pa2i['e5']])
		md_e10 = np.median(self.pricing_mat[:,pa2i['e10']])

		# make sure the first index has a appropriate value
		if(np.abs(self.pricing_mat[0,pa2i['diesel']]-md_diesel)>0.3*md_diesel):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['diesel']]-md_diesel)>0.3*md_diesel):
				idx += 1
			self.pricing_mat[0,pa2i['diesel']] = self.pricing_mat[idx,[pa2i['diesel']]]

		if(np.abs(self.pricing_mat[0,pa2i['e5']]-md_e5)>0.3*md_e5):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['e5']]-md_e5)>0.3*md_e5):
				idx += 1
			self.pricing_mat[0,pa2i['e5']] = self.pricing_mat[idx,[pa2i['e5']]]

		if(np.abs(self.pricing_mat[0,pa2i['e10']]-md_e10)>0.3*md_e10):
			idx = 1
			while(np.abs(self.pricing_mat[idx,pa2i['e10']]-md_e10)>0.3*md_e10):
				idx += 1
			self.pricing_mat[0,pa2i['e10']] = self.pricing_mat[idx,[pa2i['e10']]]

		# make sure every following index has an appropriate value
		for i in range(1,len(self.pricing_mat)):
			pricing = self.pricing_mat[i,:]
			if(np.abs(pricing[pa2i['diesel']]-md_diesel)>0.3*md_diesel):
				pricing[pa2i['diesel']] = self.pricing_mat[i-1,[pa2i['diesel']]]
			if(np.abs(pricing[pa2i['e5']]-md_e5)>0.3*md_e5):
				pricing[pa2i['e5']] = self.pricing_mat[i-1,[pa2i['e5']]]
			if(np.abs(pricing[pa2i['e10']]-md_e10)>0.3*md_e10):
				pricing[pa2i['e10']] = self.pricing_mat[i-1,[pa2i['e10']]]


	def get_raise_idc(self):
		if self.pricing_mat is None: self.get_pricing()
		raise_idc = []
		for i in range(0,len(self.pricing_mat)):
			pricing = self.pricing_mat[i,:]
			if(is_raise(pricing)):
				raise_idc.append(i)
		return raise_idc

	def get_neighbors(self, init_range=5, min=2, max=20):
		""" Compute alle distances and take those located in a certain range
		or an certain amont of the closest ones if there are too many around.
		"""
		self.neighbors = []
		lat1 = radians(self.geo_pos['lat'])
		lng1 = radians(self.geo_pos['lng'])
		R = 6371000

		for station in STATION_DICT.values():
			lat2 = radians(station.geo_pos['lat'])
			lng2 = radians(station.geo_pos['lng'])
			# earth radisu in meter
			dlng = lng2 - lng1
			dlat = lat2 - lat1
			a = (sin(dlat/2))**2 + cos(lat1) * cos(lat2) * (sin(dlng/2))**2
			c = 2 * atan2( sqrt(a), sqrt(1-a) )
			d = R * c
			d_in_km = float(d)/1000
			if(d_in_km<init_range):
				self.neighbors.append((station.id, d_in_km))

		self.neighbors = sorted(self.neighbors, key=operator.itemgetter(1))
		del self.neighbors[0]
		if(len(self.neighbors)>max):
			self.neighbors = self.neighbors[0:max]
		if(len(self.neighbors)<min):
			self.get_neighbors(init_range+1, min, max)

	def get_neighbor_related_pricings(self, t_int=3600, day=None):

		# """ Go through all own price adjustments (raises only) and count for each of the
		# surrounding stations the number of adjustments that occur in a time
		# window around the own adjustments (include average reaction time).
		# """

		# store follower and leader indexes as tupels (own index, neigh index)
		# a timestamp is a folloer if it is not more than t_int seconds after the own one
		self.follower = {}
		# a timestamp is a leader if it is not more than t_int seconds before the own one
		self.leader = {}

		# get neighbors if necessary
		if self.neighbors is None: self.get_neighbors()
		# for each neighbor get pricing and make space for f and l
		for (neigh_id, dist) in self.neighbors:
			neigh = STATION_DICT[neigh_id]
			if neigh.pricing_mat is None: neigh.get_pricing(day, day)
			# print("Got pricing of neigh: %s" % STATION_DICT[neigh[0]].name)
			self.follower[neigh_id] = []
			self.leader[neigh_id] = []

		num_neigh = len(self.neighbors)
		# store the index for each neighbor
		neigh_pricing_idc = np.zeros((num_neigh, ))
		dif_mat = np.zeros((len(self.pricing_mat),num_neigh,3))

		pot_leader = []
		pot_follower = []
		# go through all own pricings
		for i in range(0,len(self.pricing_mat)):
			# raises are done of ones own accord and are treated differently
			# print(str(get_timestamp(self.pricing_mat[i,pa2i['date']], self.pricing_mat[i,pa2i['time']])) + "\t%d" % (self.pricing_mat[i,pa2i['alt']]))
			if(not(is_raise(self.pricing_mat[i,:]))):
				#get own day and time val
				own_d = self.pricing_mat[i,pa2i['date']]
				own_s = self.pricing_mat[i,pa2i['time']]
				pot_leader_row = []
				pot_follower_row = []
				# go through all neighbors
				for j in range(0,num_neigh):
					# get neighbor object and index
					fl = True

					neigh_id = self.neighbors[j][0]
					neigh = STATION_DICT[neigh_id]
					index = int(neigh_pricing_idc[j])
					dif = 0
					# go up through neighbor pricings until it time dif is bigger than +60 min
					while(dif<t_int and index+1<len(neigh.pricing_mat)):
						# get neighbor day and time val
						neigh_d = neigh.pricing_mat[index,pa2i['date']]
						neigh_s = neigh.pricing_mat[index,pa2i['time']]
						# compute dif and increase index
						dif = SECS_PER_DAY*(neigh_d-own_d)+(neigh_s-own_s)
						index+=1
					# go down to the last in index in the below 60 min range might be even below 60
					index = index-1
					# set this as new index for following iterations
					neigh_pricing_idc[j] = index
					# go down from this index and add relevant pricings as f por l until we break lower bound
					while(dif>-t_int and index>=0):
						# get neighbor day and time val and compute dif
						neigh_d = neigh.pricing_mat[index,pa2i['date']]
						neigh_s = neigh.pricing_mat[index,pa2i['time']]
						dif = SECS_PER_DAY*(neigh_d-own_d)+(neigh_s-own_s)
						# if it is in the scope -60 to +60
						if(dif>-t_int and dif<t_int):
							# and positive its a follower
							if(dif>0):
								pot_follower_row.append((neigh_id, index))
								self.follower[neigh_id].append((i,index))
							# otherwise a leader
							else:
								if(fl):
									dif_mat[i,j,:] = get_price_dif(self.pricing_mat[i,:],neigh.pricing_mat[index,:])
									fl = False
								pot_leader_row.append((neigh_id, index, dif))
								self.leader[neigh_id].append((i,index))
							# same time dont know yet
						index-=1
					if(fl):
						dif_mat[i,j,:] = 30

				"""
				TODO:
				
				Erase all pricings where there are two of one neighbor and its obvious which one was followed
				
				"""
				pot_leader.append(pot_leader_row)
				pot_follower.append(pot_follower_row)

			else:
				"""
				TODO

				Analyse raise data

				"""
				dif_mat[i,:,:] = 20
		if not(day is None):
			self.print_first_leader_analysis(pot_leader, day)
		# self.plot_dif_hist(dif_mat)

	def get_competition(self, lead_t=3600, split_criteria=['tod','we'], d_int=None):
		# get all stations if not done
		if STATION_DICT is None: STATION_DICT = get_station_dict()
		# get all neighbors if not done
		if self.neighbors is None: self.get_neighbors()
		# get all leading data if not done
		if self.leader is None: self.get_neighbor_related_pricings(lead_t)

		# print progress documentation
		print(print_bcolors(["OKBLUE","BOLD"],'Evaluating competition'.center(120)))
		# go through neighbors
		for i in range(0,len(self.neighbors)):

			neigh_id = self.neighbors[i][0]
			neigh = STATION_DICT[neigh_id]
			print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n\n"+station_to_string(neigh_id)+"\n"))

			num_neigh_p = len(neigh.pricing_mat)
			neigh_data_idc = range(0,num_neigh_p)
			raise_idc = neigh.get_raise_idc()
			post_raise_idc = raise_idc + 1
			if(post_raise_idc[-1] > num_neigh_p): post_raise_idc.pop()

			print("num neigh pricings: %d" % len(neigh.pricing_mat))
			print("num neigh raise_idc: %d" % len(raise_idc))
			rel_idc = [x for x in neigh_data_idc if x not in raise_idc]

			follower_idc = [x[1] for x in self.follower[neigh_id]]
			print("num neigh following idc: %d" % len(follower_idc))
			print("num neigh leading idc: %d" % len(self.leader[neigh_id]))
			rel_idc = [x for x in rel_idc if x not in follower_idc]

			# self.filter_follower_and_leader(neigh_id)
			# self.explore_follower()
			self.explore_statistics_tree(rel_idc, neigh_id, split_criteria)
			pause()

	def filter_follower_and_leader(self, neigh_id):
		neigh = STATION_DICT[neigh_id]
		l_idx = 0
		f_idx = 0
		leader = self.leader[neigh_id]
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

	def get_concrete_rule(self):
		"""TODO"""
		pass

	def split_at(self, data_idc, station_id, split_criterium):


		'''
		CAN BE IMPROVED DICTS RATHER THAN LISTS AND JUST ITERATING ONCE OVER 
		ALL INDICES !!!!
		'''


		data = STATION_DICT[station_id].pricing_mat
		data_split = [data[i] for i in data_idc]
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
				dow_set = set(data_split[:,pa2i['dow']])
				splits = []
				labels = []
				for dow in dow_set:
					labels.append('dow ' + dow)
					splits.append([idx for idx in data_idc if data[idx][pa2i['dow']]==dow])
				return splits, dow_set

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
				hour_set = set(map(int, data[:,pa2i['time']]/3600))
				splits = []
				labels = []
				for hour in hour_set:
					labels.append('hour ' + hour)
					splits.append([idx for idx in data_idc if int(data[idx][pa2i['time']]/3600)==hour])
				return splits, labels
			else:
				raise ValueError("Wrong split criterium")

		except ValueError:
			traceback.print_exc()
			print("You used %s as split criterium. Please use we, dow, tod or hour only!" % split_criterium)
			sys.exit(1)

	def explore_statistics_tree(self, data_idc, neigh_id , split_criteria, node_label='all'):

		textwidth = 80

		leader = self.leader[neigh_id] #(own_idx, leader_idx)
		matches = self.get_matching_leader_subset(data_idc, leader)
		match_cnt = len(matches)
		data_cnt = len(data_idc)
		# if(node_label=="all"):
		# 	if(float(match_cnt)/data_cnt<0.6):
		# 		print(print_bcolors(["WARNING"], 'Probably not a leader:'))
		# 		print(print_bcolors(["WARNING"], 'contains %d pricings with %d leader matches, making only %.3f' % (data_cnt, match_cnt, float(match_cnt)/data_cnt)))
		# 		return
		# 	else:
		# 		print(print_bcolors(["OKGREEN"], 'Might be a leader:'))
		# 		print(print_bcolors(["OKGREEN"], 'contains %d pricings with %d leader matches, making about %.3f' % (data_cnt, match_cnt, float(match_cnt)/data_cnt)))
		# 		return

		if(len(matches)>0):
			mean_r_time, std_r_time = self.get_mean_and_dev_r_time(matches, neigh_id) 
			all_r, prop_r, modes, counts = self.get_price_dif_stats(matches, neigh_id)
			# follower_stats = self.get_follower_stats(data, neigh_id)

			# append statsplot to tree using ETE?
			# plot histogram
			print(print_bcolors(["OKGREEN","BOLD"], "\n" + node_label.center(textwidth)))
			self.print_leader_stats(node_label, len(data_idc), len(matches), mean_r_time, std_r_time, all_r, prop_r, modes, counts)

		else:
			print(print_bcolors(["OKGREEN","BOLD"], "\n" + node_label.center(textwidth)))
			print(print_bcolors(["WARNING"], 'no matches in this intervall!!!'))
		# self.print_follower_stats(follower_stats)
		if(len(split_criteria)>0):

			c_copy = split_criteria[:]
			crit = c_copy.pop()

			print(print_bcolors(["BOLD","UNDERLINE"], '\n' + ('Splitting at: ' + crit).center(textwidth)))
			data_splits, labels = self.split_at(data_idc, neigh_id, crit)
			for i in range(0,len(data_splits)):
				self.explore_statistics_tree(data_splits[i], neigh_id, c_copy[:], node_label=labels[i])

	def get_mean_and_dev_r_time(self, leader, neigh_id):
		neigh = STATION_DICT[neigh_id]
		time_dif = np.zeros((len(leader), ))
		for i in range(0,len(leader)):
			o = leader[i][0]
			l = leader[i][1]
			own_d = self.pricing_mat[o,pa2i['date']]
			own_s = self.pricing_mat[o,pa2i['time']]
			neigh_d = neigh.pricing_mat[l,pa2i['date']]
			neigh_s = neigh.pricing_mat[l,pa2i['time']]
			time_dif[i] = SECS_PER_HOUR*(neigh_d-own_d)+(neigh_s-own_s)
			
		try:
			m = np.mean(time_dif)
			s = np.std(time_dif)
		
		except:
			print(len(time_dif))
			# sys.exit(1)

		return m, s

	def get_price_dif_stats(self, leader, neigh_id):
		neigh = STATION_DICT[neigh_id]
		price_dif = np.zeros((len(leader), 9))

		d_cnt = 0
		e10_cnt = 0
		e5_cnt = 0
		all_cnt = 0
		prop_cnt = 0
		all_true = True

		for i in range(0,len(leader)):

			o = leader[i][0]
			l = leader[i][1]
			o_alt = self.pricing_mat[o,pa2i['alt']]
			l_alt = neigh.pricing_mat[l,pa2i['alt']]

			reset_val = 0
			all_true = True

			price_dif[i,0] = self.pricing_mat[o-1,pa2i['diesel']] - neigh.pricing_mat[l-1,pa2i['diesel']]
			price_dif[i,1] = self.pricing_mat[o-1,pa2i['diesel']] - neigh.pricing_mat[l,pa2i['diesel']]
			price_dif[i,2] = self.pricing_mat[o,pa2i['diesel']] - neigh.pricing_mat[l,pa2i['diesel']]
			if(price_dif[i,0]!=price_dif[i,1] and price_dif[i,0]==price_dif[i,2]):
				reset_val += 1
				d_cnt+=1
			else: all_true= False

			price_dif[i,3] = self.pricing_mat[o-1,pa2i['e5']] - neigh.pricing_mat[l-1,pa2i['e5']]
			price_dif[i,4] = self.pricing_mat[o-1,pa2i['e5']] - neigh.pricing_mat[l,pa2i['e5']]
			price_dif[i,5] = self.pricing_mat[o,pa2i['e5']] - neigh.pricing_mat[l,pa2i['e5']]
			if(price_dif[i,3]!=price_dif[i,4] and price_dif[i,3]==price_dif[i,5]):
				reset_val += 4
				e5_cnt+=1
			else: all_true= False

			price_dif[i,6] = self.pricing_mat[o-1,pa2i['e10']] - neigh.pricing_mat[l-1,pa2i['e10']]
			price_dif[i,7] = self.pricing_mat[o-1,pa2i['e10']] - neigh.pricing_mat[l,pa2i['e10']]
			price_dif[i,8] = self.pricing_mat[o,pa2i['e10']] - neigh.pricing_mat[l,pa2i['e10']]
			if(price_dif[i,6]!=price_dif[i,7] and price_dif[i,6]==price_dif[i,8]):
				reset_val += 16
				e10_cnt+=1
			else: all_true= False

			if(all_true):
				all_cnt+=1
			elif(not(all_true) and o_alt==reset_val):
				prop_cnt += 1

		m = stats.mode(price_dif)

		return all_cnt, prop_cnt, m[0][0], m[1][0]
		
	def get_matching_leader_subset(self, data_idc_sub, leader):
		matches = []
		d_idx = 0
		l_idx = 0 
		while(d_idx < len(data_idc_sub) and l_idx < len(leader)):
			if(data_idc_sub[d_idx] == leader[l_idx][1]):
				matches.append(leader[l_idx])
				d_idx += 1
				l_idx += 1
			elif(data_idc_sub[d_idx] < leader[l_idx][1]):
				d_idx += 1
			else:
				l_idx += 1
		return matches

	
	
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

	def plot_dif_hist(self, dif_mat):

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
			filedir = join(ANALYSIS_PATH, self.name)
			if(not(isdir(filedir))): os.makedirs(filedir)
			filedir = join(filedir, "neigh_diff_hist")
			if(not(isdir(filedir))): os.makedirs(filedir)
			file_name = station_to_string(self.neighbors[n][0], False).replace(" ", "_")
			file_name = file_name.replace(".", "-")
			fig.savefig(join(filedir,file_name))

	def print_first_leader_analysis(self, leader_mat, day):
		real_contenders =  ['8a5b2591-8821-4a36-9c82-4828c61cba29', 'ebc673e0-8359-4ab6-0afa-c31cc35c4bd2',
		'30d8de2f-7728-4328-929f-b45ff1659901', '51d4b54f-a095-1aa0-e100-80009459e03a', '51d4b5a3-a095-1aa0-e100-80009459e03a',
		'f4b31676-e65e-4b60-8851-609c107f5d93']

		filedir = join(ANALYSIS_PATH, 'Q1 Tankstelle')
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, "day_timeline")
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, str(day))
		if(not(isdir(filedir))): os.makedirs(filedir)
		HTMLFILE = 'pricings.html'
		f = open(join(filedir,HTMLFILE), 'w')

		for i in range(0,len(leader_mat)):
			row = leader_mat[i]
			f.write(html_heading(1,pricing_to_string(self.pricing_mat[i])))
			t = HTML.Table(header_row=['t-dif', GAS[0], GAS[1], GAS[2], 'station'])
			for (neigh_id,index, dif) in row:
				neigh = STATION_DICT[neigh_id]
				d_dif_pre, e5_dif_pre, e10_dif_pre = get_price_dif(self.pricing_mat[i-1,:],neigh.pricing_mat[index-1,:])
				d_dif_bet, e5_dif_bet, e10_dif_bet = get_price_dif(self.pricing_mat[i-1,:],neigh.pricing_mat[index,:])
				d_dif_post, e5_dif_post, e10_dif_post = get_price_dif(self.pricing_mat[i,:],neigh.pricing_mat[index,:])

				station_str = station_to_string(neigh_id, False)
				time_dif = "%2d"%(int(dif/60))
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

	def plot_day_timeline(self, day):

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

		filedir = join(ANALYSIS_PATH, 'Q1 Tankstelle')
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, "day_timeline")
		if(not(isdir(filedir))): os.makedirs(filedir)
		filedir = join(filedir, str(day))
		if(not(isdir(filedir))): os.makedirs(filedir)

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
			plt.savefig(join(filedir,file_name), bbox_extra_artists=(lgd,), bbox_inches='tight')

	#	plt.show()

	def print_follower_and_leader(self):
		self.get_neighbor_related_pricings(3600)

		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)

		print(len(self.pricing_mat))

		for i in range(0,len(self.leader)):
			neigh_id = self.neighbors[i][0]

			neigh = STATION_DICT[neigh_id]
			# i_str = 'Neighboring station:'
			# print(i_str.center(40))
			s_str = '%s %s' %(neigh.name, neigh.id)
			print(s_str.center(40))
			a_str = '%s %s %s %s' %(neigh.address['street'], neigh.address['house_number'],
					neigh.address['post_code'], neigh.address['place'])
			print(a_str.center(40))

			self.print_leader(self.leader[neigh_id], neigh)
			self.print_follower(self.follower[neigh_id], neigh)

	def print_leader(self, leader, neigh):

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

	def print_follower(self, follower, neigh):

		d_cnt = 0
		e10_cnt = 0
		e5_cnt = 0
		all_cnt = 0
		all_true = True

		# f = open(join(filedir, "drop_history_" + days + ".txt"),'w+')

		for (own_idx,neigh_idx) in follower:
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

		print("| %5d | %5d | %5d | %5d | %5d |" % (len(follower),
			all_cnt, d_cnt, e10_cnt, e5_cnt))
		print("")

	def print_leader_stats(self, node_label, data_sub_cnt, match_cnt, mean_r_time, std_r_time, all_res, prop_res, modes, counts):

		if(data_sub_cnt==0 or match_cnt==0):
			print('no matches in thís intervall!!!')
		else:
			print('contains %d pricings with %d leader matches, making %f' % (data_sub_cnt, match_cnt, float(match_cnt)/data_sub_cnt))
			print('reacted in an average of %f with a std of %f' % (mean_r_time, std_r_time))
			print('the own pricing resettet %d times all prices making %f' % (all_res, float(all_res)/match_cnt))
			print('the own pricing resettet %d times the appropriate prices making %f' % (prop_res, float(prop_res)/match_cnt))
			zipped = zip(modes,counts,(counts/float(match_cnt)))

			print(print_bcolors(["UNDERLINE"], "diesel".center(25) + "e5".center(25) + "e10".center(25)))
			for i in range(0,len(zipped)/3):
				row = "%2d\t%2d\t%.3f | " %(int(zipped[i][0]), zipped[i][1], zipped[i][2])
				row += "%2d\t%2d\t%.3f | " %(int(zipped[i+3][0]), zipped[i+3][1], zipped[i+3][2])
				row += "%2d\t%2d\t%.3f" %(int(zipped[i+6][0]), zipped[i+6][1], zipped[i+6][2])
				print(row)
			# print('modes: ' + str(modes))
			# print('counts: ' + str(counts))
			# print('percents: '+ str(counts/float(match_cnt)))



	######### Granger Causality ##########
	def check_Granger_Causality(self):
		if self.neighbors is None:
			self.get_neighbors()
		num_neigh = len(self.neighbors)

		own_time_series_data = self.get_time_series_data()
		len_series = len(own_time_series_data)
		granger_data = np.zeros((len_series,2))

		own_rand = np.random.random_sample((len_series,)) * 0.001
		for i in range(6,num_neigh):
			neigh_id = self.neighbors[i][0]
			print(print_bcolors(["OKBLUE","BOLD","UNDERLINE"],"\n\n"+station_to_string(neigh_id)+"\n"))
			neigh = STATION_DICT[neigh_id]
			if neigh.pricing_mat is None:
				neigh.get_pricing()
			neigh_time_series_data = neigh.get_time_series_data()
			neigh_rand = np.random.random_sample((len_series,)) * 0.001
			for j in range(0,3):
				granger_data[:,0] = own_time_series_data[:,j]
				granger_data[:,1] = neigh_time_series_data[:,j]
				res_dict = st.grangercausalitytests(granger_data, maxlag=30, addconst=True, verbose=True)
				print(res_dict[1][0])

	def get_time_series_data(self):
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



	######### Some visualisations (old)##########
	def plot_pricing_month_hist(self, from_date=None, to_date=None):

		if(from_date==None): from_date = INIT_DATE
		if(to_date==None): to_date = END_DATE

		year = from_date.year
		month = from_date.month
		to_year = to_date.year
		to_month = to_date.month

		month_hist = []
		xTickMarks = []
		while(year<=to_year and month<=to_month):
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
				" WHERE " + STDI + " AND " + PG_MONTH + " AND " + PG_YEAR % (self.id, year, month))
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

	def plot_pricing_hour_hist(self, d=None, from_date=None, to_date=None):
		""" Get all price adaptions in the selected interval und and count 
		the ocCURSORances for each hour.
		"""
		time_str = (" WHERE " + STDI)
		tup = (self.id, )
		if(d!=None): time_str += (" AND " + (day[d]))
		if(from_date!=None):
			time_str += (" AND date::date>=%s")
			tup += (from_date, )
		if(to_date!=None):
			time_str += (" AND date::date<=%s")
			tup += (to_date, )
		
		pricing_hist = np.zeros((24, ))
		for i in range(0,24):
			CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history" +
				time_str + " AND EXTRACT(HOUR FROM date)=%s", (tup+(i,)))
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

	def print_raises(self):
		textwidth = 68
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		f = open(join(filedir, "raise_history.txt"),'w+')

		print(print_bcolors(["BOLD","OKBLUE"], "Raises by station %s" % self.name))
		f.write(("Raises by station %s" % self.name).center(textwidth))
		f.write("\n")
		textwidth_reduced = textwidth - 15
		header = "%s | %s | %s | %s | %s | %s" % ("date".center(10),
                "time".center(10),
                "alt".center(6),
                "diesel".center(9),
                "e5".center(9),
                "e10".center(9))
		print(header)
		f.write(header)
		f.write("\n")
		print(("-" * textwidth))
		f.write(("-" * textwidth))
		f.write("\n")

		raise_idx = self.get_raise_idc()

		raises = self.pricing_mat[raise_idx[0],:]
		print(int(raises[0,pa2i['id']]))
		for r in raises:
			
			d_str = "%s"% r[pa2i['diesel']] + (bcolors.OKGREEN + " +%2d" + bcolors.ENDC) %r[pa2i['d_diesel']]
			e5_str = "%s"% r[pa2i['e5']] + (bcolors.OKGREEN + " +%2d" + bcolors.ENDC) %r[pa2i['d_e5']]
			e10_str = "%s"% r[pa2i['e10']] + (bcolors.OKGREEN + " +%2d" + bcolors.ENDC) %r[pa2i['d_e10']]
			f_d_str = "%s"% r[pa2i['diesel']] + (" +%2d") %r[pa2i['d_diesel']]
			f_e5_str = "%s"% r[pa2i['e5']] + (" +%2d") %r[pa2i['d_e5']]
			f_e10_str = "%s"% r[pa2i['e10']] + (" +%2d") %r[pa2i['d_e10']]
			date = INIT_DATE+timedelta(r[pa2i['date']])
			time = get_timestamp_from_sec(r[pa2i['time']])
			row = "%s | %s | %s | %s | %s | %s" % (str(date).center(10),
				str(time).center(10),
				(("%" + str(6) + "d") % r[pa2i['alt']]),
                d_str,
                e5_str,
                e10_str)
			f_row = "%s | %s | %s | %s | %s | %s\n" % (str(date).center(10),
				str(time).center(10),
				(("%" + str(6) + "d") % r[pa2i['alt']]),
                f_d_str,
                f_e5_str,
                f_e10_str)
			print(row)
			f.write(f_row)

		f.close()

	def print_drops(self, days='all'):
		textwidth = 68
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		f = open(join(filedir, "drop_history_" + days + ".txt"),'w+')

		print((bcolors.BOLD + bcolors.OKBLUE + "Drops by station %s on %s" + bcolors.ENDC) % (self.name, days))
		f.write(("Drops by station %s" % self.name).center(textwidth))
		f.write("\n")
		textwidth_reduced = textwidth - 15
		header = "%s | %s | %s | %s | %s | %s" % ("date".center(10),
                "time".center(10),
                "alt".center(6),
                "diesel".center(9),
                "e5".center(9),
                "e10".center(9))
		print(header)
		f.write(header)
		f.write("\n")
		print(("-" * textwidth))
		f.write(("-" * textwidth))
		f.write("\n")

		if(self.pricing_mat==None): self.get_pricing(CURSOR)

		ind_d = [self.pricing_mat[:,pa2i['d_diesel']]<0] 
		ind_5 = [self.pricing_mat[:,pa2i['d_e5']]<0]
		ind_10 = [self.pricing_mat[:,pa2i['d_e10']]<0]

		wd = [[((INIT_DATE+timedelta(date)).weekday())<5 for date in self.pricing_mat[:,pa2i['date']]]]
		we = [[((INIT_DATE+timedelta(date)).weekday())>=5 for date in self.pricing_mat[:,pa2i['date']]]]

		if(days=="we"):
			raise_idx = [(a|b|c)&d for (a,b,c,d) in zip(ind_d,ind_5,ind_10,we)]
		elif(days=="wd"):
			raise_idx = [(a|b|c)&d for (a,b,c,d) in zip(ind_d,ind_5,ind_10,wd)]
		else:
			raise_idx = [a|b|c for (a,b,c) in zip(ind_d,ind_5,ind_10)]


		raises = self.pricing_mat[raise_idx[0],:]
		for r in raises:
			
			d_str = "%s"% r[pa2i['diesel']] + (" %3d") %r[pa2i['d_diesel']]
			e5_str = "%s"% r[pa2i['e5']] + (" %3d") %r[pa2i['d_e5']]
			e10_str = "%s"% r[pa2i['e10']] + (" %3d") %r[pa2i['d_e10']]
			date = INIT_DATE+timedelta(r[pa2i['date']])
			time = get_timestamp_from_sec(r[pa2i['time']])
			row = "%s | %s | %s | %s | %s | %s" % (str(date).center(10),
				str(time).center(10),
				(("%" + str(6) + "d") % r[pa2i['alt']]),
                d_str,
                e5_str,
                e10_str)
			f_row = row + '\n'
			# print(row)
			f.write(f_row)

		f.close()

	def print_pricings_per_time_category(self, m=None, d=None, t=None):
		time_str = " WHERE " + STDI
		if(m!=None): time_str += (" AND " + MONTH % m)
		if(d!=None): time_str += (" AND " + day[d])
		if(t!=None): time_str += (" AND " + time[t]) 
		time_str += " ORDER BY date"

		CURSOR.execute("SELECT * FROM gas_station_information_history"+
			time_str, (self.id, ))
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



	######### Some visualisations (old)##########
	def day_analysis(self, day):
		self.get_pricing(day,day)
		self.get_neighbor_related_pricings(t_int=3600, day=day)

		# plot timeline
		self.plot_day_timeline(day)



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
	c_date = INIT_DATE + timedelta(days=days)
	m, s = divmod(secs, 60)
	h, m = divmod(m, 60)
	berlin = pytz.timezone('Etc/GMT-2')
	c_time = time(int(h),int(m),int(s),0,berlin)
	return datetime.combine(c_date,c_time)

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

def is_raise(p):
	if(p[pa2i['d_diesel']]>0 and p[pa2i['d_e5']]>0 and p[pa2i['d_e10']]>0):
		return True
	else:
		return False



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

	from_date = datetime(2016,3,5).date()
	to_date = datetime(2016,3,5).date()
	# set_global_d_int(from_date, to_date)
	try:
		con = psycopg2.connect(database='pricing', user='kai', password='Sakral8!')
		CURSOR = con.cursor()
		STATION_DICT = get_station_dict()
		# plot_pricing_month_hist(CURSOR)

		CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(plz_osnabrueck,"Q1"))
		gas_station_id = CURSOR.fetchall()[0][0]
		station = STATION_DICT[gas_station_id]


		station.day_analysis(from_date)
		
		# station.check_Granger_Causality()
		# station.print_follower_and_leader()
		# station.get_competition(lead_t=3600,split_criteria=['tod','we'],d_int=(from_date,to_date))


	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()