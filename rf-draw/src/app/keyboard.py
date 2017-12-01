from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.vkeyboard import VKeyboard
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from functools import partial
from kivy.config import Config
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy import require

import hmac
import hashlib
import base64
import time
import datetime

from app import globals


require("1.8.0")

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


class PinInput(App):

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

	def build(self):
		Config.set("kivy", "keyboard_mode", 'dock')
		Config.write()
		self.set_layout('numeric.json' )
		self.input = ''


if __name__ == "__main__":
	PinInput().run()
	# set S_PIN with virtual keyboard
	print(S_PIN)
	print( SESSION_KEY )
	packet = b"098928472someinforandsomecommand<<end"
	invalid_packet = b"098928472someinforandsomecommand<<<end"
	invalid_sig = b"e3c8102868d28b5ff85fc35dda07329970d1a01e273c37481326fe0c861c8142"
	# Begin calls
	sig = blake2s_hmac(packet)	
	print( blake2s_verify(packet, sig) )
	print( blake2s_verify(packet, invalid_sig) )
	print( blake2s_verify(invalid_packet, sig) )
	print( blake2s_verify(invalid_packet, invalid_sig) )