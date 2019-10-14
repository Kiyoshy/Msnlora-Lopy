#!/usr/bin/python

# PM: based on http://blog.wachowicz.eu/?p=256
# PM: added POST handling
# import signal  # Signal support (server shutdown on signal receive)
# KN: Added connection to local network, server execution mode
# KN: Added support for 100000KB
# AM: Agregado funcionamiento entre dos dispositivos

import socket  # Networking support
from time import time    # Current time
import ubinascii
import binascii
import posthandler # PM: code to be executed to handle a POST
import swlp #AM: LoRa Protocol
from tabla import BaseDatos #AM: Management of user and messages
from network import LoRa #AM: LoRa
import network
import select #AM: Used to change between the sockets
import ufun #AM: Used to handle the leds in the lopy
import machine
from network import WLAN
from machine import SD
import gc
import os
import utime


RED = 0xFF0000
YELLOW = 0xFFFF33
GREEN = 0x007F00
PINK=0x6b007f
BLUE= 0x005e63
OFF = 0x000000
WEB_PAGES_HOME_DIR = '/flash' # Directory where webpage files are stored
ANY_ADDR = b'FFFFFFFF'
flag = 0
DEBUG_MODE = False
VERBOSE_MODE=False
NORMAL_MODE=False
#LoRA parameters to work with raspberry
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
region=LoRa.EU868               # def.: region=LoRa.EU868 just for LoPy4         
dev_class=LoRa.CLASS_A          # def.: device_class=LoRa.CLASS_A   
flag_mode=0

class Server:
 """ Class describing a simple HTTP server objects."""

 def __init__(self, port, mode):
     """ Constructor """
     self.host = ''   # <-- works on all avaivable network interfaces
     self.port = port
     self.www_dir =  WEB_PAGES_HOME_DIR
     self.flag_null = 0
     self.userR = ""
     self.modep=mode #int number 1: Debug Mode 2:Verbose Mode 3:Normal Mode

 def activate_server(self):
     """ Attempts to aquire the socket and launch the server """
     self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     try: # user provided in the __init__() port may be unavaivable
         if(self.modep==1):print("Launching HTTP server on ", self.host, ":",self.port)
         self.socket.bind((self.host, self.port))

     except Exception as e:
         print ("Warning: Could not acquire port:",self.port,"\n")
         print ("I will try a higher port")
         # store to user provided port locally for later (in case 8080 fails)
         user_port = self.port
         self.port = 8080

         try:
             print("Launching HTTP server on ", self.host, ":",self.port)
             self.socket.bind((self.host, self.port))
         except Exception as e:
             print("ERROR: Failed to acquire sockets for ports ", user_port, " and 8080. ")
             print("Try running the Server in a privileged user mode.")
             self.shutdown()
             import sys
             sys.exit(1)

     if(self.modep==1):print ("Server successfully acquired the socket with port:", self.port)
     print ("Press Ctrl+C to shut down the server and exit.")
     if(self.modep==1):print ("Awaiting New connection")
     self.socket.listen(3) # maximum number of queued connections

 def connectionLoRa(self): #Function to create LoRa socket
    try:
        self.s_right = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        self.loramac = binascii.hexlify(network.LoRa().mac())
        if(self.modep==1):print("Socket Created") # AM: Adquisicion socket LoRa
    except socket.error:
        exit('Error creating socket.') 

 def shutdown(self):
     """ Shut down the server """
     try:
         print("Shutting down the server")
         s.socket.shutdown(socket.SHUT_RDWR)
     except Exception as e:
         print("Warning: could not shut down the socket. Maybe it was already closed...", e)

 def _gen_headers(self, code):
     """ Generates HTTP response Headers. """
     # determine response code
     h = ''
     if (code == 200):
        h = 'HTTP/1.1 200 OK\n'
     elif(code == 404):
        h = 'HTTP/1.1 404 Not Found\n'

     # write further headers
     # current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
     # PM: should find an alternative for LoPys
     current_date = '4 Agosto 1965'
     h += 'Date: ' + current_date +'\n'
     h += 'Server: Simple-Python-HTTP-Server\n'
     h += 'Connection: close\n\n'  # signal that the conection will be closed after completing the request
     return h

 def _wait_for_connections(self,s_left,addr,treq):
     #determine request method  (HEAD and GET are supported) (PM: added support to POST )
     request_method = treq.split(' ')[0]
     if(self.modep==1):
        print ("Method: ", request_method)
        print ("Full HTTP message: -->")
        print (treq)
        print ("<--")
     treqhead = treq.split("\r\n\r\n")[0]
     treqbody = treq[len(treqhead):].lstrip() # PM: makes easier to handle various types of newlines
     if(self.modep==1):
        print ("only the HTTP body: -->")
        print (treqbody)
        print ("<--")

     # split on space "GET /file.html" -into-> ('GET','file.html',...)
     file_requested = treq.split(' ')
     if(self.modep==1): print("Debug Server: File Requested: ", file_requested)   ###
     if(file_requested==''):
        file_requested = '/index.html'
     file_requested = file_requested[1] # get 2nd element

     #Check for URL arguments. Disregard them
     file_requested = file_requested.split('?')[0]  # disregard anything after '?'

     if (file_requested == '/'):  # in case no file is specified by the browser
             file_requested = '/index.html' # load index.html by default
     elif (file_requested == '/favicon.ico'):  # most browsers ask for this file...
             file_requested = '/index.html' # ...giving them index.html instead
     
     file_requested = self.www_dir + file_requested
     if(self.modep==1):print ("Serving web page [",file_requested,"]")

