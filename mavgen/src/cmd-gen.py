import argparse
import os
import xml.etree.ElementTree as ET

DEFINITION_FILE = os.path.join(os.path.dirname(__file__), 'definitions/rf-draw.xml')
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__),'output/')
OUTPUT_FILE_PYTHON = "PLinkCmdInterface.py"
OUTPUT_FILE_C = "Definitions.c"
OUTPUT_FILE_CH = "Definitions.h"

PLINK_MAX_COMMANDS = 256

pythonTypeMappings = {
	'int8_t': 'b',
	'uint8_t': 'B',
	'int16_t': 'h',
	'uint16_t': 'H',
	'int32_t': 'i',
	'uint32_t': 'I',
	'float': 'f',
	'double': 'd',
	'char': 'c'
}

def exportCommandsPython(deviceList, deviceLang, enumList, messages):
	for device in deviceList:
		if deviceLang[device] != "python":
			continue
		
		fileName = OUTPUT_DIRECTORY + device + "/" + OUTPUT_FILE_PYTHON
		if not os.path.exists(os.path.dirname(fileName)):
			try:
				os.makedirs(os.path.dirname(fileName))
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise
		print("OUTPUT FILE " + fileName)
		file = open(fileName, 'w');
		
		#IMPORTS
		file.write("import struct\n")
		
		# Transmit and receive handlers.
		file.write("RECEIVER = None\n")
		file.write("def setRecieveHandler(obj): RECEIVER = obj\n")
		file.write("TRANSMITTER = None\n")
		file.write("def setTransmitHandler(obj): TRANSMITTER = obj\n")
		
		#ENUMS
		for enum in enumList:
			name = enum[0]
			entries = enum[1]
			file.write("PLENUM_" + name + "={\n")
			entStr = ""
			for entry in entries:
				file.write("\t\'" + str(entry[0]) + "\':" + str(entry[1]) + ",\n")
			file.write(entStr)
			file.write("};\n")
		for enum in enumList:
			name = enum[0]
			entries = enum[1]
			file.write("PLENUM_INV_" + name + "={\n")
			entStr = ""
			for entry in entries:
				file.write("\t" + str(entry[1]) + ":\'" + str(entry[0]) + "\',\n")
			file.write(entStr)
			file.write("};\n")

		#IDs
		file.write("PLCMD_ID={\n")
		for message in messages:
			id = str(message[0])
			name = str(message[1])
			file.write("\t\'" + name + "\':" + id + ",\n")
		file.write("}\n")
		
		#FORMATS
		file.write("PLCMD_FORMAT={\n")
		for message in messages:
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			format = '!'
			for field in fields:
				type = field[1]
				try:
					format += pythonTypeMappings[type]
				except KeyError:
					print("ERROR: unknown variable type: " + str(type))
			file.write("\t\'" + name + "\':\'" + format + "\',\n")
		file.write("}\n")
		
		#SEND COMMANDS
		# for message in messages:
			# if device not in message[3]:
				# continue
			# id = str(message[0])
			# name = str(message[1])
			# fields = message[2]
			# func = "PLSEND_" + name
			# file.write("def " + func + "(destination,")
			# for field in fields:
				# file.write(str(field[0]) + ",")
			# file.write("options=0):\n")
			# file.write("\tdata=struct.pack(PLCMD_FORMAT[\'" + name + "\'],")
			# for field in fields:
				# file.write(str(field[0]) + ",")
			# file.write(")\n")
			# file.write("\tpacket=PLinkPacket(commandID=PLCMD_ID[\'" + name +
				# "\'],payload=data,options=options)\n")
			# file.write("\tTRANSMITTER.transmit(destination,packet)\n")

		file.write("def PLSEND(destination, cmdName, fields=(), options=0):\n")
		file.write("\tdata=struct.pack(PLCMD_FORMAT[cmdName], *fields)\n")
		file.write("\tpacket=PLinkPacket(commandID=PLCMD_ID[cmdName],"
			"payload=data,options=options)\n")
		file.write("\tTRANSMITTER.transmit(destination,packet)\n")

		#PARSE COMMANDS
		for message in messages:
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "PLPARSE_" + name
			file.write("def " + func + "(packet):\n")
			file.write("\tdata = struct.unpack(PLCMD_FORMAT[\'" + name + "\'], packet.payload)\n")
			file.write("\tRECEIVER." + name + "(*data)\n")

		#PARSE COMMAND DICTIONARY
		file.write("PLCMD_PARSER={\n")
		for message in messages:
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			func = "PLPARSE_" + name
			file.write("\t" + id + ":" + func + ",\n")
		file.write("}\n")
		
		file.close()

