###############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  26 Nov 2014
##INPUT      :
##DESCRIPTION : This code find a match in sample name in .csv file and parse the corresponding Library Molarity value into
##		the UDF field of Sample Details in the "Record Details" screen in "Library Dilution" step
##D_VERSION    :  1.1.0 gets hostname automatically
##		1.1.1 allows args of data input column header and data to get column header 
##		1.2.0 changed from csv.Reader to csv.DictReader, allows user to change match origin and get column headers
##		1.2.1 edited findmatch2 function, put for loop in DictReader iteration
##		1.3.0 Script now assigns QC value automatically, fail if Molarity < 10
##		1.4.0 Allows multiple parameter y inputs. (i.e -y '<UDF Name>::<Header Name>' -y '<UDF Name>::<Header Name>')
##		1.4.1 Accepts multiple samples correctly
##		1.4.2 Added exception handlings
##		1.4.3 Refined search for resultfile
##		1.5.0 findMatch2 func skips line until it finds the correct first header, removes /n/r from endline in excel
##		1.6.0 Added mode 2 that does parsing with sample name based on partial name recognition
##		1.6.1 Added batch retrieve, more efficient
##		1.6.2 Added ability to read tab formated files
##P_VERSION : 1.0.0
##############################################

import os
import socket
from sys import exit
import sys
from datetime import datetime as dt
import csv
import getopt
import glsapiutil
import paramiko
import re
from xml.dom.minidom import parseString
from itertools import islice
import pdb

#HOST='dlap73v.gis.a-star.edu.sg'
GLSFTP='glsftp'
GLSFTPPW='OverSandManyDate251'

#UDFNAME='Library Molarity (nM)'

#HOSTNAME = 'http://'+HOST+':8080'
VERSION = "v2"
BASE_URI = ""

DEBUG = False
api = None

mode = ""

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

def batchArtRetrieve( artIDArr ):
	
	## Batch retrieve
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	 
	for limsid in artIDArr:
                link = '<link uri="' + BASE_URI + 'artifacts/' + limsid + '" rel="artifacts"/>'
                lXML += link
        lXML += '</ri:links>'
        gXML = api.getBatchResourceByURI( BASE_URI + "artifacts/batch/retrieve", lXML )
        gDOM = parseString( gXML )	
		
	## get name
	Nodes = gDOM.getElementsByTagName( "art:artifact" )

	return Nodes

def getArtifactName(artIDs):
	
	oNameDict = {}

	## Access artifact names from output xml it its an artifact
        Nodes = batchArtRetrieve( artIDs )
	for artifact in Nodes: 
		id = artifact.getAttribute( "limsid" )
	        temp = artifact.getElementsByTagName( "name" )
	
        	## getInnerXml gets string from between tags
        	oNameDict[ id ] = api.getInnerXml(temp[0].toxml(), "name" )
	
	return oNameDict


def getArtifactWell(artIDs):

	wellNumDict = {}

	## Access artifact names from output xml it its an artifact
        Nodes = batchArtRetrieve( artIDs )
	for artifact in Nodes:
		id = artifact.getAttribute( "limsid" )
	        temp = artifact.getElementsByTagName( "value" )

        	## getInnerXml gets string from between tags
	        oriWellNum = api.getInnerXml(temp[0].toxml(), "value" )
		strTok = oriWellNum.split(":")	
	
		## From A:2 to A02	
		wellNumDict[ id ] = strTok[0] + "%02d" % int(strTok[1])
	
        return wellNumDict

def getArtifactArr( limsidArr ):

	artValDict = {}
	temp = ""

	## stores all output artifact in a list
	if mode == '0' or mode == '2':	
		artValDict = getArtifactName(limsidArr)
	elif mode == '1':
		artValDict = getArtifactWell(limsidArr)
	
	return artValDict

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

def determineSlice( csvfile, oriCol):	
	
	fieldVal = []

	## if args[ "delim" ] is used	
	if "delim" in args.keys():
		## convert tab text to csv file if args[ "delim" ] = 'tab'
		if args[ "delim" ].find( "tab" ) > -1:
			with open(csvfile, 'rb') as infile:
				with open('temp.csv', 'wb') as outfile:
    					in_txt = csv.reader(infile, delimiter = '\t')
    					out_csv = csv.writer(outfile)
	    				out_csv.writerows(in_txt)

			csvfile = 'temp.csv'

			infile.close()
			outfile.close()
	
	## open file and scan if desired header is in line
	with open(csvfile, 'r') as f:
		startRow = 0
		for line in f.readlines():
			startRow += 1
			if oriCol in line:
				bfieldVal = line.split(',')
				print bfieldVal
				break
	f.close()
	
	## strip L + T white spaces	
	for i in range(0, len( bfieldVal)):
        	fieldVal.append(bfieldVal[i].rstrip().lstrip())

        ## Uses DictReader that organizes csv file data by row with columnheaders as keys
        ## islice makes dictreader start from specific row
        tempFile = islice(open(csvfile, 'rb'), startRow, None)
        processedFile = csv.DictReader(tempFile, fieldnames = fieldVal)
	
	## remove temp csv file created during conversion AND if file exist
	if os.path.isfile('temp.csv'): 
		os.remove('temp.csv')
	
	return processedFile

