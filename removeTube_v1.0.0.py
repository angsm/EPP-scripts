#############################################
##SCRIPT BY  :  
##CREATED    :  04 Nov 2014
##INPUT      :
##DESCRIPTION : This script removes tube 1 from workflow by setting next action as remove and tube 2 to next step
##D_VERSION    :  1.0.0
##P_VERSION    : 1.0.0
##############################################
import sys
import getopt
import xml.dom.minidom
import re
import glsapiutil
from xml.dom.minidom import parseString
import socket

HOSTNAME = 'http://plap19v.gis.a-star.edu.sg:8080'
VERSION = "v2"

BASE_URI = HOSTNAME + '/api/' + VERSION + '/'

DEBUG = False
api = None

def getNextActionURI( cfXML ):

	response = ""

	if len( cfXML ) > 0:
		DOM = parseString( cfXML )
		nodes = DOM.getElementsByTagName( "configuration" )
		if len(nodes) > 0:
			cfURI = nodes[0].getAttribute( "uri" )
			stXML = api.getResourceByURI( cfURI )
			stDOM = parseString( stXML )
			nodes = stDOM.getElementsByTagName( "transition" )
			if nodes:
				naURI = nodes[0].getAttribute( "next-step-uri" )
				response = naURI

	return response

def checkTubeName( artURI ):
    	gXML = api.getResourceByURI( artURI )
    	gDOM = parseString( gXML )

	artifact = gDOM.getElementsByTagName( "art:artifact" )
	nameTag = artifact[0].getElementsByTagName( "name" )
	name = api.getInnerXml( nameTag[0].toxml(), "name" )

	if name.find( "_1" ) > -1:
	    return 0
	elif name.find( "_2" ) > -1:
	    return 1

def routeAnalytes():

	## Step 1: Get the XML relating to the actions resource for this step
	aURI = args[ "stepURI" ] + "/actions"
	aXML = api.getResourceByURI( aURI )
	aDOM = parseString( aXML )

	## Step 2: Get the URI for the next-step, and select an action
	## if we weren't given a -a flag, use the default next action for this step
	nsURI = ""
	nsURI = getNextActionURI( aXML )

	## Step 3: Hone in on the next-action nodes, as these will be the ones we update
	nodes = aDOM.getElementsByTagName( "next-action" )
	for node in nodes:
		
	    	## check artifact name
		artURI = node.getAttribute( "artifact-uri" )
	    	nameFlag = checkTubeName( artURI )

		if "action" in args.keys():
		    action = args[ "action" ]
		elif nameFlag == 0:
		    action = "remove"
		elif nameFlag == 1:
		    action = "nextstep"
		else:
		    action = "unknown"
		
		## set action attribute to node
		node.setAttribute( "action", action )
		## set step-uri attribute only when action is nextstep
		if action.find( "nextstep" ) > -1 :
			node.setAttribute( "step-uri", nsURI )
		
	## Step 4: update the LIMS
	rXML = api.updateObject( aDOM.toxml(), args[ "stepURI" ] + "/actions" )
	print rXML
	try:
		rDOM = parseString( rXML )
		nodes = rDOM.getElementsByTagName( "next-action" )
		if len(nodes) > 1:
			##api.reportScriptStatus( args[ "stepURI" ], "OK", "set Next Actions to default value" )
			pass
		else:
			api.reportScriptStatus( args[ "stepURI" ], "ERROR", "An error occured while trying to set Next Actions to default value:" + rXML )
	except:
		api.reportScriptStatus( args[ "stepURI" ], "ERROR", "An error occured while trying to set Next Actions to default value:" + rXML )

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


	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( VERSION )
	api.setup( args[ "username" ], args[ "password" ] )
	
	## at this point, we have the parameters the EPP plugin passed, and we have network plumbing
	## so let's get this show on the road!

	routeAnalytes()

if __name__ == "__main__":
	main()
