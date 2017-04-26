# Mc Guffin Radio
# 
# Author: A.T. seeper
# Cloned: 24/4/2017 S. Jackson

# Import SPI library (for hardware SPI) and MCP3008 library.
# import OSC
import time
import datetime

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

STARTER_STATE = 2  # the initial state after reset for the ease of build does vary (AT 4 FOR FINAL CODE)

# ============================================
# ============================================
# SET MODE FIRST (NO PIN DEFS BEFORE)
# ============================================
# ============================================
GPIO.setmode(GPIO.BCM)

# 3008 SPECIFIC MCP ADC
CLK = 12
MISO = 24
MOSI = 23
CS = 18

# BCM MODE
gaugePin = 19  # set pin for tunning gauge

rfidPins = [25, 8, 7, 16, 20]  # change??!!


# ===================================
# RFID CODE
# ===================================
def rfid_init():
    global rfidPins
    for i in range(5):
        pin = rfidPins[i]
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


rfid_init()


def rfid():
    global rfidPins
    flag = True
    for i in range(5):
        j = GPIO.input(rfidPins[i])
        if j:
            send_packet('1' + str(i) + '1')
        else:
            send_packet('1' + str(i) + '0')
        flag = flag and j
    if flag:
        send_packet('201')
    else:
        send_packet('200')
    return flag


# ====================================
# REMOTE DEBUG CODE
# ====================================
def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/0')


# ====================================
# TOUCHSCREEN CODE
# ====================================
ts = ft5406.Touchscreen()
# 7 by 4 icon division

# 0 to 27 for the valid 4 key combination
the_key = [0, 1, 2, 3]  # a list of the active combination

visible_select = [False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False,
                  False, False, False, False, False, False, False]

touch_grid = [[-1, -1, -1, -1, False], [-1, -1, -1, -1, False], [-1, -1, -1, -1, False],
              [-1, -1, -1, -1, False]]  # the four active touches
current_touch = 0
correctly_keyed = False


def handle_event(event, touch):
    global touch_grid
    global current_touch
    # debug(["Release", "Press", "Move"][event] + ':' + str(touch.slot) + ':'+ str(touch.x) + ':' + str(touch.y))
    if event == 1:  # press
        touch_grid[current_touch] = [touch.slot, touch.x, touch.y, -1, False]
        current_touch = (current_touch + 1) % 4
        # debug('new cur touch:' + str(current_touch))
    elif event == 2:  # move
        nop = True
        # debug('wobbly finger')
    else:
        # debug(str(touch_grid))
        for i in range(4):
            if touch_grid[i][0] == touch.slot:
                touch_grid[i][4] = True  # reset
                touch_grid[i][3] = time.time()  # released
                # debug('touch_grid set')


def do_touch():
    for i in range(4):
        if (touch_grid[i][4] == True) and (time.time() - touch_grid[i][3] > 0.5):
            touch_grid[i] = [-1, -1, -1, -1, False]  # reset
    set_touch()
    return correctly_keyed


for touch in ts.touches:
    touch.on_press = handle_event
    touch.on_release = handle_event
    touch.on_move = handle_event

ts.run()


def set_touch():
    global w
    global correctly_keyed
    global visible_select
    global the_key
    global touch_grid
    xsize = 800
    ysize = 480
    xper = xsize / 7
    yper = ysize / 4
    hits = [0, 0, 0, 0]
    visible_select = [False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False,
                      False, False, False, False, False, False, False]

    # debug(str(touch_grid)) # print grid
    for touch in touch_grid:
        # debug('touch:' + str(touch))
        if touch[0] > -1:
            index = touch[1] / xper + touch[2] / yper * 7  # create a touch index
            index = min(27, index)  # an extra check
            visible_select[index] = True  # set as on
            # debug(str(visible_select)) # should show
            for idx in range(4):
                if index == the_key[idx]:
                    hits[idx] += 1
    locked = False
    # debug(str(hits))
    # debug('hit check')
    for symbol in hits:
        if symbol < 1:
            locked = True
    # all symbols in the_key have been touched at the same time?
    # debug('update display')
    w.set_panel_image()
    # debug('exit touch_poll')
    correctly_keyed = not locked


if sys.version_info[0] == 2:  # Just checking your Python version to import Tkinter properly.
    from Tkinter import *
else:
    from tkinter import *


class FullscreenWindow:
    cache = []
    panels = []

    def __init__(self):
        self.tk = Tk()
        self.tk.config(cursor='none')  # check for cursor hide
        self.tk.attributes('-zoomed',
                           True)  # This just maximizes it so we can see the window. It's nothing to do with fullscreen.
        self.frame = self.tk  # the frame is not required
        # self.frame.pack() going to be a grid
        self.tk.attributes("-fullscreen", True)
        self.frame.bind('<Escape>', self.close)
        debug('should have escape key but do not.')
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
        panel.image = self.img  # -- this is just to maintain a handle and the handle is now a instance var
        debug('should have a background but do not. Used solid colour.')
        # the background appears not to show
        panel.place()

    def image_pair(self, num):  # the number of the image pair
        debug('building image: ' + str(num))
        digits = "00" + str(num + 1)
        digits2 = digits[len(digits) - 2:len(digits)]  # a pair of digits
        imgon = PIL.Image.open(self.dir() + '/SYMBOLS/ON/SymbolsON_' + digits2 + '.jpg')
        imgon = imgon.resize((114, 120), PIL.Image.ANTIALIAS)
        imgoff = PIL.Image.open(self.dir() + '/SYMBOLS/OFF/SymbolsOFF_' + digits2 + '.jpg')
        imgoff = imgoff.resize((114, 120), PIL.Image.ANTIALIAS)
        self.cache.append(ImageTk.PhotoImage(imgon))
        self.cache.append(ImageTk.PhotoImage(imgoff))
        # 56 images in cache

    def set_panel_image(self):
        global visible_select
        # debug('update')
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
        # stky = N + E + S + W
        for i in range(28):
            self.image_pair(i)  # create loaded images
            panel = Label(self.frame, image=self.img, highlightthickness=0, padx=0, pady=0, bg='grey9')  # padding test
            self.panels.append(panel)
            # then place in grid
            debug('placing image: ' + str(i))
            panel.grid(row=i / 7, column=i % 7)

    def close(self):
        self.frame.destroy()  # should close window


