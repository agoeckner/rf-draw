from . import Exceptions
import struct
import hmac
import hashlib
import datetime
from app import globals

# Packet configuration.
PLINK_SIZE_HEADER = 8
PLINK_SIZE_CHECKSUM = 4
PLINK_SIZE_EMPTY_PACKET = PLINK_SIZE_HEADER + PLINK_SIZE_CHECKSUM
PLINK_START_BYTE = 0xEB
PLINK_FORMAT_HEADER = '!BHBHH'
PLINK_FORMAT_CHECKSUM = '!I'


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
			if len(byteArray) < PLINK_SIZE_EMPTY_PACKET:
				raise Exceptions.InvalidPacket("Packet size less than minimum possible.")

			# Unpack the header
			header = struct.unpack(PLINK_FORMAT_HEADER,
				byteArray[0:PLINK_SIZE_HEADER])
			if header[0] != PLINK_START_BYTE:
				raise Exceptions.InvalidPacket("Invalid start byte.")
			if header[1] + PLINK_SIZE_EMPTY_PACKET != len(byteArray):
				raise Exceptions.InvalidPacket("Packet size does not match stated size.")
			self.options = header[2]
			try:
				self.sequence = int(header[3])
				self.commandID = int(header[4])
			except ValueError:
				raise Exceptions.InvalidPacket("Packet has malformed integer values.")

			# Unpack the checksum
			checksum = byteArray[-PLINK_SIZE_CHECKSUM:]

			# Verify checksum

			if not blake2s_verify(bytes(byteArray[:-PLINK_SIZE_CHECKSUM]), checksum):
				raise Exceptions.InvalidPacket("Checksum does not match.")

			# Pull out the payload
			self.payload = byteArray[PLINK_SIZE_HEADER:-PLINK_SIZE_CHECKSUM]

	def serialize(self):
		# Construct the header
		length = len(self.payload)
		header = (PLINK_START_BYTE, length, self.options, self.sequence,
			self.commandID)
		packedHeader = struct.pack(PLINK_FORMAT_HEADER, *header)
		
		# Concatenate body and header.
		message = packedHeader + self.payload
		
		# Calculate the checksum.
		checksum = blake2s_hmac(bytes(message))
		
		return message + checksum


'''
	blake2s HMAC library example
'''
def blake2s_hmac(packet):
	print("[PLinkCore] Session Pin:")
	print(globals.SESSION_KEY)	

	h = hashlib.blake2s( digest_size=globals.DIG_SIZE, key=globals.SESSION_KEY )
	h.update(packet)
	# print("Digest Size: " + str(h.digest_size) )
	return h.digest()

def blake2s_verify(packet, sig):
	good_sig = blake2s_hmac(packet)
	# use compare_digest() for timing based attacks
	return hmac.compare_digest(good_sig, sig)
