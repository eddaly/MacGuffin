#!/bin/bash


pd-extended -nogui /home/pi/documents/THEREMIN/Theremin_pd_.pd &

sleep 5

/usr/bin/python /home/pi/documents/THEREMIN/Theremin.py &

