import sys
import time
import datetime
import os.path
import math
import numpy as np

try:
	import simwbClient as swb
	import simwbConstants as swbC
	import simwbDLClient as dl
except:
    sys.exit('Import failed')


# ---- DEFINE INPUT ----

PROJECT = 'Rebecca'
HOST = 'localhost'
LOGIN = 'admin/nimda'
TEST = 'val_demo'
SESSION = 'demo1'
RTDB = 'validation'

POINT_IN1 = 'In.point1'
POINT_IN2 = 'In.point3'
POINT_OUT1 = 'Out.point2'
POINT_OUT2 = 'Out.point4'
TOL = 2.3

TIMESTAMP = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H:%M:%S')


# ---- INITIALIZE & START TEST ----

r = swb.connect(HOST)
if r < 0: sys.exit('Connection failed: %s' %swb.strerror(r))

r,p,g= swb.login(LOGIN)
if r < 0: sys.exit('Login failed: %s' %swb.strerror(r))

r = swb.projectSelect(PROJECT)
if r < 0: 
	r = swb.projectCreate(PROJECT)
	if r < 0:	
		sys.exit('Project selection failed: %s' %swb.strerror(r))

r = swb.dbDelete(RTDB)
if r > 0:
    print('RTDB delete: success\n')
else:
    print('RTDB did not delete: %s\n' %swb.strerror(r))

r = swb.dbSave(RTDB)
if r < 0: sys.exit('RTDB create failed: %s' %swb.strerror(r))


# Initialize RTDB

def createAtts(pointType, cvtType, message):
# pointType: either 'AI' or 'AO'
# cvtType: 'packed', 'char', 'short', 'int', 'llong', 'float', 'double', 'string', 'uint', 'uchar', 'ushort' (all have not been tested yet)		C type different from CVT type??
	if pointType=='AI':
		name = 'NET-IO_1_Min_S0s0n64_Rt10_IN__ctrl0_%s' %message
		atts = {'pointtype':pointType, 'cvttype':cvtType, 'mappingrecords':name, 'metaflags':'8'}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'IN', 'startbyte':'0', 'startbit':'0', 'numbits':'64', \
		 		'rawtype':cvtType, 'stringlength':'0', 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	else:
		name = 'NET-IO_1_Mout_S0s0n64_Rt10_OUT__ctrl0_%s' %message
		atts = {'pointtype':pointType, 'cvttype':cvtType, 'mappingrecords':name, 'metaflags':'8'}
		maps = {'boardid':'NET-IO', 'boardnum':'1', 'type':'OUT', 'startbyte':'0', 'startbit':'0', 'numbits':'64', \
		 		'rawtype':cvtType, 'stringlength':'0', 'ioflags':'0x0000', 'controltype':'0', 'message':message}
	return [name,atts,maps]

def createMsg(name, pointType, msgId, protocol, src, dest):
	msg.append(str.encode('name=%s,type=%s,messageid=%s,protocol=%s,messagelength=18,srcport=%s,destip=127.0.0.1,destport=%s,samplingrate=10,msgflags=0x0000\n' 
						  %(name, pointType, msgId, protocol, src, dest)))

msg = []
def createPoints(cvtType, protocol):
	[name1,atts1, maps1] = createAtts('AI', cvtType, 'in1')
	[name2,atts2, maps2] = createAtts('AO', cvtType, 'out1')
	[name3,atts3, maps3] = createAtts('AI', cvtType, 'in2')
	[name4,atts4, maps4] = createAtts('AO', cvtType, 'out2')

	points = {POINT_IN1:atts1, POINT_OUT1:atts2, POINT_IN2:atts3, POINT_OUT2:atts4}
	r = swb.dbItemPut(points, save=True,)
	if r < 0: sys.exit('Item create failed: %s' %swb.strerror(r))

	iorecs = {name1:maps1, name2:maps2, name3:maps3, name4:maps4}
	r = swb.putIOMappingRecords(iorecs)
	if r < 0: sys.exit('IO mapping failed: %s' %swb.strerror(r))

	createMsg('in1', 'IN', '0', protocol, '1', '1000')
	createMsg('out1', 'OUT', '0', protocol, '1000', '1')
	createMsg('in2', 'IN', '1', protocol, '1', '1000')
	createMsg('out2', 'OUT', '1', protocol, '1000', '1')
	r = swb.putFileLines(msg, remoteDir='RTDB/'+RTDB, remoteFile='NET-IO.msgs.1')
	if r < 0: sys.exit('Message transfer failed: %s' %swb.strerror(r))
	
	r = swb.dbSave(RTDB)
	if r < 0: sys.exit('RTDB save failed: %s' %swb.strerror(r))

