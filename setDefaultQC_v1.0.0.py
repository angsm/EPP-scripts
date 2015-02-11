##############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  25 Nov 2014
##INPUT      :
##DESCRIPTION : This code sets default QC value to whatever is indicated in parameter
##D_VERSION    :  1.0.0
##		1.0.1 batch retreive, more efficient
##P_VERSION : 1.0.0
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
				
			print limsidArr[-1]

	return limsidArr

def getArtifactName( IDArr ):

	nameDict = {}
	
	## Batch retrieve artifacts
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	
	for limsid in IDArr:
                link = '<link uri="' + BASE_URI + 'artifacts/' + limsid + '" rel="artifacts"/>'
                lXML += link
        lXML += '</ri:links>'
        gXML = api.getBatchResourceByURI( BASE_URI + "artifacts/batch/retrieve", lXML )
        gDOM = parseString( gXML )	
	
	## get nodes by determining artifact from tag
	Nodes = gDOM.getElementsByTagName( "art:artifact" )
	
	for artifact in Nodes:
		## get limsid from artifact
		id = artifact.getAttribute( "limsid" )
		
		## get name tag from artifact
        	nameTag = artifact.getElementsByTagName( "name" )
        
		## map artifact name to its limsid	
		## getInnerXml gets string from between tags
        	nameDict[ id ] = api.getInnerXml(nameTag[0].toxml(), "name")

	return nameDict

def updateQC( artIDArr, flag ):

	artNameDict = getArtifactName( artIDArr )

	for ID in artIDArr:

		#XML file for PUT, partial update
		xml ='<?xml version="1.0" encoding="UTF-8"?>'
		xml += '<art:artifact xmlns:art="http://genologics.com/ri/artifact">'
		xml += '<name>' + artNameDict[ ID ] + '</name>'
        	xml += '<qc-flag>' + flag + '</qc-flag>'
		xml += '</art:artifact>'

		response = api.updateObject(xml, BASE_URI + "artifacts/" + ID )     #PUT requires exact path	
	
		responseN = response.replace('\n', '')
		print response	


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
	global argsx
	args = {}

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:l:q:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-l':
			args[ "processID" ] = p
		elif o == '-q':
			args[ "flagBool" ] = p
	
	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)	
	
	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )

	artifactIDArr = getOutputLimsid( args[ "processID" ] )
	updateQC( artifactIDArr, args[ "flagBool" ] )


if __name__ == "__main__":
	main()