def exportCommandsC(deviceList, deviceLang, enumList, messages):

	for device in deviceList:
		if deviceLang[device] != "c":
			continue
		
		fileName = OUTPUT_DIRECTORY + device + "/" + OUTPUT_FILE_C
		if not os.path.exists(os.path.dirname(fileName)):
			try:
				os.makedirs(os.path.dirname(fileName))
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise
		print("OUTPUT FILE " + fileName)
		file = open(fileName, 'w');
		
		#INCLUDES
		file.write("#include \"../Comms.h\"\n")
		file.write("#include \"./Definitions.h\"\n")

		#PARSER POINTERS
		messageIdDict = {}
		for message in messages:
			#check for valid RX mode
			if device not in message[4]:
				continue
			messageIdDict[message[0]] = message
		file.write("void (*PLPARSER_FUNCTION[])(COMM_PLINK_PACKET packet) = \n{\n")
		for id in range(0, PLINK_MAX_COMMANDS):
			try:
				message = messageIdDict[id]
				file.write("\tPLPARSE_" + str(message[1]))
			except KeyError:
				file.write("\tNULL");
			if id == PLINK_MAX_COMMANDS - 1:
				file.write("\n")
			else:
				file.write(",\n")
		file.write("};\n")
		
		#RECIEVE COMMANDS
		for message in messages:
			#check for valid RX mode
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "PLPARSE_" + name
			file.write("void " + func + "(COMM_PLINK_PACKET packet)\n{\n")
			if len(fields) > 0:
				file.write("\tstruct __attribute__((__packed__)) values\n\t{\n")
				for field in fields:
					file.write("\t\t" + str(field[1]) + " " + str(field[0]) + ";\n")
				file.write("\t};\n")
				file.write("\tunion converter\n\t{\n")
				file.write("\t\tstruct values *values;\n")
				file.write("\t\tvoid *bytes;\n")
				file.write("\t};\n")
				file.write("\tunion converter converter;\n")
				file.write("\tstruct values values;\n")
				file.write("\tconverter.values = &values;\n")
				file.write("\tconverter.bytes = packet.payload;\n")
			else:
				file.write("\t(void)packet;\n")
			file.write("\tMAVRCV_" + name + "(")
			args = ""
			for field in fields:
				args += "converter.values->" + str(field[0]) + ","
			if args != "":
				args = args[:-1]
			file.write(args + ");\n")
			file.write("}\n")

		#SEND COMMANDS
		for message in messages:
			#check for valid TX mode
			if device not in message[3]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "PLSEND_" + name
			file.write("void " + func + "(CIRCULAR_BUFFER* transmitBuffer")
			for field in fields:
				file.write("," + str(field[1]) + " " + str(field[0]))
			file.write(")\n{\n")
			file.write("\tstruct __attribute__((__packed__)) values\n\t{\n")
			for field in fields:
				file.write("\t\t" + str(field[1]) + " " + str(field[0]) + ";\n")
			file.write("\t};\n")
			file.write("\tstruct values data =\n\t{\n")
			args = ""
			for field in fields:
				args += "\t\t" + str(field[0]) + ",\n"
			if args != "":
				args = args[:-2]
			file.write(args + "\n\t};\n")
			file.write("\tuint8_t payloadSize = sizeof(struct values);\n")
			file.write("\tuint8_t messageID = " + id + ";\n")
			file.write("\tCOMM_PLINK_PACKET packet = commGeneratePacket((void*)(&data), payloadSize, messageID);\n")
			file.write("\tcommSendPacket(transmitBuffer, packet);\n")
			file.write("}\n")
			
		file.close()