new_env = dict(os.environ)
new_env['DISPLAY'] = '0.0'
w = FullscreenWindow()  # a window

# ===================================
# MORE CODE PINS ETC.
# ===================================

# client = OSC.OSCClient()
# client.connect(('127.0.0.1', 4559))

GPIO.setup(gaugePin, GPIO.OUT)
gauge = GPIO.PWM(gaugePin, 50)  # default of no signal

# Import SPI library (for hardware SPI) and MCP3008 library. ADC

mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

percent_tune = 20
tune_centre = 711  # MUST CHANGE
pot = 0  # A default, must set before check to acquire position
near = 0  # A default for the near tuning 100 is spot on 0 is far away

state = 0  # set initial state to RESET, use STARTER_STATE to control entry ^^^^^^^ (see above)

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
    global state
    l.acquire()
    state = num
    l.release()


# ====================================
# SOCKET TOOLS
# ====================================
SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 6000

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))


# CLEAN UP ROUTINE
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


# ========================================
# THE MAIN RESET CONTROL FUNCTIONS
# ========================================

#BCM of PIN 7
RESET = 4
GPIO.setup(RESET, GPIO.OUT, initial=GPIO.LOW)

def reset_all():
    state_w(0)  # indicate reset
    GPIO.output(RESET, GPIO.LOW)
    time.sleep(0.5) # wait active low reset
    GPIO.output(RESET, GPIO.HIGH)
    debug('reset all - wawiting to acquire lock')
    debug('reset all - got the lock... continue processing')
    gauge.start(0)  # start PWM
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)

    debug('all reset - releasing the lock')
    start_game()


def start_game():
    global correctly_keyed
    correctly_keyed = False
    state_w(STARTER_STATE)  # indicate enable and play on TODO: MUST CHANGE TO FIVE???!!!
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
        debug('isAlive:' + datetime.datetime.now().strftime('%G-%b-%d %I:%M%p'))
        time.sleep(10)


# ==================================
# GUI ON MAIN THREAD
# ==================================
def gui_loop():
    global w
    w.tk.mainloop()  # needs some checking. I think this blocks.


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
# EVERYTHING BELOW SPECIFIC TO RADIO
# ===================================
def non_terminal():  # a non terminal condition?
    global pot
    global mcp
    global near
    time.sleep(0.5)
    pot = mcp.read_adc(0)
    #debug('tunning: ' + str(pot) + ' near: ' + str(near) + ' state: ' + str(state_r()))  # strangely near global is 0


def tuning_lock():
    global tune_centre
    global percent_tune
    global pot
    global near
    non_terminal()
    p_tune = 1024 * percent_tune / 100 # yep percent!
    debug('pt: ' + str(p_tune))
    scale = abs(pot - tune_centre)
    near = scale / p_tune * 100
    debug('tunning: ' + str(pot) + ' near: ' + str(near) + ' state: ' + str(state_r()))
    gauge.start(min(near, 100))  # tuning indication, maybe sensitivity needs changing
    if near > 97:  # arbitary? and fine tuning issues 33 buckets
        if state_r() == 2: # just in case the controller restarts timer!!!
            send_packet('302')
            #state_w(3)  # whey hey, tuned in!!
            debug('Yup!!!!!!!!!!!!!!!!!!')
            return True
    elif near > 90:
        send_packet('301')
    else:
        send_packet('300')
    return False

tunning_sounds = ['/play1', '/play2']


# ===================================
# SPECIFICS OF RADIO PLAY (NOT USED?)
# ===================================
def radio():  # use near global as the closeness of the station.
    global near
    non_terminal()
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


# ===============================
# IDLE WITH SOME SETUP CHECKS
# ===============================
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
    global correctly_keyed
    while True:
        # debug('state main:' + str(state_r()))
        time.sleep(0.001)
        if state_r() == 0:  # RESET
            idle()  # in reset so idle and initialize display
        if state_r() == 1:  # CODE
            if do_touch() == True:  # main gaming entry state check for touch events
                # unlocked
                state_w(2)
                debug('BINGO!!!!!!')
        if state_r() == 2:  # TUNE
            if tuning_lock() == True:  # touched success turn on radio
                state_w(3)
            radio()  # needed??
        if state_r() == 3:  # POST TUNE?????????? <======================= CURRENT TERMINAL STATE
            # tuning locked in maybe different state, but tuning lock should do both??
            # ===============================================
            # What happens when the announcement half made?
            # ===============================================
            radio()  # needed??
        if state_r() == 4:  # RFID
            if rfid() == True:  # check for 5 active highs
                state_w(1)
                debug('MATCH!!!!!!')


def main():
    initialise()
    gui_loop()  # TEST ---


if __name__ == "__main__":
    main()
