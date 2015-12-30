#!/usr/bin/python

import getopt
import socket
import sys
import re 
import shutil
import time
from threading import Thread, Semaphore, Lock, Condition, Timer


host = "127.0.0.1"
port = 8765


clientResquestCV = Semaphore(0)
clientMonitor = Semaphore(1)
clientResuests = []
emailCount = 0

writeLock = Lock()
writeCv = Condition(writeLock)

# handle a single client request
class ConnectionHandler:
    curHostname = "" 
    curNid = ""
    recipients = [] 
    emailData = ""
    counter = 1
    done = False 
    name = 0
    time = 10
    oldTime = None

    def __init__(self, socket, i):
        self.socket = socket
        self.name = i

    def sendMsg(self, msg):
        try:
            sent = self.socket.send(msg.encode('utf-8')+"\n")
        except: 
            pass
            

    def collectInput(self,curData):
        clientData = curData
        if(self.oldTime == None):
            self.oldTime = time.time()
        try: 
            while(True):
                self.socket.settimeout(self.time)
                newData = self.socket.recv(100)
                clientData += newData
                if "\r\n" in clientData:
                    return clientData
        except:
            self.done = True

    def dataInput(self, curData):
        clientData = curData
        try:
            while(True):
                self.socket.settimeout(self.time)
                newData = self.socket.recv(100)
                clientData += newData
                if "\r\n.\r\n" in clientData:
                    return clientData
        except:
            self.done = True


    def parseInput(self, input):
        return str.strip(input[:str.find(input,"\r\n")])



    #Searching for the HELO command                                                               
    def handleBegin(self,collectedData):     
        collectedData = self.parseInput(collectedData)
        heloRe = "\A^[H,h][e,E][l,L][o,O]( )+[^ ]+( )*\Z"
        heloCommandRe = "\A^[H,h][e,E][l,L][o,O]\Z"
        # index 0 should be HELO 1 should be hostname                                             
        if( re.match(heloRe, collectedData)):
            self.hostName = str.strip(collectedData[str.find(collectedData," "):])
            self.sendMsg("250 oas25")
            return "Helo"
        elif( re.match(heloCommandRe, collectedData)):
            #send valid helo but invalid cou                                                      
            self.sendMsg("501 Syntax:  HELO yourhostname")
        else:
            self.handleError(collectedData, "Helo ")
        return "Begin"

            
    #Lookign for Mail From                                                                        
    def handleHelo(self,collectedData):
        collectedData = self.parseInput(collectedData)+" "
        
        mailFromCompRe = "\A^[M,m][a,A][I,i][l,L] [F,f][R,r][O,o][M,m]:( )+[^ ]+@[^ ]+[ ]*\Z"
        mailFromRe = "\A^[M,m][a,A][I,i][l,L] [F,f][R,r][o,O][M,m]: (.)*\Z"

        if( re.match(mailFromCompRe, collectedData)):
            self.sender  =  str.strip(   collectedData[(str.find(collectedData,":")+1):] )
            self.sendMsg("250 OK")
            return "MailFrom"
        elif( re.match(mailFromRe, collectedData)):
            sender = (str.strip( collectedData[str.find(collectedData,":")+1:]))
            if(sender=="" or (" " in sender)):
                self.sendMsg("501 Syntax: MAIL FROM: MAILING@ADDRS")
            else:
                self.sendMsg("555 <"+  sender + ">: Sender address rejected ")
        else:
            self.handleError(collectedData, "MAIL FROM: ")
   
        return "Helo"    
            
    def handleMailFrom(self, collectedData):
        collectedData = self.parseInput(collectedData) + " "

        mailToCompRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]:( )+[^ ]+@[^ ]+[ ]*\Z"
        mailToRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]: (.)*\Z"
        
        if( re.match(mailToCompRe, collectedData)):
            self.recipients.append (str.strip(   collectedData[     (str.find(collectedData,":")+1)    :] ))
            self.sendMsg("250 OK")
            return "RcptTo"
        elif( re.match(mailToRe, collectedData)):
            sender =  (str.strip(collectedData[str.find(collectedData,":")+1:]))
            if(sender=="" or (" " in sender)):
                self.sendMsg("501 Syntax: RCPT TO: MAILING@ADDRS")
            else:
                self.sendMsg("555 <"+ sender  + ">: Recipient address invalid ")
        else:
            self.handleError(collectedData, "RCPT TO: ")
        return "MailFrom"

    def handleRcptTo(self, collectedData):

        collectedData = self.parseInput(collectedData) + " "
        mailToCompRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]:( )+[^ ]+@[^ ]+[ ]*\Z"
        mailToRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]: (.)*\Z"
        dataRe = "\A^[D,d][A,a][T,t][A,a] \Z"
 
        if(re.match(mailToCompRe, collectedData)):
            self.recipients.append (str.strip(   collectedData[     (str.find(collectedData,":")+1)    :] ))
            self.sendMsg("250 OK")
            return "RcptTo"
        elif( re.match(mailToRe, collectedData)):
            sender =  (str.strip(collectedData[str.find(collectedData,":")+1:]))
            if(sender=="" or (" " in sender)):
                self.sendMsg("501 Syntax: RCPT TO: MAILING@ADDRS")
            else:
                self.sendMsg("555 <"+ sender  + ">: Recipient address invalid ")
        elif(re.match(dataRe, collectedData)):
             self.sendMsg("354 End data with <CR><LF>.<CR><LF>")
             return "Data"
        else:
            self.handleError(collectedData,"Data ")
        return "RcptTo"


    def handleData(self, collectData):
        
        collectData = str.strip(collectData[:str.find(collectData,"\r\n.\r\n")]);

        self.emailData = collectData;
        with writeLock:
            self.printToFile()
        self.sendMsg("250 OK")
        self.recipients[:] = []
        return "Helo"


    def printToFile(self):
        global emailCount
        
        if( emailCount == 0):
            open('mailbox', 'w').close()
            
        if(emailCount%32 == 0):
            while(emailCount%32 == 0 and not(emailCount == 0) ):
                writeCv.notify()
                writeCv.wait()
        else:
            emailCount = emailCount+1
        
        if( emailCount == 0):
            emailCount = emailCount +1
        
        f = open('mailbox', 'a+')
        f.write("Received: from client by oas25 (CS4410MP3) \n")
        f.write("Number: " + str(emailCount) +"\n")
        f.write("From: " + self.sender + "\n")
        f.write("To: ")
        for x in self.recipients:
            f.write(x + ", ")
        f.write("\n \n" + self.emailData +"\n \n")


    def handleError(self, badInput, wantedCommand):
        badInput = badInput+" "
        collectedData = badInput
        heloRe = "\A^[H,h][e,E][l,L][o,O]( )+[^ ]+( )*\Z"
        heloCommandRe = "\A^[H,h][e,E][l,L][o,O] \Z"

        mailFromCompRe = "\A^[M,m][a,A][I,i][l,L] [F,f][R,r][O,o][M,m]:( )+[^ ]+@[^ ]+[ ]*\Z"
        mailFromRe = "\A^[M,m][a,A][I,i][l,L] [F,f][R,r][o,O][M,m]: (.)*\Z"      
  
        mailToCompRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]:( )+[^ ]+@[^ ]+[ ]*\Z"
        mailToRe = "\A^[R,r][C,c][P,p][T,t] [T,t][o,O]: (.)*\Z"
        
        dataRe = "\A^[D,d][A,a][T,t][A,a] (.)*\Z"

        if(re.match(heloRe, badInput)):
            self.sendMsg("503 Error: duplicate HELO")
        elif(re.match(mailFromCompRe, badInput) and not(wantedCommand == "Halo" or wantedCommand == "Begin" )):
            self.sendMsg("503 Nested Mail Command")
        elif( re.match(mailFromCompRe, badInput) or re.match(mailToCompRe, badInput) or re.match(dataRe, badInput) or re.match(heloCommandRe, badInput)):
            self.sendMsg("503 Error: need " + wantedCommand +  "command")
        elif( re.match(mailToRe, collectedData)):
            sender =  (str.strip(collectedData[str.find(collectedData,":")+1:]))
            if(sender=="" or (" " in sender)):
                self.sendMsg("501 Syntax: RCPT TO: MAILING@ADDRS")
            else:
                self.sendMsg("555 <"+ sender  + ">: Recipient address invalid ")
        elif( re.match(mailFromRe, collectedData)):
            sender = (str.strip( collectedData[str.find(collectedData,":")+1:]))
            if(sender=="" or (" " in sender)):
                self.sendMsg("501 Syntax: MAIL FROM: MAILING@ADDRS")
            else:
                self.sendMsg("555 <"+  sender + ">: Sender address rejected ")
        elif( re.match(dataRe, collectedData)):
            self.sendMsg("501 Syntax: DATA")
        else:
            self.sendMsg("500 Command Not Recognized")
        

    def handle(self):
        collectedData = ""
        curStatus = "Begin"
        oldStatus =""
        t = None 
        oldlen = 0
        
        #continously poll for input
        while(True):
            #START TIMER HERE
            if(oldStatus != curStatus or len(self.recipients)!= oldlen ):
                self.time = 10
                self.oldTime = time.time()
            else: 
                self.time = 10 - (time.time() - self.oldTime) 

            oldlen = len(self.recipients)
            oldStatus = curStatus 
            
            if( curStatus == "Data"):
                collectedData = self.dataInput(collectedData)
            else: 
                collectedData = self.collectInput(collectedData)
            
            if self.done == True or ("\r\n" not in collectedData):
                break
                
            if (curStatus == "Begin"):
                #serch for Halo
                curStatus = self.handleBegin(collectedData)
            elif (curStatus == "Helo"):
                curStatus = self.handleHelo(collectedData)
            elif ( curStatus == "MailFrom"):
                curStatus = self.handleMailFrom(collectedData)
            elif (curStatus == "RcptTo"):
                curStatus = self.handleRcptTo(collectedData)
            elif(curStatus == "Data"): 
                curStatus = self.handleData(collectedData)
            collectedData = collectedData[str.find(collectedData,"\r\n")+2:]

        self.socket.close()

