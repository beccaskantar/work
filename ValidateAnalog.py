from __future__ import print_function
import sys
import time
import math
import numpy as np
import string

try:
	import simwbClient as swb
	import simwbConstants as swbC
	import simwbDLClient as dl
except:
    sys.exit('Import failed')

debug = 0	#change to 1 to see test progress


# ---- DEFINE INPUT AND CONNECT TO HOST ----

PROJECT = 'Hardware-Tests'
HOST = 'localhost'
LOGIN = 'admin/nimda'
TEST = 'analog'
RTDB = 'analog_val'

r = swb.connect(HOST)
if r < 0: sys.exit('Connection failed: %s' %swb.strerror(r))

r,p,g= swb.login(LOGIN)
if r < 0: sys.exit('Login failed: %s' %swb.strerror(r))

r = swb.projectSelect(PROJECT)
if r < 0: 
	r = swb.projectCreate(PROJECT)
	if r < 0:	
		sys.exit('Project selection failed: %s' %swb.strerror(r))


# ---- INITIALIZE RTDB ----

def createHWAttributes(pointType, cvtType, message, rawTypeNum, rawType, metaFlags):
	'''
	Helper function for createAnalogPoints
	Input:
		pointType		either 'AI' (analog in) or 'AO' (analog out)
		cvtType			point type specified in initial point creation
		message			message assigned to point 
		rawTypeNum		number based on raw type of point (specified in SimWB Constants)
		rawType			point type specified in point mapping
		metaFlags		RTDB meta flags for the item
	Return:
		name			point name created using hardware attributes
		atts			attributes used during point initialization
		maps			point mappings used to create mapping records
	'''
	if pointType=='AI':
		name = 'NET-IO_1_Min_S0s0n64_Rt%d_IN__ctrl0_%s' %(rawTypeNum,message)
		atts = {'pointtype':pointType, 'cvttype':cvtType, 'mappingrecords':name, 'metaflags':'0x%s'%metaFlags}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'IN', 'startbyte':'0', 'startbit':'0', 'numbits':'64', \
		 		'rawtype':rawType, 'stringlength':'0', 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	else:
		name = 'NET-IO_1_Mout_S0s0n64_Rt%d_OUT__ctrl0_%s' %(rawTypeNum,message)
		atts = {'pointtype':pointType, 'cvttype':cvtType, 'mappingrecords':name, 'metaflags':'0x%s'%metaFlags}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'OUT', 'startbyte':'0', 'startbit':'0', 'numbits':'64', \
		 		'rawtype':rawType, 'stringlength':'0', 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	return [name,atts,maps]

def createMsg(name, pointType, msgId, protocol, src, dest):
	'''
	Helper function for createAnalogPoints
	Input:
		name			name of message
		pointType		either 'IN' or 'OUT'
		msgId			ID number associated with message
		protocol		either 'tcp' or 'udp'
		src				source port number
		dest			destination port number
	Return:
		msg				new line of message with information to be added to file NET-IO.msgs.1
	'''
	msg = str.encode('name=%s,type=%s,messageid=%s,protocol=%s,messagelength=18,srcport=%s,destip=127.0.0.1,destport=%s,samplingrate=10,msgflags=0x0000\n' 
						  %(name, pointType, msgId, protocol, src, dest))
	return msg
  
