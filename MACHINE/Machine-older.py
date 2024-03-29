# Mc Guffin MACHINE
# 
# Author: J seeper
# Basic template 28/4/2017 S. Jackson

# Import SPI library (for hardware SPI) and MCP3008 library.
# import OSC
import time
import datetime

# import serial
# import Adafruit_GPIO.SPI as SPI
# import Adafruit_MCP3008
import RPi.GPIO as GPIO
import socket
import threading

import sys
import os
import atexit
import random

import serial

# import MFRC522 # the RFID lib

BUILD = False  # enable show controller
STARTER_STATE = 1  # the initial state after reset for the ease of build
USES_BUTTON = False
PI_BUTTON_PULL_UP = 20  # A BCM of the CS // was 8 now going through NANO in slot 5
# 1 is button pressed, 0 is button released
TX_UDP_MANY = 1  # UDP reliability retransmit number of copies
RX_PORT = 5000  # Change when allocated, but to run independent of controller is 8080
BUTTON_PRESS_POLARITY = 1 # as per the vero board 3 strip and arduino convention?
RESET_LOCK_ON_WRONG = True
LATCH = False

gaugePin = 26  # set pin for gauge for use as some kind of indicator
wiredPin = 18  # BCM detect wired up connectors.
motorPin = 19  # motor control
wired = 0

# ============================================
# ============================================
# SET MODE FIRST (NO PIN DEFS BEFORE)
# ============================================
# ============================================
GPIO.setmode(GPIO.BCM)

if BUTTON_PRESS_POLARITY == 1:
    GPIO.setup(PI_BUTTON_PULL_UP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
else:
    GPIO.setup(PI_BUTTON_PULL_UP, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# wired
GPIO.setup(wiredPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# motor
GPIO.setup(motorPin, GPIO.OUT)
GPIO.output(motorPin, 0)  # turn off motor by default

# SPECIFIC SPI (Use default SPI library for Pi)
CLK = 11
MISO = 9
MOSI = 10
CS = 8  # technically SDA (check spec on RFID reader)

# BCM MODE (other definitions for pins)
GPIO.setup(gaugePin, GPIO.OUT)
gauge = GPIO.PWM(gaugePin, 157)  # default of no signal

# ===================================
# RFID CODE
# ===================================

the_key = [105, 102, 103, 101, 104, 106]  # tag ids must be 1 to 255

# Create an object of the class MFRC522
# MIFAREReader = MFRC522.MFRC522()
id_code = -1

ser = serial.Serial('/dev/ttyUSB0', 9600)  # maybe change after device scan

if BUTTON_PRESS_POLARITY == 1:
    button_dbounce = 0
else:
    button_dbounce = 1


def rfid():
    # This loop keeps checking for chips. If one is near it will get the UID and authenticate
    while True:
        time.sleep(0.1)
        debug('waiting for serial')
        input = ser.readline()  # BLOCKING
        debug('serial read done')
        debug(input)
        id_w(int(input))  # load in number to use next


# ====================================
# ASSUME GPIO DOES WIERD THINGS HERE
# ====================================

def db():
    global button_dbounce
    global wired
    while True:
        time.sleep(0.1)
        button_dbounce = GPIO.input(PI_BUTTON_PULL_UP)  # uses the 0.1 sleep as a debounce
        # debug(str(button_dbounce))
        if LATCH:
            if GPIO.input(wiredPin) ==1:
                wired = 1  # latch??
        else:
            wired = GPIO.input(wiredPin)
       # debug(str(wired))



current_step = 0


def check_button():
    if USES_BUTTON:
        if button_dbounce == BUTTON_PRESS_POLARITY:  # BUTTON PRESSED
            return True
        else:
            return False  # didn't press button
    else:
        return True


def code():
    global current_step
    tmp = id_r()
    # GETS TO HERE
    length = len(the_key)
    #debug('the key length is: ' + str(length) + ' current step: ' + str(current_step))
    if tmp == the_key[current_step]:  # a correct digit
        debug('correct digit: ' + str(id_r()))
        current_step += 1  # move onto next digit?
        debug('correct digit (increased and packet out): ' + str(current_step))
        send_packet('10' + str(current_step))  # send correct code for digit the_key[0] => 101
        # ==============================
        # INPUT OK
        # ==============================
        while USES_BUTTON and (check_button() == False):  # check button
            time.sleep(0.1)  # wait
            debug('waiting for press')
        while (not USES_BUTTON) and (id_r() != -1):  # not using button wait for remove
            debug('Not using button. key pulled out?')
            time.sleep(0.1)
        # ===============================
        # SO HAVE REGISTERED PADDLE
        # ===============================
        while USES_BUTTON and (check_button() == True):
            # check button release
            debug('check button release.')
            time.sleep(0.1)
            # ==================================
            # SO HAVE REMOVED OR BUTTON RELEASE
            # ==================================
    elif tmp != -1:  # reset combination unless daudling
        # ==================================
        # SO WRONG PADDLE
        # ==================================
        # a bit of a work around to allow the last digit to not reset the combination
        if tmp != the_key[max(current_step - 1, 0)]:  # last key or first key so not indexing array [-1]
            # ============================================================
            # SO NOT LAST PADDLE (AS IT WOULD BE ON WOBBLES AND BOUNCING)
            # ============================================================
            debug('some wrong card inserted.')
            send_packet('100')
            if RESET_LOCK_ON_WRONG:
                # ===================================
                # START OVER
                # ===================================
                debug('reset combination')
                current_step = 0
                return False
        # MUST BE -1 HERE
        else:
            debug('clone of last digit/paddle')
            return False
    else:  # -1
        # =========================================
        # NOT GOOD, NOT BAD, NOT LAST, BUT NO RFID
        # =========================================
        # debug('no card detected')
        nop = True
    if length == current_step:  # yep got combination as line 142 would have made current step == 6
        debug('combination valid')
        return True
    return False


# ====================================
# REMOTE DEBUG CODE
# ====================================
def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/0')


# ===================================
# MORE CODE PINS ETC.
# ===================================

def motor():
    global current_step
    length = len(the_key)
    complete = float(length - min(current_step, length)) / float(length)
    complete *= complete  # bias toward the end of the entry conditions
    rand = (1.0 - complete) + random.random() * 0.25

    if (rand > 0.5) and not ((state_r() == 0) or (state_r() == 3)):  # not idle or ended game
        GPIO.output(motorPin, 1)  # turn on motor
    else:
        GPIO.output(motorPin, 0)  # turn off motor


# ====================================
# A GAUGE ON THE MACHINE
# ====================================

def gauge_func(num):  # a 0 to 100% dial approximatly. Could be upto 10% out depending on situation
    # A name space collision function has priority over variable
    gauge.start(int(num / 1.75 * 97 / 60))  # tuning indication, maybe sensitivity needs changing 1.3
    time.sleep(0.001)


def gauge_motion():
    time.sleep(0.3)
    gauge_func(random.random() * 20.0 * max(current_step + 1, 5))  # a limit check so the last digit does not go over !!
    motor()  # update the motor too


# =======================================
# A THREADING LOCK
# =======================================
# All reads too must be locked due to the atomic condition of read partial write
# Not really too relevant if the interpreter uses aligned pointers to objects
# or aligned bus wifth integers
l = threading.Lock()  # A master lock as some code had no lock on atomic state change
state = 0  # set initial state to RESET, use STARTER_STATE to control entry ^^^^^^^ (see above)


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


# could use an extra lock but for such average performant code it's not required

def id_r():
    l.acquire()
    tmp = id_code
    l.release()
    return tmp


def id_w(num):
    global id_code
    l.acquire()
    id_code = num
    l.release()


# ====================================
# SOCKET TOOLS
# ====================================
SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = RX_PORT

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))


# CLEAN UP ROUTINE
def clean_up():
    recv_sock.close()  # just in case there is a hanging socket reaalocation problem (but it's not C)
    ser.close()

atexit.register(clean_up)


def send_packet(body):
    global l
    l.acquire()
    for i in range(TX_UDP_MANY):
        send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
        time.sleep(0.1)  # slight spread of packets for burst noise spectrum avoidance
    l.release()


def receive_packet():
    debug('r_packet: ')
    data, addr = recv_sock.recvfrom(1024)
    return data


# ========================================
# THE MAIN RESET CONTROL FUNCTIONS
# ========================================

# BCM of PIN 7
RESET = 4
GPIO.setup(RESET, GPIO.OUT, initial=GPIO.LOW)


def reset_all():
    global wired
    state_w(0)  # indicate reset
    GPIO.output(RESET, GPIO.LOW)
    time.sleep(0.5)  # wait active low reset
    GPIO.output(RESET, GPIO.HIGH)
    debug('reset all - wawiting to acquire lock')
    debug('reset all - got the lock... continue processing')
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)

    debug('all reset - releasing the lock')
    wired = 0
    GPIO.output(motorPin, 0)  # turn off motor by default
    if BUILD: # for tests
        start_game() #-- should not start game yet


