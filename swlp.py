# !/usr/bin/env python
"""
Stop & Wait like protocol to be used on a LoRa raw channel

Based on https://github.com/arturenault/reliable-transport-protocol by Artur Upton Renault

Modified by: Pietro GRC dic2017
"""

import machine
import socket
import struct
import sys
import time
import hashlib
import binascii
import gc


DEBUG_MODE = True
VERBOSE_MODE = False
NORMAL_MODE = False

#
# BEGIN: Utility functions
#

MAX_PKT_SIZE = 230  # Must determine which is the maximum pkt size in LoRa with Spread Factor 7...
HEADER_FORMAT = "!8s8sHHB3s"
HEADER_SIZE = 24
# header structure:
# 8B: source addr (last 8 bytes)
# 8B: dest addr (last 8 bytes)
# 2B: seqnum 
# 2B: acknum
# 1B: flags
# 3B: checksum 
PAYLOAD_SIZE = MAX_PKT_SIZE - HEADER_SIZE

DATA_PACKET = False
ANY_ADDR = b'FFFFFFFF'      # last 8 bytes


# Create a packet from the necessary parameters
def make_packet(source_addr, dest_addr, seqnum, acknum, is_a_ack, last_pkt, content):
    flags = 0
    if last_pkt: flags = flags | (1<<0)
    if is_a_ack: flags = flags | (1<<4)
    check = get_checksum(content)
    header = struct.pack(HEADER_FORMAT, source_addr, dest_addr, seqnum, acknum, flags, check)
    return header + content

# Break a packet into its component parts
def unpack(packet):
    header  = packet[:HEADER_SIZE]
    content = packet[HEADER_SIZE:]
    sp, dp, seqnum, acknum, flags, check = struct.unpack(HEADER_FORMAT, header)
    is_a_ack = (flags >> 4) == 1
    last_pkt = (flags & 1)  == 1
    return sp, dp, seqnum, acknum, is_a_ack, last_pkt, check, content

def get_checksum(data):
    h = hashlib.sha256(data)
    ha = binascii.hexlify(h.digest())
    return ha[-3:]

def debug_printpacket(msg, packet, cont=False):
    sp, dp, seqnum, acknum, is_a_ack, last_pkt, check, content = unpack(packet)
    if cont:
        print ("{}: s_p: {}, d_p: {}, seqn: {}, ackn: {}, ack: {}, fin: {}, check: {}, cont: {}".format(msg, sp, dp, seqnum, acknum, is_a_ack, last_pkt, check, content))
    else:
        print ("{}: s_p: {}, d_p: {}, seqn: {}, ackn: {}, ack: {}, fin: {}, check: {}".format(msg, sp, dp, seqnum, acknum, is_a_ack, last_pkt, check))

def timeout(signum, frame):
    raise socket.timeout

def choose_mode(mode):   # KN: Execution mode assignment
    if mode == 1:
        DEBUG_MODE = True
        VERBOSE_MODE = False
        NORMAL_MODE = False
    elif mode == 2:
        DEBUG_MODE = False
        VERBOSE_MODE = True
        NORMAL_MODE = False
    elif mode == 3:
        DEBUG_MODE = False
        VERBOSE_MODE = False
        NORMAL_MODE = True
    return DEBUG_MODE, VERBOSE_MODE, NORMAL_MODE

#
# END: Utility functions
#

