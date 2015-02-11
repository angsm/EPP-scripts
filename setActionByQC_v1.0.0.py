###############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  26 Nov 2014
##INPUT      :
##DESCRIPTION : script gets qc-flag from resultFile. If FAILED, next action is set to manager review
##D_VERSION    :  1.0.0
##		1.0.1 sets action for multiple samples correctly
##		1.0.2 Refined search for resultfile 
##		1.1.0 Handles replicates
##		1.1.1 Set one step control to be removed (a MUST by LIMS)
##		1.1.2 Uses batch retrieve, more efficient
##		1.1.3 Detects QC protocol by aggregate QC step, sets action to nothing instead of complete
##		1.1.4 Combined analyte and resultfile info retrieval
##P_VERSION : 1.0.0
##############################################

import socket
import sys
import getopt
import xml.dom.minidom
import re
import glsapiutil
from xml.dom.minidom import parseString

## This is a recipe for Python 2.7 and below, its in collections in python 2.7
from orderedDictRecipe import OrderedDict

#HOSTNAME = 'http://dlap73v.gis.a-star.edu.sg:8080'
VERSION = "v2"
BASE_URI = ""

DEBUG = False
api = None

def getStepConfiguration( stepURI ):

	response = ""

	if len( stepURI ) > 0:
		stepXML = api.getResourceByURI( stepURI )
		stepDOM = parseString( stepXML )
		nodes = stepDOM.getElementsByTagName( "configuration" )
		if nodes:
			response = nodes[0].toxml()

	return response

def getNextActionURI( cfXML ):

	response = ""

	if len( cfXML ) > 0:
		DOM = parseString( cfXML )
		nodes = DOM.getElementsByTagName( "configuration" )
		if nodes:
			cfURI = nodes[0].getAttribute( "uri" )
			stXML = api.getResourceByURI( cfURI )
			stDOM = parseString( stXML )
			nodes = stDOM.getElementsByTagName( "transition" )
			if nodes:
				naURI = nodes[0].getAttribute( "next-step-uri" )
				response = naURI

	return response

def getArtInfo( processID ):
	resultIDArr = []
	analyteIDArr = []
	analyteURIArr = []
	
	## Access artifact limsid from process XML	
	gURI = BASE_URI + "processes/" + processID
	gXML = api.getResourceByURI( gURI )
	gDOM = parseString( gXML )

	IOMaps = gDOM.getElementsByTagName( "input-output-map" )
	for IOMap in IOMaps:

		## OUTPUT
		output = IOMap.getElementsByTagName( "output" )
                oType = output[0].getAttribute( "output-type" )
                ogType = output[0].getAttribute( "output-generation-type" )

                if oType == "ResultFile" and ogType == "PerInput":
			resultIDArr.append(output[0].getAttribute( "limsid" ))

		## INPUT
		input = IOMap.getElementsByTagName( "input" )
		tmpID = input[0].getAttribute( "limsid" )
		if tmpID not in analyteIDArr:
			analyteIDArr.append( tmpID )

		tmpURI = input[0].getAttribute( "post-process-uri" )
		tmpURI = api.removeState( tmpURI )
		if tmpURI not in analyteURIArr:
			analyteURIArr.append( tmpURI )
		
	return resultIDArr, analyteIDArr, analyteURIArr

def batchArtRetrive( artIDArr ):
	
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

def getArtifactInfoBatch(artIDs):
	
	nameDict = {}
	qcFlagDict = {}
		
	## get name
	Nodes = batchArtRetrive( artIDs )
	for artifact in Nodes:
        	id = artifact.getAttribute( "limsid" )
		nameTag = artifact.getElementsByTagName( "name" )
		qcFlagTag = artifact.getElementsByTagName( "qc-flag" ) 	
		
		## map properties to id and store in dictionary for reference
        	nameDict[ id ] = api.getInnerXml( nameTag[0].toxml(), "name" )
		qcFlagDict[ id ] = api.getInnerXml( qcFlagTag[0].toxml(), "qc-flag" ) 
		
	return nameDict, qcFlagDict

def getQCFlag( analyteIDs, resultIDs ):

	FAILCount = 0
	matchCount = 0
	flagDict = {}
	
	## RESULTFILES
        ## get resultfile info
        rNameDict, rQCFlagDict = getArtifactInfoBatch( resultIDs )
	
	## ANALYTES
	## get name
	Nodes = batchArtRetrive( analyteIDs )
	for artifact in Nodes:
		id = artifact.getAttribute( "limsid" )		

        	nameTag = artifact.getElementsByTagName( "name" )
		oName = api.getInnerXml( nameTag[0].toxml(), "name" )		
		
		for j in range(0, len(resultIDs)):
		
			rName = rNameDict[ resultIDs[j] ]	
	
			## if analyte name and resultfile name matches, get qc-flag determined by molarity from xml
			if rName.find( oName ) > -1 :
				matchCount += 1
				
				qcFlag = rQCFlagDict[ resultIDs[j] ]
				
#				print qcFlag	
				if qcFlag == "FAILED":
					FAILCount += 1
		if FAILCount > 0:
			## If there are replicates, even if 1 fails, overall will pass
			if resultIDs > 1:
				if matchCount == FAILCount:
					overallQc = "FAILED"
				else:
					overallQc = "PASSED"
			else:
				overallQc = "FAILED"
		else:
			overallQc = "PASSED"
		
