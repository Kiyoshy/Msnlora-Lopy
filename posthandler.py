from network import LoRa
import socket
import machine
from time import time    # Current time
import binascii
import network
import swlp #Stop and Wait Protocol
import struct
import ufun
from tabla import BaseDatos #AM: Libreria Bases de Usuarios y mensajes
import utime

ANY_ADDR = b'FFFFFFFFFFFFFFFF'
MAX_PKT_SIZE_REC = 32  # Must determine which is the maximum pkt size in LoRa...
HEADER_FORMAT = "BB"
HEADER_SIZE = 2
# header structure:
# 1B: Tipo de Archivo
# 1B: Tipo de Paquete 
PAYLOAD_SIZE = MAX_PKT_SIZE_REC - HEADER_SIZE
DATA_PACKET = False
RED = 0xFF0000
YELLOW = 0xFFFF33
GREEN = 0x007F00
PINK=0x6b007f
BLUE= 0x005e63
OFF = 0x000000
DEBUG_MODE = False
VERBOSE_MODE = False
NORMAL_MODE = False
#LoRA parameters
freq=869000000                  # def.: frequency=868000000         
tx_pow=14                       # def.: tx_power=14                 
band=LoRa.BW_125KHZ             # def.: bandwidth=LoRa.868000000    
spreadf=7                       # def.: sf=7                        
prea=8                          # def.: preamble=8                  
cod_rate=LoRa.CODING_4_5        # def.: coding_rate=LoRa.CODING_4_5 
pow_mode=LoRa.ALWAYS_ON         # def.: power_mode=LoRa.ALWAYS_ON   
tx_iq_inv=False                 # def.: tx_iq=false                 
rx_iq_inv=False                 # def.: rx_iq=false                 
ada_dr=False                    # def.: adr=false                   
pub=False                       # def.: public=true                 
tx_retr=1                       # def.: tx_retries=1                
dev_class=LoRa.CLASS_A          # def.: device_class=LoRa.CLASS_A

# AM: subpacket creation not implemented
def make_subpacket(TipoMensaje, TipoPaquete, content):
    
    Paquete = 0
    Mensaje = 0
    if TipoPaquete: Paquete = Paquete | (1<<0) #False for Audio, True for plain text
    if TipoMensaje: Mensaje = Mensaje | (1<<0) # False for Control, True for payload

    header = struct.pack(HEADER_FORMAT, Mensaje, Paquete)
    return header + content

# AM: Unpack, not implemented
def unpack(packet):
    header  = packet[:HEADER_SIZE]
    content = packet[HEADER_SIZE:]

    TM, TP = struct.unpack(HEADER_FORMAT, header)
    
    return TM, TP, content    

def reconocimiento(the_sock,tbs,message,flag_broadcast):
    # AM: We send a broadcast message looking for the user
    mensaje =""
    content= ""
    cuenta = 0
    address = b""
    m_broadcast = 0
    lora = LoRa(mode=LoRa.LORA,
        frequency=freq,         
        tx_power=tx_pow,               
        bandwidth=band,    
        sf=spreadf,                       
        preamble=prea,               
        coding_rate=cod_rate,
        power_mode=pow_mode,  
        tx_iq=tx_iq_inv,                
        rx_iq=rx_iq_inv,                
        adr=ada_dr,                  
        public=pub,       
        tx_retries=tx_retr,              
        device_class=dev_class)
    my_lora_address = binascii.hexlify(network.LoRa().mac())
    dest_lora_address = b'FFFFFFFFFFFFFFFF'
    if(tbs=="broadcast"):
        content=message+","+str(tbs)
    else:
        content=str(str(my_lora_address)+","+str(tbs))
    if DEBUG_MODE: print("DEBUG: Content: ", content)
    if DEBUG_MODE: print("DEBUG: Searching: ", tbs)
    # AM: We wait 20 seconds for the user
    while True:
        if(tbs=="broadcast"):#We check if the message is broadcast
            if DEBUG_MODE: print("DEBUG: Sending Message broadcast")
            sent,retrans,nsent = swlp.tsend(content, the_sock, my_lora_address, dest_lora_address)
            mensaje=b""
            m_broadcast = 1
            break
        elif(flag_broadcast==2):#When is a message via telegram
            dest_lora_address=b'FFFFFFFraspberry'
            if DEBUG_MODE: print("DEBUG: Searching Via Telegram to: ", tbs)
        if DEBUG_MODE: print("DEBUG: Searching: ", cuenta)
        sent,retrans,nsent = swlp.tsend(content, the_sock, my_lora_address, dest_lora_address)
        mensaje,address = swlp.trecvcontrol(the_sock, my_lora_address, dest_lora_address)
        if DEBUG_MODE: print("DEBUG: Message: ", mensaje)
        if DEBUG_MODE: print("DEBUG: Retransmisions",retrans)
        cuenta+=1
        if(mensaje!=b""): #We found the user receiver
            break
        elif(cuenta==3 and mensaje==b""):
            if DEBUG_MODE: print("DEBUG: Message when destination not found: ", mensaje)
            break
    return mensaje,m_broadcast

