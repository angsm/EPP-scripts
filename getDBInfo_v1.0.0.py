#############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  23 Oct 2014
##INPUT      :
##DESCRIPTION : This script gets data from database and output as using print to LIMS file placeholder
##D_VERSION    :  1.0.0
##		1.1.0 Changed row grab logic
##P_VERSION : 1.0.0
##############################################

import socket
import sys
import os
import getopt
import xml.dom.minidom
import re
import glsapiutil
from xml.dom.minidom import parseString
import calendar
import cx_Oracle

VERSION = "v2"
BASE_URI = ""

api = None

def connectSQL( sqlFile ):

	varDict = {}
	infoDict = {}
	tempDict = {}
	
	idList = []
	
	## Dev server **RMB TO CHANGE WHEN IN PRODUCTION SERVER**
	SQL_USERNAME = "claritylims"
	SQL_PASS = "claritylims"
	SQL_HOST = "pldb01"
	SQL_PORT = "1521"
	SQL_SID = "clarityDB"

	f = open( sqlFile )
	full_sql = f.read()
	sql_commands = full_sql.split(';')
	f.close()	
	
#	print full_sql	

	HEADERS = "Run Date, Run ID, Instrument Name, Operator, Base > Q30(%), Cluster Density(K/mm^2), PF(%), Aligned(%), Error Rate(%)"
	FIELDS = ["% Bases >=Q30", "Cluster Density (K/mm^2)", "%PF", "% Aligned", "% Error Rate"]
	
	## Make connection to Oracle SQL database
	connection = cx_Oracle.connect( SQL_USERNAME + "/" + SQL_PASS + "@//" + SQL_HOST + ":" + SQL_PORT + "/" + SQL_SID )
	cursor = connection.cursor()
	cursor.execute(sql_commands[0])

	## Add header first
	for row in cursor:

		## Define
	        RUNDATE = row[0]
        	PROCESSNAME = row[1]
     		EQUIP = row[2]
        	RUNID = row[3]
		OP = row[4]
        	VARNAME = row[5]
        	VARVAL = row[6]

		## Store LUID of process, remains in order
		if RUNID not in idList:
			idList.append( RUNID )

		## Get fields
		## RUNID is LUID of process
		if RUNID not in varDict:
			varDict[ RUNID ] = []
			
		## UDF = UDF data
		tempDict[ VARNAME ] = VARVAL
		varDict[ RUNID ].append( tempDict )
		tempDict = {}

		## Get process info
		if RUNID not in infoDict:
			infoDict[ RUNID ] = []		
				
			## Run date
			infoDict[ RUNID ].append(RUNDATE)
			## Run ID
			infoDict[ RUNID ].append(RUNID)
			## Instrument name
			infoDict[ RUNID ].append(EQUIP)
			## Operator
			infoDict[ RUNID ].append(OP)

	cursor.close()
	connection.close()

	displayInfo( idList, varDict, infoDict, HEADERS, FIELDS)

def displayInfo( orderedIdList, variableDict, informationDict, header, header_col):
	
	## Formats data order for display		
	outputStr = ""
	outputStr += header + "\n"
	for processID in orderedIdList:
		
		## Run date
		outputStr += formatDate(str(informationDict[processID][0])) + ","

		## Rest of run information
		for i in range( 1, len( informationDict[processID])):
			outputStr += str(informationDict[processID][i]) + ","

		## Fields	
		for head in header_col:
			## Variable is a dictionary obj in variableDict dictionary which has date for key
			for variable in variableDict[ processID ]:
				for key in variable:
					if key.find( head ) > -1:
						outputStr += str(variable[ key ]) + ","
		outputStr += "\n"

	## ***** OUTPUT LIVE, DO NOT COMMENT THIS PRINT AWAY *****
	## Print will output data to bash and into receiving file on bash
	print outputStr

def formatDate( dateStr ):

	if not (str(dateStr) == "None"):
		processedDate = ""
		
		## Tokenize string that contains date and time
		timeRemoved = str(dateStr).split( " " )
		
		## Use only date portion of token and remove hyphen
		dateTok = timeRemoved[0].split( "-" )
		
		## Rearrange date
		processedDate += "%02d" % int(dateTok[2]) + "-"
		
		## Change numeric month to month name
		month = ((calendar.month_name[int(dateTok[1])])[:3]).upper()
		processedDate += month + "-"
		processedDate += dateTok[0]
		
		return processedDate
	else:
		return str(dateStr)

def getHostname():

        response = ""
        
	## retrieve host name using UNIX command
        temp = socket.gethostname()

        response = "http://" + temp + ".gis.a-star.edu.sg:8080"
        
	return response

def setBASEURI(hostname):

        global BASE_URI

        BASE_URI = hostname + "/api/" + VERSION + "/"

def main():

	global api
	global args

	args = {}

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:f:") 
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-f':
			args[ "file" ] = p
	
	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)

	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )

	connectSQL( args[ "file" ])

if __name__ == "__main__":
	main()
