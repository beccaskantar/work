from __future__ import print_function
import sys
import time
import math
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
TEST = 'string'
RTDB = 'string_val'

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

def createStrAtts(pointType, message, strLength, startByte):
	'''
	Helper function for createStringPoints
	Input:
		pointType		either 'STRI' (string in) or 'STRO' (string out)
		message			message assigned to point
		strLength		length of string
		startByte		byte offset of string
	Return:
		name			point name created using hardware attributes
		atts			attributes used during point initialization
		maps			point mappings used to create mapping records
	'''
	if pointType=='STRI':
		name = 'NET-IO_1_Min_S%ss0n64_Rt8_IN__ctrl0_%s' %(startByte,message)
		atts = {'pointtype':pointType, 'cvttype':'string', 'mappingrecords':name}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'IN', 'startbyte':startByte, 'startbit':'0', 'numbits':'64', \
		 		'rawtype':'string', 'stringlength':strLength, 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	else:
		name = 'NET-IO_1_Mout_S%ss0n64_Rt8_OUT__ctrl0_%s' %(startByte,message)
		atts = {'pointtype':pointType, 'cvttype':'string', 'mappingrecords':name}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'OUT', 'startbyte':startByte, 'startbit':'0', 'numbits':'64', \
		 		'rawtype':'string', 'stringlength':strLength, 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	return [name,atts,maps]