def findMatch2( csvfile, artValArr, oriCol, getColArr):

	getList = {}
	matchTxt = []
	matchID = []

	## determine which row to start scanning from, if desired header column is in row
	inputFile = determineSlice( csvfile, oriCol)

	for row in inputFile:
		## remove \r\n
		row = dict([(k.replace('\r\n', ''),v) for k,v in row.items() ])
#		pdb.set_trace()

		for artKey, artValue in artValArr.iteritems():
			## if artifact name/wellno matches value in desired column
			if artValue == row[oriCol]:
				matchID.append(artKey)
				
				## append values that matches artifact name/wellno
				for j in range(0, len(getColArr)):
					## if 1 UDF is blank, the second one will not be printed out
                                        if row[getColArr[j]] == "":
                                                getList[str(getColArr[j])] = '0'
                                        else:
                                                getList[str(getColArr[j])] = row[getColArr[j]]

				matchTxt.append(getList)
				
				## empty dict to prevent residue	
				getList = {}

	return matchTxt, matchID

def findPartialMatch( csvfile, artValArr, oriCol, getColArr):

        getList = {}
	matchTxt = []
	matchID = []

	## parse value into UDF as long as header matches partially
        inputFile = determineSlice( csvfile, oriCol)
	preReadDict = preReadData( inputFile, oriCol, getColArr )
	
	for artKey, artValue in artValArr.iteritems():
		for key in preReadDict:
			if artValue.find( key ) > -1:
				matchID.append(artKey)
				matchTxt.append(preReadDict[ key ])
	
	return matchTxt, matchID

def preReadData( inputFile, oriCol, getColArr ):

        dataDict = {}
        getList = {}

        for row in inputFile:
                row = dict([(k.replace('\r\n', ''),v) for k,v in row.items() ])

                ## get wanted columns and their respective values
                for j in range(0, len(getColArr)):
                        if not ((row[getColArr[j]] == "") or (row[getColArr[j]] == "#DIV/0!")):
                                getList[str(getColArr[j])] = row[getColArr[j]]
        	if not getList == {}:       		
			dataDict[ row[ oriCol] ] = getList

		getList = {}
        return dataDict

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
	global args
	global mode

	args = {}

	UDFNAMEArr = []
	getColArr = []

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:f:l:m:x:y:q:d:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-f':
			args[ "csvfile" ] = p
		elif o == '-l':
			args[ "processLimsid" ] = p
		elif o == '-m':
			mode = p
		elif o == '-x':
			args[ "oriCol" ] = p
		elif o == '-y':

			## tokenize with delimiter, splits <UDF Name>::<Header Name>
			strOri = p
			strTok = strOri.split("::")
			
			## stores multiple y input in array for processing later
			UDFNAMEArr.append(strTok[0])
			getColArr.append(strTok[1]) 		
		elif o == '-q':
			args[ "qcVar" ] = p
		elif o == '-d':
			args[ "delim" ] = p

	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)
	
	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )
	artIDArr = getOutputLimsid( args[ "processLimsid" ] )
	artValDict = getArtifactArr( artIDArr )
	
	try:
		csvfile= args[ "csvfile" ]
		fURI = BASE_URI + "artifacts/" + csvfile
		fXML = api.getResourceByURI( fURI )
		fDOM = parseString( fXML )
			
#		print fURI

		file = fDOM.getElementsByTagName( "file:file" )[0]
		fLUID = file.getAttribute( "limsid" )

#		print fLUID

		GetFile('./' + fLUID , fLUID, HOSTNAME )
		
		## mode 0 -> using sample name 
		## mode 1 -> using well number
		## mode 2 -> partial match of sample name
		if mode == "2":
			matchTxt, matchID = findPartialMatch( fLUID, artValDict, args[ "oriCol" ], getColArr )
		else:
			matchTxt, matchID = findMatch2( fLUID, artValDict, args[ "oriCol" ], getColArr )

		rXML = ""	
		
		if len(matchTxt) > 0:
			# save to xml
			for i in range(0, len(matchTxt)):
						
				url = BASE_URI + "artifacts/" + matchID[i]
			
				pXML = api.getResourceByURI(url)
				pDOM = parseString( pXML )

				for j in range(0, len(UDFNAMEArr)):
					api.setUDF(pDOM,UDFNAMEArr[j],str(matchTxt[i][getColArr[j]]))
					print "Updated " + "\""  + UDFNAMEArr[j] + "\""  + " value for " + matchID[i]

				rXML += api.updateObject( pDOM.toxml(), url )
#				print rXML
			
                	print "Parse Done"  
		else:
			raise Exception("Nothing found")

	except IndexError:
		sys.exit("File input not found...Please Check.")
	
	except Exception as e:
		if e.message == "Nothing found":
			sys.exit("No matching sample name detected...")
		else:
			print str(e)
		

if __name__ == "__main__":
	main()
