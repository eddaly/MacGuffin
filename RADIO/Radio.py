# Mc Guffin Radio
# 
# Author: A.T. seeper
# Cloned: 24/4/2017 S. Jackson

# Import SPI library (for hardware SPI) and MCP3008 library.
import OSC
from random import randint
import time

import serial
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import RPi.GPIO as GPIO
import socket
import threading
import PIL

import ft5406
ts = ft5406.Touchscreen()
# 7 by 4 icon division

the_key = [ 0, 1, 8, 9 ] # a list of the active combination

visible_select = [False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False]

def poll_touch():
    global ts
    global w
    global visible_select
    global the_key
    xoffset = 0
    yoffset = 0
    xsize = 65536
    ysize = 65536
    xper = (xsize - 2 * xoffset) / 7
    yper = (ysize - 2 * yoffset) / 4
    hits = [ 0, 0, 0, 0 ]
    visible_select = [ False, False, False, False, False, False, False,
                       False, False, False, False, False, False, False,
                       False, False, False, False, False, False, False,
                       False, False, False, False, False, False, False ]
    for touch in ts.poll():
        if touch.valid == True:
            index = (touch.x - xoffset) / xper + (touch.y - yoffset) / yper * 7 #create a touch index
            visible_select[index] = True
            for idx in the_key:
                if index == idx:
                    addto = the_key.index(idx)
                    hits[addto] += 1
    locked = false
    for symbol in hits:
        if symbol < 1:
            locked = true
    # all symbols in the_key have been touched at the same time?
    w.fill_grid
    return locked

import sys
if sys.version_info[0] == 2:  # Just checking your Python version to import Tkinter properly.
    from Tkinter import *
else:
    from tkinter import *

class FullscreenWindow:

    cache = []
    panels = []

    def __init__(self):
        self.tk = Tk()
        self.tk.attributes('-zoomed', True)  # This just maximizes it so we can see the window. It's nothing to do with fullscreen.
        self.frame = Frame(self.tk)
        self.frame.pack()
        self.state = True # full screen state
        self.tk.attributes("-fullscreen", self.state)
        fill_grid()
        set_panel_image()

    def background(self): # not yet called!!!
        img = Image.open('SYMBOLS/TouchSCreenBackground.jpg')
        # img = img.resize((250, 250), Image.ANTIALIAS) 800 * 480
        img = ImageTk.PhotoImage(img)
        panel = Label(root, image=img)
        panel.image = img
        panel.pack()

    def image_pair(self, num): # the number of the image pair
        digits = "00" + str(num)
        digits2 = digits[len(digits) - 2:len(digits) - 1] # a pair of digits
        imgon = Image.open('SYMBOLS/ON/SymbolsON_' + digits2 + '.jpg')
        imgoff = Image.open('SYMBOLS/OFF/SymbolsOFF_' + digits2 + '.jpg')
        cache.append(ImageTk.PhotoImage(imgon))
        cache.append(ImageTk.PhotoImage(imgoff))
        # 56 images in cache

    def set_panel_image(self):
        global visible_select
        for i in range(28):
            selected = 1 # off
            if visible_select[i] == True:
                selected = 0 # on
            panels[i].image = cache[i * 2 + selected]
            panels[i].pack() # redraw!!

    def fill_grid(self):
        for i in range(28):
            image_pair(i) # create loaded images
            panel = Label(root) #is it root NOOOOOOO!!
            panels.append(panel)
            #then place in grid

w = FullscreenWindow() # a window

ser = serial.Serial(
port='/dev/ttyUSB0',
baudrate= 9600,)
s = 0

client = OSC.OSCClient()
client.connect(('127.0.0.1', 4559))

GPIO.setmode(GPIO.BCM)

gaugePin = 19 #set pin for tunning gauge

GPIO.setup(gaugePin,GPIO.OUT)
gauge = GPIO.PWM(gaugePin,100) 

# Import SPI library (for hardware SPI) and MCP3008 library.