class Backup(Thread):
    def __init__(self):
        Thread.__init__(self)
        open('mailbox', 'w').close()
    
    def run(self):
        global emailCount
        written = 0
        while(True):
            with writeLock: 
                while(emailCount%32 != 0 or written == emailCount):
                    writeCv.wait()
                shutil.move('mailbox', "mailbox."+str((emailCount-31))+"-"+str(emailCount))
                written = emailCount
                emailCount = emailCount+1
                writeCv.notify()




# the main server loop
def serverloop():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # mark the socket so we can rebind quickly to this port number
    # after the socket is closed
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to the local loopback IP address and special port
    serversocket.bind((host, port))
    # start listening with a backlog of 5 connections
    serversocket.listen(5)
    Backup().start()

    for i in range (0,32):
        ClientHandler(serversocket, i).start()
    
        
#Build a Thread pool 
class ClientHandler(Thread):
    serverSocket = None
    name = 0;
    def __init__(self, serverSocket, i):
        Thread.__init__(self)
        self.name = i
        self.serverSocket = serverSocket
        
    def run(self):
        while(True):
            clientMonitor.acquire()
            (clientsocket, address) = self.serverSocket.accept()
            clientMonitor.release()
            ct = ConnectionHandler(clientsocket, self.name)
            ct.handle()
       

# You don't have to change below this line.  You can pass command-line arguments
# -h/--host [IP] -p/--port [PORT] to put your server on a different IP/port.
opts, args = getopt.getopt(sys.argv[1:], 'h:p:', ['host=', 'port='])

for k, v in opts:
    if k in ('-h', '--host'):
        host = v
    if k in ('-p', '--port'):
        port = int(v)

print("Server coming up on %s:%i" % (host, port))
serverloop()