# GET method
     if (request_method == 'GET') | (request_method == 'HEAD') :
     ## Load file content
         try:
             gc.collect()
             if (self.modep==1): print("mem_free: ", gc.mem_free())
             if(request_method=='GET' and file_requested=='/flash/registro'):
                 if (self.modep==1): print('Regreso del Usuario',self.userR)
                 tabla=BaseDatos(self.modep)
                 response_content,self.userR=tabla.ingresoRegistro(self.userR,1)
                 if(self.modep==1): print('Datos Regreso',response_content)
             else:
                 file_handler = open(file_requested,'rb')
                 if(self.modep==1): print('file_handler',file_handler)
                 if (request_method == 'GET'):  #only read the file when GET
                    response_content = file_handler.read() # read file content
                 file_handler.close()
             response_headers = self._gen_headers(200)
             if(self.modep==1): print('response_headers',response_headers)
         except Exception as e: #in case file was not found, generate 404 page
             error_str = str(e)
             if (error_str[:24] == 'memory allocation failed'):
                print ("Warning, memory allocation failed. Serving response code 500"+" -> "+error_str)
                response_headers = self._gen_headers(500)
                if (request_method == 'GET'):
                    response_content = b"<html><body><p>Error 500: Memory allocation failed</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"
                else:
                    print ("Warning, file not found from GET. Serving response code 404\n", e)
                    response_headers = self._gen_headers( 404)
                    if (request_method == 'GET'):
                        response_content = b"<html><head><meta charset='utf-8'><title>LoRa</title></head><body><p>Error 404: File not found</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"
         server_response =  response_headers.encode() # return headers for GET and HEAD   
         if (request_method == 'GET'):
            server_response +=  response_content  # return additional conten for GET only
         s_left.send(server_response)
         if(self.modep==1):print ("Closing connection with client")
         ufun.set_led_to(OFF)
         s_left.close()