createPoints('double','tcp')
print('RTDB intialized')
time.sleep(1)


# Initialize test

def startTest():
	r = swb.testDelete(TEST)
	if r > 0:
	    print('Test delete: success\n')
	else:
	    print('Test did not delete\n')

	r = swb.sessionDelete(TEST, SESSION)
	if r > 0:
	    print('Session delete: success\n')
	else:
	    print('Session did not delete\n')

	r = swb.testCreate(TEST, RTDB, 'New test', fixedstep=1000)
	if r < 0: sys.exit('Test create failed: %s' %swb.strerror(r))
	
	r = swb.sessionCreate(TEST, SESSION, 'New test session', schedType=3, noDataLogging=0)
	if r < 0: sys.exit('Session create failed: %s' %swb.strerror(r))
	 
	r = swb.sessionStart(TEST, SESSION) 
	if r < 0: sys.exit('Session start failed: %s' %swb.strerror(r))
	
startTest()
print('Test start successful\n')
time.sleep(1)


# ---- ADD & START GENERATOR ----

def startGenerator(points):
# points is a list of points that will have signal generators attached
	gen1 = swb.addGenerator(points[0], swbC.GEN_SIGGENEND_DURATION, swbC.SIG_TYPE_SINE, 1, 30, 0, 0, 100, 0, 30)
	if gen1 < 0: sys.exit('Signal generator failed: %s' %swb.strerror(gen1))

	gen2 = swb.addGenerator(points[1], swbC.GEN_SIGGENEND_DURATION, swbC.SIG_TYPE_TRIANGLE, 1, 30, 0, 0, 100, 0, 30)
	if gen1 < 0: sys.exit('Signal generator failed: %s' %swb.strerror(gen2))

	r = swb.startAllGenerators()
	if r < 0: sys.exit('Signal generator failed: %s' %swb.strerror(r))

startGenerator([POINT_OUT1,POINT_OUT2])
print('Signal generator started\n')
time.sleep(5)


# ---- VALIDATE DATA (as test is running) ----
'''
l = []
elapsed = 0
t = time.time()
while(elapsed < 10):
	r,info = swb.getItemValues([POINT_IN1, POINT_OUT1])
	out_alt = info[POINT_OUT1]['altvalue']
	in_cvt = info[POINT_IN1]['value']
	diff = math.fabs(out_alt-in_cvt)
	l.append(diff)
	if(diff > TOL):
		sys.exit('Validation failed: difference %0.5r exeeds tolerance %r' %(diff,TOL))
	time.sleep(0.01)
	elapsed = time.time() - t

print('Max difference: '+str(max(l))+'\n')

'''
# ---- VALIDATE DATA (after test is complete) ----

t0 = None
r = swb.sessionStop()
def validate(point_in, point_out):

	r = dl.dlConnect('swb64x16')
	if r != 0: sys.exit('Connection failed: %s' %dl.strerror(r))
	
	r = dl.dlSetProject(PROJECT)
	if r != 0: sys.exit('Project selection failed: %s' %dl.strerror(r))
	
	r = dl.dlSetSession(TEST+'/'+SESSION)
	if r != 0: sys.exit('Test/session selection failed: %s' %dl.strerror(r))
	
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
	r = dl.dlGetRecords(point_in, 1100, dl.dlAllSamples, cb)		#using index number here does not work
	if r != 0: sys.exit('Get records failed: %s' %dl.strerror(r))

	inpoint = False
	r = dl.dlGetRecords(point_out, 1100, dl.dlAllSamples, cb)
	if r != 0: sys.exit('Get records failed: %s' %dl.strerror(r))

	print('')

	diff = np.subtract(cvtVals,altVals)	# can be changed to not include numpy, but this is easier

	for val in diff:
		if math.fabs(val) > TOL:
			sys.exit('Validation of %s and %s failed: difference %0.5r exeeds tolerance %r\n' %(point_in,point_out,math.fabs(val),TOL))

validate(POINT_IN1, POINT_OUT1)
validate(POINT_IN2, POINT_OUT2)


# ---- STOP TEST ----

r = swb.sessionStop(swbC.SCHED_USERABORT)


print('Test complete: all differences within tolerance\n')


# test data types (all), number of messages, variable message length, protocol

