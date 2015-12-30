#!/usr/bin/python                                                                                                                                                                                          
                                                                                                                                                   
import sys
import socket
import datetime
from threading import Thread
from random import randint

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
#toaddr = sys.argv[3] if len(sys.argv) > 3 else "nobody@example.com"
#fromaddr = sys.argv[4] if len(sys.argv) > 4 else "nobody@example.com"

def send(socket, message):
    # In Python 3, must convert message to bytes explicitly.                                                                                                                                                
    # In Python 2, this does not affect the message.                                                                                                                                                        
    socket.send(message.encode('utf-8'))

def sendmsg(msgid, hostname, portnum):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, portnum))

    commandlst = ["", " ", "Helo ", "helo ", "HELO","Mail from:", "Mail from: ", "RCPT TO: " , "RCPT TO: ","data", "DATA ", "DATA ", "bats "]
    begParamList = ["", " ","kalsmo#44e", "  b#RInale", "  nai[]l", "fai334l", "Helo", "Mail From: ", "RCPT To: ", "DATA "]
    endParamList = ["", " ", "@", " @", "@kalsmo#44e", "  b#RInale", "  nai[]l", "fai334al", "@Helo@df", "@Mail From: ", "@RCPT To: ", "@DATA ", "@sdsd" ]

    for i in range (1, 1000):
        first = commandlst[randint(0,len(commandlst)-1)]
        mid = begParamList[randint(0,len(begParamList)-1)]
        last = endParamList[randint(0,len(endParamList)-1)]
        
        if 'd' in first or 'D' in first:
            print first 
            mid =""
            last = ""
            

        if(randint(0,1) == 0):
            end = "\r\n"
        else: 
            end = "\r\n.\r\n"

        total = first + mid + last + end
    
        send(s,total)
        print(s.recv(500))
    s.close()
    
for i in range(0, 32):
    thread = Thread(target = sendmsg, args = (10,host, port ))
    thread.start()





