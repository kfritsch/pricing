# -*- coding: utf-8 -*-
import os, sys, traceback, copy
from os.path import join, realpath, dirname, isdir

# the module path is the path to the project folder
# beeing the parent folder of the folder of this file
SRC_PATH = dirname(realpath(__file__))
MODUL_PATH = join(dirname(realpath(__file__)), os.pardir)
# the analysis_docs path is the projects subfolder for outputs to be analysed
ANALYSIS_PATH = join(join(MODUL_PATH,os.pardir), "analysis_docs")

import numpy as np
import matplotlib.pyplot as plt

import HTML
import inspect
import json
import codecs
import psql_pricing

st_dict = None
rule_conf = 0.99

class NumpyAwareJSONEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, np.ndarray):
			return {'__np.ndarray__': True, 'items': obj.tolist()}
		return json.JSONEncoder.default(self, obj)

def json_object_hook(obj):
    if '__np.ndarray__' in obj:
    	return np.array(obj['items'])
    else:
        return obj

def load_test_dict(filename):
	j = codecs.open(join(join(ANALYSIS_PATH,"TESTING_DATA"),filename), 'r').read()
	data = json.loads(j,  object_hook=json_object_hook)
	return data

def get_crosstable(vals, targets, op=None,):
	"""
	Test a set of values at a choosable operator.
	Provide statistics about how the truth values of this comparison translate to the classification

	@param vals: the data examples that are to be tested
	@dtype vals: list

	@param op: the operator with which to compare the data.
	Its a unary or binary operator with the righthand side already defined.
	@dtype op: operator

	@param targets: the target values
	@dtype targets: list

	@param ttable_counter: the table
	@dtype ttable_counter: np.array
	"""

	ttable_counter = np.zeros((3,3))
	if(not(op is None)):
		op_args = len(inspect.getargspec(op)[0])
		if(op_args>2): raise ValueError('Too many arguments for the operator 2 maximum')

	# go through the values and count  up the stats
	for i in range(len(vals)):
		test_con = None
		if(op is None):
			test_con = vals[i]
		else:
			if(op_args==1):
				test_con = op(vals[i])
			else:
				test_con = op(vals[i,0],vals[i,1])

		if(test_con):
			ttable_counter[0][2]+=1
			if(targets[i]):
				ttable_counter[2][0]+=1
				ttable_counter[0][0]+=1
			else:
				ttable_counter[2][1]+=1
				ttable_counter[0][1]+=1
		else:
			ttable_counter[1][2]+=1
			if(targets[i]):
				ttable_counter[2][0]+=1
				ttable_counter[1][0]+=1
			else:
				ttable_counter[2][1]+=1
				ttable_counter[1][1]+=1
		ttable_counter[2][2]+=1
	return ttable_counter

