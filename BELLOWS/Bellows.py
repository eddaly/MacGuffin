# Mc Guffin BELLOWS
# 
# Author: A.T. seeper
# Basic template 02/05/2017 S. Jackson

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

# import serial

# import MFRC522 # the RFID lib

POLARITY = 0 # the active polarity
BUILD = True # this one can remain in loop as just a proxy for SC
STARTER_STATE = 1  # the initial state after reset for the ease of build
TX_UDP_MANY = 1  # UDP reliability retransmit number of copies
RX_PORT = 5000  # Change when allocated, but to run independent of controller is 8080

DETECT = 25 # physical 22
#LOCK = 8

heart = True

# ============================================
# ============================================
# SET MODE FIRST (NO PIN DEFS BEFORE)
# ============================================
# ============================================
GPIO.setmode(GPIO.BCM)

if POLARITY == 1:
    GPIO.setup(DETECT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
else:
    GPIO.setup(DETECT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#GPIO.setup(LOCK, GPIO.OUT)


# ====================================
# CHECK MANOMETER
# ====================================

latch = False

def man(): # latching detect
    global latch
    if POLARITY == 1:
        off = 0
    else:
        off = 1
    input = GPIO.input(DETECT)
    if latch == False: # off
        if input == POLARITY: # and become on
            latch = True
            send_packet('101')
            time.sleep(0.5) # debounce
    else: # on
        if input == off: # and become off
            latch = False
            send_packet('100')
            time.sleep(0.5) # debounce
#    return True


# ====================================
# REMOTE DEBUG CODE
# ====================================
def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/0')


# ===================================
# MORE CODE PINS ETC.
# ===================================

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


atexit.register(clean_up)


def send_packet(body):
    global l
    debug(body)  # send packet
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
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)

    #GPIO.output(LOCK, 1)  # lock
    debug('all reset - releasing the lock')
    if BUILD:
        start_game()  # should not start game yet


def start_game():
    state_w(STARTER_STATE)  # indicate enable and play on TODO: MUST CHANGE TO FIVE???!!!
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    #GPIO.output(LOCK, 1)  # lock



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
    if not BUILD:
        t1 = threading.Thread(target=reset_loop)
        t1.daemon = False
        t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    # t3 = threading.Thread(target=rfid)
    # t3.daemon = False
    # t3.start()
    # t4 = threading.Thread(target=led)
    # t4.daemon = False
    # t4.start()


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
            # send_packet('200')
        if state_r() == 1:  # CHECK IR
            man()
                #state_w(2)
                #send_packet('101')
            #else:
                #send_packet('100')
#        if state_r() == 2:
#            if ir2() == True:
#                state_w(3)
#                send_packet('111')
#            else:
#                send_packet('110')
#        if state_r() == 3:
#            # send_packet('201')
#            GPIO.output(LOCK, 0) # open


def main():
    initialise()
    main_loop()  # TEST ---


if __name__ == "__main__":
    main()
