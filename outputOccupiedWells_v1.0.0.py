##############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  7 Oct 2014
##INPUT      :
##DESCRIPTION : This code outputs and updates UDF using no of occupied wells. Multiple containers input is possible
##D_VERSION    :  1.0.0
##		1.1.0 added ability to encode extended ascii on XML before using PUT request
##		1.1.1 Now using batch retrieve in specific functions to hasten data retrieve
##P_VERSION : 1.0.0
##############################################
import pdb
import socket
from sys import exit
import sys
import getopt
import glsapiutil
import re
from xml.dom.minidom import parseString

#HOSTNAME = 'http://'+HOST+':8080'
VERSION = "v2"
BASE_URI = ""
DEBUG = False
api = None

def getOutputLimsid( limsid ):
	
	analyteIDArr = []

	## Access artifact limsid from process XML	
	gURI = BASE_URI + "processes/" + limsid
	gXML = api.getResourceByURI( gURI )
	gDOM = parseString( gXML )
	IOMaps = gDOM.getElementsByTagName( "input-output-map" )

	for IOMap in IOMaps:
		output = IOMap.getElementsByTagName( "output" )
                oType = output[0].getAttribute( "output-type" )
                ogType = output[0].getAttribute( "output-generation-type" )

                if oType == "ResultFile" and ogType == "PerInput":
			analyteIDArr.append(output[0].getAttribute( "limsid" ))
	
	## use set() to rid of duplicates
	unique = set(analyteIDArr)
	analyteIDArr = list(unique)	

	return analyteIDArr

def getContainerLimsid(analyteIDs):

	containerIDArr = []
	
	## Batch retrieve
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	
	for limsid in analyteIDs:
                link = '<link uri="' + BASE_URI + 'artifacts/' + limsid + '" rel="artifacts"/>'
                lXML += link
        lXML += '</ri:links>'

        gXML = api.getBatchResourceByURI( BASE_URI + "artifacts/batch/retrieve", lXML )
        gDOM = parseString( gXML )	
		
	## get name
	Nodes = gDOM.getElementsByTagName( "art:artifact" )

	for artifact in Nodes:
        	temp = artifact.getElementsByTagName( "container" )
        	
		## getInnerXml gets string from between tags
        	containerIDArr.append(temp[0].getAttribute( "limsid" ))

	## use set() to rid of duplicates
        unique = set(containerIDArr)
        containerIDArr = list(unique)
		
	return containerIDArr

def getNoOfOccupiedWells(containerIDs):
	
	noOfOccupiedWells = ""
	totalNoOfWells = 0
	
	## Batch retrieve
        lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'

        for limsid in containerIDs:
                link = '<link uri="' + BASE_URI + 'containers/' + limsid + '" rel="containers"/>'
                lXML += link
        lXML += '</ri:links>'

        gXML = api.getBatchResourceByURI( BASE_URI + "containers/batch/retrieve", lXML )
        gDOM = parseString( gXML )

        ## get name
        Nodes = gDOM.getElementsByTagName( "con:container" )

	for container in Nodes:
                temp = container.getElementsByTagName( "occupied-wells" )
		noOfOccupiedWells = api.getInnerXml(temp[0].toxml(), "occupied-wells")
		
		totalNoOfWells += int(noOfOccupiedWells)
	
	return totalNoOfWells
	
def setNoOfReact( noOfWells, processID ):

	UDFName = "Total number of reactions"
	noOfStds = 6
	noOfExReacts = 10
	repNum = 3
	
	## noOfWells already includes appropriate replicates.
	calculatedReacts = (noOfWells + (noOfStds * repNum)) + noOfExReacts

	url = BASE_URI + "processes/" + processID 	
	pXML = api.getResourceByURI(url)

	pDOM = parseString( pXML )
	api.setUDF( pDOM, UDFName, str(calculatedReacts))
	
	## changes non-ascii char to unicode
	oriDOM = pDOM.toxml()
	newDOM = oriDOM.encode('ascii', 'xmlcharrefreplace')
	
	pXML = api.updateObject( newDOM, url )
	print "Wells occupied: " + str(calculatedReacts)

#	print pXML

def getHostname():

        response = ""

        ## retrieve host name using UNIX command
        temp = socket.gethostname()
        response = "http://" + temp + ".gis.a-star.edu.sg:8080"
        
	return response

def setBASEURI( hostname ):

        global BASE_URI
        BASE_URI = hostname + "/api/" + VERSION + "/"

def main():

	global api
	global argsx
	args = {}

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:l:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-l':
			args[ "processID" ] = p
	
	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)
	
	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )
	

	try:
		analyteIDArr = getOutputLimsid( args[ "processID" ] )
		containerIDArr = getContainerLimsid( analyteIDArr )
		noOfWellsOccupied = getNoOfOccupiedWells( containerIDArr )

		## set UDF
		setNoOfReact( noOfWellsOccupied, args [ "processID" ] )

	except Exception as e:
		print str(e)

if __name__ == "__main__":
	main()
