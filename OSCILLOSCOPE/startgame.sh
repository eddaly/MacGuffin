#!/bin/bash

export DISPLAY=:0.0
xset s noblank
xset s off 
xset -dpms
unclutter -root -noevents -grab -display :0 -idle 0 &
pd-extended -nogui /home/pi/MacGuffin/OSCILLOSCOPE/Oscilloscope_pd_.pd &
sleep 5
/home/pi/MacGuffin/OSCILLOSCOPE/game.py

