import kivy
kivy.require('1.0.6') # replace with your current kivy version !

from random import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line

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
		
	def onRemoteDrawStart(source, hue, x, y):
		self.painter.lineStart(source, hue, x, y)
	
	def onRemoteDrawContinue(source, x, y):
		self.painter.lineContinue(source, x, y)
	
	def onRemoteClear(source):
		self.painter.canvas.clear()
	
	def build(self):
		parent = Widget()
		self.painter = MyPaintWidget()
		self.painter.app = self
		clearbtn = Button(text='Clear')
		clearbtn.bind(on_release=self.clear_canvas)
		parent.add_widget(self.painter)
		parent.add_widget(clearbtn)
		return parent

	def clear_canvas(self, obj):
		self.painter.canvas.clear()
		self.network.commandMgr.sendCommand(
			self.network.hosts.broadcast,
			"APP_DRAW_CLEAR",
			())


if __name__ == '__main__':
	MyPaintApp().run()