def createMsg(name, pointType, msgId, protocol, src, dest):
	'''
	Helper function for createStringPoints
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
	msg = str.encode('name=%s,type=%s,messageid=%s,protocol=%s,messagelength=30,srcport=%s,destip=127.0.0.1,destport=%s,samplingrate=10,msgflags=0x0000\n' 
						  %(name, pointType, msgId, protocol, src, dest))
	return msg
  
def createStringPoints(strLength, startByte, protocol):
	'''
	Calls the functions createStrAttributes and createMsg to create string points and their NET-IO mappings in the current RTDB.
	Inputs:
		strLength		length of string
		startByte		byte offset of string
		protocol		either 'tcp' or 'udp'
	'''
	r = swb.dbDelete(RTDB)

	r = swb.dbSave(RTDB)
	if r < 0: sys.exit('RTDB create failed: %s\n' %swb.strerror(r))

	r = swb.dbLoad(RTDB)
	if r < 0: sys.exit('RTDB load failed: %s\n' %swb.strerror(r))

	[name1,atts1,maps1] = createStrAtts('STRI', 'in1', strLength, '0')
	[name2,atts2,maps2] = createStrAtts('STRI', 'in1', strLength, startByte)
	[name3,atts3,maps3] = createStrAtts('STRI', 'in1', strLength, str(int(startByte)*2))
	[name4,atts4,maps4] = createStrAtts('STRI', 'in1', strLength, str(int(startByte)*3))
	[name5,atts5,maps5] = createStrAtts('STRI', 'in1', strLength, str(int(startByte)*4))

	[name6,atts6,maps6] = createStrAtts('STRO', 'out1', '0', '0')	
	[name7,atts7,maps7] = createStrAtts('STRO', 'out1', '0', startByte)
	[name8,atts8,maps8] = createStrAtts('STRO', 'out1', '0', str(int(startByte)*2))
	[name9,atts9,maps9] = createStrAtts('STRO', 'out1', '0', str(int(startByte)*3))
	[name10,atts10,maps10] = createStrAtts('STRO', 'out1', '0', str(int(startByte)*4))

	points = {POINT_IN1:atts1, POINT_IN2:atts2, POINT_IN3:atts3, POINT_IN4:atts4, POINT_IN5:atts5,\
			  POINT_OUT1:atts6, POINT_OUT2:atts7, POINT_OUT3:atts8, POINT_OUT4:atts9, POINT_OUT5:atts10}
	r = swb.dbItemPut(points, save=True,)
	if r < 0: sys.exit('Item create failed: %s' %swb.strerror(r))

	iorecs = {name1:maps1, name2:maps2, name3:maps3, name4:maps4, name5:maps5,\
			  name6:maps6, name7:maps7, name8:maps8, name9:maps9, name10:maps10}
	r = swb.putIOMappingRecords(iorecs)
	if r < 0: sys.exit('IO mapping failed: %s' %swb.strerror(r))

	r = swb.dbSave(RTDB)
	if r < 0: sys.exit('RTDB save failed: %s' %swb.strerror(r))
	
	msg = []
	msg.append(createMsg('in1', 'IN', '0', protocol, '1', '1000'))
	msg.append(createMsg('out1', 'OUT', '0', protocol, '1000', '1'))
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
	
	r = swb.sessionCreate(TEST, SESSION, 'New test session', schedType=3, noDataLogging=1)
	if r < 0: sys.exit('Session create failed: %s' %swb.strerror(r))
	 
	r = swb.sessionStart(TEST, SESSION) 
	if r < 0: sys.exit('Session start failed: %s' %swb.strerror(r))


# ---- VALIDATE DATA ----

def validateString(point_in, point_out, new):
	'''
	Compares values of points against each other after test has finished running.
	Input:
		point_in		'IN' point to gather data from
		point_out		'OUT' point to gather data from
		new				value of point_out
	'''
	r, info = swb.getItemValues(point_in)
	outVal = info[point_in]['value']
	outVal = filter(lambda x: x in string.printable, outVal)
		
	if new != outVal:
		print('string validation failed for %s and %s: %s and %s not equal\n' %(point_in, point_out, new, outVal))
		return False
	
	return True


# ---- EXECUTE STRING TEST ----

POINT_IN1 = 'In.point01'
POINT_IN2 = 'In.point03'
POINT_IN3 = 'In.point05'
POINT_IN4 = 'In.point07'
POINT_IN5 = 'In.point09'

POINT_OUT1 = 'Out.point02'
POINT_OUT2 = 'Out.point04'
POINT_OUT3 = 'Out.point06'
POINT_OUT4 = 'Out.point08'
POINT_OUT5 = 'Out.point10'

SESSION = 'test_string'

print('TESTING STRING VALUES...\n')
createStringPoints('3', '4', 'tcp')
time.sleep(1)

startTest(SESSION)
time.sleep(2)

new = ['abc','def','ghi','jkl','mno','pqr','stu']

n = 0
count = 0
index = 0
while(n<10):
	swb.setItemValue(POINT_OUT1, new[index])
	time.sleep(0.3)
	a = validateString(POINT_IN1, POINT_OUT1, new[index])
	if a==False: count += 1
	if count > 5: break
	index += 1
	if index > 6: index = 0

	swb.setItemValue(POINT_OUT2, new[index])
	time.sleep(0.3)
	a = validateString(POINT_IN2, POINT_OUT2, new[index])
	if a==False: count += 1
	if count > 5: break
	index += 1
	if index > 6: index = 0

	swb.setItemValue(POINT_OUT3, new[index])
	time.sleep(0.3)
	a = validateString(POINT_IN3, POINT_OUT3, new[index])
	if a==False: count += 1
	if count > 5: break
	index += 1
	if index > 6: index = 0

	swb.setItemValue(POINT_OUT4, new[index])
	time.sleep(0.3)
	a = validateString(POINT_IN4, POINT_OUT4, new[index])
	if a==False: count += 1
	if count > 5: break
	index += 1
	if index > 6: index = 0

	swb.setItemValue(POINT_OUT5, new[index])
	time.sleep(0.3)
	a = validateString(POINT_IN5, POINT_OUT5, new[index])
	if a==False: count += 1
	if count > 5: break
	index += 1
	if index > 6: index = 0
	
	n += 1

if count==0:
	print('All tests passed\n')
else:
	print('Validation failed: %d tests failed\n' %count)

swb.sessionStop(swbC.SCHED_USERABORT)
print('String testing complete\n')