# POST method
     elif (request_method == 'POST'):
             ## Load file content
         try:
             if (file_requested.find("execposthandler") != -1):
                 if(self.modep==1):
                    print("... PM: running python code")
                    print("DEBUG Server: lenght message:",len(treqbody))
                 if (len(treqbody) > 25):
                     self.form=treqbody
                     response_content, self.dest_lora_address = posthandler.run(treqbody,self.s_right,self.loramac,self.userR,0, self.modep)
                 else:
	                 if(self.modep==1):print("... PM: empty POST received")
	                 response_content = b"<html><body><p>Error: EMPTY FORM RECEIVED, Please Check Again</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"
             elif (file_requested.find("tabla") != -1):                 
                 if (self.modep==1): print("DEBUG Server: Checking Messages")
                 if (self.modep==2): print("Checking Messages")
                 if (self.modep==3): print("Checking messages")
                 gc.collect()
                 tabla=BaseDatos(self.modep)
                 response_content = tabla.consulta(self.userR)
             elif (file_requested.find("registro") != -1):
                 if(self.modep==1): 
                    print("DEBUG Server: Register")
                    print("DEBUG Server: lenght user:",len(treqbody))
                    print("DEBUG Server: treqbody:",treqbody)
                 tabla=BaseDatos(self.modep)
                 if (len(treqbody) > 12 ):
                     response_content,self.userR = tabla.ingresoRegistro(treqbody,0)
                     gc.collect()
                     print("Register Ok")
                 else:
                     print("... PM: empty POST received")
                     response_content = b"<html><body><p>Error: Please Choose a username</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"
             elif (file_requested.find("broadcast") != -1):
                if(self.modep==1 | self.modep==2): print("AM: Sending Message Broadcast")
                if(self.modep==3): print("Message Broadcast sent")
                gc.collect()
                tabla=BaseDatos(self.modep)
                response_content, self.dest_lora_address = posthandler.run(treqbody,self.s_right,self.loramac,self.userR,1, self.modep)
             elif (file_requested.find("telegram") != -1):
                print("AM: Telegram Message")
                tabla=BaseDatos(self.modep)
                if(self.modep==1): print("DEBUG Server: lenght message:",len(treqbody))
                if (len(treqbody) > 25):
                    response_content, self.dest_lora_address = posthandler.run(treqbody,self.s_right,self.loramac,self.userR,2, self.modep)
                else:
                    print("... AM: empty POST received")
                    response_content = b"<html><body><p>Error: EMPTY FORM RECEIVED, Please Check Again</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"
             elif (file_requested.find("resend") != -1):
                    if(self.modep==1): print("DEBUG Server: Resending message")
                    response_content = posthandler.resend(self.form, self.s_right, self.loramac, self.userR, self.dest_lora_address, self.modep)
             else:
                 file_handler = open(file_requested,'rb')
                 response_content = file_handler.read() # read file content
                 file_handler.close()

             response_headers = self._gen_headers(200)
         except Exception as e: #in case file was not found, generate 404 page
             print ("Warning, file not found. Serving response code 404\n", e)
             response_headers = self._gen_headers(404)
             response_content = b"<html><body><p>Error 404: File not found</p><p>Python HTTP server</p><p><a href='/'>Back to home</a></p></body></html>"

         server_response =  response_headers.encode() # return headers
         server_response +=  response_content  # return additional content
         s_left.send(server_response)
         if(self.modep==1):print ("Closing connection with client")
         ufun.set_led_to(OFF)
         s_left.close()

     else:
         print("Unknown HTTP request method:", request_method)
 
 # Function to receive all the message via TCP
 def checking_connection(self,s_left,addr):
    data=b""
    data = s_left.recv(1024)
    while True:
        check_header = bytes.decode(data)
        check_header_list = (check_header.split('\r\n'))  #Create list to check header
        check_header_dict={}
        for element in check_header_list:  #Create a dict
            s_element= (str(element))
            if (s_element.find(':')) != -1:
                keyValue = element.split(': ')
                check_header_dict[keyValue[0]]=keyValue[1]
        content_length = int(check_header_dict.get('Content-Length', 0))     #Content lenght
        checking_header = check_header.split("\r\n\r\n")[0]
        checking_body = check_header[len(checking_header):].lstrip()
        rec_body = len(checking_body)
        r_data = content_length - rec_body
        if (self.modep==1): print ("DEBUG Server: Remaining Body: ", r_data)
        if r_data!=0:
            data += s_left.recv((1024))
            check_headerx = bytes.decode(data)
        else:
            if (self.modep==1): print("DEBUG Server: Data Received")
            break

    if(self.modep==1):print("Got connection from: ", addr)
    if(self.modep==1): print("DEBUG Server: Data received: ",data)
    if(data==b""):
        if(self.modep==1 | self.modep==2): print("Null Method, Discarding")
    else:
        treq = bytes.decode(data)
        self._wait_for_connections(s_left,addr,treq)

 def conexion(self): #Function in charge of the coordination of sockets
    ANY_ADDR = b'FFFFFFFFFFFFFFFF'
    while True:
        s_read, _, _ = select.select([self.socket, self.s_right], [], [])
        for a in s_read:
            if a == self.socket:
                # reading data from the HTTP channel
                if(self.modep==1): print("DEBUG Server: In connections_handler: reading data from the HTTP channel")
                s_left, addr = self.socket.accept()
                self.checking_connection(s_left,addr)
            elif a == self.s_right:
                # reading data from the LORA channel using swlpv3
                if(self.modep==1): print("DEBUG Server: reading data from the LORA channel using swlpv3")
                ufun.flash_led_to(YELLOW)
                data,sender = swlp.trecvcontrol(self.s_right, my_lora_address, ANY_ADDR, self.modep)
                LoRaRec(data,self.s_right,sender)
                if(self.modep==1): 
                    print("DEBUG Server: done reading data from the LORA channel using swlpv3:",data)
                    print("The End")                
                ufun.flash_led_to(OFF)

###################################################################################