def run(post_body,socket,mac,sender,flag_broadcast):
    tabla=BaseDatos(1)
    ufun.set_led_to(BLUE)
    dest_lora_address =b""
    # PM: extracting data to be sent from passed POST body 
    blks = post_body.split("&")
    if DEBUG_MODE: print("DEBUG: Data received from the form: ", blks)
    tbs=str(mac)
    for i in blks:
        v = i.split("=")
        tbs += ","+v[1]
    if DEBUG_MODE: print("DEBUG: tbs: ", tbs)
    loramac, receiver, message=tbs.split(",")
    # AM: Checking where to send the message
    start_search_time = utime.ticks_ms()
    if(flag_broadcast==1):
        receiver = "broadcast"
    dest_lora_address, m_broadcast = reconocimiento(socket,receiver,message,flag_broadcast)#Function to look for the user
    search_time = utime.ticks_ms() - start_search_time
    dest_lora_address2 = dest_lora_address[2:]
    if DEBUG_MODE: print("DEBUG: dest lora address: ", dest_lora_address2)
    if DEBUG_MODE: print("DEBUG: Search Destination time: %0.10f mseconds."% search_time)
    if(dest_lora_address != b""):
        start_time = utime.ticks_ms()
        aenvio = str(sender)+","+str(message)+","+str(receiver) # AM: When you know where to send the message
        if DEBUG_MODE: print("DEBUG: Payload to be sent: ", aenvio)
        sent, retrans,sent = swlp.tsend(aenvio, socket, mac, dest_lora_address)
        elapsed_time = utime.ticks_ms() - start_time
        if DEBUG_MODE: print("DEBUG: Sent OK, Message time: %0.10f mseconds."% elapsed_time)
        if DEBUG_MODE: print("DEBUG: Retransmisions",retrans)
        if DEBUG_MODE: print("DEBUG: Segments sent:",sent)
        ufun.set_led_to(OFF)
        # PM: creating web page to be returned
        r_content = "<h1>Message sent via LoRa</h1>\n"
        r_content += "\n"
        r_content += tbs + "\n"
        r_content += "\n"
        r_content += "<p><a href='/registro'>Back to home</a></p>\n"
    elif(m_broadcast==1):
        # AM: Creating Web Page to be returned
        r_content = "<h1>Message sent to all users via LoRa</h1>\n"
        r_content += "\n"
        r_content += tbs + "\n"
        r_content += "\n"
        r_content += "<p><a href='/registro'>Back to home</a></p>\n"
    else:
        ufun.set_led_to(OFF)
        r_content = "<h1>Destination Not found\n"
        r_content += "<h1><a href='/registro'>Back To Home</a></h1>\n"
    return r_content

def broadcast(message):#Function to save a broadcast message
    tabla=BaseDatos()
    tabla.broadcast_message(message)
    print("received")

def consultat(user):
    tabla=BaseDatos(1)
    bandera=tabla.consultaControl(user)
    #mode=tabla.get_mode()
    #choose_mode()
    print("Consulta")
    #bandera=1
    return bandera