def tsend(payload, the_sock, SND_ADDR, RCV_ADDR, mode):
    DEBUG_MODE,VERBOSE_MODE, NORMAL_MODE = choose_mode(mode)
    # Shortening addresses to save space in packet
    if DEBUG_MODE: print ("RCV_ADDR", RCV_ADDR)
    SND_ADDR = SND_ADDR[8:]
    RCV_ADDR = RCV_ADDR[8:]
    if DEBUG_MODE: print ("New RCV_ADDR", RCV_ADDR)
    # identify session with a number between 0 and 255: NOT USED YET
    sessnum = machine.rng() & 0xFF
    # Initialize counters et al
    seqnum = 0
    acknum = 0
    sent    = 0
    retrans = 0
    bandera = 0
    flagn = 0
    nsent = 0
    timeout_time    =  1    # 1 second
    estimated_rtt   = -1
    dev_rtt         =  1
    # Reads first block from string "payload"
    text    = payload[0:PAYLOAD_SIZE]    # Copying PAYLOAD_SIZE bytes header from the input string
    payload = payload[PAYLOAD_SIZE:]    # Shifting the input string
    # Checking if this is the last packet
    if (len(text) == PAYLOAD_SIZE) and (len(payload) > 0): 
        last_pkt = False
    else: 
        last_pkt = True
        bandera = 0 
    the_sock.setblocking(True)
    packet = make_packet(SND_ADDR, RCV_ADDR, seqnum, acknum, DATA_PACKET, last_pkt, text)
    the_sock.send(packet)
    send_time = time.time()
    sent += 1
    if DEBUG_MODE: debug_printpacket("Sending 1st", packet)
    the_sock.settimeout(5)      # 5 seconds initial timeout.... LoRa is slow
    notsend = 0
    dentro = False
    if not dentro:
        while True:
            try:
                # waiting for a ack
                if DEBUG_MODE: print("DEBUG Swlp: SND_ADDR", SND_ADDR)
                ack = the_sock.recv(HEADER_SIZE)
                recv_time = time.time()
                # Unpack packet information
                ack_source_addr, ack_dest_addr, ack_seqnum, ack_acknum, ack_is_ack, ack_final, ack_check, ack_content = unpack(ack)
                if (ack_seqnum == 0 and bandera ==0):
                    rcv2 = ack_source_addr
                    bandera = 1
                if DEBUG_MODE: 
                    debug_printpacket("Received ack", ack)
                    print(str(ack_source_addr))
                if ack_final: break 
                # If valid, here we go!
                if (ack_is_ack) and (ack_acknum == acknum) and (rcv2 == ack_source_addr):
                    # RTT calculations
                    sample_rtt = recv_time - send_time
                    if estimated_rtt == -1:
                        estimated_rtt = sample_rtt
                    else:
                        estimated_rtt = estimated_rtt * 0.875 + sample_rtt * 0.125
                    dev_rtt = 0.75 * dev_rtt + 0.25 * abs(sample_rtt - estimated_rtt)
                    the_sock.settimeout(estimated_rtt + 4 * dev_rtt)
                    if DEBUG_MODE: print ("setting timeout to", estimated_rtt + 4 * dev_rtt)
                    text    = payload[0:PAYLOAD_SIZE]   # Copying PAYLOAD_SIZE bytes header from the input string
                    payload = payload[PAYLOAD_SIZE:]    # Shifting the input string
                    # AM: Checking if it's the last ACK
                    if last_pkt:
                        dentro = True
                    # Checking if this is the last packet
                    if (len(text) == PAYLOAD_SIZE) and (len(payload) > 0): 
                        last_pkt = False
                    else: 
                        last_pkt = True
                        bandera = 0
                    # Increment sequence and ack numbers
                    seqnum += 1
                    acknum += 1
                    RCV_ADDR = rcv2
                    packet = make_packet(SND_ADDR, RCV_ADDR, seqnum, acknum, DATA_PACKET, last_pkt, text)
                    the_sock.send(packet)
                    send_time = time.time()
                    sent += 1
                    flagn=0
                    if DEBUG_MODE: debug_printpacket("Sending new packet", packet, True)
                else:
                    if DEBUG_MODE: print ("ERROR: packet received not valid")
                    raise socket.timeout
            except socket.timeout:
                if DEBUG_MODE: print("EXCEPTION!! Socket timeout: ", time.time())
                packet = make_packet(SND_ADDR, RCV_ADDR, seqnum, acknum, DATA_PACKET, last_pkt, text)
                the_sock.send(packet)
                flagn += 1
                if DEBUG_MODE: 
                    debug_printpacket("Re-sending packet", packet)
                    print ("From Swlp Flag Number: ", flagn)
                sent += 1
                retrans += 1
                if(flagn == 3):   # AM: In order not to leave the socket hung, a 3 packet forwarding is placed
                    dentro = True
                    notsend = 1
                    break
    if DEBUG_MODE: print ("DEBUG Swlp: RETURNING tsend")
    return(sent, retrans, sent, notsend)

#
# Trecv persistent

