from . import Exceptions
from . import PLinkCore
from . import XBeeCore
import struct
import queue

class PLinkCommandManager:
	def __init__(self, network, queue):
		self.queueIn = queue['in']
		print("CMDMGR QUEUEIN " + str(self.queueIn))
		self.cmdCount = 0
		self.commandByID = {}
		self.commandByName = {}
		self.hosts = network.hosts
		self.transmissionMgr = network.transmissionMgr

	# Registers a new PLink command. `paramaters` is a list of tuples
	# containing the name and the py.struct type of the parameter.
	# TYPE LIST: https://docs.python.org/3/library/struct.html#format-characters
	def registerCommand(self, name, parameters=[], callback=None):
		cmd = PLCommand(self.cmdCount, name, parameters, callback)
		self.commandByID[self.cmdCount] = cmd
		self.commandByName[name] = cmd
		self.cmdCount += 1
	
	def drainInboundQueue(self, dt):
		while True:
			try:
				frame = self.queueIn.get(False)
			except queue.Empty:
				break
			print("Received frame with API ID " + str(frame.apiID))
			# if frame.apiID != XBeeCore.RX_API_ID:
				# continue
			try:
				packet = PLinkCore.PLinkPacket(byteArray = frame.payload)
				self.parseCommandPacket(0xFFFE, packet)
			except Exceptions.InvalidPacket as e:
				print("PACKET ERROR: " + str(e))
	
	def parseCommandPacket(self, source, packet):
		try:
			# Get command object.
			cmd = self.commandByID[packet.commandID]
		except KeyError:
			raise PLInvalidCommand(packet.commandID)
		# Unpack parameters and call callback.
		data = struct.unpack(cmd.format, packet.payload)
		print("RECEIVED COMMAND: " + str(cmd.name))
		#TODO
		try:
			host = self.hosts.getHostByAddress(source)
		except:
			host = self.hosts.broadcast
		cmd.callback(host, *data)
	
	def sendCommand(self, destination, cmdName, parameters=(), options=0):
		try:
			cmd = self.commandByName[cmdName]
		except KeyError:
			raise PLInvalidCommand(cmdName)
		data = struct.pack(cmd.format, *parameters)
		packet = PLinkCore.PLinkPacket(
			commandID = cmd.id,
			payload = data,
			options = options)
		self.transmissionMgr.transmit(destination, packet)

class PLCommand:
	def __init__(self, id, name, parameters, callback):
		self.id = id
		self.name = name
		self.parameters = parameters
		self.format = "!"
		for param in parameters:
			self.format += param[1]
		self.callback = callback
		print("NEW COMMAND: " + name)
		print(parameters)
		print(self.format)