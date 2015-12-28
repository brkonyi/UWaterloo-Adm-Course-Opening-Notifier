#!/usr/bin/python

import argparse
import requests #INSTALL: pip install requests
import time
import smtplib
from email.mime.text import MIMEText
from bs4 import BeautifulSoup #INSTALL: sudo apt-get install python-bs4  OR  pip install beautifulsoup4

#---------------------------------------------------#
#------------------EMAIL SETTINGS-------------------#
#---------------------------------------------------#
SMTP_SERVER = "smtp.live.com"
SMTP_USER   = "my@email.com"
SMTP_PASS   = "hunter12"
SMTP_PORT   = 587 
#---------------------------------------------------#
#----------------EMAIL SETTTINGS END----------------#
#---------------------------------------------------#

ADM_URL = 'http://www.adm.uwaterloo.ca/cgi-bin/cgiwrap/infocour/salook.pl'

#Column numbers in the table of lecture information
CLASS_INDEX     = 0
SECTION_INDEX   = 1
ENR_CAP_INDEX   = 6
ENR_TOTAL_INDEX = 7
TIME_DATE_INDEX = 10

#Number of elements in a table of lecture information
ENTRY_LENGTH = 13

#Lecture object keys
CLASS_NUM	  = "ClassNum"
SECTION_NUM       = "Section"
SECTION_ENR_CAP   = "Capacity"
SECTION_ENR_TOTAL = "Enrolled"
SECTION_DATES     = "Dates"

#Config object keys
CONFIG_SESSION    = "Session"
CONFIG_SUBJECT    = "Subject"
CONFIG_COURSE_NUM = "CourseNum"
CONFIG_LEVEL      = "Level"

#Valid levels for course queries
LEVEL_UNDERGRAD = 'under'
LEVEL_GRADUATE  = 'grad'

#Retrieves lecture information for the given course
def getLectures(config):
	param = {"sess"    : str(config[CONFIG_SESSION]),
		 "subject" : config[CONFIG_SUBJECT],
          	 "cournum" : config[CONFIG_COURSE_NUM],
         	 "level"   : config[CONFIG_LEVEL]}

	#Get the results of the query from adm.uwaterloo.ca
	req = requests.post(ADM_URL, data=param)

	#Some fiddling with the returned HTML to get the tables containing the lecture information
	results = BeautifulSoup(req.content).find_all('table')[0].findAll('tr')[2].findAll('tr')

	#First <tr> is garbage. Removing first element of results gives a list of lecture information 
	del results[0]

	lectures = []

	#Create more usable objects to represent lectures
	for result in results:
		result = result.findAll('td')

		if len(result) != ENTRY_LENGTH:
			continue
		
		lecture = {}
		lecture[CLASS_NUM] = int(result[CLASS_INDEX].get_text())
		lecture[SECTION_NUM] = result[SECTION_INDEX].get_text().split(' ')[1]
		lecture[SECTION_ENR_CAP] = int(result[ENR_CAP_INDEX].get_text())
		lecture[SECTION_ENR_TOTAL] = int(result[ENR_TOTAL_INDEX].get_text())
		lecture[SECTION_DATES] = result[TIME_DATE_INDEX].get_text()
		lectures.append(lecture)

	return lectures

def sendEmail(toAddresses, subject, contents):
	print "Sending email..."
	s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
	s.ehlo()
	s.starttls()
	s.login(SMTP_USER, SMTP_PASS)
	
	hdr = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n\r\n" % (SMTP_USER, toAddresses, subject)
	s.sendmail(SMTP_USER, toAddresses, hdr + contents)
	s.quit()
	print "Email sent!"

def sendCourseOpen(config, lecture):
	emailSubject = "OPEN: %s%d-%s %s %d/%d" % (config[CONFIG_SUBJECT], config[CONFIG_COURSE_NUM], lecture[SECTION_NUM], lecture[SECTION_DATES], lecture[SECTION_ENR_TOTAL], lecture[SECTION_ENR_CAP])
	print "Course Open!"
	print emailSubject
	sendEmail(SMTP_USER, emailSubject, "")

def sendCourseClosed(config, lecture):
	emailSubject = "FULL: %s%d-%s %s %d/%d" % (config[CONFIG_SUBJECT], config[CONFIG_COURSE_NUM], lecture[SECTION_NUM], lecture[SECTION_DATES], lecture[SECTION_ENR_TOTAL], lecture[SECTION_ENR_CAP])
	print "Course Full!"
	print emailSubject
	sendEmail(SMTP_USER, emailSubject, "")

def createArgParser():
	parser = argparse.ArgumentParser(description='Check to see if spots are available in a UWaterloo course.')
	parser.add_argument('session', type=int, help='Session number for the term.')
	parser.add_argument('subject', help='Course subject (i.e., CS).')
	parser.add_argument('code', type=int, help='Course code (i.e., 486).')
	parser.add_argument('--level', default=LEVEL_UNDERGRAD, help='Level of study (under for Undergrad, grad for Graduate). Default: under.')
	parser.add_argument('--interval', type=int, default=60, help='Delay between queries. Default: 60.')
	return parser.parse_args()

def main():
	args = createArgParser()
	config = {}
	config[CONFIG_SESSION]    = args.session
	config[CONFIG_SUBJECT]    = args.subject.upper()
	config[CONFIG_COURSE_NUM] = args.code
	config[CONFIG_LEVEL]      = args.level

	lectureStates = {}

	print "Checking for spots available in: %s%d..." % (config[CONFIG_SUBJECT], config[CONFIG_COURSE_NUM])
	while True:
		results = getLectures(config)
		for result in results:
			classNum = result[CLASS_NUM]
			
			if not classNum in lectureStates:
				lectureStates[classNum] = False

			enrolled = result[SECTION_ENR_TOTAL]
			capacity = result[SECTION_ENR_CAP]

			#Check to see if there's capacity in the course and we haven't sent a notification yet.
			if enrolled < capacity and not lectureStates[classNum]:
				lectureStates[classNum] = True
				sendCourseOpen(config, result)
			#Check to see if the course filled up and we notified the user there was spots available.
			elif enrolled >= capacity and lectureStates[classNum]:
				lectureStates[classNum] = False
				sendCourseClosed(config, result)
		time.sleep(args.interval)

if __name__ == "__main__":
	main()
