# Mc Guffin Radio
# 
# Author: A.T. seeper
# Cloned: 24/4/2017 S. Jackson

# Import SPI library (for hardware SPI) and MCP3008 library.
# import OSC
import time

# import serial
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import RPi.GPIO as GPIO
import socket
import threading
import PIL.Image
from PIL import ImageTk

import ft5406
import sys
import os
import atexit

def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/0')

ts = ft5406.Touchscreen()
# 7 by 4 icon division

the_key = [0, 1, 8, 9]  # a list of the active combination

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
    hits = [0, 0, 0, 0]
    visible_select = [False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False]
    for touch in ts.poll():
        if touch.valid == True:
            index = (touch.x - xoffset) / xper + (touch.y - yoffset) / yper * 7  # create a touch index
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
    w.set_panel_image()
    return locked


if sys.version_info[0] == 2:  # Just checking your Python version to import Tkinter properly.
    from Tkinter import *
else:
    from tkinter import *


class FullscreenWindow:
    cache = []
    panels = []

    def __init__(self):
        self.tk = Tk()
        self.tk.attributes('-zoomed',
                           True)  # This just maximizes it so we can see the window. It's nothing to do with fullscreen.
        self.frame = self.tk # the frame is not required
        # self.frame.pack() going to be a grid
        self.tk.attributes("-fullscreen", True)
        self.frame.bind('<Escape>', self.close)
        self.fill_grid()
        self.set_panel_image()

    def dir(self):
        dir, file = os.path.split(os.path.abspath(__file__))  # current path
        return dir

    def background(self):  # not yet called!!!
        self.img = PIL.Image.open(self.dir() + '/SYMBOLS/TouchSCreenBackground.jpg')
        # img = img.resize((250, 250), Image.ANTIALIAS) 800 * 480
        self.img = ImageTk.PhotoImage(self.img)  # also used as a placeholder image before call to set_panel_image()
        panel = Label(self.frame, image=self.img)
        panel.image = self.img #-- this is just to maintain a handle and the handle is now a instance var
        debug('should have a background')
        # the background appears not to show
        panel.place()

    def image_pair(self, num):  # the number of the image pair
        digits = "00" + str(num + 1)
        digits2 = digits[len(digits) - 2:len(digits)]  # a pair of digits
        imgon = PIL.Image.open(self.dir() + '/SYMBOLS/ON/SymbolsON_' + digits2 + '.jpg')
        imgon = imgon.resize((114, 120), Image.ANTIALIAS)
        imgoff = PIL.Image.open(self.dir() + '/SYMBOLS/OFF/SymbolsOFF_' + digits2 + '.jpg')
        imgoff = imgoff.resize((114, 120), Image.ANTIALIAS)
        self.cache.append(ImageTk.PhotoImage(imgon))
        self.cache.append(ImageTk.PhotoImage(imgoff))
        # 56 images in cache

    def set_panel_image(self):
        global visible_select
        for i in range(28):
            # self.panels[i].grid_forget() #remove the panel from the grid
            selected = 1  # off
            if visible_select[i] == True:
                selected = 0  # on
            self.panels[i].config(image=self.cache[i * 2 + selected])
            # self.panels[i].grid(row=i / 7, column=i % 7) should not need re-adding
            # self.frame.pack() # redraw again? should nest!! (no mix grid and pack)

    def fill_grid(self):
        self.background()
        for i in range(28):
            self.image_pair(i)  # create loaded images
            panel = Label(self.frame, image=self.img, highlightthickness=0)  # is it root NOOOOOOO!! --toplevel
            self.panels.append(panel)
            # then place in grid
            panel.grid(row=i / 7, column=i % 7)

    def close(self):
        self.frame.destroy() # should close window


new_env = dict(os.environ)
new_env['DISPLAY'] = '0.0'
w = FullscreenWindow()  # a window

# client = OSC.OSCClient()
# client.connect(('127.0.0.1', 4559))

GPIO.setmode(GPIO.BCM)

gaugePin = 19  # set pin for tunning gauge

GPIO.setup(gaugePin, GPIO.OUT)
gauge = GPIO.PWM(gaugePin, 100)

# Import SPI library (for hardware SPI) and MCP3008 library. ADC

CLK = 12
MISO = 24
MOSI = 23
CS = 18
mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

percent_tune = 20
tune_centre = 50  # MUST CHANGE
pot = 0  # A default, must set before check to aquire position
near = 0  # A default for the near tuning 100 is spot on 0 is far away

state = 0  # set initial state
debug('state:' + str(state))

