from . import PLinkCommandManager
from . import PLinkCore
from . import XBeeCore
from . import SerialInterface
from . import Exceptions
import queue
from collections import deque
from kivy.clock import Clock
from random import randint
import time

ADDR_BROADCAST = 0xFFFF
ADDR_UNICAST_MAX = 0xFFFD
ADDR_UNICAST_MIN = 0x0000

OPTION_INFRASTRUCTURE = 0x80
OPTION_IMPORTANT = 0x40
OPTION_BROADCAST = 0x20
OPTION_ACK_BROADCAST = 0x10

TIMEOUT_PACKET_ACK = 1 #seconds
TIMEOUT_SEND_HEARTBEAT = 5 #seconds
TIMEOUT_NACK = 1 #seconds
HEARTBEAT_TICKS_DEAD = 6 #ticks
RETRANSMIT_BATCH_SIZE = 200 #packets

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
		self.packetMgr.cmdAck = self.commandMgr.registerCommand("NET_ACK",
			callback = self.packetMgr.onPacketAck,
			passPacket = True)
		self.packetMgr.cmdNAck = self.commandMgr.registerCommand("NET_NACK",
			callback = self.packetMgr.onPacketNegAck,
			passPacket = True)
		
		# Set up timers.
		Clock.schedule_interval(self.packetMgr.drainInboundQueue, 1 / 10.)
		Clock.schedule_interval(self.packetMgr.onRetransmitTick, TIMEOUT_PACKET_ACK / 2)
		Clock.schedule_interval(self.hosts.onHeartbeatTick, TIMEOUT_SEND_HEARTBEAT)
		
		# Send out initial request.
		self.commandMgr.sendCommand(ADDR_BROADCAST, "NET_REQUEST",
			options = OPTION_INFRASTRUCTURE,
			sequence = self.hosts.broadcast.packetCounter)

