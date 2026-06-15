import socket
import threading
import hashlib
import random
import os
import sympy
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import time

users={"Jon":["localhost",50000],
	"Jom":["localhost",51000]}

client1 = None
client2 = None
server1 = None
aesgcm = None

def derriveKey(sharedkey: int) -> bytes:
	byte_length = (sharedkey.bit_length()+7) // 8
	sharedkey = sharedkey.to_bytes(byte_length,byteorder='big')
	return hashlib.sha256(sharedkey).digest()

def diffieHellman():
	global aesgcm
	r = random.randint(0,1000)
	client1.send(f"{r}\n".encode("utf-8"))
	print (f"Sent {r}")
	s = chunkify().strip()
	s = int(s)
	if r > s:
		p = sympy.randprime(10000,10000000)
		g = random.randint(30,100)
		b = random.randint(100,1000)
		client1.send(f"{p},{g},{pow(g,b,p)}\n".encode("utf-8"))
		alicepublic=chunkify().strip()
		privatekey = pow(int(alicepublic),b,p)
		aes_key = derriveKey(privatekey)
		aesgcm = AESGCM(aes_key)
	elif s > r:
		pgb = chunkify().strip().split(",")
		p = int(pgb[0])
		g = int(pgb[1])
		a = random.randint(100,1000)
		bob = int(pgb[2])

		alice = pow(g,a,p)
		client1.send(f"{alice}\n".encode("utf-8"))
		privatekey = pow(int(bob),a,p)
		aes_key = derriveKey(privatekey)
		aesgcm = AESGCM(aes_key)

	else:
		 diffieHellman()

def create_Server(myself):
	global server1
	global client1
	server1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	server1.bind((users[myself][0],users[myself][1]))
	server1.listen()
	client1,addr = server1.accept()
	print (f"Server started and listening on localhost:50000")

def chunkify():
	global client2
	buffer = ""
	while True:
		try:
			chunk = client2.recv(1).decode("utf-8")
			if chunk is None:
				continue
			if chunk != "\n":
				buffer += chunk
			else:
				return buffer
		except Exception as e:
			time.sleep(0.5)
			return None

def create_Client(user):
	global client2
	while True:
		try:
			client2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			client2.connect((users[user][0],users[user][1]))
			break
		except Exception as e:
			time.sleep(0.5)
			continue

def get_message(user):
	while True:
		msg=client2.recv(4096)
		if aesgcm:
			nonce = msg[:12]
			cipher = msg[12:]
			data = aesgcm.decrypt(nonce,cipher,None).decode("utf-8")
			print (f"{user}: {data}\n")
		else:
			print (f"{user}: {msg.decode('utf-8')}")

def send_message():
	global myself
	while True:
		message = input()
		print("\033[A\033[K", end="")
		nonce = os.urandom(12)
		cipher = aesgcm.encrypt(nonce,message.encode("utf-8"),None)
		client1.send(nonce+cipher)
		print (f"{myself}: {message}")

if __name__=="__main__":
	global myself
	global user
	myself = input("Enter your name: ")
	user = input("Who do you want to text: ")
	createserver = threading.Thread(target=create_Server, args=(myself,))
	createclient = threading.Thread(target=create_Client, args =(user,))
	createserver.start()
	createclient.start()
	while client1 is None or client2 is None:
		time.sleep(0.5)
	client1.send(f"Ready from my side\n".encode("utf-8"))
	while True:
		try:
			msg = chunkify()
			if msg == "Ready from my side":
				break
		except Exception as e:
			continue
	print ("Duplex connection established")
	diffieHellman()
	sending = threading.Thread(target=get_message, args=(user,))
	sending.start()
	getting = threading.Thread(target=send_message)
	getting.start()


