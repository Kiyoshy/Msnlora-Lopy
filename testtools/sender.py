import getopt
import json
import socket
import sys
import time

#
# When sender is a LoPy
#
# import ufun
# WIFI_SSID = "messenger_e57"

TCP_IP    = '192.168.4.1'
TCP_PORT  = 80

USER      = "pietro"
RCVR      = "scarlett"
MESSAGE  = "Hola, que tal?"


def create_POST_msg(type, content):
    cl = len(content)
    m  = 'POST ' + type + ' HTTP/1.1\r\n'
    m += 'Host: '+ TCP_IP + '\r\n'
    m += 'User-Agent: TestingDevice\r\n'
    m += 'Content-Length: ' + str(cl) + '\r\n'
    m += '\r\n'
    m += content

    return(m)


def send_it(m):
    BUFFER_SIZE = 1024

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(m.encode())

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

def main(argv):
    global WIFI_SSID, USER, MESSAGE, RCVR

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'w:u:r:m:', ['wifissid=', 'user=', 'receiver=', 'message='])
    except getopt.GetoptError:
        print ('sender.py -w <WIFI_SSID> -u <USER> -r <RCVR> -m <MESSAGE>')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-m', '--message'):
            MESSAGE = arg
        elif opt in ('-w', '--wifissid'):
            WIFI_SSID = arg
        elif opt in ('-u', '--user'):
            USER = arg
        elif opt in ('-r', '--receiver'):
            RCVR = arg
        else:
            print ('sender.py -w <WIFI_SSID> -u <USER> -r <RCVR> -m <MESSAGE>')
            sys.exit(2)


if __name__ == "__main__":

    main(sys.argv[1:])

#
# When sender is a LoPy
#
#    ufun.connect_to_wifi(WIFI_SSID, "")

    #
    # registering
    #
    print("registering USER: ", USER)
    rest_msg = create_POST_msg("/registro.html", "sender_name="+USER)
    send_it(rest_msg)

    time.sleep(1)

    # dest_name=Luigi&user_message=Testo
    print("sending: ", MESSAGE, " to ", RCVR)

    rest_msg = create_POST_msg("/execposthandler", "dest_name="+RCVR+"&user_message="+MESSAGE)
    send_it(rest_msg)

    time.sleep(1)


                
