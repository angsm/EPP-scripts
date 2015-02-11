###############################################
##SCRIPT BY  :  Ang Shimin
##CREATED    :  3 Oct 2014
##INPUT      :
##DESCRIPTION : This code retrieves attributes of samples, working solutions and controls from the server, triplicates them and
##              determines the new well plate positions ignoring their original postion. Triplicated working solutions and
##              controls are place in the first 3 rows and in a downwards fashion. Artifacts are also placed in a similar fashion.
##D_VERSION:	2.3.1 getContainer uses xml attributes
##		2.3.2 get hostname added
##		2.4 fixed artifact placement not in order
##		2.4_Kapa customised for Kapa step, inserts dilution name behind		
##		2.4.1 Extract insertDilutionName function into a seperate script
##		2.4.1_Kapa Customized for Kapa step where dilution buffer is places from row G in triplicates instead of 6x
##		2.4.2_Kapa Removed excess coding and fixed out of list error due to heterogenous replication
##		2.4.3_Kapa Search for controls instead of DIlution Buffer specifically
##		2.5.0_Kapa accepts param -a aAlphabet -c aCutOff -w aOffset to allow more customization
##		2.6.0 Added function to enable checking if its a clinical sample and sort artifact by its 5 portions starting ##		      for the first portion (i.e XXX-00-XX-0000), added optional parameters to controls as well. 
##			using --cOffset --cCutOff --cAlphabet --aOffset --aCutOff --aAlphabet
##P_VERSION:	1.0.0
###############################################

from collections import defaultdict
import socket
import sys
import getopt
import xml.dom.minidom
import glsapiutil
from xml.dom.minidom import parseString
import pdb
import re

##HOSTNAME = 'http://dlap73v.gis.a-star.edu.sg:8080'
##HOSTNAME = 'http://192.168.8.10:8080'
VERSION = "v2"
BASE_URI = ""

DEBUG = False
api = None

ARTIFACTS = {}
CACHE_IDS = []
I2OMap = {} # A mapping of inputs to their outputs

## control WP static variables
conPOSITIONS = []
conPOSITIONS_idx = 0
conLoopCount = 0
conCutOff = 0
conOffset = 0

## artifact WP static variables
wellArr = []
artLoopCount = 0
wellArr_idx = 0
artOffset = 0
artCutOff = 0

## artifact array variables
iWPArr = []
limsidArr_clinical = []
limsidArr_test = []
nameDict = {}

## highest replication number for artifact and control
artRepNum = 0
conRepNum = 0

def getStepConfiguration( ):

        response = ""

        if len( args[ "stepURI" ] ) > 0:
                stepXML = api.getResourceByURI( args[ "stepURI" ] )
                stepDOM = parseString( stepXML )
                nodes = stepDOM.getElementsByTagName( "configuration" )
                if nodes:
                        response = nodes[0].toxml()
        return response

def cacheArtifact( limsid ):

        global CACHE_IDS

        if limsid not in CACHE_IDS:
                CACHE_IDS.append( limsid )

def prepareCache():

        global ARTIFACTS

        lXML = '<ri:links xmlns:ri="http://genologics.com/ri">'

        for limsid in CACHE_IDS:
                link = '<link uri="' + BASE_URI + 'artifacts/' + limsid + '" rel="artifacts"/>'
                lXML += link
        lXML += '</ri:links>'

        mXML = api.getBatchResourceByURI( BASE_URI + "artifacts/batch/retrieve", lXML )
        mDOM = parseString( mXML )
        nodes = mDOM.getElementsByTagName( "art:artifact" )
        for artifact in nodes:
                aLUID = artifact.getAttribute( "limsid" )
                ARTIFACTS[ aLUID ] = artifact

def getArtifact( limsid ):

        response = ARTIFACTS[ limsid ]
        return response

