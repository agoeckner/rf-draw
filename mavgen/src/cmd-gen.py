import xml.etree.ElementTree as ET
import os

DEFINITION_FILE = os.path.join(os.path.dirname(__file__), 'definitions/rf-draw.xml')
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__),'output/')
OUTPUT_FILE_PYTHON = "MAVLink.py"
OUTPUT_FILE_C = "Definitions.c"
OUTPUT_FILE_CH = "Definitions.h"

MAVLINK_MAX_COMMANDS = 256

pythonTypeMappings = {
	'int8_t': 'b',
	'uint8_t': 'B',
	'int16_t': 'h',
	'uint16_t': 'H',
	'int32_t': 'i',
	'uint32_t': 'I',
	'float': 'f',
	'double': 'd',
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
    file.write("import MAVLinkCore\n")
		file.write("import MAVMessageHandlers\n")
    
		#ENUMS
		for enum in enumList:
			name = enum[0]
			entries = enum[1]
			file.write("MAVENUM_" + name + "={\n")
			entStr = ""
			for entry in entries:
				file.write("\t\'" + str(entry[0]) + "\':" + str(entry[1]) + ",\n")
			file.write(entStr)
			file.write("};\n")
		for enum in enumList:
			name = enum[0]
			entries = enum[1]
			file.write("MAVENUM_NAME_" + name + "={\n")
			entStr = ""
			for entry in entries:
				file.write("\t" + str(entry[1]) + ":\'" + str(entry[0]) + "\',\n")
			file.write(entStr)
			file.write("};\n")

		#IDs
		file.write("MAVCMD_ID={\n")
		for message in messages:
			id = str(message[0])
			name = str(message[1])
			file.write("\t\'" + name + "\':" + id + ",\n")
		file.write("}\n")
		
		#FORMATS
		file.write("MAVCMD_FORMAT={\n")
		for message in messages:
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			format = '<'
			for field in fields:
				type = field[1]
				try:
					format += pythonTypeMappings[type]
				except KeyError:
					print("ERROR: INVALID TYPE: " + str(type))

			file.write("\t\'" + name + "\':\'" + format + "\',\n")
		file.write("}\n")
		
		#SEND COMMANDS
		for message in messages:
			if device not in message[3]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "MAVSEND_" + name
			file.write("def " + func + "(commandQueue,")
			for field in fields:
				file.write(str(field[0]) + ",")
			file.write("):\n")
			file.write("\tdata=struct.pack(MAVCMD_FORMAT[\'" + name + "\'],")
			for field in fields:
				file.write(str(field[0]) + ",")
			file.write(")\n")
			file.write("\tpacket=MAVLinkPacket(messageID=MAVCMD_ID[\'" + name + "\'],payload=data)\n")
			file.write("\tcommandQueue.put(packet)\n")

		#PARSE COMMANDS
		for message in messages:
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "MAVPARSE_" + name
			file.write("def " + func + "(programData, packet):\n")
			file.write("\tdata = struct.unpack(MAVCMD_FORMAT[\'" + name + "\'], packet.payload)\n")
			file.write("\tMAVMessageHandlers.MAVRCV_" + name + "(programData, *data)\n")

		#PARSE COMMAND DICTIONARY
		file.write("MAVCMD_PARSER={\n")
		for message in messages:
			if device not in message[4]:
				continue
			id = str(message[0])
			name = str(message[1])
			func = "MAVPARSE_" + name
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
		file.write("void (*MAVPARSER_FUNCTION[])(COMM_MAVLINK_PACKET packet) = \n{\n")
		for id in range(0, MAVLINK_MAX_COMMANDS):
			try:
				message = messageIdDict[id]
				file.write("\tMAVPARSE_" + str(message[1]))
			except KeyError:
				file.write("\tNULL");
			if id == MAVLINK_MAX_COMMANDS - 1:
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
			func = "MAVPARSE_" + name
			file.write("void " + func + "(COMM_MAVLINK_PACKET packet)\n{\n")
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
			func = "MAVSEND_" + name
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
			file.write("\tCOMM_MAVLINK_PACKET packet = commGeneratePacket((void*)(&data), payloadSize, messageID);\n")
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
		file.write("extern void (*MAVPARSER_FUNCTION[])(COMM_MAVLINK_PACKET packet);\n")
		
		#SEND COMMANDS
		for message in messages:
			#check for valid TX mode
			if device not in message[3]:
				continue
			id = str(message[0])
			name = str(message[1])
			fields = message[2]
			func = "MAVSEND_" + name
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
			func = "MAVPARSE_" + name
			file.write("void " + func + "(COMM_MAVLINK_PACKET packet);\n")
		
		file.write("#endif")
		file.close()

def main():
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
	for message in messages.iter('message'):
		id = int(message.get('id'))
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
