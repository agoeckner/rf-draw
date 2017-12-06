# Turn off Kivy's console output.
from kivy.config import Config
Config.set("kivy", "log_level", "warning")

import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from random import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line
from kivy.core.window import Window
from kivy.config import Config
from kivy.uix.label import Label
import hashlib
import datetime
import time
from subprocess import call

import globals


def on_enter(instance, value):
	print('User pressed enter in', instance)

'''
Convert arbitrary PIN to a 256-bit key
'''
def pin_to_key(pin):
	h = hashlib.sha256()
	h.update(pin)
	h.hexdigest()
	return h.digest()

'''
Set Global Session Key
	- Call after set_pin()
'''
def set_key():
	today = datetime.datetime.now()
	r = today.day + today.month + today.year
	temp = bytes(r)
	globals.SESSION_KEY = pin_to_key(globals.S_PIN + temp + globals.PRESHARED_KEY  )
	print("[Draw] Session Pin:")
	print(globals.SESSION_KEY)  


class MyPaintWidget(Widget):
	line = {}
	app = None

	def on_touch_down(self, touch):
		hue = random()
		self.lineStart('local', hue, touch.x, touch.y)
		self.app.network.commandMgr.sendCommand(
			self.app.network.hosts.broadcast.address,
			"APP_DRAW_TOUCH_DOWN",
			(hue, touch.x, touch.y))
	
	def lineStart(self, identifier, hue, x, y):
		color = (hue, 1, 1)
		with self.canvas:
			Color(*color, mode='hsv')
			d = 30.
			Ellipse(pos=(x - d / 2, y - d / 2), size=(d, d))
			self.line[identifier] = Line(points=(x, y))
	
	def lineContinue(self, identifier, x, y):
		self.line[identifier].points += [x, y]

	def on_touch_move(self, touch):
		if random() > 0.40:
			return
		self.lineContinue('local', touch.x, touch.y)
		self.app.network.commandMgr.sendCommand(
			self.app.network.hosts.broadcast.address,
			"APP_DRAW_TOUCH_CONTINUE",
			(touch.x, touch.y))


class MyPaintApp(App):
	def __init__(self, network, *args, **kwargs):
		super(MyPaintApp, self).__init__(*args, **kwargs)
		
		# Register callbacks.
		self.network = network
		self.network.commandMgr.registerCommand(
			"APP_DRAW_TOUCH_DOWN",
			[("hue", "d"), ("x", "d"), ("y", "d")],
			self.onRemoteDrawStart)
		self.network.commandMgr.registerCommand(
			"APP_DRAW_TOUCH_CONTINUE",
			[("x", "d"), ("y", "d")],
			self.onRemoteDrawContinue)
		self.network.commandMgr.registerCommand(
			"APP_DRAW_CLEAR",
			callback = self.onRemoteClear)
		
	def onRemoteDrawStart(self, source, hue, x, y):
		self.painter.lineStart(source, hue, x, y)
	
	def onRemoteDrawContinue(self, source, x, y):
		self.painter.lineContinue(source, x, y)
	
	def onRemoteClear(self, source):
		self.painter.canvas.clear()
	
	def build(self):
		# Set full screen
		if globals.RPI:
			Window.fullscreen = 'auto'
		else:
			Window.fullscreen = False
	
		# pin entry stuff
		Config.set("kivy", "keyboard_mode", 'dock')
		Config.write()
		self.set_keyboard('numeric.json' )
		self.input = ''
		# Show PIN to user as they type in
		self.textbox = Label(text='Enter PIN',
			pos_hint={ 'top': 1},
			size_hint = (.8,.8),
			font_size='90sp')
		Window.add_widget(self.textbox)

	def clear_canvas(self, obj):
		self.painter.canvas.clear()
		self.network.commandMgr.sendCommand(
			self.network.hosts.broadcast.address,
			"APP_DRAW_CLEAR", ())
	'''
		Pin Entry code
	'''
	def set_keyboard(self, layout):
		""" Change the keyboard layout to the one specified by string layout. """
		kb = Window.request_keyboard(
			self._keyboard_close, self)
		if kb.widget: # Keyboard is a widget
			self._keyboard = kb.widget
			self._keyboard.layout = layout
		else:
			self._keyboard = kb
		self._keyboard.bind(on_key_down=self.key_down,
			on_key_up=self.key_up)

	def _keyboard_close(self, *args):
		""" The active keyboard is being closed. """
		if self._keyboard:
			self._keyboard.unbind(on_key_down=self.key_down)
			self._keyboard.unbind(on_key_up=self.key_up)
			Window.remove_widget(self._keyboard)
			Window.remove_widget(self.textbox)
			Window.clear()
			# Pin recieved. Setup Drawing
			self.init_painter()

	def init_painter(self):
	
		# Initialize the network system.
		self.network.initialize()
	
		self.painter = MyPaintWidget()
		self.painter.app = self
		clearbtn = Button(text='Clear', 
			size_hint = (.1,.1), 
			pos_hint={'bottom': 0.9})
		clearbtn.bind(on_release=self.clear_canvas)
		quitbtn = Button(text='Quit', 
			size_hint = (.1,.1), 
			pos_hint={'bottom': 0.9, 'right': 1.0})
		quitbtn.bind(on_release=self.onQuitBtnPress)
		Window.add_widget(self.painter)
		Window.add_widget(clearbtn)
		Window.add_widget(quitbtn)

	def onQuitBtnPress(self, obj):
		if globals.RPI:
			call("sudo shutdown -h now", shell=True)
		else:
			quit(0)
		
	def key_down(self, keyboard, keycode, text, modifiers):
		""" The callback function that catches keyboard events. """
		self.input += u"{0}".format(text)

# BACKSPACE entry = len 13	
	def key_up(self, keyboard, keycode, *args):
		if isinstance(keycode, tuple):
			keycode = keycode[1]
		self.input += u"{0}".format(keycode)
		try:
			int(self.input)
			self.textbox.text = self.input
		except ValueError:
			if 'backspace' in self.input:
				self.input = self.input[:-14]
				self.textbox.text = self.input
		# Pin recieved
		if len(self.input) == 4:
			print("PIN recieved: ")
			print(self.input)
			input_pin = self.input
			# global S_PIN
			globals.S_PIN = str.encode(input_pin)
			set_key()
			self._keyboard_close(args)


if __name__ == '__main__':
	MyPaintApp().run()