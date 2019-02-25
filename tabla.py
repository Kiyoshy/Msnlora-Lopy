import struct
import sys
import time
from socket import *
import swlp
import os
from machine import SD


VERBOSE_MODE = False
NORMAL_MODE = False
q=0

class BaseDatos:
	BaseM=[]
	BaseU=[]
	BaseB=[]
	n=0
	message_number = 0
	parameter_mode=""
	DEBUG_MODE = 0
	
	def __init__(self, mode):
		self.modep=mode

	def get_mode():
		sndmode=self.modep
		return sndmode

	def ingresoRegistro(self,usuario,flag): #AM: Register from a new user
		if flag==0:
			tbs="a"
			blks = usuario.split("&")
			for i in blks:
				v = i.split("=")
				tbs += ","+v[1]
			print("tbs",tbs)
			x=tbs.split(",")
			if(self.modep==1):print("DEBUG: data from the form: ", x)
			user=x[1]
		else:
			user=usuario
		if self.modep==1: print("DEBUG: User: ", user)
		if user in self.BaseU:
			posicion=self.BaseU.index(user)
		else:
			self.BaseU.append(user)
			self.BaseM.append(user)
			posicion=self.BaseU.index(user)
			self.BaseM[posicion]={}	
		if self.modep==1: print("DEBUG: Position: ", posicion)
		if self.modep==1: print("DEBUG: User Database: ", self.BaseU)
		r_content='<head><meta charset="utf-8"><title>Register LoRa</title>\n'
		r_content +='<style type="text/less">\n'
		r_content +=".dropdown-toggle {display:none;}\n"
		r_content +=".dropdown-menu {display:none;}\n"
		r_content +="</style>\n"
		r_content +="</head>\n"
		r_content += "<body><h1>Welcome</h1>\n"
		r_content += "<h1>"+user+"</h1>\n"
		r_content += '<form class="form-horizontal well" action="" method="post"><div><label for="named">Destination or Telegram User:</label><input type="text" id="named" name="dest_name"></div><div><label for="msg">Message:</label> <textarea id="msg" name="user_message"></textarea></div><div class="button"><button type="submit" onclick=this.form.action="execposthandler.html";document.getElementById("oculto").style.visibility="visible">Send your message</button></div><div class="button"><button type="submit" onclick=this.form.action="tabla.html">Check my messages</button></div>'
		r_content += '<div class="button"><button type="submit" onclick=this.form.action="broadcast.html">Send Message To All Users</button></div>'
		r_content += '<div class="button"><button type="submit" onclick=this.form.action="telegram.html">Send Message Via telegram</button></div>'
		r_content += '<div id="oculto" style="visibility:hidden">Sending...</div>'
		r_content += "<p><a href='/'>Back to home</a></p></body>\n"
		return r_content,user

	def ingreso(self,Emisor,destino,Mensaje): #AM: Function to save the messages
		print("Saving Message")
		if self.modep==1: print("DEBUG: Number of Message: ", self.message_number)
		BaseDatos.n+=1
		if self.modep==1: print("DEBUG: Number of Message: ", self.n)
		if self.modep==1: print("DEBUG: Message Database: ", self.BaseM)
		if self.modep==1: print("DEBUG: User Database: ", self.BaseU)
		posicion=self.BaseU.index(destino)
		if self.modep==1: print("DEBUG: Position: ", posicion)
		self.BaseM[posicion][str(self.n)+"Emisor "]=Emisor
		self.BaseM[posicion][str(self.n)+"Mensaje "]=Mensaje
		if self.modep==1: print("DEBUG: New Users Database: ", self.BaseU)
		if self.modep==1: print("DEBUG: New Message Database: ", self.BaseM)
		if self.modep==1: print("DEBUG: Number of Message: ", self.n)
		self.message_number=self.n
		if(self.message_number==10):
			print("Saving Databases")
			x = save_backup(self.BaseU,self.BaseM)
			self.message_number=0


	def consultaControl(self,destino):
		if self.modep==1: print("DEBUG: User Database: ", self.BaseU)
		bandera = 0
		if destino in self.BaseU: # AM: Checking if the user is in the database
			bandera = 1
		else:
			bandera = 0
		return bandera

	def consulta(self,user):
		if self.modep==1: print("DEBUG: User: ", user)
		BaseUConsulta = self.BaseU
		if self.modep==1: print("DEBUG: User Database: ", BaseUConsulta)
		BaseMConsulta = self.BaseM
		posicion=BaseUConsulta.index(user)
		if sself.modep==1: print("DEBUG: Messages: ", BaseMConsulta[posicion])
		if (BaseMConsulta[posicion]!={}):
			r_content = "<h1>Messages sent via LoRa</h1>\n"
			r_content += "\n"
			for key,val in BaseMConsulta[posicion].items(): 
				r_content += str(val)+" , \n"
			r_content += "\n"
			r_content += "<h1>Broadcast Messages</h1>\n"
			r_content += str(self.BaseB)+" , \n"
			r_content += "<p><a href='/registro'>Back to home</a></p>\n"
		else:
			r_content = "<h1>No Messages</h1>\n"
			r_content += "\n"
			r_content += "\n"
			r_content += "<h1>Broadcast Messages</h1>\n"
			r_content += str(self.BaseB)+" , \n"
			r_content += "<p><a href='/registro'>Back to home</a></p>\n"
		if self.modep==1: print("DEBUG: r_content", r_content)
		return r_content

	def broadcast_message(self,message):
		self.BaseB.append(message)
		print("Message Broadcast Saved")

################################################################################################################
#Management of the data in the SD Card
def save_backup(DBU,DBM):
	global q
	f = open('/sd/DatabaseU'+str(q)+'.txt', 'w')
	f.write(str(DBU))
	f.close()
	f = open('/sd/DatabaseM'+str(q)+'.txt', 'w')
	f.write(str(DBM))
	f.close()
	print("Databases Saved")
	q+=1
	return q

def open_backup(a):
	f = open('/sd/DatabaseU'+str(a-1)+'users.txt', 'r')
	dataUser = f.readall()
	f.close()
	listaUser = eval(dataUser)
	f = open('/sd/DatabaseM'+str(a-1)+'users.txt', 'r')
	dataMess = f.readall()
	f.close()
	listaMess = eval(dataMess)
	return listaUser,listaMess