#Trecv no persistent
def trecvcontrol(the_sock, MY_ADDR, SND_ADDR, mode):
    DEBUG_MODE,VERBOSE_MODE, NORMAL_MODE=choose_mode(mode)
    flag_recv = False
    # Shortening addresses to save space in packet
    MY_ADDR = MY_ADDR[8:]
    SND_ADDR = SND_ADDR[8:]
    address_check = b""
    # Buffer storing the received data to be returned
    rcvd_data = b""
    packet_repeated = 0
    next_acknum = 0
    the_sock.settimeout(5)
    while True:
        try:
            # Receive any packet
            if DEBUG_MODE: print ("DEBUG Swlp: From Swlp My Address: ", MY_ADDR)
            packet = the_sock.recv(MAX_PKT_SIZE)
            if DEBUG_MODE: print ("Content received", packet)
            source_addr, dest_addr, seqnum, acknum, ack, last_pkt, check, content = unpack(packet)
            address_check = dest_addr
            if DEBUG_MODE: print ("From Swlp receiving source Address: ", source_addr) 
            if (dest_addr == MY_ADDR) or (dest_addr == ANY_ADDR):
                flag_recv = True
                break
            else: 
                if DEBUG_MODE: debug_printpacket("DISCARDED received packet; not for me!!", packet)
        except socket.timeout:
            if DEBUG_MODE: print ("EXCEPTION!! Socket timeout: ", time.time())
            break
        except Exception as e:
            if DEBUG_MODE: print ("EXCEPTION!! Packet not Valid")
            break
    if (flag_recv == True):
        if DEBUG_MODE: debug_printpacket("Received 1st packet", packet, True)
        checksum_OK = (check == get_checksum(content))
        if (checksum_OK) and (next_acknum == acknum):
            packet_valid = True
            rcvd_data += content
            next_acknum += 1
            # Sending first ACK
            ack_segment = make_packet(MY_ADDR, source_addr, seqnum, acknum, packet_valid, last_pkt, "")
            the_sock.setblocking(False)
            the_sock.send(ack_segment)
            if DEBUG_MODE: debug_printpacket("Sent 1st ACK", ack_segment)
        else: 
            packet_valid = False
            rcvd_data = b"Failed"
            return rcvd_data, address_check
        if (source_addr == b'raspberr') or (source_addr == b'aspberry'):
            if DEBUG_MODE: print("DEBUG Swlp: Sending again because it's a raspberry")
            time.sleep(1)
            the_sock.send(ack_segment)
        if not last_pkt:
            while True:
                try:
                    while True:
                        # Receive every other packet
                        the_sock.setblocking(True)
                        packet = the_sock.recv(MAX_PKT_SIZE)
                        source_addr, dest_addr, seqnum, acknum, ack, last_pkt, check, content = unpack(packet)
                        dest_addra = str(dest_addr)
                        dest_addr2=dest_addra[2:(len(dest_addra)-1)]
                        if DEBUG_MODE: 
                            print ("DEBUG Swlp: dest_addr",dest_addra)
                            print ("DEBUG Swlp: MY_ADDR",MY_ADDR)
                        if (dest_addr==MY_ADDR):
                            if DEBUG_MODE: debug_printpacket("Received packet", packet, True)
                            break
                        else: 
                            if DEBUG_MODE: debug_printpacket("DISCARDED received packet; not for me!!", packet)
                    checksum_OK = (check == get_checksum(content))
                    # ACK the packet if it's correct; otherwise send NAK.
                    if (checksum_OK) and (next_acknum == acknum):
                        packet_valid = True
                        rcvd_data += content
                        next_acknum += 1
                        ack_segment = make_packet(MY_ADDR, source_addr, seqnum, acknum, packet_valid, last_pkt, "")
                        time.sleep(.3)
                        the_sock.setblocking(True)
                        the_sock.send(ack_segment)
                        if DEBUG_MODE: debug_printpacket("Sending ACK", ack_segment)
                        packet_repeated = 0
                    else:
                        last_acknum = next_acknum - 1
                        if acknum == last_acknum:
                            packet_valid = True
                            ack_segment = make_packet(MY_ADDR, source_addr, seqnum, acknum, packet_valid, last_pkt, "")
                            time.sleep(.3)
                            the_sock.setblocking(True)
                            the_sock.send(ack_segment)
                            if DEBUG_MODE: debug_printpacket("Re-sending ACK", ack_segment)
                        else:
                            packet_valid = False
                            ack_segment = make_packet(MY_ADDR, source_addr, seqnum, acknum, packet_valid, last_pkt, "")
                            time.sleep(.3)
                            the_sock.setblocking(True)
                            the_sock.send(ack_segment)
                            if DEBUG_MODE: debug_printpacket("Sending NAK", ack_segment)
                        packet_repeated += 1
                        if packet_repeated == 3:
                            rcvd_data = b"Failed"
                            if DEBUG_MODE: print ("DEBUG Swlp: Send message failed")
                            if VERBOSE_MODE: print ("Send message failed")
                            break
                    if (source_addr == b'raspberr'):
                        if DEBUG_MODE: print ("DEBUG Swlp: Sending again because it's a raspberry")
                        time.sleep(1)
                        the_sock.send(ack_segment)
                    if last_pkt:
                        break
                except socket.timeout:
                    if DEBUG_MODE: print ("EXCEPTION!! Socket timeout: ", time.time())
                    break
    return rcvd_data, address_check