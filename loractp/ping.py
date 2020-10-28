# MicroPython

import time
import ujson
import math
import ucrypto
import loractp

def random_in_range(l=0,h=1000):
    r1 = ucrypto.getrandbits(32)
    r2 = ((r1[0]<<24)+(r1[1]<<16)+(r1[2]<<8)+r1[3])/4294967295.0
    return math.floor(r2*h+l)

ctpc = loractp.CTPendpoint()

myaddr, rcvraddr, quality, result = ctpc.connect()
if (result == 0):
	print("ping.py: connected to {} (myaddr = {}, quality {})".format(rcvraddr, myaddr, quality))
else:
	print("ping.py: failed connection to {} (myaddr = {}, quality {})".format(rcvraddr, myaddr, quality))

time.sleep(1)

while True:

	t0 = time.time()
	tbs_ = {"type": "PING", "value": random_in_range(), "time": time.time()}
	tbsj = ujson.dumps(tbs_)
	tbsb = str.encode(tbsj)
	print('--->ping.py: sending ', tbsb)
	try:
		addr, quality, result = ctpc.sendit(rcvraddr, tbsb)
		print("ping.py: ACK from {} (quality = {}, result {})".format(addr, quality, result))
	except Exception as e:
		print ("ping.py: EXCEPTION when sending -> ", e)
		break

	print('ping.py: waiting pong from: ', rcvraddr)
	try:
		rcvd_data, addr = ctpc.recvit(rcvraddr)
		print("ping.py: pong {} from {}".format(rcvd_data, addr))
	except Exception as e:
		print ("ping.py: EXCEPTION when receiving ->", e)
		break
	t1 = time.time()
	print ("ping.py: elapsed time = ", t1-t0)


	if input("Q to exit: ") == "Q": break