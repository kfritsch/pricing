# -*- coding: utf-8 -*-

# comp_http_server.py
import os, sys, traceback, copy, operator, time
from os.path import join, realpath, dirname, isdir
# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
SRC_PATH = dirname(realpath(__file__))
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
# the analysis_docs path is the projects subfolder for outputs to be analysed
ANALYSIS_PATH = join(MODUL_PATH, "tmp")
if(not(isdir(ANALYSIS_PATH))): os.makedirs(ANALYSIS_PATH)

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import urllib2
import urlparse
import requests
from datetime import datetime, timedelta

import psycopg2

import pricing_globals

from station import *
from helper_functions import *
from pricing_helper_functions import *
import comp_config_handler as cf

from multiprocessing import Pool
import cProfile

import codecs, json

pg_params = None
server_params = None
comp_params = None

class My_HTTP_Request_Handler(BaseHTTPRequestHandler):

	def do_GET(self):
		rootdir = '/home/kai/Workspace/test/default/'
		param_dict = {}
		con = None
		try:
			# if(self.path.endswith('.html')):
			purl = urlparse.urlparse(self.path)
			query = urlparse.parse_qs(purl.query)

			station_id = query['id'][0]
			end_date = datetime.strptime(query['time'][0], "%Y-%m-%dT%H:%M:%S")
			days = int(query['days'][0])
			start_date = end_date - (timedelta(days=days))
			d_int = (start_date.date(), end_date.date())


			if(pricing_globals.CURSOR is None):
				con = psycopg2.connect(host=pg_params['host'],
					database=pg_params['database'],
					user=pg_params['user'],
					password=pg_params['password'])
				# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
				pricing_globals.CURSOR = con.cursor()
			if(pricing_globals.STATION_DICT is None):
				pricing_globals.STATION_DICT = get_station_dict()

			station = pricing_globals.STATION_DICT[station_id]

			# print station details
			print('analysing station:')
			print(str(station) + ' ' + station.id) 

			# get the stations competition
			print('getting the stations competition')

			# pool = Pool()
			# pool.map(station.get_competition, (d_int,
			# 	comp_params['lead_t'],
			# 	(comp_params['n_max_range'],comp_params['n_min_num'],comp_params['n_max_num']),
			# 	comp_params['one_rule'],
			# 	comp_params['com_conf_div'],
			# 	comp_params['hour_min'],
			# 	comp_params['rule_conf'],
			# 	comp_params['com_conf']))

			# station.c_profile_competition(d_int=d_int,
			# 	lead_t=comp_params['lead_t'],
			# 	n_vals=(comp_params['n_max_range'],comp_params['n_min_num'],comp_params['n_max_num']),
			# 	one_rule=comp_params['one_rule'],
			# 	com_conf_div=comp_params['com_conf_div'],
			# 	hour_min=comp_params['hour_min'],
			# 	rule_conf=comp_params['rule_conf'],
			# 	com_conf=comp_params['com_conf'])

			station.get_competition(d_int=d_int,
				lead_t=comp_params['lead_t'],
				n_vals=(comp_params['n_max_range'],comp_params['n_min_num'],comp_params['n_max_num']),
				one_rule=comp_params['one_rule'],
				com_conf_div=comp_params['com_conf_div'],
				hour_min=comp_params['hour_min'],
				rule_conf=comp_params['rule_conf'],
				com_conf=comp_params['com_conf'])

			print('saving the json file')
			report = station.get_json()

			self.send_response(200)

			self.wfile.write(report)
			clear_dir(ANALYSIS_PATH)
			return

		except IOError:
			self.send_error(404, 'file_not_found')

		except psycopg2.DatabaseError, e:
			print('Error %s' % e)

			sys.exit(1)

		finally:
			if con:
				con.close()

def run(server_params):
	print('http server is starting...')

	server_address = (server_params['address'], server_params['port'])
	httpd = HTTPServer(server_address, My_HTTP_Request_Handler)
	print(str(datetime.now()) + " Server Starts - %s:%s" % server_address)
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	print (str(datetime.now()) + " Server Stops - %s:%s" % server_address)

if __name__ == '__main__':
	config = cf.Config(cf.get_config())
	pg_params = config.pg_params()
	server_params = config.server_params()
	comp_params = config.comp_params()
#	print(comp_params)
	run(server_params)