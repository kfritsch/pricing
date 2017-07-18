# -*- coding: utf-8 -*-

# helper_functions.py

import os, shutil
import numpy as np
import colorsys

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
	return color

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

def label_barchart_rects2(rects, heights, ax):
	"""
	Label each rectangle in the bar chart with its value

	@param rects: the bars of a bar chart
	@dtype rects: list(rectangle)
	"""
	for (height,rect) in zip(heights,rects):
		# add the label at right above the center of the rect
		ax.text(rect.get_x() + rect.get_width()/2., 1.0*height,
				'%d' % int(height),
				ha='center', va='bottom', fontsize=16)	

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

def clear_dir(directory):
	folder = directory
	for the_file in os.listdir(folder):
		file_path = os.path.join(folder, the_file)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path): shutil.rmtree(file_path)
		except Exception as e:
			print(e)