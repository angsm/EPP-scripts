##############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  4 Dec 2014
##INPUT      :
##DESCRIPTION : This code checks if artifact has complete or nextStep as next action and proceeds to assign it to workflow 
##		choosen using UDF in the records detail screen
##D_VERSION :  1.0.0
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

def getWorkflow( processID ):

	wfURI = ""
	selectedWF = ""
	isFound = 0
	
	## Access artifact limsid from process XML	
	pURI = BASE_URI + "processes/" + processID
	pXML = api.getResourceByURI( pURI )
	pDOM = parseString( pXML )

	## get selected workflow UDF
	selectedWF = api.getUDF( pDOM, "Next Workflow")
	
	## check if UDF is None
	if selectedWF.find( "None" ) > -1:
		raise Exception( "Workflow was not selected, please select a workflow on the record details screen" )

	## get workflow URI
	wURI = BASE_URI + "configuration/workflows"
	wXML = api.getResourceByURI( wURI )
	wDOM = parseString( wXML )

	nodes = wDOM.getElementsByTagName( "workflow" )
	for wfTag in nodes:
		if isFound == 0:
			wfName = wfTag.getAttribute( "name" )
			if wfName.find(selectedWF) > -1:
				wfStatus = wfTag.getAttribute( "status" )

				## check if selected workflow is active
				if wfStatus.find( "ACTIVE" ) > -1:
					wfURI = wfTag.getAttribute( "uri" )
					isFound = 1
					break
				else:
					## signals workflow found but inactive
					raise Exception("Selected workflow is inactive")
	
			elif wfName.find( "None" ) > -1:
				exit()
		else:
			break
	
	## if workflow is not found
	if isFound == 0:
		raise Exception("Selected workflow does not exist")

	return wfURI, selectedWF

def getCompleteArt( stepURI ):

	analyteIDArr = []	

	## retrieve analytes uri which are set to complete 
	aURI = stepURI + "/actions"
	aXML = api.getResourceByURI( aURI )
	aDOM = parseString( aXML )

	nodes = aDOM.getElementsByTagName( "next-action" )
	for node in nodes:
		## ignore any nodes that already have an action attribute
		if node.hasAttribute( "action" ):
			artAction = node.getAttribute( "action" )

			if (artAction.find("nextstep") > -1) or (artAction.find("complete") > -1):
				artURI = node.getAttribute( "artifact-uri" )

				## extract only artifact ID
				strTok = artURI.split( "/" )
				analyteIDArr.append( strTok[6] )

	return analyteIDArr	

def getSubmittedSmp( analyteIDs  ):
	
	sampleIDArr = []

	## Batch retrieve artifacts
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	
	for limsid in analyteIDs:
                link = '<link uri="' + BASE_URI + 'artifacts/' + limsid + '" rel="artifacts"/>'
                lXML += link
        lXML += '</ri:links>'
        gXML = api.getBatchResourceByURI( BASE_URI + "artifacts/batch/retrieve", lXML )
        gDOM = parseString( gXML )	
	
	## get nodes by determining artifact from tag
	Nodes = gDOM.getElementsByTagName( "art:artifact" )

	for artifact in Nodes:
		sampleTag = artifact.getElementsByTagName( "sample" )
		sampleIDArr.append(sampleTag[0].getAttribute( "limsid" ))

	return sampleIDArr

def getBaseAnalyteID( sampleIDs ):
	
	baseArtIDArr = []

	## Batch retrieve artifacts
	lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'
	
	for limsid in sampleIDs:
                link = '<link uri="' + BASE_URI + 'samples/' + limsid + '" rel="samples"/>'
                lXML += link
        lXML += '</ri:links>'
        gXML = api.getBatchResourceByURI( BASE_URI + "samples/batch/retrieve", lXML )
        gDOM = parseString( gXML )	
	
	## get nodes by determining artifact from tag
	Nodes = gDOM.getElementsByTagName( "smp:sample" )
	
	for sample in Nodes:
		baseArtTag = sample.getElementsByTagName( "artifact" )
		baseArtIDArr.append( baseArtTag[0].getAttribute( "limsid" ))

	return baseArtIDArr
		
def assignWorkflow( baseArtIDs, stepURI, workflowURI, wfName ):

	aXML = ""
	
	aXML += '<?xml version="1.0" encoding="UTF-8"?>'
	aXML += '<rt:routing xmlns:rt="http://genologics.com/ri/routing">'
	aXML += '<assign workflow-uri="' + workflowURI + '">'

	for base in baseArtIDs:
		aXML += '<artifact uri="' + BASE_URI + 'artifacts/' + base + '">'
		aXML += '</artifact>'

	aXML += '</assign>'
	aXML += '</rt:routing>'

	## update the LIMS
	rXML = api.createObject( aXML, BASE_URI + "route/artifacts/" )

	## Check if there is any error in the update log	
	if rXML.find( "exception" ) > -1:
		msg = "An Error occured when updating the XML"
        	api.reportScriptStatus( stepURI, "ERROR", msg )		
	else:
		msg = str(len(baseArtIDs)) + " have been successfully assigned onto workflow" + ":\n" + wfName
		api.reportScriptStatus( stepURI, "OK", msg )	

#	print '\n' + "OUTPUT" + '\n' + aXML + '\n'
	print "ERROR" + '\n' + rXML

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

	opts, extraparams = getopt.getopt(sys.argv[1:], "u:p:l:s:")
	for o,p in opts:
		if o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-l':
			args[ "processID" ] = p
		elif o == '-s':
			args[ "stepURI" ] = p
	
	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)	
	
	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )

	try:	
		analyteIDs = getCompleteArt( args[ "stepURI" ]  )
		sampleIDs = getSubmittedSmp( analyteIDs )
		baseArtIDs = getBaseAnalyteID( sampleIDs )
		wfURI, wfName = getWorkflow( args[ "processID" ] )	
		assignWorkflow ( baseArtIDs, args[ "stepURI" ], wfURI, wfName )

	except Exception as e:
		sys.exit(e)

if __name__ == "__main__":
	main()