def exportCommandsCH(deviceList, deviceLang, enumList, messages):
	for device in deviceList:
		if deviceLang[device] != "c":
			continue
		
		fileName = OUTPUT_DIRECTORY + device + "/" + OUTPUT_FILE_CH
		if not os.path.exists(os.path.dirname(fileName)):
			try:
				os.makedirs(os.path.dirname(fileName))
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise
		print("OUTPUT FILE " + fileName)
		file = open(fileName, 'w');
	
		#INCLUDES
		file.write("#ifndef DEFINITIONS_H\n#define DEFINITIONS_H\n")
		file.write("#include <stdint.h>\n")
		file.write("#include \"../Comms.h\"\n")
		
		#ENUMS
		for enum in enumList:
			name = enum[0]
			entries = enum[1]
			file.write("enum " + name + "\n{\n")
			entStr = ""
			for entry in entries:
				entStr += "\t" + str(entry[0] + " = " + str(entry[1]) + ",\n")
			if entStr != "":
				entStr = entStr[:-2]
			file.write(entStr)
			file.write("\n};\n")
		
		#PARSER POINTERS
		file.write("extern void (*PLPARSER_FUNCTION[])(COMM_PLINK_PACKET packet);\n")
		
		#SEND COMMANDS
		for message in messages:
			#check for valid TX mode
			if device not in message[3]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "PLSEND_" + name
			file.write("void " + func + "(CIRCULAR_BUFFER* transmitBuffer")
			for field in fields:
				file.write("," + str(field[1]) + " " + str(field[0]))
			file.write(");\n")
		
		#RECIEVE COMMANDS
		for message in messages:
			#check for valid RX mode
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "MAVRCV_" + name
			file.write("void " + func + "(")
			args = ""
			for field in fields:
				args += str(field[1] + " " + str(field[0]) + ",")
			if args == "":
				args = "void"
			else:
				args = args[:-1]
			file.write(args)
			file.write(");\n")

		#PARSE COMMANDS
		for message in messages:
			#check for valid RX mode
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "PLPARSE_" + name
			file.write("void " + func + "(COMM_PLINK_PACKET packet);\n")
		
		file.write("#endif")
		file.close()

def main():
	# Parse args
	# parser = argparse.ArgumentParser(description='Generate PLink command code.')
	# parser.add_argument('--definition', help='A definition file to include.')
	# parser.add_argument('--outputdir', help='Output directory.')
	# args = parser.parse_args()
	# return
	
	deviceList = []
	deviceLang = {}
	enumList = []
	messageList = []

	tree = ET.parse(DEFINITION_FILE)
	
	#root is the 'mavlink' tag
	root = tree.getroot()
	
	#devices
	enums = tree.find('devices')
	for dev in enums.iter('device'):
		name = str(dev.get('name'))
		language = str(dev.get('lang'))
		if language == "":
			print("ERROR: Define language for device \"" + name + "\"")
			return 1
		deviceList.append(name);
		deviceLang[name] = language;
		print("PARSED DEVICE " + str(name))
	
	#enums contains a bunch of enums
	lastVal = 0
	enums = tree.find('enums')
	for enum in enums.iter('enum'):
		entries = []
		name = str(enum.get('name'))
		for entry in enum.iter('entry'):
			ename = entry.get('name')
			val = entry.get('value')
			if val == None:
				val = lastVal
			else:
				val = int(val)
			lastVal = val + 1
			entries.append((ename, val))
		
		enumList.append((name, entries))
		print("PARSED ENUM " + str(name))
	
	#messages contains all commands/messages
	messages = tree.find('messages')
	commandID = 0
	for message in messages.iter('message'):
		id = commandID #int(message.get('id'))
		commandID += 1
		name = message.get('name')
		args = []
		
		# Which devices can send/receive?
		tx = []
		rx = []
		for device in message.iter('txdevice'):
			if device.text not in deviceList:
				print("ERROR: Device \"" + name + "\" not defined")
				return 1
			tx.append(device.text)
		for device in message.iter('rxdevice'):
			if device.text not in deviceList:
				print("ERROR: Device \"" + name + "\" not defined")
				return 1
			rx.append(device.text)
		if len(tx) == 0:
			tx = deviceList
		if len(rx) == 0:
			rx = deviceList
		
		#each field is another argument
		for field in message.iter('field'):
			ftype = field.get('type')
			fname = field.get('name')
			fdesc = field.text
			args.append((fname, ftype, fdesc))
		
		messageList.append((id, name, args, tx, rx))
		print("PARSED COMMAND " + str(id) + " " + str(name))
	
	#export
	exportCommandsPython(deviceList, deviceLang, enumList, messageList)
	exportCommandsC(deviceList, deviceLang, enumList, messageList)
	exportCommandsCH(deviceList, deviceLang, enumList, messageList)

main()
