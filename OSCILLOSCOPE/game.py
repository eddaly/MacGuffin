#!/usr/bin/python

import OSC
import random
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib import image
import threading
import time
import Adafruit_MCP3008
import os
import socket
import pyaudio

debug = 1

height = 480
width = 800
off = 200
delay = 0.25 # quarter second delay on note tracking
min_dial_range = 55
max_dial_range = 57
target_pitch = 440
pitch_mult = 2.0
pitch = target_pitch-(pitch_mult*min_dial_range)
max_pot_value = 1023.0
min_pot_value = 5.0 # the default pot value so that the wave is always moving
dialTime = 0
winTime = 4 #win condition time out
theremin = 0

# connect to pd
client = OSC.OSCClient()
client.connect(('127.0.0.1', 4559))

# First set up the figure, the axis, and the plot element we want to animate
back = image.imread('/home/pi/MacGuffin/OSCILLOSCOPE/OSC_backgorund.png')

# set up the figure and the axis, and the plot element we want to animate
plt.rcParams['toolbar'] = 'None'
fig = plt.figure(facecolor="black", edgecolor="black", linewidth=0.0)
ax = plt.gca()

# create data and the plot
x = np.linspace(off, 2*np.pi, width-(off*2))
y = (height/4) * np.sin(.5*np.pi * (x - 0.1* 5)) + (height/2)
xx = np.linspace(off, width-off, width-(off*2))
line, = ax.plot(xx, y, lw=2, animated=True, zorder=1,color='#46ffe6')

# render the background plate
plt.imshow(back, zorder=0)

ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.set_frame_on(False)
fig.tight_layout(pad=0)

# the state variable
state = -1;

# Dial variables
dial_value = 2;

# variables for the A/D controller
CLK  = 12
MISO = 24
MOSI = 23
CS   = 18
mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

# networking
SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 5000
RECV_BUFFER_SIZE = 1024
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))

def send_packet(body):
    l = threading.Lock()
    l.acquire
    send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
    l.release

def receive_packet():
    global RECV_BUFFER_SIZE
    data, addr = recv_sock.recvfrom(RECV_BUFFER_SIZE)
    return data

def reset_all():
    global state
    global dial_value
    global old_dial_value
    global dialTime
    
    l = threading.Lock()
    l.acquire
    dialTime = 0
    old_dial_value = 2
    dial_value = 2
    state = -1
    
    msg = OSC.OSCMessage()
    msg.setAddress("/play")
    msg.insert(0,0)
    client.send(msg)
    print (dial_value)
    l.release

def start_game():
    global state
    global pitch
    global dial_value
    dial_value = 2
    msg = OSC.OSCMessage()
    msg.setAddress("/play")
    msg.insert(0,1)
    client.send(msg)
    state = 0

def reset_loop():
    global debug
    global delay
    global theremin

    while True:
        packet = receive_packet()
        if debug == 1:
            print 'Received packet: ', packet
        if packet == "reset":
            reset_all()
        if packet == "start":
            start_game()
        if packet == "123":
        	theremin = 1    
        time.sleep(delay)

def heartbeat_loop():
    while True:
        send_packet("I am alive!")
        if debug == 1:
            print "I am alive!"
        time.sleep(10)

filtered_dial = 0

def dial_thread():
    global dial_value
    global state
    global debug
    global max_pot_value
    global min_pot_value
    global pitch
    global pitch_mult
    global filtered_dial

    old_dial_value = dial_value
    filtered_dial = dial_value
    msg = OSC.OSCMessage()

    while True:
        time.sleep(delay)
        if state == 0:
            dial_value = max(100.0*(mcp.read_adc(0)/max_pot_value),min_pot_value)
            filtered_dial = filtered_dial * 0.1 + dial_value * 0.9 # get a filtered dial value
            if abs(dial_value - filtered_dial) >= 0.0: # 3% change pitch
                msg.clearData()
                msg.setAddress("/play_this")
                msg.insert(0,pitch+(pitch_mult*filtered_dial)) # track filtered dial sound
                client.send(msg)
            old_dial_value = dial_value

        if debug == 1:
            print "Dial value = ", dial_value


# initialization function: plot the background of each frame
def init():
    line.set_data(xx, y)
    return line,

# animation function
def animate(k):
    global dial_value
    global state
    global min_dial_range
    global max_dial_range
    global target_pitch
    global filtered_dial
    global dialTime 
    global winTime
    # update the wave
    y = (height/4) * np.sin(0.01*np.pi * (x - k*dial_value)) + (height/2)
    line.set_data(xx, y) # plot the data
    if dial_value >= min_dial_range and dial_value <= max_dial_range and state == 0:
        if abs(filtered_dial - dial_value) > 1.0:
            # balk due to fast twisty
            return line,
        dialTime = dialTime + 1
        if debug == 1:
            print "stop!"
        if dialTime > winTime:
        	msg = OSC.OSCMessage()
        	msg.setAddress("/play_this")
        	msg.insert(0,target_pitch)
        	client.send(msg)
        	state = 1
        	send_packet("202")
        	os.system('/usr/bin/omxplayer --win "0 0 800 480" /home/pi/MacGuffin/OSCILLOSCOPE/OSC_SCREEN_MACGUFFIN.mp4')
    else: 
    	dialTime = 0
    return line,


# call the animator.  blit=True means only re-draw the parts that have changed.
anim = animation.FuncAnimation(fig, animate, init_func=init,
			interval=10, blit=True)

# do final configuration to the figure... yes I know... this is odd this being here but for some reason it has to be :/
mgr = plt.get_current_fig_manager()
mgr.window.state('withdrawn')
mgr.full_screen_toggle()

t1 = threading.Thread(target=dial_thread)
t1.start()

t2 = threading.Thread(target=reset_loop)
t2.start()

t3 = threading.Thread(target=heartbeat_loop)
t3.start()

reset_all()

# game blocks in a loop here
plt.show()

