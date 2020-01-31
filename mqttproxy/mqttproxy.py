import socket
import json
import re

import paho.mqtt.client as mqtt

THE_BROKER = "test.mosquitto.org"

TCP_IP = '192.168.4.1'
TCP_PORT = 80
WIFI_SSID = "messenger_e89"

BUFFER_SIZE = 1024  # Normally 1024

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

	return(r)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected to ", client._host, "port: ", client._port)
    print("Flags: ", flags, "returned code: ", rc)

# The callback for when a message is published.
def on_publish(client, userdata, mid):
    print("sipub: msg published (mid={})".format(mid))

client = mqtt.Client(client_id="", 
                     clean_session=True, 
                     userdata=None, 
                     protocol=mqtt.MQTTv311, 
                     transport="tcp")

client.on_connect = on_connect
client.on_publish = on_publish

#client.username_pw_set(None, password=None)
client.connect(THE_BROKER, port=1883, keepalive=60)

rest_msg = 'POST /mqttproxypop HTTP/1.1\r\n'
rest_msg += 'Host: 192.168.4.1\r\n'
rest_msg += 'User-Agent: LoPy\r\n'
rest_msg += 'Content-Length: 13\r\n'
rest_msg += '\r\n'
rest_msg += 'Popping data\n'
pop = send_it(rest_msg)

# Extracting json of the sensor data
b = re.search(".*?\{(.*)\}.*",pop)
bd = '{' + b.group(1) + '}'

jinp = json.loads(bd)

print(jinp["TOPIC"]+ " with value ", jinp["VALUE"])

# 	d = {"DEV_ID": DEV_ID, "QOS": QOS, "TOPIC": TOPIC, "VALUE": v}

client.loop_start()
client.publish(jinp["TOPIC"], payload=jinp["VALUE"], qos=jinp["QOS"], retain=False)
client.loop_stop()
