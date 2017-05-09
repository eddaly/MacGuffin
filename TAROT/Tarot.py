# Mc Guffin TAROT
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

#import serial

# import MFRC522 # the RFID lib

BUILD = True
STARTER_STATE = 1  # the initial state after reset for the ease of build
TX_UDP_MANY = 1  # UDP reliability retransmit number of copies
RX_PORT = 5000  # Change when allocated, but to run independent of controller is 8080

TAROT_ACK = [25, 8, 7, 16, 20, 21]  # Tarot placed ACK
CORRECT_ACK = [2, 3, 17, 27, 22, 10]  # Correct placed ACK <== NUMBER OF GPIO, TOLD 2 PER DUINO

# the_key = [101, 102, 103, 104, 105, 106]  # cards correct <== KEY DONE BY DUINO

heart = True

# ============================================
# ============================================
# SET MODE FIRST (NO PIN DEFS BEFORE)
# ============================================
# ============================================
GPIO.setmode(GPIO.BCM)

for i in range(6):
    GPIO.setup(TAROT_ACK[i], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(CORRECT_ACK[i], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ===================================
# RFID CARDS
# ===================================

card_at = [False, False, False, False, False, False]

# a nice lock free algorithm for detection
# duino max signalling 0.3 seconds
#
def cards():  # check for right id code return true on got
    global card_at
    flag = True
    for i in range(len(TAROT_ACK)):
        if GPIO.input(TAROT_ACK[i]) == 1:
            if GPIO.input(CORRECT_ACK[i]) == 1:
                if card_at[i] == False:
                    send_packet('1' + str(i) + '2')  # correct
                card_at[i] = True
            else:
                flag = False
                # for j in range(len(CORRECT_ACK)): # must check others?? <== via duino script 2 lines active
                if card_at[i] == False:
                    send_packet('1' + str(i) + '1')  # bad order
                card_at[i] = True
        else:
            if (GPIO.input(CORRECT_ACK[i]) == 1) and (GPIO.input(TAROT_ACK[i]) == 0): # race check
                # this makes the assertion order important
                time.sleep(0.2) # SLEEP TO MAKE SURE IN SAME CYCLE OF DUINO
                if (GPIO.input(TAROT_ACK[i]) == 1) or (GPIO.input(CORRECT_ACK[i]) == 0): # exit race
                    return False # exit and reloop
                flag = False
                if card_at[i] == False:
                    send_packet('1' + str(i) + '0')  # bad card
                card_at[i] = True
            else:
                flag = False
                card_at[i] = False

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

    debug('all reset - releasing the lock')
    if BUILD:
        start_game()  # should not start game yet


def start_game():
    global card_at
    state_w(STARTER_STATE)  # indicate enable and play on TODO: MUST CHANGE TO FIVE???!!!
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    card_at = [False, False, False, False, False, False]  # reset empty


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
        if state_r() == 1:  # PLACE CARDS
            if cards() == True:
                state_w(2)
        if state_r() == 2:
            send_packet('161')
            nop = True


def main():
    initialise()
    main_loop()  # TEST ---


if __name__ == "__main__":
    main()
