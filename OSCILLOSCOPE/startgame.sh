#!/bin/bash

export DISPLAY=:0.0
xset s noblank
xset s off 
xset -dpms
unclutter -display :0 -noevents -grab&
/home/pi/MacGuffin/OSCILLOSCOPE/game.py 2>&1 >> /home/pi/MacGuffin/OSCILLOSCOPE/game.log &

