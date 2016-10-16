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
from datetime import datetime, timedelta

import psycopg2

import pricing_globals

from station import *
from helper_functions import *
from pricing_helper_functions import *

import codecs, json

class My_HTTP_Request_Handler(BaseHTTPRequestHandler):

	def do_GET(self):
		rootdir = '/home/kai/Workspace/test/default/'
		param_dict = {}
		con = None
		try:
			# if(self.path.endswith('.html')):
			path = self.path
			arguments = path.split('&')[1:]
			for arg in arguments:
				vals = arg.split('=')
				if(vals[0]=='time'):
					param_dict[vals[0]] = datetime.strptime(vals[1], "%Y-%m-%dT%H:%M:%S")
				elif(vals[0]=='days'):
					param_dict[vals[0]] = int(vals[1])
				else:
					param_dict[vals[0]] = vals[1]

			station_id = param_dict['id']
			start_date = param_dict['time'] - (timedelta(days=param_dict['days']))
			d_int = (start_date.date(),param_dict['time'].date())

			if(pricing_globals.CURSOR is None):
				con = psycopg2.connect(host='localhost', database='pricing_31_8_16', user='kai', password='Sakral8!')
				# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
				pricing_globals.CURSOR = con.cursor()
			if(pricing_globals.STATION_DICT is None):
				pricing_globals.STATION_DICT = get_station_dict()

			station = pricing_globals.STATION_DICT[station_id]

			run_vals = [2700, (5,5,20),False,False,3,0.5,0.03]
			# print station details
			print('analysing station:')
			print(str(station) + ' ' + station.id) 

			# get the stations competition
			print('getting the stations competition')
			station.get_competition(d_int=d_int,lead_t=run_vals[0],n_vals=run_vals[1], one_rule=run_vals[2], com_conf_div=run_vals[3], hour_min=run_vals[4], rule_conf=run_vals[5], com_conf=run_vals[6])

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

def run():
	print('http server is starting...')

	server_address = ('127.0.0.1', 80)
	httpd = HTTPServer(server_address, My_HTTP_Request_Handler)
	print(str(datetime.now()) + " Server Starts - %s:%s" % server_address)
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	print (str(datetime.now()) + " Server Stops - %s:%s" % server_address)

if __name__ == '__main__':
	run()