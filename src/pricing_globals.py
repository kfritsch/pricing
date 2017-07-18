# -*- coding: utf-8 -*-

# pricing_globals.py

import os, sys, traceback, copy
from os.path import join, realpath, dirname, isdir

from datetime import datetime, timedelta, time

# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
SRC_PATH = dirname(realpath(__file__))
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
# the analysis_docs path is the projects subfolder for outputs to be analysed
ANALYSIS_PATH = join(MODUL_PATH, "tmp")
if(not(isdir(ANALYSIS_PATH))): os.makedirs(ANALYSIS_PATH)

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