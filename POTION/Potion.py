# Mc Guffin POTION
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

BUILD = False # set for shoe controller
DYNAMIC_CODE = True  # selects the code solve being active at the same time as pumps
STARTER_STATE = 1  # the initial state after reset for the ease of build
TX_UDP_MANY = 1  # UDP reliability retransmit number of copies
RX_PORT = 5000  # Change when allocated, but to run independent of controller is 8080

RGB_LED = [8, 9, 10]  # R, G, B PWM? Software POV effect??!! <== NOT USED
RFID_TAG_ACK = [25, 8, 7]  # Duino #1, #2, #3
PUMP_IN = [16, 20, 21]  # Duino #4, #5, #6 pulse on pull script
PROB = 0.5  # filter for persistance of vision 0 -> 1

# the_key = [3, 5, 4]  # parts red/green/blue

heart = True

# ============================================
# ============================================
# SET MODE FIRST (NO PIN DEFS BEFORE)
# ============================================
# ============================================
GPIO.setmode(GPIO.BCM)

for i in range(3):
    GPIO.setup(RFID_TAG_ACK[i], GPIO.IN)
    GPIO.setup(PUMP_IN[i], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # GPIO.setup(RGB_LED[i], GPIO.OUT)

# ===================================
# RFID CODE
# ===================================

correct = [False, False, False]


# Create an object of the class MFRC522
# MIFAREReader = MFRC522.MFRC522()

def code():  # check for right id code return true on got
    global correct
    flag = True
    for i in range(len(RFID_TAG_ACK)):
        if GPIO.input(RFID_TAG_ACK[i]) == 1:
            if correct[i] == False:
                send_packet('1' + str(i) + '1')  # on
                correct[i] = True
        else:
            flag = False
            if correct[i] == True:
                send_packet('1' + str(i) + '0')  # off
                correct[i] = False

    return flag


# ====================================
# PUMP SEQUENCE
# ====================================
rgb = [0, 0, 0]  # the colour
latch = [False, False, False]


def pump():
    global latch
    global rgb
#    flag = True
    for i in range(len(PUMP_IN)):
        if (GPIO.input(PUMP_IN[i]) == 1) and ((GPIO.input(RFID_TAG_ACK[i]) == 1) or (not DYNAMIC_CODE)):  # check tag
            # are the sounds to be made even when the stopper not in????????
            if latch[i] == False:
                # send_packet('2' + str(i + 1) + '1')  # on
                rgb[i] += 1
                send_packet('2' + str(i) + '1')
            latch[i] = True
        elif (GPIO.input(RFID_TAG_ACK[i]) == 1) or (not DYNAMIC_CODE):
            # flag = False
            if latch[i] == True:
                send_packet('2' + str(i) + '0')  # off
            latch[i] = False

#        if rgb[i] != the_key[i]:
#            flag = False
#        if rgb[i] > the_key[i]:
#            send_packet('overfill')  # NO CODE ISSUED YET
#            rgb = [0, 0, 0]
#    if flag:
#        send_packet('gotit')  # NO CODE ISSUED YET
#    return False


# ====================================
# LED SET
# ====================================

err = False

filtered = [0.0, 0.0, 0.0]  # a residual for later output


# The following is not used as the SC is doing all the lighting
def led():
    global rgb
    global err
    global filtered
    global PROB
    time.sleep(0.01)  # 100 Hz
    red = float(rgb[0]) / float(the_key[0])  # 0 -> 1
    green = float(rgb[1]) / float(the_key[1])  # 0 -> 1
    blue = float(rgb[2]) / float(the_key[2])  # 0 -> 1
    if (red > 1.0) or (green > 1.0) or (blue > 1.0):
        err = True  # over filled
    if err:
        for j in range(5):
            for i in range(3):
                GPIO.output(RGB_LED[i], 1)  # white
            time.sleep(0.5)
            for i in range(3):
                GPIO.output(RGB_LED[i], 0)  # black
            time.sleep(0.5)
        rgb = [0, 0, 0]
        send_packet('2' + str(i) + '0')  # back to
        err = False
    else:  # colour modulation
        red -= filtered[0]
        green -= filtered[1]
        blue -= filtered[2]
        # offsets
        red += 0.5
        green += 0.5
        blue += 0.5
        # clamps
        if red > 1.0:
            red = 1.0
        if red < 0:
            red = 0.0
        if green > 1.0:
            green = 1.0
        if green < 0:
            green = 0.0
        if blue > 1.0:
            blue = 1.0
        if blue < 0:
            blue = 0.0
        # delta sigma lpf????
        s_red = int(red + 0.5)
        s_green = int(green + 0.5)
        s_blue = int(blue + 0.5)
        # output
        GPIO.output(RGB_LED[0], s_red)
        GPIO.output(RGB_LED[1], s_green)
        GPIO.output(RGB_LED[2], s_blue)
        # filtered
        filtered[0] = PROB * filtered[0] + (1.0 - PROB) * s_red
        filtered[1] = PROB * filtered[1] + (1.0 - PROB) * s_green
        filtered[2] = PROB * filtered[2] + (1.0 - PROB) * s_blue


# ====================================
# REMOTE DEBUG CODE
# ====================================
def debug(show):
    # print to pts on debug console
    os.system('echo "' + show + '" > /dev/pts/1')


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

    debug('all reset - releasing the lock')
    if BUILD:
        start_game()  # should not start game yet


def start_game():
    global correct
    global latch
    global rgb
    state_w(STARTER_STATE)  # indicate enable and play on TODO: MUST CHANGE TO FIVE???!!!
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)

    correct = [False, False, False]
    latch = [False, False, False]
    rgb = [0, 0, 0]


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
        if state_r() == 1:  # STOPPERS
            if DYNAMIC_CODE == True:
                state_w(2)  # auto go to pump sequencing
            if code() == True:  # run the code finder
                state_w(2)
                # more states?
        if state_r() == 2:  # PUMPS
            if DYNAMIC_CODE == True:
                code()  # do code sequencing too
            pump()


def main():
    initialise()
    main_loop()  # TEST ---


if __name__ == "__main__":
    main()
