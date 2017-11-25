from . import Exceptions

# Frame configuration.
XBEE_START_BYTE = 0x7E
XBEE_SIZE_HEADER = 4
XBEE_SIZE_CHECKSUM = 1
XBEE_FORMAT_HEADER = '!BHB'
XBEE_FORMAT_CHECKSUM = '!B'

TX_SIZE_HEADER = 4
TX_SIZE_EMPTY_FRAME = XBEE_SIZE_HEADER + TX_SIZE_HEADER + XBEE_SIZE_CHECKSUM
TX_SIZE_MAX_PAYLOAD = 100
TX_API_ID = 0x01
TX_FORMAT_HEADER = '!BHB'

RX_SIZE_HEADER = 4
RX_SIZE_EMPTY_FRAME = XBEE_SIZE_HEADER + RX_SIZE_HEADER + XBEE_SIZE_CHECKSUM
RX_SIZE_MAX_PAYLOAD = 100
RX_API_ID = 0x81
RX_FORMAT_HEADER = '!HBB'

TXS_SIZE_HEADER = 2
TXS_SIZE_EMPTY_FRAME = XBEE_SIZE_HEADER + TXS_SIZE_HEADER + XBEE_SIZE_CHECKSUM
TXS_API_ID = 0x89
TXS_FORMAT_HEADER = '!BB'

class XBeeFrame:
	# Create a new Tx frame.
	def __init__(self,
			frameID = 0,
			destination = 0,
			options = 0,
			payload = None):
		self.frameID = frameID
		self.destination = destination
		self.options = options
		self.payload = payload
		self.apiID = TX_API_ID
	
	# Create a new Rx frame.
	def __init__(self,
			source = 0,
			rssi = 0,
			options = 0):
		self.source = source
		self.rssi = rssi
		self.options = options
		self.apiID = RX_API_ID
	
	# Create a new frame from a serialized frame.
	def __init__(self, byteArray):
		# Unpack the header
		header = struct.unpack(XBEE_FORMAT_HEADER,
			byteArray[0:XBEE_SIZE_HEADER])
		if header[0] != XBEE_START_BYTE:
			raise InvalidFrame("Invalid start byte.")
		if header[1] != len(byteArray[3:-1]):
			raise InvalidFrame("Length does not match.")
		payload = byteArray[XBEE_SIZE_HEADER:-XBEE_SIZE_CHECKSUM]
		
		# Verify checksum.
		if not verifyChecksum(byteArray[3:]):
			raise InvalidFrame("Invalid checksum.")
		
		self.apiID = header[2]

		# Process Tx frames.
		if self.apiID == TX_API_ID:
			if len(byteArray) < TX_SIZE_EMPTY_FRAME:
				raise InvalidFrame("Frame size less than minimum possible.")
			txHeader = struct.unpack(TX_FORMAT_HEADER, payload[:TX_SIZE_HEADER])
			self.frameID = txHeader[0]
			self.destination = txHeader[1]
			self.options = txHeader[2]
			txPayload = payload[TX_SIZE_HEADER:]
			length = len(txPayload)
			if length > TX_SIZE_MAX_PAYLOAD:
				raise InvalidFrame("Payload size cannot be greater than 100.")
			if header[1] != length:
				raise InvalidFrame("Frame size does not match stated size.")
			self.payload = payload
		
		# Process Rx frames.
		elif self.apiID == RX_API_ID:
			if len(byteArray) < RX_SIZE_EMPTY_FRAME:
				raise InvalidFrame("Frame size less than minimum possible.")
			rxHeader = struct.unpack(RX_FORMAT_HEADER, payload[:RX_SIZE_HEADER])
			self.source = rxHeader[0]
			self.rssi = rxHeader[1]
			self.options = txHeader[2]
			rxPayload = payload[RX_SIZE_HEADER:]
			length = len(rxPayload)
			if length > RX_SIZE_MAX_PAYLOAD:
				raise InvalidFrame("Payload size cannot be greater than 100.")
			if header[1] != length:
				raise InvalidFrame("Frame size does not match stated size.")
			self.payload = payload
		
		# Process Tx Status frames.
		elif self.apiID == TXS_API_ID:
			if len(byteArray) != TXS_SIZE_EMPTY_FRAME:
				raise InvalidFrame("Frame size less than minimum possible.")
			txsHeader = struct.unpack(TXS_FORMAT_HEADER, payload[:TXS_SIZE_HEADER])
			self.originalFrameID = txsHeader[0]
			self.status = txsHeader[1]
		
		else:
			raise InvalidFrame("Invalid API ID.")

	def serialize(self):
		# Construct the payload.
		if self.apiID == TX_API_ID:
			length = 5 + len(self.payload)
			apiHeader = struct.pack(TX_FORMAT_HEADER, (
				self.frameID,
				self.destination,
				self.options))
			payload = apiHeader + self.payload
		else:
			raise Exception("Can only serialize Tx packets.")
		
		# Construct the header
		header = struct.pack(XBEE_FORMAT_HEADER, (
			TX_START_BYTE,
			length,
			TX_API_ID))
		
		frame = header + payload
		checksum = struct.pack(XBEE_FORMAT_CHECKSUM, (
			calculateChecksum(frame[3:])))
		
		return bytes(frame + checksum)

# This function gets the CRC value of a bytearray
def calculateChecksum(array):
	total = 0
	for byte in array:
		total += int(byte)
	total = 0xFF & total
	return 0xFF - total

# Returns true iff checksum is valid.
def verifyChecksum(array):
	total = 0
	for byte in array:
		total += int(byte)
	return total == 0xFF
	
	