from . import Exceptions
from . import PLinkCore
from . import XBeeCore
import struct
import queue

class PLinkCommandManager:
	def __init__(self, network, queue):
		self.queueIn = queue['in']
		self.cmdCount = 0
		self.commandByID = {}
		self.commandByName = {}
		self.hosts = network.hosts
		self.packetMgr = network.packetMgr

	# Registers a new PLink command. `paramaters` is a list of tuples
	# containing the name and the py.struct type of the parameter.
	# TYPE LIST: https://docs.python.org/3/library/struct.html#format-characters
	def registerCommand(self, name, parameters=[], callback=None,
			passPacket=False):
		cmd = PLCommand(self.cmdCount, name, parameters, callback, passPacket)
		self.commandByID[self.cmdCount] = cmd
		self.commandByName[name] = cmd
		self.cmdCount += 1
		return cmd
	
	def parseCommandPacket(self, source, packet):
		try:
			# Get command object.
			cmd = self.commandByID[packet.commandID]
		except KeyError:
			raise PLInvalidCommand(packet.commandID)
		# Unpack parameters and call callback.
		data = struct.unpack(cmd.format, packet.payload)
		print("RECEIVED COMMAND: " + str(cmd.name))
		if cmd.passPacket:
			cmd.callback(source, packet, *data)
		else:
			cmd.callback(source, *data)
	
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
		self.packetMgr.transmit(destination, packet)
		print("SENT COMMAND: " + str(cmd.name))

class PLCommand:
	def __init__(self, id, name, parameters, callback, passPacket):
		self.id = id
		self.name = name
		self.parameters = parameters
		self.format = "!"
		for param in parameters:
			self.format += param[1]
		self.callback = callback
		self.passPacket = passPacket