def createContainer( type, name ):
	
	## cType changes on server shift. Please check containerTypes xml
        response = ""

        if type == '96':
                cType = '1'
                cTypeName = "96 well plate"
        elif type == '384':
                cType = '3'
                cTypeName = "384 well plate"
	elif type == '384K':
                cType = '154'
                cTypeName = "384 Well Kapa Plate"

        xml ='<?xml version="1.0" encoding="UTF-8"?>'
        xml += '<con:container xmlns:con="http://genologics.com/ri/container">'
        xml += '<name>' + name + '</name>'
        xml += '<type uri="' + BASE_URI + 'containertypes/' + cType + '" name="' + cTypeName + '"/>'
        xml += '</con:container>'

        response = api.createObject( xml, BASE_URI + "containers" )

        rDOM = parseString( response )
        Nodes = rDOM.getElementsByTagName( "con:container" )
        if Nodes:
                temp = Nodes[0].getAttribute( "limsid" )
                response = temp

        return response, cTypeName

def recursiveMinus( recVal, minusVal ):

	##Recursive function to check and subtract value til it fits the condition of cutoff
	if recVal > minusVal:
		        recVal = recVal - minusVal
			return recursiveMinus( recVal, minusVal )	
		
	else:
		return recVal
	

def getNewWP(replicateType, containerName ):
 
        global wellArr
	global wellArr_idx
	global artCutOff
	global artOffset	
	global artLoopCount    	
	 
	if artLoopCount == 0:
		## OPTIONAL PARAMETERS
		## used only when present in parameter, if replication number does not rep # of sample in each row
       		if "artCutOff" in args.keys():
			artCutOff = int(args[ "artCutOff" ])
		else:
			artCutOff = artRepNum

		## OPTIONAL or set by optional parameters
	        if "artAlphabet" in args.keys():
    	         	artStart = int(args[ "artAlphabet" ])
    	                if containerName == "96 well plate":
    	                 	artEnd = 72 + 1
    	                else:
    	                 	artEnd = 80 + 1
     
                    	artCount = artEnd - artStart
		else:
			artStart = 65
			if containerName == "96 well plate":
                        	artCount = 8
                        else:
                                artCount = 16

                for i in range (0, artCount):
                	wellArr.append(chr(artStart+i))

		## offset right from column	
		if "artOffset" in args.keys():
			artOffset = int(args[ "artOffset" ])
		else:
			artOffset = 3

	## generates well plate number for artifact
        if(artLoopCount % artCutOff == 0) and (not artLoopCount == 0):
                wellArr_idx += 1
		
		## when placement position have exceed the last row on plate
		if wellArr_idx >= len(wellArr):
			artStart = 65
                        if containerName == "96 well plate": 
                                artCount = 8
                        else:   
                                artCount = 16

			wellArr = []
			## reassign row alphabets from A to last row of plate	
			for i in range (0, artCount):
                        	wellArr.insert(i, chr(artStart+i))
				
			wellArr_idx = 0
			artOffset += artCutOff			
	
        ## always make sure placement is always in the first n rows
        if(replicateType > artCutOff):
                replicateType = recursiveMinus(replicateType, artCutOff)
	
        alpha =  wellArr[ wellArr_idx ]
	## return well number i.e. A:1
        response = alpha +  ":" + str(replicateType + artOffset)

	artLoopCount += 1
        #print(response)
        return response

