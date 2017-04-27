#!/usr/bin/python

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

height = 480
width = 800
off = 200
delay = 1
debug = 1

# First set up the figure, the axis, and the plot element we want to animate
back = image.imread('OSC_backgorund.png')

# set up the figure and the axis, and the plot element we want to animate
plt.rcParams['toolbar'] = 'None'
fig = plt.figure()
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
state = 0;

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
RECV_UDP_PORT = 6000
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
    state = -1;

def start_game():
    global state
    state = 0

def reset_loop():
    global debug
    global delay

    while True:
        packet = receive_packet()
        if debug == 1:
            print 'Received packet: ', packet
        if packet == "101":
            reset_all()
        if packet == "102":
            start_game()
        time.sleep(delay)
            
def heartbeat_loop():
    while True:
        send_packet("I am alive!")
        if debug == 1:
            print "I am alive!"
        time.sleep(10)


def dial_thread():
    global dial_value
    global state
    global plt
    max_pot_value = 1023.0
    min_pot_value = 5.0 # the default pot value so that the wave is always moving
    while True:
        time.sleep(delay)
        if state == 0:
            dial_value = max(100.0*(mcp.read_adc(0)/max_pot_value),min_pot_value)
        
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
    # update the wave
    y = (height/4) * np.sin(0.01*np.pi * (x -1* k*dial_value)) + (height/2)
    line.set_data(xx, y) # plot the data

    if dial_value >= 56 and dial_value <= 57 and state == 0:
        if debug == 1:
            print "stop!"
        state = 1
        send_packet("201")
        os.system('/usr/bin/omxplayer --win "0 0 800 480" /home/pi/MacGuffin/OSCILLOSCOPE/OSC_SCREEN_MACGUFFIN.mp4')
    return line,


# call the animator.  blit=True means only re-draw the parts that have changed.
anim = animation.FuncAnimation(fig, animate, init_func=init,
			interval=1, blit=True)

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

# game blocks in a loop here
plt.show()

