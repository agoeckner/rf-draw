class KnownHosts:
	def __init__(self):
		self.hosts = {}
	
	def getHostByID(self, id):
		try:
			return self.hosts[id]
		except KeyError:
			raise UnknownHostException("No host with ID " + str(id))
	
	def registerHost(self, host):
		self.hosts[host.id] = host
	
	def unregisterHost(self, host):
		self.hosts.pop(host.id, None)

class Host:
	def __init__(self, uniqueID):
		self.id = uniqueID

class UnknownHostException(Exception): pass