class KnownHosts:
  def __init__():
    self.hosts = {}
  
  def getHostByID(id):
    try:
      return self.hosts[id]
    except KeyError:
      raise UnknownHostException("No host with ID " + str(id))
  
  def registerHost(host):
    self.hosts[host.id] = host
  
  def unregisterHost(host):
    self.hosts.pop(host.id, None)

class Host:
  def __init__(uniqueID):
    self.id = uniqueID

class UnknownHostException(Exception): pass