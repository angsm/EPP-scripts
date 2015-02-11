###############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  22 Dec 2014
##INPUT      :
##DESCRIPTION : This code find a match of a specified value and populate sample detail field
##D_VERSION    :  1.2.0
##		1.3.0 more accurate reading
##		1.4.0 added mode to read below header( -d 'bottom' / 'side' -s 1), use offset to offset rows to cols
##P_VERSION: 1.0.0
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
GLSFTPPW='OverSandManyDate251'

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
#			print limsidArr[i]

	return limsidArr
			
def analyseFile_Single( csvfile, header, offset, pos):
	temp = ""
	UDFVal = ""	

	## search for row where getCol header exist and returns all fieldnames and row number of row
	with open(csvfile, 'rb') as f:
		## read whole file line by line, removes /r/n
		lines = f.read().splitlines()

		for i in range(0, len(lines)):
			if header in lines[i]:
				## find index of header in line list
				line = lines[i]
				plist = line.split(',')
				idx = plist.index(header)

				if pos.find( "horizontal" ) > -1:
					## move n col(s) the right of the header for data
					UDFVal = plist[idx+offset]
					
				elif pos.find( "vertical" ) > -1:
					## move n row(s) to the bottom of the header for data
					line = lines[i+offset]
					plist = line.split(',')
					UDFVal = plist[idx]					
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

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:f:l:y:d:s:")

	for o,p in opts:

		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-f':
			args[ "csvfile" ] = p
		elif o == '-l':
			args[ "processLimsId" ] = p
		elif o == '-y':
			## tokenize with delimiter, splits <UDF Name>::<Header Name>
			strOri = p
			strTok = strOri.split("::")
			
			## stores multiple y input in array for processing later
			UDFNAME = strTok[0]
			getCol = strTok[1]
		elif o == '-d':
			args[ "direction" ] = p
		elif o == '-s':
			args[ "offset" ] = p

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

		GetFile('./' + fLUID, fLUID, HOSTNAME )
		
		## colIdx determines the col in which the data is in from the header horizontally
		colValue = analyseFile_Single( fLUID, getCol, int(args[ "offset" ]), args[ "direction" ])
#		print colValue
		
		artIDArr = getOutputLimsid( args[ "processLimsId" ] )
		
		rXML = ""		

		# save to xml
		UDFList = ""
		for i in range(0, len(artIDArr)):
			
			url = BASE_URI + "artifacts/" + artIDArr[i]
			
			pXML = api.getResourceByURI(url)
			pDOM = parseString( pXML )
			
			api.setUDF(pDOM,UDFNAME,colValue)

			rXML += api.updateObject( pDOM.toxml(), url )
#			print rXML
			
			print "Updated " +  "\"" + UDFNAME + "\"" + " value for " + artIDArr[i]
			
			if not ( UDFList.find(UDFNAME) > -1):
				UDFList = UDFList + UDFNAME			
	
		print "Parsing of UDFs done: " + UDFList	
	
	except IndexError:
		sys.exit("File input not found...Please Check.")

	except Exception as e:
		print str(e)

if __name__ == "__main__":
	main()

