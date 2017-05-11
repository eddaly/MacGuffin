#!/bin/bash

sudo apt-get update
sudo apt-get install pd-extended

echo "@lxpanel --profile LXDE-pi" > ~/.config/lxsession/LXDE-pi/autostart
echo "@pcmanfm --desktop --profile LXDE-pi" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@point-rpi" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@xset s noblank" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@xset s off" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@xset -dpms" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@unclutter -display :0 -noevents -grab" >> ~/.config/lxsession/LXDE-pi/autostart
echo "@/home/pi/MacGuffin/OSCILLOSCOPE/startgame.sh" >> ~/.config/lxsession/LXDE-pi/autostart


