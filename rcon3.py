#!/usr/bin/python3

# This code is a rewrite loosely based on work first done by this guy:
# https://github.com/frostschutz/SourceLib/blob/master/SourceRcon.py
# I've reworked most of it, and at this point there is only a few lines left of the original.
# A major difference is support for reliable multipacket response handling.
# This isn't really meant to be modular either, just a stand-alone RCON CLI.

import socket
import struct
import readline

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0
MAX_COMMAND_LENGTH=510          # Found by trial and error by frostschutz
MIN_MESSAGE_LENGTH=4+4+1+1      # command (4), id (4), string1 (1), string2 (1)
MAX_MESSAGE_LENGTH=4+4+4096+1   # command (4), id (4), string (4096), string2 (1)

class Rcon(object):
    def __init__(self, host, port, password, timeout):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.tcp = None
        self.requestId = 8 # Dangit, now I forget why I set this to 8.
        self.packtype = '<i'

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if(self.tcp):
            self.tcp.close()

    def connect(self):
        try:
            self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except OSError:
            print('Could not establish a socket.')
            self.disconnect()
            exit()
        try:
            self.tcp.settimeout(self.timeout)
            self.tcp.connect((self.host, self.port))
        except OSError:
            print('Could not connect to server.')
            self.disconnect()
            exit()
        try:
            self.__sendPacket(SERVERDATA_AUTH, self.password)
            # Empty SERVERDATA_RESPONSE_VALUE. requestID is in this one
            response = self.__receivePacket()
            if response[0] != SERVERDATA_RESPONSE_VALUE:
                print("Unexpected response type. Was not SERVERDATA_RESPONSE_VALUE. Got %d." % (response[0]))
                self.disconnect()
                exit()
            # SERVERDATA_AUTH_RESPONSE indicating requestID on success, -1 on failure
            response = self.__receivePacket()
            if response[0] != SERVERDATA_AUTH_RESPONSE:
                print("Unexpected response type. Was not SERVERDATA_AUTH_RESPONSE. Got %d." % (response[0]))
                self.disconnect()
                exit()
            if response[1] == -1:
                print("Authentication failure. Wrong password.")
                self.disconnect()
                exit()
        except ValueError:
            exit()

    def __sendPacket(self, commandType, body):
        if len(body) > MAX_COMMAND_LENGTH:
            raise ValueError('RCON message too large to send')
        self.requestId += 1
        packet = bytearray()
        packet += struct.pack(self.packtype, (len(body)+10))
        packet += struct.pack(self.packtype, self.requestId)
        packet += struct.pack(self.packtype, commandType)
        packet += str.encode(body)
        packet += b'\x00\x00'
        self.tcp.send(packet)

    def __receivePacket(self):
        try:
            packetSize = struct.unpack(self.packtype, self.tcp.recv(4))[0]
            packetID = struct.unpack(self.packtype, self.tcp.recv(4))[0]
            packetType = struct.unpack(self.packtype, self.tcp.recv(4))[0]
            body = self.tcp.recv(packetSize-6)
        except socket.timeout:
            print("Socket timed out. Did not recieve data.")
            self.disconnect()
            exit()

        return ((packetType, body))

    def sendCommand(self, body):
        self.__sendPacket(SERVERDATA_EXECCOMMAND, body)
        self.__sendPacket(SERVERDATA_RESPONSE_VALUE, "")
        response = self.__recieve()
        return response

    def __recieve(self):
        fullResponse = ''
        body = ''
        # pong = "".join(map(chr, b'\x00\x00\x00\x01\x00\x00\x00\x00')) # Works on my local server. Is this because it's Windows based?
        pong = "".join(map(chr, b'\x00\x01\x00\x00\x00\x00')) # Works on production server (Linux). OS difference?
        while(not pong in body):
            response = self.__receivePacket()
            packetType = response[0]
            body = "".join(map(chr, response[1]))
            if not pong in body:
                fullResponse += body
        return fullResponse

def main():
	addr = input("Connect to where? ")
    port = int(input("Port number? "))
    password = input("Password? ")
    # timeout = input("Timeout? ")

    #addr = '1.3.3.7'
    #port = 27015
    #password = '12345'
    timeout = 2.0

    console = Rcon(addr, port, password, int(timeout))
    console.connect()
    while(1):
        try:
            command = input("RCON3@%s> " % (addr))
            if(command == 'exit'):
                break
            print(console.sendCommand(command))
        except EOFError:
            console.disconnect()
            break

main()