def get_crosstable_values_and_stats(predictions, targets, vals, boxplot=False, hist=False, bp_file="tt_bp"):
	"""
	Test a set of values at a choosable operator.
	Provide statistics about how the truth values of this comparison translate to the classification

	@param vals: the data examples that are to be tested
	@dtype vals: list

	@param op: the operator with which to compare the data.
	Its a unary or binary operator with the righthand side already defined.
	@dtype op: operator

	@param targets: the target values
	@dtype targets: list

	@param ttable_counter: the table
	@dtype ttable_counter: np.array
	"""

	ttable_counter = np.zeros((3,3))

	tt_lists = [[[],[],[]],[[],[],[]],[[],[],[]]]
	# go through the values and count  up the stats
	for i in range(len(predictions)):

		if(predictions[i]):
			ttable_counter[0][2]+=1
			tt_lists[0][2].append(vals[i])
			if(targets[i]):
				ttable_counter[2][0]+=1
				tt_lists[2][0].append(vals[i])
				ttable_counter[0][0]+=1
				tt_lists[0][0].append(vals[i])
			else:
				ttable_counter[2][1]+=1
				tt_lists[2][1].append(vals[i])
				ttable_counter[0][1]+=1
				tt_lists[0][1].append(vals[i])
		else:
			ttable_counter[1][2]+=1
			tt_lists[1][2].append(vals[i])
			if(targets[i]):
				ttable_counter[2][0]+=1
				tt_lists[2][0].append(vals[i])
				ttable_counter[1][0]+=1
				tt_lists[1][0].append(vals[i])
			else:
				ttable_counter[2][1]+=1
				tt_lists[2][1].append(vals[i])
				ttable_counter[1][1]+=1
				tt_lists[1][1].append(vals[i])
		ttable_counter[2][2]+=1
		tt_lists[2][2].append(vals[i])

	if(boxplot):
		create_boxplot([tt_lists[0][0],tt_lists[0][1]], bp_file)
	if(hist):
		create_hist([tt_lists[0][0],tt_lists[0][1]], bp_file)

	avg_table = np.zeros((3,3))
	min_table = np.zeros((3,3))
	max_table = np.zeros((3,3))
	for i in range(0,3):
		for j in range(0,3):
			cell_sum = sum(tt_lists[i][j])
			avg_table[i,j] = float(cell_sum)/ttable_counter[i,j] if(cell_sum!=0) else None
			max_table[i,j] = max(tt_lists[i][j]) if len(tt_lists[i][j])>0 else None
			min_table[i,j] = min(tt_lists[i][j]) if len(tt_lists[i][j])>0 else None
	return avg_table, min_table, max_table

def print_crosstable(data):
	if(not(isinstance(data,list))):
		data = data.tolist()
	ttable_counter = [["test/target", "true", "false", "total"],
	["true"],
	["false"],
	["total"]]
	for i in range(1,4):
		ttable_counter[i]+=data[i-1][:]
	for row in ttable_counter:
		str_row = ""
		for cell in row:
			if(isinstance(cell,float)):
				cell = round(cell,3)
			str_row += str(cell).center(10)
		print(str_row)

def html_intro(page_title):
	"""
	Create the top of an html page with a page title

	@param page_title: the page title
	@dtype page_title: string

	@return intro: the html intro with the title
	@dtype intro: string
	"""
	intro = "<!DOCTYPE html>\n<html>\n<head>\n<title>%s</title>\n</head>\n<body>\n" %(page_title)
	return intro

def html_end():
	"""
	Create a html ending

	@return end: the html ending
	@dtype end: string
	"""
	end = "</body>\n</html>\n"
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
	heading = "<h%d>%s</h%d>\n"% (num,heading,num)
	return heading

def html_crosstable(data):
	# start table
	t = HTML.Table()
	# add header rows
	t.rows.append(HTML.TableRow([HTML.TableCell("Confusion\n<br>\nTable", header=True, bgcolor="#617DD2", attribs={"rowspan":"2","colspan":"2","width":"20%"})],
		attribs={"height":"10px"}))
	t.rows[-1].cells.append(HTML.TableCell("Acutal", header=True, bgcolor="#99A6CB", attribs={"colspan":"2","width":"70%"}))
	t.rows[-1].cells.append(HTML.TableCell("Total", header=True, bgcolor="#617DD2", attribs={"rowspan":"2","width":"10%"}))

	t.rows.append(HTML.TableRow([HTML.TableCell("True", header=True, bgcolor="#C1C4CE")], attribs={"height":"10px"}))
	t.rows[-1].cells.append(HTML.TableCell("False", header=True, bgcolor="#C1C4CE"))
	# add data rows
	t.rows.append(HTML.TableRow([HTML.TableCell("Predicted", attribs={"rowspan":"2"}, header=True, bgcolor="#99A6CB"),
		HTML.TableCell("True", header=True, bgcolor="#C1C4CE"),
		HTML.TableCell(data[0,0], attribs={"style":"font-weight:bold"}),
		HTML.TableCell(data[0,1], attribs={"style":"color:#c23e3e; font-weight:bold"}),
		HTML.TableCell(data[0,2])], attribs={"height":"50px"}))
	t.rows.append(HTML.TableRow([HTML.TableCell("False", header=True, bgcolor="#C1C4CE", attribs={"height":"50px"}),
		HTML.TableCell(data[1,0], attribs={"style":"color:#c23e3e; font-weight:bold"}),
		HTML.TableCell(data[1,1], attribs={"style":"font-weight:bold"}),
		HTML.TableCell(data[1,2])]))
	t.rows.append(HTML.TableRow([HTML.TableCell("Total", attribs={"colspan":"2"}, header=True, bgcolor="#617DD2"),
		HTML.TableCell(data[2,0]),
		HTML.TableCell(data[2,1]),
		HTML.TableCell(data[2,2])], attribs={"height":"10px"}))

	return str(t)