class PacketManager:
	def __init__(self, network, queue):
		self.network = network
		self.hosts = network.hosts
		self.queueIn = queue['in']
		self.queueOut = queue['out']

	def transmit(self, destAddr, packet, options = 0, sequence = None,
			register = True):
		destination = self.hosts.getHostByAddress(destAddr)
				
		# Determine packet sequence number.
		if sequence == None:
			if packet.options & OPTION_INFRASTRUCTURE:
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
		if register:
			self._registerPacket(destination, packet.sequence, packet)
		
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
	
	def _registerPacket(self, destination, id, packet):
		currentTime = time.time()
		if destination == self.hosts.broadcast:
			for addr in self.hosts.hosts:
				host = self.hosts.hosts[addr]
				if host == destination:
					continue #broadcast
				host.broadcastPackets[packet.sequence] = (currentTime, packet)
		else:
			destination.packets[packet.sequence] = (currentTime, packet)
	
	def onRetransmitTick(self, dt):
		for addr in self.hosts.hosts:
			if addr == ADDR_BROADCAST:
				continue
			
			host = self.hosts.hosts[addr]
			
			# Get sequence number of first to retransmit.
			if host.txLastAckUnicast >= 0xFFFF:
				seq = 1
			else:
				seq = host.txLastAckUnicast + 1
			
			# Perform retransmission.
			retrans = None
			packets = host.packets
			if seq in packets:
				retrans = packets[seq]
				currentTime = time.time()
				if (currentTime - retrans[0]) > TIMEOUT_PACKET_ACK:
					count = 0
					while retrans != None and count < RETRANSMIT_BATCH_SIZE:
						count += 1
						self.transmit(addr, retrans[1], sequence=seq,
							register = False)
						packets[seq] = (currentTime, retrans[1])
						if seq >= 0xFFFF:
							seq = 1
						else:
							seq += 1
						if seq not in packets:
							break
						retrans = packets[seq]
			
			# Get sequence number of first to retransmit.
			if host.txLastAckBroadcast >= 0xFFFF:
				seq = 1
			else:
				seq = host.txLastAckBroadcast + 1
			
			# Perform broadcast retransmission.
			retrans = None
			packets = host.broadcastPackets
			if seq in packets:
				retrans = packets[seq]
				currentTime = time.time()
				if (currentTime - retrans[0]) > TIMEOUT_PACKET_ACK:
					count = 0
					while retrans != None and count < RETRANSMIT_BATCH_SIZE:
						count += 1
						self.transmit(addr, retrans[1], sequence=seq,
							register = False)
						packets[seq] = (currentTime, retrans[1])
						if seq >= 0xFFFF:
							seq = 1
						else:
							seq += 1
						if seq not in packets:
							break
						retrans = packets[seq]
		return True
	
	def _sendAcknowledgement(self, destAddr, broadcast, positive, sequence):
		if positive:
			cmd = self.cmdAck
		else:
			cmd = self.cmdNAck
		options = OPTION_INFRASTRUCTURE
		if broadcast:
			options = options | OPTION_ACK_BROADCAST
		packet = PLinkCore.PLinkPacket(
			commandID = cmd.id,
			payload = b'',
			options = options)
		self.transmit(destAddr, packet, sequence = sequence)
	
	def onPacketAck(self, srcAddr, packet):
		# Get host object from source address.
		try:
			source = self.hosts.getHostByAddress(srcAddr)
		except:
			return
		
		# Figure out whether the packet was originally sent via broadcast.
		if packet.options & OPTION_ACK_BROADCAST:
			packets = source.broadcastPackets
			source.txLastAckBroadcast = packet.sequence
		else:
			packets = source.packets
			source.txLastAckUnicast = packet.sequence
		
		# Remove from retransmission list.
		packets.pop(packet.sequence, None)
		
		
	def onPacketNegAck(self, srcAddr, packet):
		# Get host object from source address.
		try:
			source = self.hosts.getHostByAddress(srcAddr)
		except:
			return
		
		# Figure out whether the packet was originally sent via broadcast.
		if packet.options & OPTION_ACK_BROADCAST:
			packets = source.broadcastPackets
		else:
			packets = source.packets
		
		# Get sequence number of first to retransmit.
		if packet.sequence >= 0xFFFF:
			seq = 1
		else:
			seq = packet.sequence + 1
		
		# Perform retransmission.
		retrans = None
		if seq in packets:
			retrans = packets[seq]
			while retrans != None:
				self.transmit(srcAddr, retrans[1], sequence=seq,
					register = False)
				packets[seq] = (time.time(), retrans[1])
				
				if seq >= 0xFFFF:
					seq = 1
				else:
					seq += 1
				if seq not in packets:
					break
				retrans = packets[seq]
	
	def drainInboundQueue(self, dt):
		while True:
			# Get frame from inbound queue.
			try:
				frame = self.queueIn.get(False)
			except queue.Empty:
				break
			
			# Handle RX frames. (Or TX in the case of direct serial
			# connection with no radios.)
			if frame.apiID == XBeeCore.RX_API_ID or\
					frame.apiID == XBeeCore.TX_API_ID:
				try:
					packet = PLinkCore.PLinkPacket(byteArray = frame.payload)
					if not (packet.options & OPTION_INFRASTRUCTURE):
						try:
							source = self.hosts.getHostByAddress(frame.source)
						except:
							continue
						
						# For simulating packet loss.
						# if randint(0, 10) == 0:
							# continue
						
						# Drop packets that are out of order.
						isBroadcast = packet.options & OPTION_BROADCAST
						if source.checkAndSetSequence(isBroadcast, packet.sequence) == 0:
							lastRx = source.getLastRxSequence(isBroadcast)
							if isBroadcast:
								rtr = source.broadcastRetransmitRequested
							else:
								rtr = source.retransmitRequested
							if lastRx not in rtr or \
									time.time() - rtr[lastRx] > TIMEOUT_NACK:
								rtr[lastRx] = time.time()
								self._sendAcknowledgement(source.address,
									isBroadcast, False, lastRx)
							continue
						
						self._sendAcknowledgement(source.address,
							isBroadcast, True, packet.sequence)
					
					# Packet received properly. Parse command.
					self.network.commandMgr.parseCommandPacket(frame.source, packet)
					
				except Exceptions.InvalidPacket as e:
					print("PACKET ERROR: " + str(e))
		return True