# =======================================
# A THREADING LOCK
# =======================================
# All reads too must be locked due to the atomic condition of read partial write
# Not really too relevant if the interpreter uses aligned pointers to objects
# or aligned bus wifth integers
l = threading.Lock()  # A master lock as some code had no lock on atomic state change


def state_r():
    l.acquire()
    tmp = state
    l.release()
    return tmp


def state_w(num):
    l.acquire()
    state = num
    l.release()


SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 6000

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))


def clean_up():
    global w
    recv_sock.close()  # just in case there is a hanging socket reaalocation problem (but it's not C)
    w.close()

atexit.register(clean_up)


def send_packet(body):
    global l
    l.acquire()
    send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
    l.release()


def receive_packet():
    debug('r_packet')
    data, addr = recv_sock.recvfrom(1024)
    return data


def reset_all():
    state_w(0)  # indicate reset
    debug('reset all - wawiting to acquire lock')
    debug('reset all - got the lock... continue processing')
    gauge.start(0)  # start PWM
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)

    debug('all reset - releasing the lock')
    state_w(1) # move into run phase


def start_game():
    state_w(1)  # indicate enable and play on
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)


def reset_loop():
    while True:
        result = receive_packet()
        debug('waiting for interrupt')

        if result == "101":
            reset_all()
        if result == "102":
            start_game()

        time.sleep(0.01)


def heartbeat_loop():
    while True:
        send_packet("I am alive!")
        debug('isAlive')
        time.sleep(10)


def gui_loop():
    global w
    w.tk.mainloop() # needs some checking. I think this blocks.


# ====================================
# BACKGROUND RESET AND ALIVE DEAMONS
# ====================================
def initialise():
    reset_all()
    t1 = threading.Thread(target=reset_loop)
    t1.daemon = False
    t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    t3 = threading.Thread(target=main_loop)
    t3.daemon = False
    t3.start()


# ===================================
# EVERTHING BELOW SPECIFIC TO RADIO
# ===================================

def tuning_lock():
    global tune_centre
    global percent_tune
    global pot
    global near
    time.sleep(0.5)
    pot = mcp.read_adc(0)
    if pot >= tune_centre + percent_tune and pot <= tune_centre - percent_tune:
        state_w(2)  # better luck next time
        near = 0
        send_packet('300')
        gauge.start(0)
    else:
        near = min(100 - (pot - tune_centre) * (pot - tune_centre) / 4, 0)  # divide by 4 for 20% tune => 0
        gauge.start(near)  # tuning indication, maybe sensitivity needs changing
        state_w(3)  # whey hey, tuned in!!
        if near > 97:  # arbitary? and fine tunning issues 33 buckets
            send_packet('302')
        elif near > 90:
            send_packet('301')


tunning_sounds = ['/play1', '/play2']


# ===================================
# SPECIFICS OF RADIO PLAY (NOT USED?)
# ===================================
def radio():  # use near global as the closeness of the station.
    global near

    number_sounds = len(tunning_sounds)
    per_sound = 100.0 / float(number_sounds)
    toplay = max(number_sounds, near / per_sound)

    # exact scheduling??? is there a sync lock between the sounds and a mechanism of offset?
    # alternates

    crakle = 100 - near  # maybe a volume specification of the secondary sound
    # hetrodyne

    #    ser.flushInput()
    #    msg = OSC.OSCMessage()
    #    msg.setAddress("/play_this")
    #    play = OSC.OSCMessage()
    #    play.setAddress("/play")

    #    s = int(ser.readline())
    time.sleep(0.01)


# COMPLETE
def idle():
    # is this needed as it is never used. I guess it initializes the first value on state 1
    global pot
    pot = mcp.read_adc(0)
    debug('pot idle:' + str(pot))
    time.sleep(3)


# =========================
#  STATE MACHINE MAIN LOOP
# =========================
def main_loop():
    while True:
        debug('state main:' + str(state_r()))
        time.sleep(0.001)
        if state_r() == 0:
            idle()  # in reset so idle and initialize display
        if state_r() == 1:
            if poll_touch() == False:  # main gaming entry state check for touch events
                # unlocked
                state_w(2)
        if state_r() == 2:
            tuning_lock()  # touched success turn on radio
            radio()  # needed??
        if state_r() == 3:
            tuning_lock()  # tuning locked in maybe different state, but tuning lock should do both
            radio()  # needed??
        if state_r() == 4:
            nop = True  # message done -- is this a needed state?

def main():
    initialise()
    gui_loop() # TEST ---

if __name__ == "__main__":
    main()
