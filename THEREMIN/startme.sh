#!/bin/bash


pd-extended -nogui /home/pi/MacGuffin/THEREMIN/Theremin_pd_.pd &

sleep 5

/usr/bin/python /home/pi/MacGuffin/THEREMIN/Theremin.py &