class KnownHosts:
	def __init__(self, network):
		self.network = network
		self.hosts = {}
		self.hosts[ADDR_BROADCAST] = Host(ADDR_BROADCAST) #broadcast
		self.broadcast = self.hosts[ADDR_BROADCAST]
	
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
		print("REMOVED HOST WITH ADDRESS " + str(host.address))
		self.hosts.pop(host.address, None)
	
	def onNetRequest(self, source, packet):
		host = Host(source)
		host.setSequence(bool(packet.options & OPTION_BROADCAST), packet.sequence)
		self.registerHost(host)
		self.network.commandMgr.sendCommand(source, "NET_REPLY",
			options = OPTION_INFRASTRUCTURE,
			sequence = self.broadcast.packetCounter)
	
	def onNetReply(self, source, packet):
		if source not in self.hosts:
			host = Host(source)
			host.setSequence(True, packet.sequence)
			self.registerHost(host)
	
	def onHeartbeatTick(self, dt):
		self.network.commandMgr.sendCommand(ADDR_BROADCAST, "NET_HEARTBEAT",
			options = OPTION_INFRASTRUCTURE)
		# Check for expired heartbeats.
		remove = []
		for addr in self.hosts:
			if addr == ADDR_BROADCAST:
				continue
			host = self.hosts[addr]
			host.heartbeatTicks += 1
			if host.heartbeatTicks >= HEARTBEAT_TICKS_DEAD:
				remove.append(host)
		for host in remove:
			self.unregisterHost(host)
		return True
	
	def onNetHeartbeat(self, source):
		if source in self.hosts:
			self.hosts[source].heartbeatTicks = 0

class Host:
	def __init__(self, address):
		# Host's address.
		self.address = address
		
		# Number of heartbeat ticks without signal from host.
		self.heartbeatTicks = 0
		
		# Frame and packet counters for sequencing.
		self.frameCounter = 0
		self.packetCounter = randint(0, 0x00FF)
		
		# Sequence numbers.
		self.rxPrevSeqUnicast = 0
		self.rxPrevSeqBroadcast = 0
		self.rxNextSeqUnicast = 0
		self.rxNextSeqBroadcast = 0
		self.txLastAckUnicast = 0
		self.txLastAckBroadcast = 0
		
		# Packet retransmission data structures.
		self.packets = {}
		self.retransmitRequested = {}
		self.broadcastPackets = {}
		self.broadcastRetransmitRequested = {}
	
	# Returns 0 if packet is out of order.
	# Returns 1 if packet is correct.
	# Returns 2 if packet is duplicate #TODO
	def checkAndSetSequence(self, isBroadcast, sequence):
		if isBroadcast:
			if sequence == self.rxNextSeqBroadcast:
				self.rxPrevSeqBroadcast = self.rxNextSeqBroadcast
				if self.rxNextSeqBroadcast >= 0xFFFF:
					self.rxNextSeqBroadcast = 1
				else:
					self.rxNextSeqBroadcast += 1
				return 1
		else:
			if sequence == self.rxNextSeqUnicast:
				self.rxPrevSeqUnicast = self.rxNextSeqUnicast
				if self.rxNextSeqUnicast >= 0xFFFF:
					self.rxNextSeqUnicast = 1
				else:
					self.rxNextSeqUnicast += 1
				return 1
		return 0
	
	def setSequence(self, isBroadcast, sequence):
		if isBroadcast:
			self.rxPrevSeqBroadcast = self.rxNextSeqBroadcast
			if self.rxNextSeqBroadcast >= 0xFFFF:
				self.rxNextSeqBroadcast = 1
			else:
				self.rxNextSeqBroadcast = sequence + 1
		else:
			self.rxPrevSeqUnicast = self.rxNextSeqUnicast
			if self.rxNextSeqUnicast >= 0xFFFF:
				self.rxNextSeqUnicast = 1
			else:
				self.rxNextSeqUnicast = sequence + 1
	
	def getLastRxSequence(self, broadcast):
		if broadcast:
			return self.rxPrevSeqBroadcast
		else:
			return self.rxPrevSeqUnicast

class UnknownHostException(Exception): pass

class InvalidAddressException(Exception): pass