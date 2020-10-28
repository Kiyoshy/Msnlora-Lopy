import time
import loractp

ctpc = loractp.CTPendpoint()

while True:

    print('plainreceiver.py: waiting for data')
    try:
        rcvd_data, addr = ctpc.recvit()
        print("plainreceiver.py: got {} from {}".format(rcvd_data, addr))
    except Exception as e:
        print ("plainreceiver.py: EXCEPTION!! ", e)
        break
