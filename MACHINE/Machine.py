# Mc Guffin MACHINE
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
import random

STARTER_STATE = 4  # the initial state after reset for the ease of build does vary (AT 4 FOR FINAL CODE)
SIMULATE = False
TX_UDP_MANY = 3  # UDP reliability retransmit number of copies
CHAOS_GUAGE = False
POT_DAMP = False

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

rfidPins = [25, 8, 7, 16, 20]  # Yep, confirmed


# ===================================
# RFID CODE
# ===================================
def rfid_init():
    global rfidPins
    for i in range(5):
        pin = rfidPins[i]
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


rfid_init()


def sim_pin():
    return random.random() > 0.3  # should be almost there


def rfid():
    global rfidPins
    flag = True
    for i in range(5):
        if SIMULATE:
            j = sim_pin()
        else:
            j = GPIO.input(rfidPins[i])
        if j:
            send_packet('1' + str(i) + '1')
            debug('rnd T:' + str(i))
        else:
            send_packet('1' + str(i) + '0')
            debug('rnd F:' + str(i))
        flag = flag and j
    if flag:
        send_packet('201')
        debug('Yes!!!!!!!!!')
    else:
        send_packet('200')
        debug('No :(')
    return flag


# ====================================
# REMOTE DEBUG CODE
# ====================================
def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/0')


# ===================================
# MORE CODE PINS ETC.
# ===================================

# client = OSC.OSCClient()
# client.connect(('127.0.0.1', 4559))

GPIO.setup(gaugePin, GPIO.OUT)
gauge = GPIO.PWM(gaugePin, 157)  # default of no signal

# Import SPI library (for hardware SPI) and MCP3008 library. ADC

mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

percent_tune = 20
tune_centre = 711  # MUST CHANGE
pot = 0  # A default, must set before check to acquire position
near = 0.0  # A default for the near tuning 100 is spot on 0 is far away
dnear = 0.0  # smooth needle

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
RECV_UDP_PORT = 5000

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
    for i in range(TX_UDP_MANY):
        send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
        time.sleep(0.1)  # slight spread of packets for burst noise spectrum avoidance
    l.release()


def receive_packet():
    debug('r_packet')
    data, addr = recv_sock.recvfrom(1024)
    return data


# ========================================
# THE MAIN RESET CONTROL FUNCTIONS
# ========================================

# BCM of PIN 7
RESET = 4
GPIO.setup(RESET, GPIO.OUT, initial=GPIO.LOW)


def reset_all():
    state_w(0)  # indicate reset
    GPIO.output(RESET, GPIO.LOW)
    time.sleep(0.5)  # wait active low reset
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
    tunning_change()
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
        debug('isAlive: ' + datetime.datetime.now().strftime('%G-%b-%d %I:%M %p'))
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
    # debug('tunning: ' + str(pot) + ' near: ' + str(near) + ' state: ' + str(state_r()))  # strangely near global is 0


def tuning_lock():
    global tune_centre
    global percent_tune
    global pot
    global near
    global dnear
    non_terminal()
    p_tune = 1024.0 * percent_tune / 100  # yep percent!
    # debug('pt: ' + str(p_tune))
    if CHAOS_GUAGE:
        potin = pot
    else:  # a bit of var reuse
        if POT_DAMP:
            if dnear < 0.000001:
                dnear = pot  # initializer
            dnear = 0.1 * dnear + 0.9 * pot
            # ======================================
            # The twist dial fast tunning ....
            # ======================================
            potin = dnear
        else:
            potin = pot  # does a a bit of a fast twist capture effect without some locking
    offset = float(abs(potin - tune_centre))  # offset
    nearnew = (1.0 - min(offset / p_tune,
                         1.0)) * 100.0  # offset rel to 20% capped at 20% (0.0 -> 1.0) scaled up for gauge
    if CHAOS_GUAGE:
        # debug('tunning nn: ' + str(pot) + ' near: ' + str(nearnew) + ' state: ' + str(state_r()))
        # continuous approximation running average filter
        dnearnew = abs(nearnew - near) / 50.0  # speed scaling
        # debug('tunning dnn: ' + str(pot) + ' near: ' + str(nearnew) + ' state: ' + str(state_r()) )
        dnear = 0.2 * dnear + 0.2 * dnearnew  # damping first constant
        # debug('tunning dn: ' + str(pot) + ' near: ' + str(nearnew) + ' state: ' + str(state_r()))
        near = max(0.6 * near + 0.4 * nearnew - 2.0 * dnear, 0.0)  # some fine tuning slow inducement
        debug('tunning: ' + str(pot) + ' near: ' + str(near) + ' state: ' + str(state_r()) + ' dnn: ' + str(dnearnew))
    else:
        near = 0.5 * near + 0.5 * nearnew  # some fine tuning slow inducement
        debug('tunning: ' + str(pot) + ' near: ' + str(near) + ' state: ' + str(state_r()) + ' dnn: ' + str(dnear))
    gauge.start(int(near / 1.75 * 97 / 60))  # tuning indication, maybe sensitivity needs changing 1.3
    if near > 97.0:  # arbitary? and fine tuning issues 33 buckets
        if abs(potin - pot) > 1.0:
            # escape from routine to prevent fast tune capture effect
            send_packet('301')
            return False
        send_packet('302')
        # state_w(3)  # whey hey, tuned in!!
        debug('Yup!!!!!!!!!!!!!!!!!!')
        return True
    elif near > 90.0:
        send_packet('301')
    else:
        send_packet('300')
    return False


def tunning_change():
    global tune_centre
    global pot
    random.seed(a=pot)
    tmp = random.randrange(370)
    non_terminal()
    gauge.start(0)
    debug('tmp: ' + str(tmp) + ' pot: ' + str(pot))
    if pot - 512 > 0:
        tune_centre = tmp
    else:
        tune_centre = 1024 - tmp


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
                # gauge.start(0) #reset guage
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