def pause():
	"""
	Pause the execution until Enter gets pressed
	"""
	raw_input("Press Enter to continue...")
	return

def get_data(target_file, test_file):
	target_data = load_test_dict(target_file)
	# load test data
	test_data = load_test_dict(test_file)

	# get all stations tested
	stations = test_data.keys()
	# count for competitors which got not even checked
	not_checked = 0

	# list with stats for each competitor : target,test,conf,number of rules
	comp_stats = [[],[],[],[]]
	# list of all rules with target values : distance,target,days,hours
	tar_rules = np.empty((0,1+1+7+24))
	# list of all rules with target values : distance,target,rule_values,days,hours
	test_rules = np.empty((0,1+1+6+7+24))
	# day stats only of found rules
	test_day_stats = np.empty((0,7,5))
	# hour stats only of found rules
	test_hour_stats = np.empty((0,24,6))
	# states for every rule if the if its a target and found: target,test
	comp_rule_stats = np.empty((0,2))

	rlc = 0
	# prepare the data
	# go through all sations
	for station in stations:
		# get tested competitors
		competitors = test_data[station].keys()
		# add target competitor which didn't get testet
		not_checked_tmp = [comp for comp in target_data[station].keys() if(not(comp in test_data[station]))]
		# competitors += not_checked
		not_checked += len(not_checked_tmp)

		# go through competitors
		for competitor in competitors:
			# check if the comptitor was a target
			if(competitor in target_data[station]):
				comp_stats[0].append(True)
			else:
				comp_stats[0].append(False)
			# check the test result of the competitor
			if(competitor in test_data[station]):
				comp_stats[1].append(test_data[station][competitor][0][0][0])
				comp_stats[2].append(test_data[station][competitor][0][0][1])
				comp_stats[3].append(sum(test_data[station][competitor][0][1][:,1]>=rule_conf))

				# if(comp_stats[0][-1] and not(comp_stats[1][-1])):
					# print(str(psql_pricing.STATION_DICT[station]))
					# print(str(psql_pricing.STATION_DICT[competitor]))

			# else:
			# 	not_checked += 1
			# 	comp_stats[1].append(False)
			# 	comp_stats[2].append(0)
			# 	comp_stats[3].append(1)

			# create a set of rules for this competitor
			rule_set = []
			# if the competitor is a target
			if(competitor in target_data[station]):
				# get the real rules' distances
				rule_set += target_data[station][competitor][0].tolist()
				# if the competitor was tested
				if(competitor in test_data[station]):
					# get the found rules' distances
					rule_set += test_data[station][competitor][0][1][:,0].tolist()
					# delete the double entries
					rule_set = set(rule_set)
					# add the tt indicator for the rule
					comp_rule_stats = np.append(comp_rule_stats, np.ones((len(rule_set),2))*[comp_stats[0][-1],comp_stats[1][-1]], axis=0)
				else:
					rule_set = set(rule_set)
					# add the tt indicator for the rule
					comp_rule_stats = np.append(comp_rule_stats, np.ones((len(rule_set),2))*[comp_stats[0][-1],comp_stats[1][-1]], axis=0)
			else:
				if(competitor in test_data[station]):
					# get the found rules' distances
					rule_set += test_data[station][competitor][0][1][:,0].tolist()
					# delete the double entries
					rule_set = set(rule_set)
					# add the tt indicator for the rule
					comp_rule_stats = np.append(comp_rule_stats, np.ones((len(rule_set),2))*[comp_stats[0][-1],comp_stats[1][-1]], axis=0)
				else:
					rule_set = set(rule_set)
					# add the tt indicator for the rule
					comp_rule_stats = np.append(comp_rule_stats, np.ones((len(rule_set),2))*[comp_stats[0][-1],comp_stats[1][-1]], axis=0)

			# for each rule of this competitor
			for rule in rule_set:
				# if the competitor is a target and has this rule
				if(competitor in target_data[station] and rule in target_data[station][competitor][0].tolist()):
					# get the rule index
					tar_idx = target_data[station][competitor][0].tolist().index(rule)
					# get the target rule stats
					tmp = [rule]+[1]+target_data[station][competitor][1][:,tar_idx].tolist()+target_data[station][competitor][2][:,tar_idx].tolist()
					tar_rules = np.append(tar_rules, [tmp], axis=0)
					# print('a')
				# otherwise there is no rule so just zeros
				else:
					# print('b')
					tmp = np.zeros((1,33))
					tmp[0,0] = rule
					tar_rules = np.append(tar_rules, tmp, axis=0)

				# if the competitor was tested and the rule was found
				if(competitor in test_data[station] and rule in test_data[station][competitor][0][1][:,0].tolist()):
					# get the rule index
					test_idx = test_data[station][competitor][0][1][:,0].tolist().index(rule)
					# get the found rule stats
					tmp = [rule]+[test_data[station][competitor][0][1][test_idx,1]>=rule_conf]+test_data[station][competitor][0][1][test_idx,1:].tolist()+test_data[station][competitor][0][2][test_idx][:,0].tolist()+test_data[station][competitor][0][3][test_idx][:,0].tolist()
					test_rules = np.append(test_rules, [tmp], axis=0)
					# get the analysis stats for each day
					if(test_data[station][competitor][0][1][test_idx,1]<rule_conf):
						test_day_stats = np.append(test_day_stats, [np.zeros((7,5))], axis=0)
						test_hour_stats = np.append(test_hour_stats, [np.zeros((24,6))], axis=0)

					else:
						test_day_stats = np.append(test_day_stats, [test_data[station][competitor][0][2][test_idx][:,1:]], axis=0)
						# get the analysis stats for each hour
						test_hour_stats = np.append(test_hour_stats, [test_data[station][competitor][0][3][test_idx][:,1:]], axis=0)
					# print('a')
				# otherwise there is no rule so just zeros
				else:
					tmp = np.zeros((1,39))
					tmp[0,0] = rule
					test_rules = np.append(test_rules, tmp, axis=0)
	print(not_checked)
	return comp_stats, tar_rules, test_rules, test_day_stats, test_hour_stats, comp_rule_stats

