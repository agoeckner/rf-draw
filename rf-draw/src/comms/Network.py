from . import PLinkCommandManager
from . import PLinkCore
from . import XBeeCore
from . import SerialInterface

ADDR_BROADCAST = 0xFFFF
ADDR_UNICAST_MAX = 0xFFFD
ADDR_UNICAST_MIN = 0x0000

class Network:
	def __init__(self, queue):
		self.queue = queue
	
		# Set up network.
		self.hosts = KnownHosts(self)
		self.transmissionMgr = TransmissionManager(self.hosts, self.queue)
		self.commandMgr = PLinkCommandManager.PLinkCommandManager(self.transmissionMgr)
		
		# Register network commands.
		self.commandMgr.registerCommand("NET_REQUEST",
			callback = self.hosts.onNetRequest)
		self.commandMgr.registerCommand("NET_REPLY",
			callback = self.hosts.onNetReply)
		self.commandMgr.registerCommand("NET_BROADCAST",
			callback = self.hosts.onNetBroadcast)
		
		# Send out initial request.
		self.commandMgr.sendCommand(self.hosts.broadcast, "NET_REQUEST")

class TransmissionManager:
	def __init__(self, hosts, queue):
		self.hosts = hosts
		self.queueOut = queue['out']

	def transmit(self, destination, packet, options = 0):
		host = destination#self.hosts.getHostByAddress(destination)
		
		print("SEND PACKET TO " + str(host.address))
		
		# Set packet sequence number.
		if host.packetCounter >= 0xFFFF:
			host.packetCounter = 1
		else:
			host.packetCounter += 1
		packet.sequence = host.packetCounter
		
		# Add packet to retransmission list.
		data = packet.serialize()
		self._registerPacket(packet.sequence, data)
		
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
				host.address,
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
	def __init__(self, network):
		self.network = network
		self.netRequestSequence = 0
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
	
	def onNetRequest(self, source):
		if source not in self.hosts:
			self.registerHost(Host(source))
		self.network.transmissionMgr.sendCommand(source, "NET_REPLY")
	
	def onNetReply(self, source):
		if source not in self.hosts:
			self.registerHost(Host(source))
	
	def onNetBroadcast(self, source):
		#TODO
		pass

class Host:
	def __init__(self, address):
		self.address = address
		self.frameCounter = 0
		self.packetCounter = 0

class UnknownHostException(Exception): pass