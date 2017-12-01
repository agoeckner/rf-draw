import argparse
import sys

if __name__ == '__main__':
	argv = []
	if "--" in sys.argv:
		index = sys.argv.index("--")
		argv = sys.argv[1:index]
		sys.argv = [sys.argv[0]] + sys.argv[index+1:]

import app
from comms import *
import os
import serial
import queue
from app import keyboard



class RFDraw:
	def __init__(self):
		# Parse command-line arguments.
		global argv
		
		parser = argparse.ArgumentParser(
			prog = "rf-draw",
			description = "The RF-Draw device software.")
		parser.add_argument(
			'--port',
			nargs = 1,
			default = ["/dev/null"])  # ["COM1"])
		args = parser.parse_args(argv)
	
		# Import settings
		# config = ConfigParser.SafeConfigParser()
		# config.read(CONFIG_FILE)
		comms_baud_rate = 57600 #config.get("comms", "baud_rate")
		comms_port = args.port[0]#"COM1" #config.get("comms", "port")
		print("Using serial port " + str(comms_port) + ".")

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
			print("Restarting application...")
			# os.execv(sys.executable, ['python'] + sys.argv)
			exit(-1)
			raise e
		self.serialIn = SerialInterface.SerialReader(self.serial, self.queue)
		self.serialOut = SerialInterface.SerialWriter(self.serial, self.queue)
		
		# Set up network.
		self.network = Network.Network(self.queue)
		
		# Set up the UI.
		self.app = app.MyPaintApp(self.network)
	
	def run(self):
		self.app.run()

if __name__ == '__main__':
	keyboard.PinInput().run()
	RFDraw().run()