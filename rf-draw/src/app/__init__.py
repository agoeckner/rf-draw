import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from random import random
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line

from app import globals



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
	# global SESSION_KEY
	# global PRESHARED_KEY 
	globals.SESSION_KEY = pin_to_key(globals.S_PIN + temp + globals.PRESHARED_KEY  )
	print("Session Pin:")
	print()	


class MyPaintWidget(Widget):
	line = {}
	app = None

	def on_touch_down(self, touch):
		hue = random()
		self.lineStart('local', hue, touch.x, touch.y)
		self.app.network.commandMgr.sendCommand(
			self.app.network.hosts.broadcast,
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
			self.app.network.hosts.broadcast,
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
		
		# Set up packet handling tick.
		Clock.schedule_interval(self.network.commandMgr.drainInboundQueue, 1 / 10.)
		
	def onRemoteDrawStart(self, source, hue, x, y):
		self.painter.lineStart(source, hue, x, y)
	
	def onRemoteDrawContinue(self, source, x, y):
		self.painter.lineContinue(source, x, y)
	
	def onRemoteClear(self, source):
		self.painter.canvas.clear()
	
	def build(self):
		parent = Widget()
		self.painter = MyPaintWidget()
		self.painter.app = self
		clearbtn = Button(text='Clear')
		clearbtn.bind(on_release=self.clear_canvas)
		parent.add_widget(self.painter)
		parent.add_widget(clearbtn)

		# pin entry stuff
		Config.set("kivy", "keyboard_mode", 'dock')
		Config.write()
		self.set_layout('numeric.json' )
		self.input = ''


		return parent

	def clear_canvas(self, obj):
		self.painter.canvas.clear()
		self.network.commandMgr.sendCommand(
			self.network.hosts.broadcast,
			"APP_DRAW_CLEAR",
			())
	'''
		Pin Entry code
	'''
	def set_layout(self, layout):
		""" Change the keyboard layout to the one specified by *layout*. """
		kb = Window.request_keyboard(
			self._keyboard_close, self)
		if kb.widget:
			# If the current configuration supports Virtual Keyboards, this
			# widget will be a kivy.uix.vkeyboard.VKeyboard instance.
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
			self._keyboard = None

	def key_down(self, keyboard, keycode, text, modifiers):
		""" The callback function that catches keyboard events. """
		self.input += u"{0}".format(text)

	# def key_up(self, keyboard, keycode):
	def key_up(self, keyboard, keycode, *args):
		""" The callback function that catches keyboard events. """
		# system keyboard keycode: (122, 'z')
		# dock keyboard keycode: 'z'
		if isinstance(keycode, tuple):
			keycode = keycode[1]
		self.input += u"{0}".format(keycode)
		print("PIN recieved: ")
		print(self.input)
		# Pin recieved
		if len(self.input) == 4:
			input_pin = self.input
			# global S_PIN
			globals.S_PIN = str.encode(input_pin)
			set_key()
			self._keyboard_close(args)
			Window.close()
		


if __name__ == '__main__':
	MyPaintApp().run()