# -*- coding: utf-8 -*-
import os, sys
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
import matplotlib.pyplot as plt
# python 
from geopy.geocoders import Nominatim

STATION_DICT = None
CURSOR = None

INIT_DATE = datetime(2014,6,8).date()

STDI = "stid=%s"
# Change to from and to dates
D_INT = "date::date>=%s AND date::date<=%s"
MONTH = "EXTRACT(MONTH FROM date) = %s"

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

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Station(object):
	__slots__ = ('id', 'version', 'version_time', 'name', 'brand', 'address',
		'geo_pos', 'neighbors', 'pricing_mat', 'month_hist')

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
		else: self.brand = 'NA'
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
		@ivar   neighbors: The neighbors of the station
		@dtype  neighbors: C{list}
		"""
		self.pricing_mat = None
		self.month_hist = None

	def plot_pricing_month_hist(self):
		if(self.month_hist == None): self.get_pricing
		fig = plt.figure()
		ax = fig.add_subplot(111)

		## necessary variables
		ind = np.arange(len(self.month_hist))
		width = 0.35

		## the bars
		rects1 = ax.bar(ind, self.month_hist[:,1], width, color='red')

		# axes and labels
		ax.set_xlim(-width,len(ind)+width)
		# ax.set_ylim(0,45)
		ax.set_ylabel('pricings')
		ax.set_xlabel('month')
		ax.set_title('pricings month hist')
		xTickMarks = []
		for i in range(0,len(self.month_hist)):
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
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		fig.savefig(join(filedir, ("month_hist")))

	def plot_pricing_time_histogram(self, d=None, from_date=None, to_date=None):
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

	def get_pricing(self):

		CURSOR.execute("SELECT * FROM gas_station_information_history"+
			" WHERE " + STDI + " ORDER BY date", (self.id, ))

		cnt = CURSOR.rowcount-1
		self.pricing_mat = np.zeros((cnt,len(pa2i)))

		month_idx = np.ones((1,2))

		cur_month = INIT_DATE.month
		idx = 0

		prev_price = CURSOR.fetchone()
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
			self.pricing_mat[i,pa2i['e10']] = float(c_e5)/10

			d_dif = (c_diesel - prev_price[4])/10
			self.pricing_mat[i,pa2i['d_diesel']] = d_dif
			e5_dif = (c_e5 - prev_price[2])/10
			self.pricing_mat[i,pa2i['d_e5']] = e5_dif
			e10_dif = (c_e10 - prev_price[3])/10
			self.pricing_mat[i,pa2i['d_e10']] = e10_dif

			prev_price = fol_price

			if(c_date.month!=cur_month):
				month_idx[idx,1] = i-month_idx[idx,0]
				month_idx = np.append(month_idx,[[i,0]],axis=0)
				idx+=1
				cur_month = c_date.month

		month_idx[idx,1] = cnt-month_idx[idx,0]
		self.month_hist = month_idx

	def get_raise_idc(self):
		if(self.pricing_mat==None): self.get_pricing()
		ind_d = [self.pricing_mat[:,pa2i['d_diesel']]>0] 
		ind_5 = [self.pricing_mat[:,pa2i['d_e5']]>0]
		ind_10 = [self.pricing_mat[:,pa2i['d_e10']]>0]
		raise_idx = [a|b|c for (a,b,c) in zip(ind_d,ind_5,ind_10)]
		return raise_idx

	def print_raises(self):
		textwidth = 68
		filedir = join(ANALYSIS_PATH, self.name)
		if(not(isdir(filedir))): os.makedirs(filedir)
		f = open(join(filedir, "raise_history.txt"),'w+')

		print((bcolors.BOLD + bcolors.OKBLUE + "Raises by station %s" + bcolors.ENDC) % self.name)
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
			
			d_str = "%s"% r[pa2i['diesel']] + (bcolors.OKGREEN + " %3d" + bcolors.ENDC) %r[pa2i['d_diesel']]
			e5_str = "%s"% r[pa2i['e5']] + (bcolors.OKGREEN + " %3d" + bcolors.ENDC) %r[pa2i['d_e5']]
			e10_str = "%s"% r[pa2i['e10']] + (bcolors.OKGREEN + " %3d" + bcolors.ENDC) %r[pa2i['d_e10']]
			f_d_str = "%s"% r[pa2i['diesel']] + (" %3d") %r[pa2i['d_diesel']]
			f_e5_str = "%s"% r[pa2i['e5']] + (" %3d") %r[pa2i['d_e5']]
			f_e10_str = "%s"% r[pa2i['e10']] + (" %3d") %r[pa2i['d_e10']]
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
			# print(row)
			f.write(f_row)

		f.close()

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

	def print_neighbors(self):
		if(self.neighbors==None): self.get_neighbors(STATION_DICT)
		textwidth = 120

		print((bcolors.BOLD + bcolors.OKBLUE +
			'Selected station: %s %s at %s %s in %s %s\n'\
			%(self.name, self.id, self.address['street'], self.address['house_number'],
				self.address['post_code'], self.address['place'])).center(textwidth)+bcolors.ENDC)
		max_dist = int(self.neighbors[len(self.neighbors)-1][1])+1
		print((bcolors.BOLD + 'Gas stations in range of %dkm\n' % max_dist).center(textwidth) + bcolors.ENDC)

		header = "%s | %s | %s | %s | %s" % ("name".center(40),
                "brand".center(10),
                "id".center(36),
                "dist".center(5),
                "address".center(10))
		print(header)
		print(("-" * textwidth))

		for neighbor in self.neighbors:
			station_id = neighbor[0]
			station_dist = neighbor[1]
			station = STATION_DICT[station_id]
			st_addr = station.address['street'] + " " + station.address['house_number'] + \
			" " + station.address['post_code'] + " " + station.address['place']
			row = "%s | %s | %s | %1.3f | %s" % (station.name.center(40),
                station.brand.center(10),
                station.id,
                station_dist,
                st_addr)
			print(row)

	def print_changes_per_time_category(self, m=None, d=None, t=None):
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

	def get_follower_and_leader(self):
		""" Go through all own price adjustments and count for each of the
		surrounding stations the number of adjustments that ocCURSOR in a time
		window around the own adjustments (include average reaction time).
		"""
		print("Getting follower and leader")
		# get neighbors if necessary
		if(self.neighbors==None): self.get_neighbors()
		# store follower and leader indexes as tupels (own index, neigh index)
		# a timestamp is a folloer if it is not more than 30min after the own one
		follower = []
		# a timestamp is a leader if it is not more than 30min before the own one
		leader = []
		# for each neighbor get pricing and make space for f and l
		for neigh in self.neighbors:
			STATION_DICT[neigh[0]].get_pricing()
			print("Got pricing of neigh: %s" % STATION_DICT[neigh[0]].name)
			follower.append([])
			leader.append([])

		# store the index for each neighbor
		neigh_pricing_idc = np.zeros((len(self.neighbors), ))
		# go through all own pricings
		for i in range(0,len(self.pricing_mat)):
			#get own day and time val
			own_d = self.pricing_mat[i,pa2i['date']]
			own_s = self.pricing_mat[i,pa2i['time']]
			# go through all neighbors
			for j in range(0,len(neigh_pricing_idc)):
				# get neighbor object and index
				neigh = STATION_DICT[self.neighbors[j][0]]
				index = neigh_pricing_idc[j]
				dif = 0
				# go up through neighbor pricings until it time dif is bigger than +30 min
				while(dif<1800 and index+1<len(neigh.pricing_mat)):
					# get neighbor day and time val
					neigh_d = neigh.pricing_mat[index,pa2i['date']]
					neigh_s = neigh.pricing_mat[index,pa2i['time']]
					# compute dif and increase index
					dif = 86400*(neigh_d-own_d)+(neigh_s-own_s)
					index+=1
				# go down to the last in index in the below 30min range might be even below -30
				index = index-1
				# set this as new index for following iterations
				neigh_pricing_idc[j] = index
				# go down from this index and add relevant pricings as f por l until we break lower bound
				while(dif>-1800 and index>=0):
					# get neighbor day and time val and compute dif
					neigh_d = neigh.pricing_mat[index,pa2i['date']]
					neigh_s = neigh.pricing_mat[index,pa2i['time']]
					dif = 86400*(neigh_d-own_d)+(neigh_s-own_s)
					# if it is in the scope -30 to +30
					if(dif>-1800 and dif<1800):
						# and positive its a follower
						if(dif>0):
							follower[j].append((i,index))
						# otherwise a leader
						else:
							leader[j].append((i,index))
						# same time dont know yet
					index-=1
		return follower, leader

		# # get all own pricings
		# CURSOR.execute("SELECT * from gas_station_information_history WHERE stid=%s ORDER BY date", (self.id, ))
		# pricings = CURSOR.fetchall()

		# # dict of neighbors - each neighbor has a list of pricing tuples
		# # each tuple contains the own pricing and the related pricing of the neighbor
		# # the pricing should contain all data + day val + time val + amounts changed
		# # use the pricing matrices and save indices in list

		# related_pricings = {entry[0]:[] for entry in self.neighbors}
		# prev_price = CURSOR.fetchone()

		# for pricing in pricings:
		# 	lower_bound = pricing[0] - timedelta(minutes=30)
		# 	upper_bound = pricing[0] + timedelta(minutes=30)
		# 	for neigh in self.neighbors:
		# 		n_id = neigh[0]
		# 		CURSOR.execute("SELECT * from gas_station_information_history WHERE stid = %s" +
		# 			" AND date > TIMESTAMP %s AND date < TIMESTAMP %s", (n_id, str(lower_bound), str(upper_bound)))
		# 		time=CURSOR.fetchone()



		# 	# 	if(not(time==None)):
		# 	# 		relations[i,0] += 1
		# 	# 		c = time[0] - pricing[0]
		# 	# 		dif= (c.days * 86400 + c.seconds)
		# 	# 		if(dif>0):
		# 	# 			compare[i] = dif-1800
		# 	# 		elif(dif<0):
		# 	# 			compare[i] = dif+1800
		# 	# 		else:
		# 	# 			compare[i] = 0
		# 	# 			relations[i,13] += 1
		# 	# 	else:
		# 	# 		compare[i] = 0

		# 	# idc = sorted(range(len(compare)), key=lambda k: compare[k])
		# 	# if(compare[idc[0]]<0):
		# 	# 	relations[idc[0],int((compare[idc[0]]+1800)/300)+7] += 1
		# 	# if(compare[idc[len(compare)-1]]>0):
		# 	# 	relations[idc[len(compare)-1],int((compare[idc[len(compare)-1]]-1800)/300)+6] += 1

	def print_follower_and_leader(self):
		follower,leader = self.get_follower_and_leader()
		neigh = STATION_DICT[self.neighbors[0][0]]
		for (own_idx,neigh_idx) in leader[0]:
			d_dif_pre = self.pricing_mat[own_idx-1,pa2i['diesel']] - neigh.pricing_mat[neigh_idx-1,pa2i['diesel']]
			d_dif_post = self.pricing_mat[own_idx,pa2i['diesel']] - neigh.pricing_mat[neigh_idx,pa2i['diesel']]
			e5_dif_pre  = self.pricing_mat[own_idx-1,pa2i['e5']] - neigh.pricing_mat[neigh_idx-1,pa2i['e5']]
			e5_dif_post = self.pricing_mat[own_idx,pa2i['e5']] - neigh.pricing_mat[neigh_idx,pa2i['e5']]
			e10_dif_pre = self.pricing_mat[own_idx-1,pa2i['e10']] - neigh.pricing_mat[neigh_idx-1,pa2i['e10']]
			e10_dif_post = self.pricing_mat[own_idx,pa2i['e10']] - neigh.pricing_mat[neigh_idx,pa2i['e10']]
			own_d = self.pricing_mat[own_idx,pa2i['date']]
			own_s = self.pricing_mat[own_idx,pa2i['time']]
			neigh_d = neigh.pricing_mat[neigh_idx,pa2i['date']]
			neigh_s = neigh.pricing_mat[neigh_idx,pa2i['time']]
			own_tst = get_timestamp(own_d, own_s)
			neigh_tst = get_timestamp(neigh_d, neigh_s)
			dif = 86400*(neigh_d-own_d)+(neigh_s-own_s)
			dif_str = "%5d" % dif

			row = "%s | %s | %5d | %2d | %2d | %2d | %2d | %2d | %2d" % (str(own_tst),
				str(neigh_tst),dif, d_dif_pre, d_dif_post, e5_dif_pre, e5_dif_post,
				e10_dif_pre, e10_dif_post)
			print(row)

	def get_concrete_rule(self):
		pass 

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

def replace_Umlaute(r_str):
	r_str = r_str.replace('ä', 'ae')
	r_str = r_str.replace('ö', 'oe')
	r_str = r_str.replace('ü', 'ue')
	r_str = r_str.replace('Ä', 'AE')
	r_str = r_str.replace('Ö', 'OE')
	r_str = r_str.replace('Ü', 'UE')
	r_str = r_str.replace('ß', 'ss')
	return r_str

def plot_pricing_histogram(d=None, from_date=None, to_date=None):
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

def get_timestamp(days, secs):
	c_date = INIT_DATE + timedelta(days=days)
	m, s = divmod(secs, 60)
	h, m = divmod(m, 60)
	berlin = pytz.timezone('Etc/GMT-2')
	c_time = time(int(h),int(m),int(s),0,berlin)
	return datetime.combine(c_date,c_time)


if __name__ == "__main__":
	con = None
	geolocator = Nominatim()
	plz_nordhorn = '48529'
	plz_osnabrueck = '49078'

	berlin = pytz.timezone('Etc/GMT-2')
	from_date = datetime(2015,6,14,23,59,40,0,berlin)
	to_date = datetime(2015,6,15,0,10,15,0,berlin)

	try:
		con = psycopg2.connect(database='pricing', user='kai', password='Sakral8!')
		CURSOR = con.cursor()
		STATION_DICT = get_station_dict()
		# plot_pricing_month_hist(CURSOR)

		CURSOR.execute("SELECT id FROM gas_station WHERE post_code=%s AND brand=%s"  ,(plz_osnabrueck,"Q1"))
		gas_station_id = CURSOR.fetchall()[0][0]
		station = STATION_DICT[gas_station_id]
		station.get_pricing()
		station.get_neighbors(init_range=5, min=2, max=20)
		station.print_neighbors()
		# print(station.id)
		station.print_follower_and_leader()
		# station.get_price_related_stations()
		# station.print_raises()
		# station.print_drops()
		# station.print_drops(days="wd")
		# station.print_drops(days="we")
		# station.plot_pricing_time_histogram(d='wd')
		# station.plot_pricing_month_hist()

		# first_neigh = STATION_DICT[station.neighbors[0][0]]
		# first_neigh.print_raises()
		# first_neigh.print_drops()
		# first_neigh.print_drops(days="wd")
		# first_neigh.print_drops(days="we")
		# first_neigh.plot_pricing_time_histogram(d='wd')
		# first_neigh.plot_pricing_month_hist()
		

	except psycopg2.DatabaseError, e:
	    print('Error %s' % e)
	    sys.exit(1)

	finally:
	    if con:
	        con.close()