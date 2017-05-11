#!/bin/bash
PROJECT=BELLOWS
SPI=CANDLE

# make the startme.sh (NO GUI)
sudo cat /etc/rc.local | sudo grep -v "exit 0" > /etc/rc.local
sudo echo "/home/pi/Macguffin/$PROJECT/startme.sh &" >> /etc/rc.local 
sudo echo "exit 0" >> /etc/rc.local

# make the startme.desktop (GUI)
sudo cp /home/pi/Macguffin/$PROJECT/startme.desktop /etc/xdg/autostart

# make the serial install (frozen fork 11th May 2017)
sudo apt-get install python-dev python-pip
sudo pip install git+https://github.com/jackokring/pyserial.git

# make the SPI on PI install
sudo python /home/pi/Macguffin/$SPI/SPI-Py/setup.py install





# SOME OLDER STUFF FOR REFERENCE
#echo "@lxpanel --profile LXDE-pi" > ~/.config/lxsession/LXDE-pi/autostart
#echo "@pcmanfm --desktop --profile LXDE-pi" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@point-rpi" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset s noblank" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset s off" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset -dpms" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@unclutter -display :0 -noevents -grab" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@/home/pi/MacGuffin/OSCILLOSCOPE/startgame.sh" >> ~/.config/lxsession/LXDE-pi/autostart