def create_boxplot(data, bp_file):

	# Create a figure instance
	fig = plt.figure(1, figsize=(9, 6))
	# Create an axes instance
	ax = fig.add_subplot(111)

	## add patch_artist=True option to ax.boxplot() 
	## to get fill color
	bp = ax.boxplot(data, whis=[20,80], vert=False, patch_artist=True)

	## change outline color, fill color and linewidth of the boxes
	for box in bp['boxes']:
		# change outline color
		box.set( color='#7570b3', linewidth=2)
		# change fill color
		box.set( facecolor = '#1b9e77' )
	## change color and linewidth of the whiskers
	for whisker in bp['whiskers']:
		whisker.set(color='#7570b3', linewidth=2)
	## change color and linewidth of the caps
	for cap in bp['caps']:
		cap.set(color='#7570b3', linewidth=2)
	## change color and linewidth of the medians
	for median in bp['medians']:
		median.set(color='#b2df8a', linewidth=2)
	## change the style of fliers and their fill
	for flier in bp['fliers']:
		flier.set(marker='.', color='#e7298a', alpha=0.2)

	## Custom x-axis labels
	ax.set_yticklabels(['Prediction:True\nActual:True', 'Prediction:True\nActual:False'])
	## Remove top axes and right axes ticks
	ax.get_xaxis().tick_bottom()
	ax.get_yaxis().tick_left()

	# Save the figure
	fig.savefig(join(join(ANALYSIS_PATH, "TESTING_DATA"),bp_file), bbox_inches='tight')
	plt.close(fig)

