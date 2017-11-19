import Exceptions

# Packet configuration.
PLINK_SIZE_HEADER = 8
PLINK_SIZE_CHECKSUM = 4
PLINK_SIZE_EMPTY_PACKET = PLINK_SIZE_HEADER + PLINK_SIZE_CHECKSUM
PLINK_START_BYTE = 0xEB
PLINK_FORMAT_HEADER = '!BHBHH'
PLINK_FORMAT_CHECKSUM = '!I'

class PLinkPacket:
	# Create a new packet.
	def __init__(self,
			options = 0,
			sequence = 0,
			commandID = 0,
			payload = None):
		self.options = options
		self.sequence = sequence
		self.commandID = commandID
		self.payload = payload
	
	# Create a new packet from a serialized packet.
	def __init__(self, byteArray):
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
		localChecksum = calculateChecksum(
			bytes(byteArray[0:-PLINK_SIZE_CHECKSUM]))
		if localChecksum != checksum:
			raise InvalidPacket("Checksum does not match.")

		# Pull out the payload
		self.payload = packetArray[PLINK_SIZE_HEADER:-PLINK_SIZE_CHECKSUM]

	def serialize(self):
		# Construct the header
		length = len(self.payload)
		header = (PLINK_START_BYTE, length, self.options, self.sequence,
			self.commandID)
		packedHeader = struct.pack(PLINK_FORMAT_HEADER, *headerPython)
		
		# Concatenate body and header.
		message = packedHeader + self.payload
		
		# Calculate the checksum.
		checksum = calculateChecksum(message)
		packedChecksum = struct.pack(PLINK_FORMAT_CHECKSUM, checksumPython)
		
		return message + packedChecksum

# This function gets the CRC value of a bytearray
def calculateChecksum(array):
	length = len(array) - 1
	poly = 0x8005
	crc = 0xFFFF
	idx = 0
	while length >= 0:
		byte = int(struct.unpack('B', array[idx])[0])
		crc = crc ^ (0xFF & byte)
		i = 0
		while i < 8:
			if ((crc & 0x8000) ^ 0x8001) == 1:
				# Python does weird stuff, so truncate to 4 bytes
				crc = ((crc << 1) ^ poly) & 0xFFFF
			else:
				# Python does weird stuff, so truncate to 4 bytes
				crc = (crc << 1) & 0xFFFF
			i += 1
		idx += 1
		length -= 1
	return crc