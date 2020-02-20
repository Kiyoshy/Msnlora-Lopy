import socket
import json
import time
import ufun

from pysense import Pysense
from LTR329ALS01 import LTR329ALS01     # Digital Ambient Light Sensor
from raw2lux import raw2Lux             # ... additional library for the light sensor

TCP_IP = '192.168.4.1'
TCP_PORT = 80
WIFI_SSID = "messenger_e57"

BUFFER_SIZE = 1024

DEV_ID = "sensor1"
QOS = 0
TOPIC = "sensor/value"

def send_it(m):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((TCP_IP, TCP_PORT))
	s.send(m)
	# simply discarding the response... for the moment
	dl = []
	while 1:
		d = s.recv(BUFFER_SIZE)
		dl.append(d)
		if not d: break
	s.close()
	dd = b''.join(dl)
	r = dd.decode()
	response = r.split('\n')[0]
	if response == "HTTP/1.1 200 OK":
	    print("Got: "+response)
	else:
	    print("ERROR Got: "+response)


def get_sdata(lite_s):

    v = raw2Lux(lite_s.light())
    print("Light (raw2lux): " + str(v))
    
    return int(v)

ufun.connect_to_wifi(WIFI_SSID, "")


# Enabling PySense boards
py = Pysense()
# Digital Ambient Light Sensor
lite_s = LTR329ALS01(py)

#
# registering
#
rest_msg = "POST /registro.html HTTP/1.1\r\n"
rest_msg += 'Host: 192.168.4.1\r\n'
rest_msg += 'User-Agent: LoPy\r\n'
rest_msg += 'Content-Length: 19\r\n'
rest_msg += '\r\n'
rest_msg += 'sender_name=sensor1'
send_it(rest_msg)

time.sleep(1)

#
# sending sensor data
#
v = get_sdata(lite_s)
d = {'DEV_ID': DEV_ID, 'QOS': QOS, 'TOPIC': TOPIC, 'VALUE': v}

jd = json.dumps(d)
print("sending:", jd)

rest_msg = 'POST /mqttproxypush HTTP/1.1\r\n'
rest_msg += 'Host: 192.168.4.1\r\n'
rest_msg += 'User-Agent: LoPy\r\n'
rest_msg += 'Content-Length: '+str(len(jd))+'\r\n'
rest_msg += '\r\n'
rest_msg += jd
send_it(rest_msg)

time.sleep(1)


            