def create_hist(data, h_file):

	fig, ((ax1, ax2)) = plt.subplots(1, 2, sharex='col', sharey='row')
	ax1.set_title('Prediction:True\nActual:True',fontsize=14, position=(0.5,1.0))
	ax2.set_title('Prediction:True\nActual:False',fontsize=14, position=(0.5,1.0))
	# the histogram of the data
	ax1.hist(data[0], 20, facecolor='green')
	ax2.hist(data[1], 20, facecolor='red')

	# Save the figure
	fig.savefig(join(join(ANALYSIS_PATH, "TESTING_DATA"),h_file), bbox_inches='tight')

	plt.close(fig)

if __name__ == "__main__":

	import psycopg2
	con = psycopg2.connect(database='pricing_31_8_16', user='kai', password='Sakral8!')
	# con = psycopg2.connect(database='postgres', user='postgres', password='Dc6DP5RU', host='10.1.10.1', port='5432')
	psql_pricing.CURSOR = con.cursor()
	psql_pricing.STATION_DICT = psql_pricing.get_station_dict()
	st_dict = psql_pricing.STATION_DICT

	test_modes = [
		# "default",
		# "lead_t",
		# "n_vals",
		# "one_rule",
		# "com_conf_div",
		# "hour_min",
		"rule_conf"]
		# "com_conf"]

	tt_def = 0

	for mode in test_modes:


		# create a file to save crosstables
		file_name = join(ANALYSIS_PATH, "TESTING_DATA")
		file_name = join(file_name, mode + "_conftable.html")
		f = open(file_name, 'w')
		f.write(html_intro("Confusiontable"))
		f.write("<style>\n")
		f.write(".floating-box {\n\tdisplay: inline-block;\n\tmargin-top: 20px;\n\tmargin-bottom: 20px;\n\tborder: 2px solid #000000;}\n")
		f.write("table, td, th {\n\tborder: 2px solid black;}\n")
		f.write("table {\n\tborder-collapse: collapse;\n\twidth: 100%;}\n")
		f.write("td {\n\tborder: 2px solid black;\n\tvertical-align: center;\n\ttext-align: center;}\n")
		f.write("</style>\n")
		f.write("<center>\n")

		comp_stats, tar_rules, test_rules, test_day_stats, test_hour_stats, comp_rule_stats = get_data("targets.json", mode+".json")

		# Analyse competitors in general
		f.write(html_heading(1, "Analysis of competitors in general\n<br>\nActual competitor vs predicted competitor"))
		# Overall competitor accuracy
		tt = get_crosstable(vals=comp_stats[1], targets=comp_stats[0])
		tt = tt.astype(int)
		f.write(html_heading(3, "Competitor overall accuracy"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(tt))
		f.write("</div>\n")
		f.write('<br>\n')

		if(mode=="default"):
			tt_def = tt

		else:
			tt=tt-tt_def
			f.write(html_heading(3, "Difference to default accuracy"))
			f.write("<div class=\"floating-box\">\n")
			f.write(html_crosstable(tt))
			f.write("</div>\n")
			f.write('<br>\n')

		# Number of rules
		f.write(html_heading(2, "Number of rules"))

		if(mode=="default"):
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=comp_stats[1],
				targets=comp_stats[0],
				vals=comp_stats[3],
				hist=True,
				bp_file="Rulenumber_hist.png")
		else:
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=comp_stats[1],
				targets=comp_stats[0],
				vals=comp_stats[3])

		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average number of rules"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum number of rules"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')

		# Confidence value
		f.write(html_heading(2, "Confidence value"))
		if(mode=="default"):
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=comp_stats[1],
				targets=comp_stats[0],
				vals=comp_stats[2],
				boxplot=True,
				bp_file="comp_conf_boxplot.png")
		else:
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=comp_stats[1],
				targets=comp_stats[0],
				vals=comp_stats[2])
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype('|S5')
		max_table = max_table.astype('|S5')
		# Average
		f.write(html_heading(3, "Average confidence value"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum confidence value"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum confidence value"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')



		# Analyse rules in general
		f.write(html_heading(1, "Analysis of found rules in general\n<br>\nActual rule vs predicted rule"))
		# Overall rule accuracy
		tt = get_crosstable(vals=test_rules[:,1], targets=tar_rules[:,1])
		tt = tt.astype(int)
		f.write(html_heading(3, "Rule overall accuracy"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(tt))
		f.write("</div>\n")
		f.write('<br>\n')

		# Reactions counts
		f.write(html_heading(2, "Reactions counts"))
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1], targets=tar_rules[:,1], vals=test_rules[:,5])
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average reaction count"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum reaction count"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum reaction count"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')

		# Rule distance
		f.write(html_heading(2, "Rule distance"))
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1], targets=tar_rules[:,1], vals=test_rules[:,0])
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average rule distance"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum rule distance"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum rule distance"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')

		# Number of exceptions
		f.write(html_heading(2, "Number of exceptions"))
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1], targets=tar_rules[:,1], vals=test_rules[:,6])
		
		if(mode=="default"):
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1],
				targets=tar_rules[:,1],
				vals=test_rules[:,6],
				hist=True,
				bp_file="exception_hist.png")
		else:
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1],
				targets=tar_rules[:,1],
				vals=test_rules[:,6])

		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average number of exceptions"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum number of exceptions"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum number of exceptions"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')

		# Rule confidence value
		f.write(html_heading(2, "Rule confidence value"))
		# avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1], targets=tar_rules[:,1], vals=test_rules[:,2])
		
		if(mode=="default"):
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1],
				targets=tar_rules[:,1],
				vals=test_rules[:,2],
				boxplot=True,
				bp_file="rule_conf_boxplot.png")
		else:
			avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules[:,1],
				targets=tar_rules[:,1],
				vals=test_rules[:,2])

		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype('|S5')
		max_table = max_table.astype('|S5')
		# Average
		f.write(html_heading(3, "Average rule confidence"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum rule confidence"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum rule confidence"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')


		# # Analyse rules with respect competitor tt
		# print("rule accuracy for comp tt")
		# # where competitor is tt
		# tar_rules_comp = tar_rules[[(row==[1,1]).all() for row in comp_rule_stats],:]
		# test_rules_comp = test_rules[[(row==[1,1]).all() for row in comp_rule_stats],:]
		# print("rule matches tt")
		# avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules_comp[:,1], targets=tar_rules_comp[:,1], vals=test_rules[:,5])
		# print("average:")
		# print_crosstable(avg_table)
		# print("maximum:")
		# print_crosstable(max_table)

		# # # where competitor is tf
		# tar_rules_comp = tar_rules[[(row==[1,0]).all() for row in comp_rule_stats],:]
		# test_rules_comp = test_rules[[(row==[1,0]).all() for row in comp_rule_stats],:]
		# print("rule matches tf")
		# avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules_comp[:,1], targets=tar_rules_comp[:,1], vals=test_rules[:,5])
		# print("average:")
		# print_crosstable(avg_table)
		# print("maximum:")
		# print_crosstable(max_table)

		# # # where competitor is ft
		# tar_rules_comp = tar_rules[[(row==[0,1]).all() for row in comp_rule_stats],:]
		# test_rules_comp = test_rules[[(row==[0,1]).all() for row in comp_rule_stats],:]
		# print("rule matches ft")
		# avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules_comp[:,1], targets=tar_rules_comp[:,1], vals=test_rules[:,5])
		# print("average:")
		# print_crosstable(avg_table)
		# print("maximum:")
		# print_crosstable(max_table)

		# # # where competitor is ff
		# tar_rules_comp = tar_rules[[(row==[0,0]).all() for row in comp_rule_stats],:]
		# test_rules_comp = test_rules[[(row==[0,0]).all() for row in comp_rule_stats],:]
		# print("rule matches ff")
		# avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=test_rules_comp[:,1], targets=tar_rules_comp[:,1], vals=test_rules[:,5])
		# print("average:")
		# print_crosstable(avg_table)
		# print("maximum:")
		# print_crosstable(max_table)
		
		# Analyse days in general
		f.write(html_heading(1, "Analysis of days where rules hold in general\n<br>\nActual days vs predicted days"))
		# Overall day accuracy
		day_tar_vals = tar_rules[:,2:9]
		day_test_vals = test_rules[:,8:15]
		tt = get_crosstable(vals=day_test_vals.reshape(len(day_test_vals)*7), targets=day_tar_vals.reshape(len(day_tar_vals)*7))
		tt = tt.astype(int)

		f.write(html_heading(3, "Day overall accuracy"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(tt))
		f.write("</div>\n")
		f.write('<br>\n')


		# Analyse hours in general
		f.write(html_heading(1, "Analysis of hours where rules hold in general\n<br>\nActual hours vs predicted hours"))
		# Overall hour accuracy
		hour_tar_vals = tar_rules[:,9:]
		hour_test_vals = test_rules[:,15:]
		tt = get_crosstable(vals=hour_test_vals.reshape(len(hour_test_vals)*24), targets=hour_tar_vals.reshape(len(hour_tar_vals)*24))
		tt = tt.astype(int)

		f.write(html_heading(3, "Hour overall accuracy"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(tt))
		f.write("</div>\n")
		f.write('<br>\n')

		# Sum of actual hour prediction changed due to surrounding hours
		f.write(html_heading(2, "Sum of actual hour prediction changed due to surrounding hours"))
		rule_found = test_rules[test_rules[:,7]>0,:]
		f_hours = rule_found[:,15:].reshape(len(rule_found)*24)
		is_target = tar_rules[test_rules[:,7]>0,:]
		h_tar = is_target[:,9:].reshape(len(rule_found)*24)
		surr = test_hour_stats[:,:,5].reshape(len(test_hour_stats)*24)
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=f_hours, targets=h_tar, vals=surr)
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')


		# Analyse hours with respect to the rule confusíon table
		f.write(html_heading(1, "Analyse hours with respect to the rule confusion table\n<br>\nActual rule vs predicted rule"))
		# Sum of actual hour prediction changed due to surrounding hours
		f.write(html_heading(2, "Sum of actual hour prediction changed due to surrounding hours"))
		rule_found = test_rules[test_rules[:,7]>0,1]
		is_target = tar_rules[test_rules[:,7]>0,1]
		surr_sums = np.sum(test_hour_stats[:,:,5],axis=1)
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=rule_found, targets=is_target, vals=surr_sums)
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum of changed hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')

		# Ńumber of hours for which a rule holds
		f.write(html_heading(2, "Number of hours for which a rule holds"))
		rule_found = test_rules[test_rules[:,7]>0,1]
		is_target = tar_rules[test_rules[:,7]>0,1]
		lenght = np.sum(test_rules[test_rules[:,7]>0,15:],axis=1)
		avg_table, min_table, max_table = get_crosstable_values_and_stats(predictions=rule_found, targets=is_target, vals=lenght)
		
		avg_table = avg_table.astype('|S5')
		min_table = min_table.astype(int)
		max_table = max_table.astype(int)
		# Average
		f.write(html_heading(3, "Average of number of hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(avg_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Maximum
		f.write(html_heading(3, "Maximum of number of hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(max_table))
		f.write("</div>\n")
		f.write('<br>\n')
		# Minimum
		f.write(html_heading(3, "Minimum of number of hours"))
		f.write("<div class=\"floating-box\">\n")
		f.write(html_crosstable(min_table))
		f.write("</div>\n")
		f.write('<br>\n')

		f.write(html_end())
		f.close()




	# overall accuracy competitor

	op = (lambda a: a <= 50000)