def createAnalogPoints(cvtType, rawType, rawTypeNum, protocol, metaFlags):
	'''
	Calls the functions createHWAttributes and createMsg to create analog points and their NET-IO mappings in the current RTDB.
	Inputs:
		cvtType			point type specified in initial point creation
		rawType			point type specified in point mapping
		rawTypeNum		number based on raw type of point (specified in SimWB Constants)
		protocol		either 'tcp' or 'udp'
		metaFlags		RTDB meta flags for the item
	'''
	r = swb.dbDelete(RTDB)

	r = swb.dbSave(RTDB)
	if r < 0: sys.exit('RTDB create failed: %s\n' %swb.strerror(r))

	r = swb.dbLoad(RTDB)
	if r < 0: sys.exit('RTDB load failed: %s\n' %swb.strerror(r))

	[name1,atts1, maps1] = createHWAttributes('AI', cvtType, 'in1', rawTypeNum, rawType, metaFlags)
	[name2,atts2, maps2] = createHWAttributes('AO', cvtType, 'out1', rawTypeNum, rawType, metaFlags)
	[name3,atts3, maps3] = createHWAttributes('AI', cvtType, 'in2', rawTypeNum, rawType, metaFlags)
	[name4,atts4, maps4] = createHWAttributes('AO', cvtType, 'out2', rawTypeNum, rawType, metaFlags)

	points = {POINT_IN1:atts1, POINT_OUT1:atts2, POINT_IN2:atts3, POINT_OUT2:atts4}
	r = swb.dbItemPut(points, save=True,)
	if r < 0: sys.exit('Item create failed: %s' %swb.strerror(r))

	iorecs = {name1:maps1, name2:maps2, name3:maps3, name4:maps4}
	r = swb.putIOMappingRecords(iorecs)
	if r < 0: sys.exit('IO mapping failed: %s' %swb.strerror(r))

	r = swb.dbSave(RTDB)
	if r < 0: sys.exit('RTDB save failed: %s' %swb.strerror(r))
	
	msg = []
	msg.append(createMsg('in1', 'IN', '0', protocol, '1', '1000'))
	msg.append(createMsg('out1', 'OUT', '0', protocol, '1000', '1'))
	msg.append(createMsg('in2', 'IN', '1', protocol, '1', '1000'))
	msg.append(createMsg('out2', 'OUT', '1', protocol, '1000', '1'))
	r = swb.putFileLines(msg, remoteDir='RTDB/'+RTDB, remoteFile='NET-IO.msgs.1')
	if r < 0: sys.exit('Message transfer failed: %s' %swb.strerror(r))


# ---- INITIALIZE TEST ----

def startTest(SESSION):
	'''
	Deletes old test (if available), then creates new test and session and starts running the session.
	'''
	r = swb.testDelete(TEST)

	r = swb.testCreate(TEST, RTDB, 'New test', fixedstep=1000)
	if r < 0: sys.exit('Test create failed: %s' %swb.strerror(r))
	
	r = swb.sessionCreate(TEST, SESSION, 'New test session', schedType=3)
	if r < 0: sys.exit('Session create failed: %s' %swb.strerror(r))
	 
	r = swb.sessionStart(TEST, SESSION) 
	if r < 0: sys.exit('Session start failed: %s' %swb.strerror(r))


# ---- ADD & START GENERATOR ----

def startGenerator(points, offset):
	'''
	Starts signal generator(s) for specified point(s).
	Input:
		points			list of points that will have signal generators attached
	'''	
	gen1 = swb.addGenerator(points[0], swbC.GEN_SIGGENEND_DURATION, swbC.SIG_TYPE_SINE, 1, 30, 0, offset, 100, 0, 30)
	if gen1 < 0: sys.exit('Signal generator failed: %s' %swb.strerror(gen1))

	gen2 = swb.addGenerator(points[1], swbC.GEN_SIGGENEND_DURATION, swbC.SIG_TYPE_TRIANGLE, 1, 30, 0, offset, 100, 0, 30)
	if gen1 < 0: sys.exit('Signal generator failed: %s' %swb.strerror(gen2))

	r = swb.startAllGenerators()
	if r < 0: sys.exit('Signal generator failed: %s' %swb.strerror(r))


# ---- VALIDATE DATA (as test is running) ----

def validateConstants(point_in, point_out, val):
	r, info = swb.getItemValues(point_in)
	outVal = info[point_in]['value']

	if val!=outVal:
		print('%s constant validation failed for %s and %s: %s and %s not equal\n' %(CVTTYPE, point_in, point_out, val, outVal))


# ---- VALIDATE DATA (after test is complete) ----

