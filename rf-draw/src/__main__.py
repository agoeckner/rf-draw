import app
from comms import *
import os
import queue

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '/config.ini')

class RFDraw:
	def __init__(self):
		# Import settings
		# config = ConfigParser.SafeConfigParser()
		# config.read(CONFIG_FILE)
		comms_baud_rate = 115200 #config.get("comms", "baud_rate")
		comms_port = "/dev/null" #config.get("comms", "port")

		# Set up inter-thread communication queues.
		self.queue = {
			'out': queue.Queue(),
			'in': queue.Queue(),
			'error': queue.Queue()}
		
		# Open serial connection.
		try:
			self.serial = serial.Serial(comms_port, comms_baud_rate)
		except serial.SerialException as e:
			print("ERROR: Could not connect to radio!")
			raise e
		self.serialIn = SerialInterface.SerialReader(self.serial, self.queue)
		self.serialOut = SerialInterface.SerialWriter(self.serial, self.queue)
		
		# Set up network.
		self.network = Network.Network()
		
		# Set up the UI.
		self.app = app.MyPaintApp(self.netTransmissionMgr)
	
	def run(self):
		self.app.run()

if __name__ == '__main__':
	RFDraw().run()