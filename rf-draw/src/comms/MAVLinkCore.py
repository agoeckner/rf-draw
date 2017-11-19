MAVLINK_SYSTEM_ID = 2
MAVLINK_COMPONENT_ID = 0
MAVLINK_EMPTY_PACKET_SIZE = 8
MAVLINK_START_BYTE = 0xFE
MAVLINK_FORMAT_HEADER = '<BBBBBB'
MAVLINK_FORMAT_CHECKSUM = '<H'

# Retransmission time in seconds.
MAVLINK_RETRANSMITION_TIME = 5

class MAVLinkPacket:
	def __init__(self, systemID=MAVLINK_SYSTEM_ID, componentID=MAVLINK_COMPONENT_ID,
		commandID=0, sequence=0, payload=None):
		self.systemID = systemID
		self.componentID = componentID
		self.commandID = commandID
		self.sequence = sequence
		self.payload = payload

	def serialize(self):
		# Construct the header
		length = len(self.payload)
		headerPython = (MAVLINK_START_BYTE, length, self.sequence, MAVLINK_SYSTEM_ID,
			MAVLINK_COMPONENT_ID, self.commandID)
		header = struct.pack(MAVLINK_FORMAT_HEADER, *headerPython)
		
		# Concatenate body and header.
		message = header + self.payload
		
		# Calculate the checksum.
		checksumPython = getCRC16(message[1:])
		checksum = struct.pack(MAVLINK_FORMAT_CHECKSUM, checksumPython)
		
		return message + checksum

key = 'some random string we need to store as global var'
pin = 'global var set by sha256(pin_from_presenter)'
mac_key = 'global session persistant key set by setMacKey'

'''
	Replaces getCRC() to carry out message integrity and
	message authentication checks.
'''
def verifySource(array):
	res = 'invalid'
	# mac_key = makeKey(key, pin)
	# res = getHash(array, mac_key)
	return res

'''
	setMacKey is run after the address exchange phase
	done during init. Returns the maximum 
'''
def setMacKey():
	# addr = getMaxUnicastAddr()
	mKey = 'key set with max Unicast address in netework'
	return mKey


# This function gets the CRC value of a bytearray
def getCRC16(array):
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