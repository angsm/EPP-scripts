##############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  09 Jan 2015
##INPUT      :
##DESCRIPTION : Script checks if container name is appropriately named by parameter -n and type of output determined by
##		parameter -r (Analyte/ResultFile) 
##D_VERSION    :  1.0.0
##P_VERSION    : 1.0.0
##############################################

import socket
import sys
from datetime import datetime as dt
import getopt
import glsapiutil
import re
from xml.dom.minidom import parseString

#HOST='dlap73v.gis.a-star.edu.sg'
#HOSTNAME = 'http://'+HOST+':8080'
VERSION = "v2"
BASE_URI = ""

DEBUG = False
api = None

def getOutputLimsid( limsid ):
	limsidArr = []
	
	## Access container limsid from process XML	
	gURI = BASE_URI + "processes/" + limsid
	gXML = api.getResourceByURI( gURI )
	gDOM = parseString( gXML )

	IOMaps = gDOM.getElementsByTagName( "input-output-map" )

	for IOMap in IOMaps:
		output = IOMap.getElementsByTagName( "output" )
                ogType = output[0].getAttribute( "output-generation-type" )
		
		## argument "resultingOutput" can be either "ResultFile" or "Analyte"
                if args[ "resultingOutput" ] and ogType == "PerInput":
			limsidArr.append(output[0].getAttribute( "limsid" ))
#			print limsidArr[-1]

	return limsidArr

def getContainerName( resultIDs ):

	containerIDArr = []
	
	## Batch retrieve
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	
	for limsid in resultIDs:
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

	return containerIDArr

def checkContainerName( containerIDs ):
		
	udNameArr = []
	conNameArr = []

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
		## get user defined name
		udNameTag = container.getElementsByTagName( "name" )
		## getInnerXml gets string from between tags
        	udName = api.getInnerXml(udNameTag[0].toxml(), "name" )

		## get container name
		conNameTag = container.getElementsByTagName( "type" )
		## get string between tags
		conName = conNameTag[0].getAttribute( "name" )	

		if not (re.match( args[ "namePattern" ], udName )):
			udNameArr.append( udName )
			conNameArr.append( conName )
	
	if len(udNameArr) > 0:
		errorMsg = "Please rename the following container(s) with prefix of \"" + args[ "namePattern" ] + "\":" + "\n"
		for i in range (0, len(udNameArr)):
			errorMsg += conNameArr[i] +  " -> " + udNameArr[i] + "\n"
		
		raise Exception( errorMsg )
		
	exit()

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

	containerIDs = []

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:l:n:r:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-l':
			args[ "processID" ] = p
		elif o == '-n':
			args[ "namePattern" ] = p
		elif o == '-r':
			args[ "resultingOutput" ] = p
	
	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)	
	
	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )
	
	try:
		## get container IDs from artifacts
		containerIDs = getContainerName( getOutputLimsid( args[ "processID" ] ) )
		## check container name for pattern match
		checkContainerName( containerIDs )		
	
	except Exception as e:
		sys.exit(e)	

if __name__ == "__main__":
	main()
