from . import Exceptions
from . import PLinkCore

class PLinkCommandManager:
	def __init__(self, transmissionMgr):
		self.cmdCount = 0
		self.commandByID = {}
		self.commandByName = {}
		self.transmissionMgr = transmissionMgr

	# Registers a new PLink command. `paramaters` is a list of tuples
	# containing the name and the py.struct type of the parameter.
	# TYPE LIST: https://docs.python.org/3/library/struct.html#format-characters
	def registerCommand(self, name, parameters=[], callback=None):
		cmd = PLCommand(self.cmdCount, name, parameters, callback)
		self.commandByID[self.cmdCount] = cmd
		self.commandByName[name] = cmd
		self.cmdCount += 1
	
	def parseCommandPacket(self, source, packet):
		try:
			# Get command object.
			cmd = self.commandByID[packet.commandID]
		except KeyError:
			raise PLInvalidCommand(packet.commandID)
		# Unpack parameters and call callback.
		data = struct.unpack(cmd.format, packet.payload)
		cmd.callback(source, *data)
	
	def sendCommand(self, destination, cmdName, parameters=(), options=0):
		try:
			cmd = self.commandByName[cmdName]
		except KeyError:
			raise PLInvalidCommand(cmdName)
		data = struct.pack(cmd.format, *paramaters)
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
			self.format = "!" + str(map(lambda x: x[1], paramaters))
			self.callback = callback