#!/bin/bash


pd-extended -nogui /home/pi/MacGuffin/THEREMIN/Theremin_pd_.pd 2>&1 > /tmp/theremin_pd.log &

sleep 5

/usr/bin/python /home/pi/MacGuffin/THEREMIN/Theremin.py 2>&1 > /tmp/theremin_py.log &

