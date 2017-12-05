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

TIMEOUT_PACKET_ACK = 5 #seconds
TIMEOUT_SEND_HEARTBEAT = 5 #seconds
TIMEOUT_NACK = 1 #seconds
HEARTBEAT_TICKS_DEAD = 99999#3 #ticks

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
		Clock.schedule_interval(self.packetMgr.onRetransmitTick, TIMEOUT_PACKET_ACK)
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
		destination.packets[packet.sequence] = (currentTime, packet)
	
	def onRetransmitTick(self, dt):
		pass#print("RETRANSMIT PACKETS")
	
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
		pass
	
	def onPacketNegAck(self, srcAddr, packet):
		# print("Received negative acknowledgement for " + str(packet.sequence))
		# print("from " + str(srcAddr))
		try:
			source = self.hosts.getHostByAddress(srcAddr)
		except:
			return
		if packet.options & OPTION_ACK_BROADCAST:
			origDest = self.hosts.broadcast
			packets = origDest.packets
		else:
			origDest = source
			packets = source.packets
		# print("ORIGINALLY SENT TO " + str(origDest.address))
		# if len(packets) > 0 and packets[0][1] >= packet.sequence:
			# print("duplicate NACK")
			# return
		if packet.sequence >= 0xFFFF:
			seq = 1
		else:
			seq = packet.sequence + 1
		retrans = None
		if seq in packets:
			retrans = packets[seq]
		else:
			print("DUPLICATED NACK " + str(packet.sequence))
		while retrans != None:
			# print("RETRANSMIT PACKET WITH SEQ " + str(seq))
			self.transmit(srcAddr, retrans[1], sequence=seq,
				register = False)	
			
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
						
						if randint(0, 10) == 0:
							continue
						
						# Drop packets that are out of order.
						isBroadcast = packet.options & OPTION_BROADCAST
						if not source.checkAndSetSequence(isBroadcast, packet.sequence):
							# print("BAD PACKET WITH SEQUENCE: " + str(packet.sequence))
							# in this case, send NACK containing last good packet.
							# sender will retransmit important packets, resetting packetCounter
							# reset packet counter with special infrastructure packet?
							#	def _sendAcknowledgement(self, destAddr, broadcast, positive, sequence):
							missing = source.getLastRxSequence(isBroadcast)
							if missing not in source.retransmitRequested or \
									time.time() - source.retransmitRequested[missing] > TIMEOUT_NACK:
								source.retransmitRequested[missing] = time.time()
								self._sendAcknowledgement(source.address,
									isBroadcast, False, missing)
							continue
						# print("SUCCESS: " + str(packet.sequence))
					
					self.network.commandMgr.parseCommandPacket(frame.source, packet)
				except Exceptions.InvalidPacket as e:
					print("PACKET ERROR: " + str(e))

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
		self.packetCounter = randint(0, 0xFFFD)
		
		# Sequence numbers.
		self.rxPrevSeqUnicast = 0
		self.rxPrevSeqBroadcast = 0
		self.rxNextSeqUnicast = 0
		self.rxNextSeqBroadcast = 0
		
		# Packet retransmission data structures.
		self.packets = {}
		self.retransmitRequested = {}
	
	# Returns false if packet is out of order.
	def checkAndSetSequence(self, isBroadcast, sequence):
		if isBroadcast:
			if sequence == self.rxNextSeqBroadcast:
				self.rxPrevSeqBroadcast = self.rxNextSeqBroadcast
				if self.rxNextSeqBroadcast >= 0xFFFF:
					self.rxNextSeqBroadcast = 1
				else:
					self.rxNextSeqBroadcast += 1
				return True
		else:
			if sequence == self.rxNextSeqUnicast:
				self.rxPrevSeqUnicast = self.rxNextSeqUnicast
				if self.rxNextSeqUnicast >= 0xFFFF:
					self.rxNextSeqUnicast = 1
				else:
					self.rxNextSeqUnicast += 1
				return True
		return False
	
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