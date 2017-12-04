from . import PLinkCommandManager
from . import PLinkCore
from . import XBeeCore
from . import SerialInterface
from . import Exceptions
import queue
from collections import deque
from kivy.clock import Clock

ADDR_BROADCAST = 0xFFFF
ADDR_UNICAST_MAX = 0xFFFD
ADDR_UNICAST_MIN = 0x0000

OPTION_INFRASTRUCTURE = 0x80
OPTION_IMPORTANT = 0x40

TIMEOUT_PACKET_ACK = 5 #seconds
TIMEOUT_DEVICE_DEAD = 15 #seconds
TIMEOUT_SEND_HEARTBEAT = 5 #seconds

class Network:
	def __init__(self, queue):
		self.queue = queue
	
		# Set up network.
		self.hosts = KnownHosts(self)
		self.packetMgr = PacketManager(self, queue)
		self.commandMgr = PLinkCommandManager.PLinkCommandManager(self, queue)
		
		# Register network commands.
		self.commandMgr.registerCommand("NET_REQUEST",
			callback = self.hosts.onNetRequest,
			passPacket = True)
		self.commandMgr.registerCommand("NET_REPLY",
			callback = self.hosts.onNetReply,
			passPacket = True)
		self.commandMgr.registerCommand("NET_HEARTBEAT",
			callback = self.hosts.onNetHeartbeat)
		self.cmdAck = self.commandMgr.registerCommand("NET_ACK",
			callback = self.packetMgr.onPacketAck,
			passPacket = True)
		self.cmdNAck = self.commandMgr.registerCommand("NET_NACK",
			callback = self.packetMgr.onPacketNegAck,
			passPacket = True)
		
		# Set up timers.
		Clock.schedule_interval(self.packetMgr.drainInboundQueue, 1 / 10.)
		Clock.schedule_interval(self.packetMgr.onRetransmitTick, TIMEOUT_PACKET_ACK)
		Clock.schedule_interval(self.hosts.onHeartbeatTick, TIMEOUT_SEND_HEARTBEAT)
		
		# Send out initial request.
		self.commandMgr.sendCommand(self.hosts.broadcast, "NET_REQUEST",
			options = OPTION_INFRASTRUCTURE)