def start_game():
    global current_step
    state_w(STARTER_STATE)  # indicate enable and play on TODO: MUST CHANGE TO FIVE???!!!
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    current_step = 0
    GPIO.output(motorPin, 1)  # start motor


def reset_loop():
    while True:
        result = receive_packet()
        debug('waiting for interrupt')

        if result == "reset":
            reset_all()
        if result == "start":
            start_game()

        time.sleep(0.01)


def heartbeat_loop():
    while True:
        send_packet("H")
        ##debug('isAlive: ' + datetime.datetime.now().strftime('%G-%b-%d %I:%M %p'))
        time.sleep(10)


# ====================================
# BACKGROUND RESET AND ALIVE DEAMONS
# ====================================
def initialise():
    reset_all()
    debug('flush about to happen')
    input = ser.readline()  # flush
    time.sleep(3)
    input = ser.readline()  # flush
    debug('flushed')
    if not BUILD:
        t1 = threading.Thread(target=reset_loop)
        t1.daemon = False
        t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    t3 = threading.Thread(target=rfid)
    t3.daemon = False
    t3.start()
    t4 = threading.Thread(target=gauge_motion)
    t4.daemon = False
    t4.start()
    t5 = threading.Thread(target=db)
    t5.daemon = False
    t5.start()


# ===============================
# IDLE WITH SOME SETUP CHECKS
# ===============================
def idle():
    debug('idle')
    time.sleep(3)


# =========================
#  STATE MACHINE MAIN LOOP
# =========================
def main_loop():
    while True:
        ##debug('state main:' + str(state_r()))
        time.sleep(0.001)
        if state_r() == 0:  # RESET
            idle()  # in reset so idle and initialize display
            #send_packet('200')
        if state_r() == 1:  # CODE
            if code() == True:  # run the code finder
                state_w(2)
                # more states?

        if state_r() == 2:  # check wired
            if wired == 1:  # can be set any time
                state_w(3)
                debug('YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY')
        if state_r() == 3:
            GPIO.output(motorPin, 0)  # turn off motor
            send_packet('201')


def main():
    initialise()
    main_loop()  # TEST ---


if __name__ == "__main__":
    main()