def LoRaRec(data,socket,source_address):
    bandera=0
    mensaje = b""
    tabla=BaseDatos(mode_print)
    my_lora_address = binascii.hexlify(network.LoRa().mac())
    if(mode_print==1): 
        print("DEBUG Server: Content in reception LoRa",data)
        print("DEBUG Server: Source Address in LoRaRec ", source_address)
    if (source_address == ANY_ADDR):
        content2 = str(data) #Capturing the data, and changing the format
        IPlora,user_raw = content2.split(",")
        if(IPlora=="b'FFFFFFFraspbsend'") or (IPlora==b'FFFFFFFraspberry'):
            if(mode_print==1): print("DEBUG Server: It's the raspberry IP")
        if(mode_print==1): print("DEBUG Server: IP Lora: ",str(IPlora))
        lenght = len(user_raw)
        userf = user_raw[:lenght-1]
        if(userf=="broadcast"): #Message to all users
            message_broadcast = str(IPlora[2:])
            tabla=BaseDatos(mode_print)
            if(mode_print==1): print("DEBUG Server: Message Broadcast received",message_broadcast)
            posthandler.broadcast(message_broadcast, mode_print) #Function to save the broadcast message
        IPloraf = IPlora[4:]
        if(mode_print==1): print("DEBUG Server: User ", userf)
        bandera=posthandler.consultat(userf, mode_print) #Checking if the user is in the database
        #bandera=tabla.consultaControl(userf)
        if(mode_print==1): print("DEBUG Server: Flag ", bandera)
        if bandera == 1: #The user is in the database, I'm going to respond
            if(mode_print==1): print("DEBUG Server: Lora Address ", IPloraf)
            sent, retrans, sent, notsend = swlp.tsend(my_lora_address, socket, my_lora_address, IPloraf, mode_print)#Function to send a LoRa Message using the protocol
    elif(source_address== my_lora_address[8:]): #The message is for me, I'm going to save it
        message_raw = data
        if(mode_print==1): print("DEBUG Server: message in server", message_raw)
        if (mode_print==2): print("Receiving message")
        if(message_raw ==b"Failed"):
            print("Reception Failed, Discarding")
        elif(message_raw !=b"") and (message_raw !=b"Failed"):
            mensajet = str(message_raw)
            idEmisor, messagef,user_final = mensajet.split(",")
            if (mode_print==1):
                print("Sender: "+str(idEmisor[1:]))
                print("Message: "+str(messagef))
                print("User: "+str(user_final))
            lenght = len(user_final)
            userf = user_final[:lenght-1]
            tabla.ingreso(idEmisor[2:],userf,messagef)#Function to save the message in the database

################################################################################################################################

def choose_mode():   # KN: Execution mode assignment
    print("---CHOOSE MODE---")
    while True:
        mode = str.lower(input('Choose the execution mode ("Debug" "Verbose" "Normal"): '))
        if mode == "debug":
            modemes=1
            print("--> Running sever in DEBUG mode")
            break
        elif mode == "verbose":
            modemes=2
            print("--> Running sever in VERBOSE mode")
            break
        elif mode == "normal":
            modemes=3
            print("--> Running sever in NORMAL mode")
            break
        else:
            print("--> Unrecognized execution mode")
    return modemes


mode_print=choose_mode() # Function to choose print mode 1:Debug Mode 2:Verbose Mode 3:Normal Mode
# Enabling garbage collection
gc.enable()
gc.collect()
if(mode_print==1):print("mem_free: ", gc.mem_free())
sd = SD()
os.mount(sd, '/sd')
if(mode_print==1):print("SD Card Enabled")
#Starting LoRa
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
        region=LoRa.EU868,              
        device_class=dev_class)
# Se configura la lopy como punto de Acceso y servidor HTTP
my_lora_address = binascii.hexlify(network.LoRa().mac())
source_address = str(str(my_lora_address[8:]))
n_network=(source_address[-4:-1])
lopy_name = "messenger"+str(n_network)
wlan = WLAN(mode=WLAN.STA_AP, ssid=lopy_name)
wlan.init(mode=WLAN.STA_AP, ssid=lopy_name, auth=None, channel=7, antenna=WLAN.INT_ANT)
print("Network Name: "+str(lopy_name))
print ("Starting web server")
tabla=BaseDatos(mode_print) #Instanciamiento Clase Base de Datos
s = Server(80,mode_print)  # construct server object
s.activate_server() # Acquire the socket
s.connectionLoRa() #Acquire Socket LoRa
s.conexion()