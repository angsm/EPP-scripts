##############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  30 Oct 2014
##INPUT      :
##DESCRIPTION : This is a custom QC script that qc cq value of dilution buffer in Kapa step
##D_VERSION   :  1.0.0
##P_VERSION   : 1.0.0
##############################################

import socket
import sys
from datetime import datetime as dt
import csv
import getopt
import glsapiutil
import paramiko
import re
from xml.dom.minidom import parseString
from itertools import islice

#HOST='dlap73v.gis.a-star.edu.sg'
GLSFTP='glsftp'
GLSFTPPW='wazUbr5j'
#UDFNAME='UDF_R2value'

#HOSTNAME = 'http://'+HOST+':8080'
VERSION = "v2"
BASE_URI = ""

DEBUG = False
api = None

def getOutputLimsid( limsid ):
	
	limsidArr = []

	## Access artifact limsid from process XML	
	gURI = BASE_URI + "processes/" + limsid
	gXML = api.getResourceByURI( gURI )
	gDOM = parseString( gXML )

	IOMaps = gDOM.getElementsByTagName( "input-output-map" )
	for IOMap in IOMaps:
		output = IOMap.getElementsByTagName( "output" )
                oType = output[0].getAttribute( "output-type" )
                ogType = output[0].getAttribute( "output-generation-type" )
                ## switch these lines depending upon whether you are placing ResultFile measurements, or real Analytes
                ##if oType == "Analyte":
                if oType == "ResultFile" and ogType == "PerInput":

			limsidArr.append(output[0].getAttribute( "limsid" ))
#			print limsidArr[-1]

	return limsidArr

def determineQC( artIDArr, criteriaVal ):

	for limsid in artIDArr:
		## Access artifact limsid from process XML
        	gURI = BASE_URI + "artifacts/" + limsid
        	gXML = api.getResourceByURI( gURI )
        	gDOM = parseString( gXML )

		nodes = gDOM.getElementsByTagName( "art:artifact" )
		temp = nodes[0].getElementsByTagName( "name" )
			
		oName = api.getInnerXml(temp[0].toxml(), "name" )
		
		## Check if artifact is a dilution buffer
		if oName.find("Dilution Buffer") > -1:
			cqVal =	api.getUDF( gDOM, "Cq" )

			if (float(cqVal) < float(criteriaVal)):
				qcFlag = "FAILED"
			else:
				qcFlag = "PASSED"

			updateQC( limsid, qcFlag, oName )

def updateQC( artID, qcVal, artName ):

	#XML file for PUT, partial update
       	xml ='<?xml version="1.0" encoding="UTF-8"?>'
        xml += '<art:artifact xmlns:art="http://genologics.com/ri/artifact">'
	xml += '<name>' + artName + '</name>'
        xml += '<qc-flag>' + qcVal + '</qc-flag>'
        xml += '</art:artifact>'

       	response = api.updateObject(xml, BASE_URI + "artifacts/" + artID )     #PUT requires exact path	
	
#	responseN = response.replace('\n', '')
#	print response


def analyseFile_Single( csvfile, header, colIdx):

	temp = ""
	
	## search for row where getCol header exist and returns all fieldnames and row number of row
	with open(csvfile, 'rb') as f:
		rowNum = 0
		for line in f.readlines():
			rowNum += 1
			if header in line:
				## pinpoint exact location where the required header starts
				idx = line.index(header)
				subStr = str(line)[idx:]

				dataList = subStr.split(',')
				UDFVal = dataList[ colIdx ]				
				break
	f.close()
	return UDFVal

def GetFile( filepath, fLUID, HOSTNAME):

	remotePath=""
	filename=""
	HOST = getHOST(HOSTNAME)

	## get the file's details
	xml = api.getResourceByURI( BASE_URI + "files/" + fLUID )
	dom = parseString( xml )

	elementList = dom.getElementsByTagName("content-location")
	for element in elementList:
		url = api.getInnerXml( element.toxml(), "content-location" )
		#print url
		remotepath = re.sub( "sftp://.*?/", "/", url )
		#print remotepath

	## ftp file from server
	transport = paramiko.Transport(( HOST, 22))
	transport.connect(username = GLSFTP, password = GLSFTPPW)
	sftp = paramiko.SFTPClient.from_transport(transport)
	sftp.get( remotepath, filepath )
	sftp.close()
	transport.close()

def getHostname():

        response = ""

        ## retrieve host name using UNIX command
        temp = socket.gethostname()
        response = "http://" + temp + ".gis.a-star.edu.sg:8080"
        
	return response

def setBASEURI(hostname):
       
	global BASE_URI

        BASE_URI = hostname + "/api/" + VERSION + "/"

def getHOST(hostname):
	
	temp = socket.gethostname()
	HOST = temp + ".gis.a-star.edu.sg"
	
	return HOST

def main():

	global api
	global argsx

	args = {}
	
	getCol = "AVE Cq value"
	colIdx = 6

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:f:l:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-f':
			args[ "csvfile" ] = p
		elif o == '-l':
			args[ "processID" ] = p

	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)	

	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )

	try:
		csvfile= args[ "csvfile" ]
		fURI = BASE_URI + "artifacts/" + csvfile
		fXML = api.getResourceByURI( fURI )
		fDOM = parseString( fXML )

		#print fXML

		file = fDOM.getElementsByTagName( "file:file" )[0]
		fLUID = file.getAttribute( "limsid" )
		#print fLUID

		GetFile('./' + fLUID , fLUID, HOSTNAME )
	
		## gets citeria value, Standard 6 "AVE Cq value"	
		colValue = analyseFile_Single( fLUID, getCol, colIdx )
	
#		print colValue

		determineQC(getOutputLimsid( args[ "processID" ] ), colValue)


	except IndexError:
		sys.exit("File input not found...Please Check.")

	except Exception as e:
		print str(e)

if __name__ == "__main__":
	main()
