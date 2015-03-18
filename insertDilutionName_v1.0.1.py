###############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  26 Nov 2014
##INPUT      :
##DESCRIPTION : This script inserts dilution values behind existing sample name.
##D_VERSION     :  1.0.0
##		1.0.0_Kapa Customized for Kapa, does not rename dilution buffers
##		1.0.1_Kapa Decide if rename is needed by determining whether its a control from control-type tag
##		1.0.2_Kapa Uses batch retrieve, more efficient
##P_VERSION : 1.0.0
##	      1.0.1 Determines dilution value by replication number n in "qPCR_n" appended by Clarity LIMS
##		    Added parameter -x for excluded names. i.e -x '<artname>,<artname>'
###############################################

from collections import defaultdict
import socket
import sys
import getopt
import xml.dom.minidom
import glsapiutil
from xml.dom.minidom import parseString
import re

VERSION = "v2"
BASE_URI = ""
DEBUG = False
api = None

limsidArr = []

def getArtifactIDs( processID ):

	global limsidArr

	## step one: get the process XML
        pURI = BASE_URI + "processes/" + processID
        pXML = api.getResourceByURI( pURI )
        pDOM = parseString( pXML )

        IOMaps = pDOM.getElementsByTagName( "input-output-map" )

	for IOMap in IOMaps:
		output = IOMap.getElementsByTagName( "output" )
                oType = output[0].getAttribute( "output-type" )
                ogType = output[0].getAttribute( "output-generation-type" )
                ## switch these lines depending upon whether you are placing ResultFile measurements, or real Analytes
                ##if oType == "Analyte":
                if oType == "ResultFile" and ogType == "PerInput":
			
			limsidArr.append(output[0].getAttribute( "limsid" ))

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

def insertDilutionInName( artifactsID, modNum ):
	
	count = 0
        n = 0
        dilution = ["_1:1000", "_1:2000"]
        response = ""

        ## get artifact info in batch and rename
        Nodes = batchArtRetrieve( artifactsID )
        for artifact in Nodes:
                id = artifact.getAttribute( "limsid" )
                nameTag = artifact.getElementsByTagName( "name" )
                oriName = api.getInnerXml(nameTag[0].toxml(), "name")
		
		if "exclude" in args.keys():
			## determine if its a artifact that should be excluded
			artName = re.search("(.+)\s[a-zA-Z]{1,4}\_([0-9]{1,2})", oriName).group(1)
			excludeArr = args[ "exclude" ].split(",")

			isExclude = None
			for ex in excludeArr:
				isExclude = re.search( ex, artName )
				if isExclude:
					break
		else:
			isExclude = None
			
		if isExclude == None:
			## restart name, remove dilution append from any previous script run
			oriName = re.search(".+\s[a-zA-Z]{1,4}\_([0-9]{1,2})", oriName).group(0)
		
			## search for n in "qPCR_n"	
			repNum = re.search("\s[a-zA-Z]{1,4}\_([0-9]{1,2})", oriName).group(1)
				
			if int(repNum) <= int(modNum):
				newName = oriName + dilution[0]
			elif int(repNum) > int(modNum):
				newName = oriName + dilution[1]
		
			#XML file for PUT, partial update
                        xml ='<?xml version="1.0" encoding="UTF-8"?>'
                        xml += '<art:artifact xmlns:art="http://genologics.com/ri/artifact">'
                        xml += '<name>' + newName + '</name>'
                        xml += '</art:artifact>'

                        response = api.updateObject(xml, BASE_URI + "artifacts/" + id )     #PUT requires exact path
			print newName

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

        hostname = ""
        args = {}

        opts, extraparams = getopt.getopt(sys.argv[1:], "l:u:p:m:x:")

        for o,p in opts:
                if o == '-l':
                        args[ "limsid" ] = p
                elif o == '-u':
                        args[ "username" ] = p
                elif o == '-p':
                        args[ "password" ] = p
                elif o == '-m':
                        args[ "modNum" ] = p
		elif o == '-x':
			args[ "exclude" ] = p

        hostname = getHostname()

        api = glsapiutil.glsapiutil()
        api.setHostname( hostname )
        api.setVersion( VERSION )
        api.setup( args[ "username" ], args[ "password" ] )
        setBASEURI(hostname)

        ## at this point, we have the parameters the EPP plugin passed, and we have network plumbing
        ## so let's get this show on the road!

	insertDilutionInName(getArtifactIDs(args[ "limsid" ]), float(args[ "modNum" ]) )	


if __name__ == "__main__":
        main()
