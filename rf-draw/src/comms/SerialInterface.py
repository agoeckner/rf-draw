import threading
import time
import serial
import struct
from . import XBeeCore
from .Exceptions import *

class SerialReader(threading.Thread):
	def __init__(self, serial, queue):
		threading.Thread.__init__(self)
		print("Initializing SerialReader.")
		self.queueIn = queue['in']
		print("SERIALREADER QUEUEIN " + str(self.queueIn))
		self.queueOut = queue['out']
		self.serial = serial
		self.setDaemon(True)
		self.start()

	def run(self):
		if not hasattr(self, 'serial'):
			print("ERROR! SerialReader initialization failed.")
			return
		frame = bytes(0x00)
		prevPrevByte = bytes(0x00)
		prevByte = bytes(0x00)
		frameLen = 0
		while True:
			try:
				# Beginning of frame.
				startByte = self.serial.read(size=1)
				while ord(startByte) != XBeeCore.XBEE_START_BYTE:
					startByte = self.serial.read(size=1)

				# Read length.
				rawLength = self.serial.read(size=2)
				length = struct.unpack("!H", rawLength)[0]

				# Read data and checksum.
				remainder = self.serial.read(size=length + XBeeCore.XBEE_SIZE_CHECKSUM)
				
				try:
					frame = XBeeCore.XBeeFrame(
						byteArray = startByte + rawLength + remainder)
					print("GOT FRAME: " + str(frame))
					# print("SOURCE: " + str(frame.source))
					# print("RSSI: " + str(frame.rssi))
					print("PAYLOAD: " + str(frame.payload))
					self.queueIn.put(frame)
				except InvalidFrame as e:
					print("ERROR: " + str(e))
				
			except serial.SerialException as e:
				raise SerialInterfaceException("receive failed")

class SerialWriter(threading.Thread):
	def __init__(self, serial, queue):
		threading.Thread.__init__(self)
		print("Initializing SerialWriter.")
		self.queueIn = queue['in']
		self.queueOut = queue['out']
		self.serial = serial
		self.setDaemon(True)
		self.start()
	
	def run(self):
		if not hasattr(self, 'serial'):
			raise SerialInterfaceException("SerialWriter initialization failed.")
		
		while True:
			try:
				frame = self.queueOut.get(block=True)
				self.serial.write(frame)
			except serial.SerialException as e:
				raise SerialInterfaceException("transmit failed")

class SerialInterfaceException(Exception): pass