def getWS_WP( replicateType, containerName ):
	
	global conPOSITIONS
	global conPOSITIONS_idx
	global conLoopCount
	global conCutOff
	global conOffset
	
	## set variables on first loop	
	if conLoopCount == 0:
		## default values or set by optional parameters 
	        if "conAlphabet" in args.keys():
        	        conStart = int(args[ "conAlphabet" ])
                	if containerName == "96 well plate":
                       		conEnd = 72 + 1
                	else:
                        	conEnd = 80 + 1


	                conCount = conEnd - conStart
			
        	        for i in range (0, conCount):
                	        conPOSITIONS.append(chr(conStart+i))
	        else:  
        	        conPOSITIONS = [ 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P' ]

	        if "conCutOff" in args.keys():
        	        conCutOff = int(args[ "conCutOff" ])
				
	        else:
        	        conCutOff = conRepNum

	        if "conOffset" in args.keys():
        	        conOffset = int(args[ "conOffset" ])
	        else:
        	        conOffset = 0

	## generates well plate number for controls
	if(conLoopCount % conCutOff == 0) and (not conLoopCount == 0):
                conPOSITIONS_idx += 1

		## when placement position have exceed the last row on plate
                if conPOSITIONS_idx >= len(conPOSITIONS):
                        conStart = 65
                        if containerName == "96 well plate":
                                conCount = 8
                        else:
                                conCount = 16

			conPOSITIONS = []
			## reassign row alphabets from A to last row of plate
                        for i in range (0, conCount):
                                conPOSITIONS.append(chr(conStart+i))

                        conPOSITIONS_idx = 0	
                        conOffset += conCutOff
				
	## always make sure placement is always in the first n rows
	if(replicateType > conCutOff):
		replicateType = recursiveMinus(replicateType, conCutOff)
	
        alpha = conPOSITIONS[ conPOSITIONS_idx ]
       	WP = alpha + ":" + str( replicateType + conOffset )
	
	conLoopCount += 1
	#print WP
	return WP

def getRepCount():

	global artRepNum
	global conRepNum	

        count = 0
        for key in I2OMap:
                outs = I2OMap[ key ]

                for output in outs:
                        oDOM = getArtifact( output )
                        Nodes = oDOM.getElementsByTagName( "name" )
                        oName = api.getInnerXml( Nodes[0].toxml(), "name" )
			
			## get control tag and determine if artifact is control
                        ctrlNode = oDOM.getElementsByTagName( "control-type" )
			
			## determine replicateNumber by replicate number appended behind artifact name by LIMS
                        words = re.search("[a-zA-Z]+\_(\d{1,2})", oName)
                        newRepNum = int(words.group(1))

			## get number of replications from label on result files
			if (len(ctrlNode) == 0):
				## find the replication number set by the user by checking for number in artifact name
				if artRepNum < newRepNum:
					artRepNum = newRepNum
			else:
				## find the replication number set by the user by checking for number in control name
				if conRepNum < newRepNum:
					conRepNum = newRepNum
	

def make_dict():
    	return defaultdict(make_dict)
        
def sortClinical():
	global limsidArr_clinical
	
	## Clinical Arr
	sampleDict = defaultdict(make_dict)

	for i in range(0, len(limsidArr_clinical)):
		## gather sample information
		sampleNamePtr = re.search("\s?([A-Z]{1,3})\s?[-_]\s?(\d{1,2})\s?[-_]\s?([A-Z]{1,2})\s?[-_]\s?(\d{1,5})", nameDict[limsidArr_clinical[i]])
		## search for sample origin
		sampleOri = sampleNamePtr.group(1)
		## search for sample year
		sampleYr = sampleNamePtr.group(2)
		## search for sample type
		sampleType = sampleNamePtr.group(3)		
		## search for last 5 digits on sample name
                sampleNum = sampleNamePtr.group(4)

		## search for _1, _2 ... _n
		sampleRepPtr = re.search("[a-zA-Z]+\_(\d{1,2})", nameDict[limsidArr_clinical[i]])
                sampleRep = sampleRepPtr.group(1)

		## place in values
		sampleDict[sampleOri][sampleYr][sampleType][sampleNum][sampleRep] = limsidArr_clinical[i]

#	print("LEN: " + str(len(sampleDict)))
#	for key in sorted(sampleDict):
#		print key
#		for key1 in sorted(sampleDict[key]):
#			print key1
#			print sampleDict[key][key1]

	return sampleDict

def sortTest():
        global iWPArr
        global limsidArr_test
        sortCount = 0
      
	## Non-clinical Arr
        testDict = defaultdict(list)
 
	## in range of number of artifacts, convert letter to digit and sum it with digit value 
	for i in range(0, len(iWPArr)):
                tokens = iWPArr[i].split(":")
                iLetter = tokens[0]
                iDigit = int(tokens[1])
		
		## multipled by 25 to clearly distingush artifacts from each letter
                asciiVal = iDigit + ((ord(iLetter) % 65) * 25)
		 
		testDict[asciiVal].append(limsidArr_test[i])

#       print("LEN: " + str(len(d)))
#       for key in sorted(d):
#               print key, ':',d[key]

	return testDict

def autoPlace():

        global I2OMap
	global bufferPOSITIONS	
	
	bufferRepNum = 1
        wsCountNum = 0

        containerType, containerName = createContainer( '384K', '384 Kapa WP' )

        ## step one: get the process XML
        pURI = BASE_URI + "processes/" + args[ "limsid" ]
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

                        limsid = output[0].getAttribute( "limsid" )
                        cacheArtifact( limsid )
                        nodes = IOMap.getElementsByTagName( "input" )
                        iLimsid = nodes[0].getAttribute( "limsid" )
                        cacheArtifact( iLimsid )

                        ## create a map entry
                        if not iLimsid in I2OMap.keys():
                                I2OMap[ iLimsid ] = []
                        temp = I2OMap[ iLimsid ]
                        temp.append( limsid )
                        I2OMap[ iLimsid ] = temp


        ## build our cache of Analytes
        prepareCache()

        pXML = '<?xml version="1.0" encoding="UTF-8"?>'
        pXML += ( '<stp:placements xmlns:stp="http://genologics.com/ri/step" uri="' + args[ "stepURI" ] +  '/placements">' )
        pXML += ( '<step uri="' + args[ "stepURI" ] + '"/>' )
        pXML += getStepConfiguration()
        pXML += '<selected-containers>'
        pXML += ( '<container uri="' + BASE_URI + 'containers/' + containerType + '"/>' )
        pXML += '</selected-containers><output-placements>'
	
	## get user selected replication number
        getRepCount()

        ## let's process our cache, one input at a time, but ignore some control samples
        for key in I2OMap:

        	## get the well position for the input
                iDOM = getArtifact( key )
                nodes = iDOM.getElementsByTagName( "value" )
                iWP = api.getInnerXml( nodes[0].toxml(), "value" )
                ## well placement should always contain a :
                if iWP.find( ":" ) == -1:
                        print( "WARN: Unable to determine well placement for artifact " + key )
                        break

                outs = I2OMap[ key ]
                if DEBUG: print( key + str(outs) )
                for output in outs:
                	oDOM = getArtifact( output )
                        oURI = oDOM.getAttribute( "uri" )
                        Nodes = oDOM.getElementsByTagName( "name" )
                        oName = api.getInnerXml( Nodes[0].toxml(), "name" )
                        if DEBUG: print oName

			## get control tag and determine if artifact is control
                        ctrlNode = oDOM.getElementsByTagName( "control-type" )

                        WP = ""

			## determine replicateNumber by replicate number appended behind artifact name by LIMS
               		words = re.search("[a-zA-Z]+\_(\d{1,2})", oName)
                	replicateType = int(words.group(1))			
	
                        ## are we dealing with control samples?
                        if (len(ctrlNode) > 0):
				WP = getWS_WP( replicateType, containerName )
						
			else:
				## check if its a clinical sample, with pattern XXX-00-XX-00000 
				## (non-clinical samples will be placed below clinical according to well number in input plate
				isClinical = re.match("\s?([A-Z]{1,3})\s?[-_]\s?(\d{1,2})\s?[-_]\s?([A-Z]{1,2})\s?[-_]\s?(\d{1,5})",oName)
				if not isClinical:
					iWPArr.append(iWP)
					limsidArr_test.append(output)

				else:
					limsidArr_clinical.append(output)
				
				nameDict[output] = oName

			if DEBUG: print( oName, WP )

                        if WP != "":
				plXML = '<output-placement uri="' + oURI + '">'
                                plXML += ( '<location><container uri="' + BASE_URI + 'containers/' + containerType + '" limsid="' + containerType + '"/>' )
                                plXML += ( '<value>' + WP + '</value></location></output-placement>' )

                                pXML += plXML

	## place samples after sorting it so that the input would be in order
	##test pattern to check if its clinical sample standard name => NCC-14-GI
	sortedLimsid = []
        if len(limsidArr_clinical) > 0:
		## sort clincal samples
		sortDict = sortClinical()

		for key in sorted(sortDict.iterkeys()):
			for key2 in sorted(sortDict[key].iterkeys()):
				for key3 in sorted(sortDict[key][key2].iterkeys()):
					for key4 in sorted(sortDict[key][key2][key3].iterkeys()):
						for key5 in sorted(sortDict[key][key2][key3][key4].iterkeys()):
							sortedLimsid.append(sortDict[key][key2][key3][key4][key5])
	if len(limsidArr_test) > 0:
		## sort test samples and append limsid at the back of sortedLimsid arr
		sortDict = sortTest()

		for key in sorted(sortDict):
			for i in range(0, len(sortDict[key])):
				sortedLimsid.append(sortDict[key][i])

	## iterate through sorted limsid arr and get artifact for processing	
	for limsid in sortedLimsid:	
		WP = ""
		
		## get artifact uri	
		oDOM = getArtifact(limsid)
		oURI = oDOM.getAttribute("uri")
		
		## determine replicateNumber by replicate number appended behind artifact name by LIMS	
		words = re.search("[a-zA-Z]+\_(\d{1,2})", nameDict[limsid])
		replicateType = int(words.group(1))
		
		WP = getNewWP( replicateType, containerName )
		#print WP
		if WP != "":
                       	plXML = '<output-placement uri="' + oURI + '">'
                        plXML += ( '<location><container uri="' + BASE_URI + 'containers/' + containerType + '" limsid="' + containerType + '"/>' )
                        plXML += ( '<value>' + WP + '</value></location></output-placement>' )

                        pXML += plXML

	pXML += '</output-placements></stp:placements>'
	#print pXML
        rXML = api.createObject( pXML, args[ "stepURI" ] + "/placements" )
        rDOM = parseString( rXML )
	#print rXML
        nodes = rDOM.getElementsByTagName( "output-placement" )
		
        if nodes:
        	msg = "Auto-placement of replicates occurred successfully"
                api.reportScriptStatus( args[ "stepURI" ], "OK", msg )
        else:
                msg = "An error occurred trying to auto-place these replicates"
                msg = msg + rXML
                #print msg
                api.reportScriptStatus( args[ "stepURI" ], "WARN", msg )

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

        opts, extraparams = getopt.getopt(sys.argv[1:], "l:u:p:s:", ["aCutOff=","aAlphabet=","aOffset=","cCutOff=","cAlphabet=","cOffset="])

        for o,p in opts:
                if o == '-l':
                        args[ "limsid" ] = p
                elif o == '-u':
                        args[ "username" ] = p
                elif o == '-p':
                        args[ "password" ] = p
                elif o == '-s':
                        args[ "stepURI" ] = p
		
		## optional samples parameters, cutoff can only be numbers that can equally divided portions
		elif o == '--aCutOff':
			args[ "artCutOff" ] = p
		elif o == '--aAlphabet':
			args[ "artAlphabet" ] = p
		elif o == '--aOffset':
			args[ "artOffset" ] = p
		
		## optional control parameters
		elif o == '--cCutOff':
			args[ "conCutOff" ] = p
		elif o == '--cAlphabet':
			args[ "conAlphabet" ] = p
		elif o == '--cOffset':
			args[ "conOffset" ] = p
		
	hostname = getHostname()	
	setBASEURI(hostname)

        api = glsapiutil.glsapiutil()
        api.setHostname( hostname )
        api.setVersion( VERSION )
        api.setup( args[ "username" ], args[ "password" ] )
	
        ## at this point, we have the parameters the EPP plugin passed, and we have network plumbing
        ## so let's get this show on the road!

        autoPlace()

if __name__ == "__main__":
        main()

