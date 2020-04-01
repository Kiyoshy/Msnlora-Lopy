import socket
import json

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
	print("response: ", r)
	response = r.split('\n')[0]
	if response == "HTTP/1.1 200 OK":
	    print("Got: "+response)
	else:
	    print("ERROR Got: "+response)

	return(r[1:])


#
# registering
#
rest_msg = "POST /registro.html HTTP/1.1\r\n"
rest_msg += 'Host: 192.168.4.1\r\n'
rest_msg += 'User-Agent: LoPy\r\n'
rest_msg += 'Content-Length: 21\r\n'
rest_msg += '\r\n'
rest_msg += 'sender_name=mqttproxy'
send_it(rest_msg)