class PacketManager:
	def __init__(self, network, queue):
		self.network = network
		self.hosts = network.hosts
		self.queueIn = queue['in']
		self.queueOut = queue['out']
		self.packets = {}
		self.lastAck = {}

	def transmit(self, destAddr, packet, options = 0, sequence = -1):
		destination = self.hosts.getHostByAddress(destAddr)
		
		if sequence == -1:
			if options & OPTION_INFRASTRUCTURE:
				packet.sequence = 0
			else:
				# Set packet sequence number.
				if destination.packetCounter >= 0xFFFF:
					destination.packetCounter = 1
				else:
					destination.packetCounter += 1
				packet.sequence = destination.packetCounter
		else:
			packet.sequence = sequence
		
		# Add packet to retransmission list.
		data = packet.serialize()
		self._registerPacket(destAddr, packet.sequence, packet)
		
		# Split data into multiple frames.
		length = len(data)
		maxPayloadLen = XBeeCore.TX_SIZE_MAX_PAYLOAD
		for i in range(0, length, maxPayloadLen):
			payload = data[i:i+maxPayloadLen]
			
			# Set frame sequence number.
			if destination.frameCounter >= 0xFF:
				destination.frameCounter = 1
			else:
				destination.frameCounter += 1
			
			# Construct frame.
			frame = XBeeCore.XBeeFrame(
				destination.frameCounter,
				destination.address,
				options,
				payload)
			
			# Transmit frame.
			serializedFrame = frame.serialize()
			self.queueOut.put(serializedFrame)
	
	def _registerPacket(self, destAddr, id, packet):
		self.packets[(destAddr, id)] = packet
	
	def onRetransmitTick(self, dt):
		print("RETRANSMIT PACKETS")
	
	def _sendAcknowledgement(self, destAddr, positive, sequence):
		if positive:
			cmd = self.cmdAck
		else:
			cmd = self.cmdNAck
		packet = PLinkCore.PLinkPacket(
			commandID = cmd.id,
			payload = b'',
			options = OPTION_INFRASTRUCTURE)
		self.transmit(destination, packet, sequence = sequence)
	
	def onPacketAck(self, source, packet):
		self.packets.pop((source, packet.sequence), None)
		if packet.sequence > self.lastAck[source]:
			self.lastAck[source] = packet.sequence
	
	def onPacketNegAck(self, source, packet):
		# while True:
			# try:
				
			# except KeyError:
				# break
		pass
	
	def drainInboundQueue(self, dt):
		while True:
			try:
				frame = self.queueIn.get(False)
			except queue.Empty:
				break
			if frame.apiID == XBeeCore.RX_API_ID or\
					frame.apiID == XBeeCore.TX_API_ID:
				try:
					packet = PLinkCore.PLinkPacket(byteArray = frame.payload)
					print("GOT PACKET WITH OPTIONS " + str(packet.options))
					if not (packet.options & OPTION_INFRASTRUCTURE):
						try:
							source = self.hosts.getHostByAddress(frame.source)
						except UnknownHostException:
							source = Host(frame.source)
						
						# Drop packets that are out of order.
						print("LASTRXSEQUENCE: " + str(source.rxLastPacketSequence) + " SEQUENCE: " + str(packet.sequence))
						if source.rxLastPacketSequence + 1 != packet.sequence:
							print("packet out of order. Dropping")
							continue
						source.rxLastPacketSequence = packet.sequence
					
					self.network.commandMgr.parseCommandPacket(frame.source, packet)
				except Exceptions.InvalidPacket as e:
					print("PACKET ERROR: " + str(e))
		

class KnownHosts:
	def __init__(self, network):
		self.network = network
		self.netRequestSequence = 0
		self.hosts = {}
		self.hosts[ADDR_BROADCAST] = Host(ADDR_BROADCAST) #broadcast
		self.broadcast = ADDR_BROADCAST
	
	def getHostByAddress(self, address):
		if address < ADDR_UNICAST_MIN or (address > ADDR_UNICAST_MAX and \
				address != ADDR_BROADCAST):
			raise InvalidAddressException("Address out of range.")
		try:
			return self.hosts[address]
		except KeyError:
			raise UnknownHostException("No host with address " + str(address))
	
	def registerHost(self, host):
		print("REGISTERED HOST WITH ADDRESS " + str(host.address))
		self.hosts[host.address] = host
	
	def unregisterHost(self, host):
		self.hosts.pop(host.id, None)
	
	def onNetRequest(self, source, packet):
		print("GOT NET REQUEST FROM " + str(source))
		host = Host(source)
		print("PACKET SEQUENCE " + str(packet.sequence))
		host.rxLastPacketSequence = packet.sequence
		self.registerHost(host)
		self.network.commandMgr.sendCommand(source, "NET_REPLY",
			options = OPTION_INFRASTRUCTURE)
	
	def onNetReply(self, source, packet):
		if source not in self.hosts:
			host = Host(source)
			host.rxLastPacketSequence = packet.sequence
			print("GOT REPLY WITH SEQUENCE " + str(host.rxLastPacketSequence))
			self.registerHost(host)
	
	def onHeartbeatTick(self, dt):
		self.network.commandMgr.sendCommand(ADDR_BROADCAST, "NET_HEARTBEAT",
			options = OPTION_INFRASTRUCTURE)
		# Check for expired heartbeats.
		# raise Exception("NOT DONE")
	
	def onNetHeartbeat(self, source):
		#TODO
		pass

class Host:
	def __init__(self, address):
		self.address = address
		self.frameCounter = 0
		self.packetCounter = 0
		self.rxLastPacketSequence = 0

class UnknownHostException(Exception): pass

class InvalidAddressException(Exception): pass