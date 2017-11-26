from . import Exceptions
import struct
import hmac
import hashlib
import datetime

# Packet configuration.
PLINK_SIZE_HEADER = 8
PLINK_SIZE_CHECKSUM = 4
PLINK_SIZE_EMPTY_PACKET = PLINK_SIZE_HEADER + PLINK_SIZE_CHECKSUM
PLINK_START_BYTE = 0xEB
PLINK_FORMAT_HEADER = '!BHBHH'
PLINK_FORMAT_CHECKSUM = '!I'

# Autentication and Message Integrity
SESSION_KEY = b""
DIG_SIZE = 4 # in bytes
PRESHARED_KEY = b"34c0eb22f5f08c4ad26c05a84aefd70c95fce0691ee0f967e14cf4f6a63d8ccb"
SESSION_PIN = b""

class PLinkPacket:
	def __init__(self,
			byteArray = None,
			options = 0,
			sequence = 0,
			commandID = 0,
			payload = None):
		# Create a new packet.
		if byteArray == None:
			self.options = options
			self.sequence = sequence
			self.commandID = commandID
			self.payload = payload
		# Create a new packet from a serialized packet.
		else:
			if len(packetArray) < PLINK_SIZE_EMPTY_PACKET:
				raise InvalidPacket("Packet size less than minimum possible.")

			# Unpack the header
			header = struct.unpack(PLINK_FORMAT_HEADER,
				byteArray[0:PLINK_SIZE_HEADER])
			if header[0] != PLINK_START_BYTE:
				raise InvalidPacket("Invalid start byte.")
			if header[1] + PLINK_SIZE_EMPTY_PACKET != len(byteArray):
				raise InvalidPacket("Packet size does not match stated size.")
			self.options = header[2]
			try:
				self.sequence = int(header[3])
				self.commandID = int(header[4])
			except ValueError:
				raise InvalidPacket("Packet has malformed integer values.")

			# Unpack the checksum
			checksum = struct.unpack(PLINK_FORMAT_CHECKSUM,
				byteArray[-PLINK_SIZE_CHECKSUM:])[0]

			# Verify checksum
			# localChecksum = calculateChecksum(bytes(byteArray[:-PLINK_SIZE_CHECKSUM]))
			if !blake2s_verify(bytes(byteArray[:-PLINK_SIZE_CHECKSUM]), checksum): #localChecksum != checksum:
				raise InvalidPacket("Checksum does not match.")

			# Pull out the payload
			self.payload = packetArray[PLINK_SIZE_HEADER:-PLINK_SIZE_CHECKSUM]

	def serialize(self):
		# Construct the header
		length = len(self.payload)
		header = (PLINK_START_BYTE, length, self.options, self.sequence,
			self.commandID)
		packedHeader = struct.pack(PLINK_FORMAT_HEADER, *header)
		
		# Concatenate body and header.
		message = packedHeader + self.payload
		
		# Calculate the checksum.
		checksum = calculateChecksum(bytes(message))
		packedChecksum = struct.pack(PLINK_FORMAT_CHECKSUM, checksum)
		
		return message + packedChecksum

'''
Set Global Session PIN
	- Call on session init.
	- Send first packet with empty pin
	- Packet will still have a preshared key HMAC
'''
def set_pin(pin): # string pin
	global SESSION_PIN
	SESSION_PIN = bytes(pin)

'''
Convert arbitrary PIN to a 256-bit key
'''
def pin_to_key(pin): # byte pin
	h = hashlib.sha256()
	h.update(pin)
	# print( "Got pin: ")
	# print( pin) 
	return h.digest()

'''
Set Global Session Key
	- Call after set_pin()
'''
def set_key():
	today = datetime.datetime.now()
	r = today.day + today.month + today.year
	temp = bytes(r) # rondomness
	global SESSION_KEY 
	SESSION_KEY = pin_to_key(SESSION_PIN + temp + PRESHARED_KEY )
	# print( "Session Key set:")
	# print( SESSION_KEY )

'''
	blake2s HMAC library example
'''
def blake2s_hmac(packet):
	h = hashlib.blake2s( digest_size=DIG_SIZE, key=SESSION_KEY )
	h.update(packet)
	# print("Digest Size: " + str(h.digest_size) )
	return h.digest()

def blake2s_verify(packet, sig):
	good_sig = blake2s_hmac(packet)
	# use compare_digest() for timing based attacks
	return hmac.compare_digest(good_sig, sig)

# This function gets the authenticated checksum of a bytearray
def calculateChecksum(array):
	return blake2s_hmac(array)