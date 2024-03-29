#!/bin/bash
PROJECT=BELLOWS
# set to YES or NO
GUI=NO
SPI=NO
# dont forget all the dots
IP=10.100.1.
GATE=254
THIS=32

# the first project with the embeded SPI on PI
SPIPROJ=CANDLE

# get pip
sudo apt-get update
sudo apt-get install python-dev python-pip pd-extended

if [ "$GUI" = "NO" ]; then
    # make the startme.sh (NO GUI)
    sudo cat /etc/rc.local | sudo grep -v "exit 0" > /etc/rc.local.bak
    sudo echo "/home/pi/Macguffin/$PROJECT/startme.sh &" >> /etc/rc.local.bak 
    sudo echo "exit 0" >> /etc/rc.local.bak
    # just to stop sudo overwrite before read
    sudo cp /etc/rc.local.bak /etc/rc.local
else
    # make the startme.desktop (GUI)
    sudo cp /home/pi/Macguffin/$PROJECT/startme.desktop /etc/xdg/autostart
    # TkInter PIL lib
    sudo pip install git+https://github.com/python-pillow/Pillow.git@b53af906d797fea736966e87c47318b039005160
fi

# make the serial install (frozen fork 11th May 2017)
sudo pip install git+https://github.com/pyserial/pyserial.git@055f31cf42eca936591827ccca19c56a0df8354f

# make the SPI on PI install
sudo python /home/pi/Macguffin/$SPIPROJ/SPI-Py/setup.py install
if [ "$SPI" = "YES"]; then
    echo "dtparam=spi=on" >> /boot/config.txt
fi


sudo echo "ssh" > /boot/ssh

sudo cat > /etc/network/interfaces << EOF
auto lo

iface lo inet loopback

allow-hotplug wlan0
iface wlan0 inet dhcp
    wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf

#Your static network configuration  
iface eth0 inet static
    address $IP$THIS
    netmask 255.255.255.0
    gateway $IP$GATE
EOF
#don't use any space before of after 'EOF' in the previous line

# SOME OLDER STUFF FOR REFERENCE
#echo "@lxpanel --profile LXDE-pi" > ~/.config/lxsession/LXDE-pi/autostart
#echo "@pcmanfm --desktop --profile LXDE-pi" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@point-rpi" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset s noblank" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset s off" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@xset -dpms" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@unclutter -display :0 -noevents -grab" >> ~/.config/lxsession/LXDE-pi/autostart
#echo "@/home/pi/MacGuffin/OSCILLOSCOPE/startgame.sh" >> ~/.config/lxsession/LXDE-pi/autostart