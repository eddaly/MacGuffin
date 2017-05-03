# Mac Guffin Lever 
# 
# Author: A.T. seeper

import time
import RPi.GPIO as GPIO
import socket
import threading

GPIO.setmode(GPIO.BCM)

#output pins
red_led = 5
green_led = 13
bot_mag = 19
top_mag = 26

#input pins
red_relay = 20
green_relay = 21
gate_relay = 16

GPIO.setup(red_led,GPIO.OUT)
GPIO.setup(green_led,GPIO.OUT)
GPIO.setup(bot_mag,GPIO.OUT)
GPIO.setup(top_mag,GPIO.OUT)

GPIO.setup(red_relay,GPIO.IN)
GPIO.setup(green_relay,GPIO.IN)
GPIO.setup(gate_relay,GPIO.IN)

GPIO.output(red_led, GPIO.LOW)
GPIO.output(green_led, GPIO.LOW)
GPIO.output(bot_mag, GPIO.LOW)
GPIO.output(top_mag, GPIO.LOW)

state = 6 #set initial state, 0 at showtime ## SET THIS IN reset_all() ## and CHECK STATE IN START FUNC 
SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 5000

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))

def send_packet(body):
    print 'sending packet:', body
    send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
    

def receive_packet():
    print 'r_packet'
    data, addr = recv_sock.recvfrom(1024)
    print 'r_packet:',data
    return data

def reset_all():
    print 'reset all'
    global state
    global red_led
    global green_led
    global bot_mag
    global top_mag

    l = threading.Lock()
    l.acquire
	# TODO: reset commands go here
    GPIO.output(red_led, GPIO.HIGH)
    GPIO.output(green_led, GPIO.LOW)
    GPIO.output(bot_mag, GPIO.LOW)
    GPIO.output(top_mag, GPIO.HIGH)    
    state = 0 ## should be 0 at show time
    # ////////////////////////////////////////////////////
    
    l.release
    print 'all reset'
    
def start_game():
    global state
    print 'start game'
    l = threading.Lock()
    l.acquire
    state = 1

    # TODO: start game commands go here
    
    
    # ////////////////////////////////////////////////////
    l.release

def reset_loop():
    
    while True:
        print 'waiting for interupt'
        result = receive_packet()
        print 'received interupt'
        
        if result == "reset":
            reset_all()
        if result == "start":
            start_game()
        
        time.sleep(0.01)
    

def heartbeat_loop():
    while True:
        l = threading.Lock()
        l.acquire
        send_packet("H")
        print 'H'
        l.release
        time.sleep(5)
    

def initialise():
    print 'init'
    reset_all()
    t1 = threading.Thread(target=reset_loop)
    t1.daemon = False
    t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    


def idle():    
    time.sleep(0.5) 
	
	
def gate():
    global gate_relay
    global red_led
    global green_led
    global bot_mag
    global top_mag
    global state
    time.sleep(0.5)
    val = GPIO.input(gate_relay)
    print val
    l = threading.Lock()
    l.acquire
    if val == 1:
        GPIO.output(red_led, GPIO.LOW)
        GPIO.output(green_led, GPIO.HIGH)
        GPIO.output(bot_mag, GPIO.HIGH)
        GPIO.output(top_mag, GPIO.LOW)
        send_packet("101")
        state = 2
        #print 'yes the state should be 2 ffs'
        l.release
    elif val == 0:
        state = 1
        l.release
	
def lightning():
    global green_relay
    global state
    global gate_relay
    global top_mag
    val = GPIO.input(green_relay)
    print val
    l = threading.Lock()
    if GPIO.input(green_relay) == 1:
        l.acquire
        send_packet("301")
        state = 3
        l.release
    elif GPIO.input(gate_relay) == 0:
        l.acquire
        send_packet("100")
        GPIO.output(top_mag, GPIO.HIGH)
        state = 1
        l.release	
    time.sleep(0.1)


def main():

    initialise()

    while True:
        global state
        print 'state:', state
        time.sleep(0.0001)
        if state == 0:
            idle()
        if state == 1:
            gate()
        if state == 2:
            lightning()
        if state == 3:
            idle()


if __name__ == "__main__":
    main()
    
    
