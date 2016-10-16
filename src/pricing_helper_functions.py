# -*- coding: utf-8 -*-

# pricing_helper_functions.py

import pricing_globals

from datetime import datetime, timedelta, time
from math import sin, cos, atan2, sqrt, radians, atan, pi
import matplotlib.pyplot as plt
from helper_functions import *

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

def split_at(data_idc, station_id, split_criterium):
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
	data = pricing_globals.STATION_DICT[station_id].pricing_mat
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

def comp_conf(support,total):
	"""
	Computes the confidence value for a rule. It compares the pricings that support this exact rule
	to the total amount of pricings in this time category.
	As confidence value we want something like the percentage of the maximal difference from all
	matches or misses respectively. However this should not be a linear function. The amount of the maximal
	difference should be weighted much higher. For moderately high values of occurances there should
	be a high total number to neglect this value as extreme values. Or to put it in slighly different way
	the percentage needed to accept a value decreases with the total amount. 
	Additionally we want to scale the value into the range of 0 to 1 to express the condifence as a percentage.
	Function: 2/pi*atan(2* (x*x/y))

	@param support: the supporting fraction
	@dtype support: int

	@param total: the total amount
	@dtype total: int

	@return conf: the confidence value as percentage
	@dtype conf: float
	"""

	conf = (float(2)/pi)*atan(2*float(pow(support,2))/total)
	return conf

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
		pricing_globals.CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history"+
			" WHERE " + PG['MONTH'] + " AND " + PG['YEAR'] % (month, year))
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
		pricing_globals.CURSOR.execute("SELECT COUNT(*) FROM gas_station_information_history" +
			" WHERE " + PG['DOW_INT'] +
			" AND " + PG['DATE_INT'] +
			" AND " + PG['HOUR'],
			dow_int+date_int+(i,))
		pricing_hist[i] = pricing_globals.CURSOR.fetchone()[0];
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