#		print "OVERALL: " + overallQc
		flagDict[ id ] = overallQc
	
		## reset counters	
		FAILCount = 0
		matchCount = 0
	
	return flagDict

def checkIfSingleStep( artIDs ):
	
	response = 0
	isSingleStep = []
	
        ## check if its a control 
        Nodes = batchArtRetrive( artIDs )
        for artifact in Nodes:
                id = artifact.getAttribute( "limsid" )
		ctrlTag = artifact.getElementsByTagName( "control-type" )

		## If its a control, the tag will exist and checks if its a single step control
		if len(ctrlTag) > 0:
			url = ctrlTag[0].getAttribute( "uri" )
	 	
 		       	controlXML = api.getResourceByURI( url )
	        	controlDOM = parseString( controlXML )
			
			## Check if its a single step artifact, meaning it should be rid off after a single step
			singleStepTag = controlDOM.getElementsByTagName( "single-step" )
			tagVal = api.getInnerXml( singleStepTag[0].toxml(), "single-step" )

			if tagVal == "true":
				isSingleStep.append( id )
			
	return isSingleStep

def isQCProtocol( stepURI ):

	gXML = api.getResourceByURI( stepURI )
	gDOM = parseString( gXML )

	confTag = gDOM.getElementsByTagName( "configuration" )
	temp = confTag[0].getAttribute( "uri" )

	idx = temp.find( "/steps" )
	confURI = temp[0:idx-1]

	gXML = api.getResourceByURI( confURI )
        gDOM = parseString( gXML )

	processTag = gDOM.getElementsByTagName( "process-type" )
	for node in processTag:
		process = api.getInnerXml( node.toxml(), "process-type" )
		if( process.find( "Aggregate QC" ) > -1 ):
			isQCProtocol = 1
			break
		else:
			isQCProtocol = 0

	return isQCProtocol

def routeAnalytes():

	RESULTS_ID = []
	ANALYTES = []
	ANALYTES_ID = []
	temp = []
	qcFlag = {}
	isQC = 0

	## get resultfile and analyte info
	RESULTS_ID, ANALYTES_ID, ANALYTES = getArtInfo( args[ "limsid" ] )

	## get dictionary of artID as key and overall qcflag as value
	qcFlag = getQCFlag(ANALYTES_ID, RESULTS_ID)
	## get dictionary of artID as key and single step flag as value
	isSingleStep = checkIfSingleStep( ANALYTES_ID )	

	## build the appropriate XML
	stepConfig = getStepConfiguration( args[ "stepURI" ] )
	## if we weren't given a -a flag, use the default next action for this step
	naXML = ""
	tXML = ""

	if "action" in args.keys():
		naXML += '<next-action step-uri="" action="' + args[ "action" ]  + '" '
	else:
		naURI = getNextActionURI( stepConfig )
					
		## if qcFlag was set to FAILED, set next action to manager review, else set to complete
		for i in range(0, len(ANALYTES_ID)):

			if ANALYTES_ID[i] in isSingleStep:
				naXML = '<next-action action="remove" '
			else:

				if(qcFlag[ANALYTES_ID[i]] == "FAILED"):
					naXML = '<next-action action="review" '
				elif(qcFlag[ANALYTES_ID[i]] == "PASSED"):
					if not (naURI == ""):
						naXML = '<next-action step-uri="' + naURI + '" action="nextstep" '
					else:
						#isQC = isQCProtocol( args[ "stepURI" ])
						if isQC == 0:
							naXML = '<next-action action="complete" '
						else:
							naXML = '<next-action '
				else:
					naXML = '<next-action action="unknown" '


			tXML += naXML + 'artifact-uri ="' + ANALYTES[i] + '"/>'

	aXML = ""
	aXML += '<?xml version="1.0" encoding="UTF-8"?>'
	aXML += ('<stp:actions xmlns:stp="http://genologics.com/ri/step" uri="' + args[ "stepURI" ] + '">')
	aXML += ('<step rel="steps" uri="' + args[ "stepURI" ] + '"/>')
	aXML += stepConfig
	aXML += '<next-actions>'
		
	aXML += tXML

	aXML += '</next-actions>'
	aXML += '</stp:actions>'

	## update the LIMS
	rXML = api.updateObject( aXML, args[ "stepURI" ] + "/actions" )

#	print(aXML)
	print "ERROR" + rXML

	rDOM = parseString( rXML )
	nodes = rDOM.getElementsByTagName( "next-action" )
	if len(nodes) > 1:
		api.reportScriptStatus( args[ "stepURI" ], "OK", "Set next action successful!" )
	else:
		api.reportScriptStatus( args[ "stepURI" ], "ERROR", "An error occured while trying to set Next Actions to default value:" + rXML )

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

	opts, extraparams = getopt.getopt(sys.argv[1:], "l:u:p:s:a:") 

	for o,p in opts:
		if o == '-l':
			args[ "limsid" ] = p
		elif o == '-u':
			args[ "username" ] = p
		elif o == '-p':
			args[ "password" ] = p
		elif o == '-s':
			args[ "stepURI" ] = p
		elif o == '-a':
			args[ "action" ] = p

	HOSTNAME = getHostname()
	setBASEURI(HOSTNAME)

	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )

	## at this point, we have the parameters the EPP plugin passed, and we have network plumbing
	## so let's get this show on the road!

	routeAnalytes()

if __name__ == "__main__":
	main()
