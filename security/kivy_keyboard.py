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


require("1.8.0")

class KeyboardDemo(App):

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

	# def key_down(self, keyboard, keycode, text, modifiers):
	# 	""" The callback function that catches keyboard events. """
	# 	self.displayLabel.text = u"Key pressed - {0}".format(text)

	# def key_up(self, keyboard, keycode):
	def key_up(self, keyboard, keycode, *args):
		""" The callback function that catches keyboard events. """
		# system keyboard keycode: (122, 'z')
		# dock keyboard keycode: 'z'
		if isinstance(keycode, tuple):
			keycode = keycode[1]
		self.input += u" (up {0})".format(keycode)
		print(self.input)

	def build(self):
		Config.set("kivy", "keyboard_mode", 'dock')
        Config.write()
		self.set_layout('numeric.json' )
		self.input = ''


if __name__ == "__main__":
	KeyboardDemo().run()