CLK  = 12
MISO = 24
MOSI = 23
CS   = 18
mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

percent_tune = 20
tune_centre = 50 #MUST CHANGE
pot = 0 #A default, must set before check to aquire position
near = 0 #A default for the near tuning 100 is spot on 0 is far away

state = 4 #set initial state, should be 0 at showtime
print 'state:', state

l = threading.Lock() # A master lock as some code had no lock on atomic state change

SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 6000

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))

def send_packet(body):
    send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
    

def receive_packet():
    print 'r_packet'
    data, addr = recv_sock.recvfrom(1024)
    return data

def reset_all():
    print 'reset all - wawiting to acquire lock'
    global state
    global l
    l.acquire
    print 'reset all - got the lock... continue processing'
    gauge.start(0) # start PWM
    state = 0 #indicate reset
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)
    
    l.release
    print 'all reset - releasing the lock'
    
def start_game():
    global state
    global l
    l.acquire
    state = 1 #indicate enable and play on
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    l.release

def reset_loop():
    while True:
        result = receive_packet()
        print 'waiting for interrupt'
        
        if result == "101":
            reset_all()
        if result == "102":
            start_game()
        
        time.sleep(0.01)
    

def heartbeat_loop():
    global l
    while True:
        l.acquire
        send_packet("I am alive!")
        print 'isAlive'
        l.release
        time.sleep(10)

def gui_loop():
    global w
    w.tk.mainloop()
    
#====================================
# BACKGROUND RESET AND ALIVE DEAMONS
#====================================
def initialise():
    reset_all()
    t1 = threading.Thread(target=reset_loop)
    t1.daemon = False
    t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    t3 = threading.Thread(target=gui_loop)
    t3.daemon = False
    t3.start()

#===================================
# EVERTHING BELOW SPECIFIC TO RADIO
#===================================

def tuning_lock():
    global state
    global tune_centre
    global percent_tune
    global pot
    global near
    global l
    time.sleep(0.5)
    pot = mcp.read_adc(0)
    l.acquire
    if pot >= tune_centre + percent_tune and pot <= tune_centre - percent_tune:
        state = 2 # better luck next time
        gauge.start(0)
        l.release
    else:
        near = min(100 - (pot - tune_centre) * (pot - tune_centre), 0)
        gauge.start(near) # tuning indication, maybe sensitivity needs changing
        state = 3 # whey hey, tuned in!!
        l.release


#===================================
# SPECIFICS OF RADIO PLAY
#===================================
def radio(): # use near global as the closeness of the station.
    global state
    global l
    global near
    ser.flushInput()
    msg = OSC.OSCMessage()
    msg.setAddress("/play_this")
    play = OSC.OSCMessage()
    play.setAddress("/play")
    
    s = int(ser.readline())
    pitch = s
    #gauge.ChangeDutyCycle(t)
    l.acquire       
    if s == 100:
        f = f + 1
        print("OOR")
    
    elif s > 109 and s < 881:
        f = 0
        if pitch != old_pitch:
            msg.insert(0,pitch)
            client.send(msg)
     
    if f == 0 :
        play.insert(0,1)
        client.send(play)
    if f > 30 :
        t = 0
        play.insert(0,0)
        client.send(play)
        

    if t >= 90:
        play.insert(0,0)
        client.send(play)
        state = 6
    
    l.release
    time.sleep(0.01)

#COMPLETE
def idle():
    global pot
    pot = mcp.read_adc(0)
    print 'pot:',pot
    time.sleep(0.5)
    
#=========================
#  STATE MACHINE MAIN LOOP
#=========================


def main():

    initialise()

    while True:
        global state
        print 'state:',state
        time.sleep(0.001)
        if state == 0:
            idle() # in reset so idle and initialize display
        if state == 1:
            # main gaming entry state check for touch events
        if state == 2:
            # touched success turn on radio
        if state == 3:
            # tuning locked in
        if state == 4:
            # message done -- is this a needed state?


if __name__ == "__main__":
    main()
