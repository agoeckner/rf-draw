#!/bin/sh

# Set up GPIO pins 27 and 28.
gpio mode 27 out
gpio mode 28 down
gpio mode 28 in
gpio write 27 1

# Check whether jumper is in place.
production = `gpio read 28`

if (( $production==1 )) then
	# set to touchscreen
else
	# set to HDMI
fi