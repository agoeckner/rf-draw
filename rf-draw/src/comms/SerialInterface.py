import threading
import time
import struct

# class SerialReader(threading.Thread):
	# def __init__(self, data, serial=None):
		# threading.Thread.__init__(self)
		
		# self.data = data
		# self.queueOut = data['uiQueue']
		# self.serial = serial
		# self.flagMAVLink = self.data['threadFlag']['MAVLinkPacket']
		
		# self.queueOut.put((self.data['threadFlag']['info'], "Initializing SerialInput."))

	# # Returns a new MAVLinkPacket
	# def deSerializePacket(self, packetArray):
		# if len(packetArray) < MAVLINK_EMPTY_PACKET_SIZE:
			# return None

		# # Unpack the header
		# headerStr = packetArray[0:6]
		# header = struct.unpack(MAVLINK_FORMAT_HEADER, headerStr)
		# if header[0] != MAVLINK_START_BYTE:
			# return None
		# payloadLen = header[1]
		# packetSequence = header[2]
		# systemID = header[3]
		# componentID = header[4]
		# commandID = int(header[5])
		
		# # Unpack the checksum
		# checksumStr = packetArray[-2:]
		# checksum = struct.unpack(MAVLINK_FORMAT_CHECKSUM, checksumStr)[0]
		
		# # Verify checksum
		# verifyStr = packetArray[1:-2]
		# localChecksum = getCRC16(bytes(verifyStr))
		# if localChecksum != checksum:
			# self.queueOut.put((self.data['threadFlag']['info'],
				# "BAD CHECKSUM! " + str(localChecksum) + " vs " + str(checksum)))
			# return None
		
		# # Pull out the payload
		# payload = packetArray[6:-2]
		
		# return MAVLinkPacket(systemID, componentID, commandID, 0, payload)
	
	# def run(self):
		# if not hasattr(self, 'serial'):
			# print("ERROR! SerialInput initialization failed.")
			# return
		# packetArray = bytearray(b'\x00')
		# prevByte = None
		# packetLen = 0
		# packetIdx = 0
		# while True:
			# try:
				# byteStr = self.serial.read()
				# byte = struct.unpack('<B', byteStr)[0]
				
				# # Beginning of the packet.
				# if prevByte == MAVLINK_START_BYTE and packetLen == 0:
					# packetLen = byte + MAVLINK_EMPTY_PACKET_SIZE
					# packetArray[0] = MAVLINK_START_BYTE
					# packetArray.append(byte)
					# packetIdx = 2
				# # Currently receiving packet.
				# elif packetLen > 0:
					# packetArray.append(byte)
					# packetIdx += 1
					# if packetIdx >= packetLen:
						# packet = self.deSerializePacket(packetArray)
						# if packet == None:
							# self.queueOut.put((self.data['threadFlag']['info'], "Bad packet."))
						# else:
							# self.queueOut.put((self.flagMAVLink, packet))
						# packetIdx = 0
						# packetLen = 0
						# packetArray = bytearray(b'\x00')
				# prevByte = byte
			# except serial.SerialException:
				# self.queueOut.put((self.data['threadFlag']['error'],
					# "FATAL\tSerial connection lost.\n\n"
					# "The connection to the serial port was lost. "
					# "Communication is no longer available."))
				# break

class SerialWriter(threading.Thread):
	def __init__(self, serial, queue):
		threading.Thread.__init__(self)
		print("Initializing SerialWriter.")
		self.queueIn = queue['in']
		self.queueOut = queue['out']
		self.serial = serial
	
	def run(self):
		if not hasattr(self, 'serial'):
			raise SerialInterfaceException("SerialWriter initialization failed.")
		
		while True:
			frame = self.queueOut.get(block=True)
			self.serial.write(frame)

class SerialInterfaceException(Exception): pass