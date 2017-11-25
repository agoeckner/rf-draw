from . import PLinkCore
from . import XBeeCore
from . import SerialInterface

ADDR_BROADCAST = 0xFFFF
ADDR_UNICAST_MAX = 0xFFFD
ADDR_UNICAST_MIN = 0x0000

class TransmissionManager:
	def __init__(self, hosts, queue):
		self.hosts = hosts
		self.queueOut = queue['out']

	def transmit(destination, packet, options = 0):
		host = self.hosts.getHostByAddress(destination)
		
		# Set packet sequence number.
		if host.packetCounter >= 0xFFFF:
			host.packetCounter = 1
		else:
			host.packetCounter += 1
		packet.sequence = host.packetCounter
		
		# Add packet to retransmission list.
		data = packet.serialize()
		self.registerPacket(packet.sequence, data)
		
		# Split data into multiple frames.
		length = len(data)
		maxPayloadLen = XBeeCore.TX_SIZE_MAX_PAYLOAD
		for i in range(0, length, maxPayloadLen):
			payload = data[i:i+maxPayloadLen]
			
			# Set frame sequence number.
			if host.frameCounter >= 0xFF:
				host.frameCounter = 1
			else:
				host.frameCounter += 1
			
			# Construct frame.
			frame = XBeeCore.XBeeFrame(
				host.frameCounter,
				destination,
				options,
				payload)
			
			# Transmit frame
			serializedFrame = frame.serialize()
			self.queueOut.put(serializedFrame)
	
	def _registerPacket(self, id, packetSer):
		pass #add a packet to the list that need to be acknowledged
	
	def _ackPacket(self, id):
		pass #packet acknowledged, remove from retransmission list
		

class KnownHosts:
	def __init__(self):
		self.hosts = {}
		self.hosts[ADDR_BROADCAST] = Host(ADDR_BROADCAST) #broadcast
		self.broadcast = self.hosts[ADDR_BROADCAST]
	
	def getHostByAddress(self, address):
		try:
			return self.hosts[address]
		except KeyError:
			raise UnknownHostException("No host with address " + str(address))
	
	def registerHost(self, host):
		self.hosts[host.address] = host
	
	def unregisterHost(self, host):
		self.hosts.pop(host.id, None)

class Host:
	def __init__(self, address):
		self.address = address
		self.frameCounter = 0
		self.packetCounter = 0

class UnknownHostException(Exception): pass