t0 = None
def validate(point_in, point_out):
	'''
	Compares values of points against each other after test has finished running.
	Input:
		point_in		'IN' point to gather data from
		point_out		'OUT' point to gather data from
	'''
	swb.sessionStop()

	r = dl.dlConnect('localhost')
	if r != 0: sys.exit('DL Connection failed: %s' %dl.strerror(r))
	
	r = dl.dlSetProject(PROJECT)
	if r != 0: sys.exit('DL Project selection failed: %s' %dl.strerror(r))
	
	r = dl.dlSetSession(TEST+'/'+SESSION)
	if r != 0: sys.exit('DL Test/session selection failed: %s' %dl.strerror(r))
	
	r,info = dl.dlQueryTest()
	if r != 0: sys.exit('Test query failed: %s' %dl.strerror(r))

	r,d = dl.dlGetMetaTable()
	if r < 0: sys.exit('Meta table failed: %s' %dl.strerror(r))

	cvtVals = []
	altVals = []
	def cb(recNum, tSec, tNSec, cvtVal, altVal, rawVal, dlF, rtF):
		global t0
		t = float(tSec)+float(tNSec)/1000000000.
		if not t0: t0 = t
		if inpoint:
			cvtVals.append(cvtVal)
		else:
			altVals.append(altVal)
	
	inpoint = True
	r = dl.dlGetRecords(point_in, 1100, dl.dlAllSamples, cb)
	if r != 0: sys.exit('Get records failed: %s' %dl.strerror(r))

	inpoint = False
	r = dl.dlGetRecords(point_out, 1100, dl.dlAllSamples, cb)
	if r != 0: sys.exit('Get records failed: %s' %dl.strerror(r))

	diff = np.subtract(cvtVals,altVals)
	for val in diff:
		if math.fabs(val) > TOL:
			print('%s validation failed: difference between %s and %s %0.2e exeeds tolerance %d\n' %(CVTTYPE,point_in,point_out,math.fabs(val),TOL))
			return
	if debug:
		print('%s test passed for %s and %s\n' %(CVTTYPE,point_in,point_out))


# ---- EXECUTE ANALOG TEST ----

POINT_IN1 = 'In.point1'
POINT_IN2 = 'In.point3'
POINT_OUT1 = 'Out.point2'
POINT_OUT2 = 'Out.point4'
TOL = 3

# Test using signal generators:
cvtTypes = ['char', 'short', 'int', 'llong', 'float', 'double', 'uint', 'uchar', 'ushort'] 		#type specified in point creation
rawTypes = ['char', 'short', 'int', 'llong', 'float', 'double', 'llong', 'short', 'int']		#type specified in mapping
protocols = ['tcp', 'udp']

print('TESTING SIGNAL GENERATOR VALUES...\n')
global CVTTYPE
global RAWTYPE
global SESSION
for RAWTYPE,CVTTYPE in zip(rawTypes,cvtTypes):
	for PROTOCOL in protocols:
		SESSION = 'test_%s' %CVTTYPE
		attr = 'RAWTYPE_%s' %RAWTYPE
		rawVal = getattr(swbC, attr)
		
		if RAWTYPE=='int':
			metaFlags = '48'
		else:
			metaFlags = '8'

		if debug:
			print('Starting %s %s test...' %(CVTTYPE,PROTOCOL))

		createAnalogPoints(CVTTYPE,RAWTYPE,rawVal,PROTOCOL,metaFlags)
		time.sleep(1)

		startTest(SESSION)
		time.sleep(1)
		
		if (CVTTYPE[0]=='u') | (CVTTYPE=='llong'):
			startGenerator([POINT_OUT1,POINT_OUT2],100)
		else:
			startGenerator([POINT_OUT1,POINT_OUT2],0)
		time.sleep(2)

		validate(POINT_IN1, POINT_OUT1)
		validate(POINT_IN2, POINT_OUT2)
		
		swb.sessionDelete(TEST, SESSION)

swb.sessionStop(swbC.SCHED_USERABORT)

print('Signal generator test complete\n')


# Test using constants:
index = 0
testVals = [-128,0,127,-32768,0,32767,-2.1e9,0,2.1e9,0,9e5,9e10,-1.1e38,0,1.1e38,-1.7e308,0,1.7e308,\
			0,1e4,4.2e9,0,128,255,0,32767,65535] #Each group of three values corresponds respectively to a CVTTYPE

print('TESTING CONSTANT VALUES...\n')
count = 1
for RAWTYPE,CVTTYPE in zip(rawTypes,cvtTypes):

	SESSION = 'test_'+CVTTYPE
	attr = 'RAWTYPE_%s' %RAWTYPE
	rawVal = getattr(swbC, attr)
	
	if RAWTYPE=='int':
		metaFlags = '48'
	else:
		metaFlags = '8'

	while count<4:
		createAnalogPoints(CVTTYPE,RAWTYPE,rawVal,'tcp',metaFlags)
		time.sleep(1)
		startTest(SESSION)
		time.sleep(1)
		swb.setItemValue(POINT_OUT1, testVals[index])
		time.sleep(1)
		validateConstants(POINT_IN1, POINT_OUT1, testVals[index])
		swb.sessionStop()
		index += 1
		count += 1
	count = 1
	
	if debug:
		print('%s constant testing complete\n' %CVTTYPE)
	swb.sessionDelete(TEST, 'test_'+CVTTYPE)

print('Constant test complete\n')

print('Analog testing complete\n')

