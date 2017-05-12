# Mac Guffin Theremin 
# 
# Author: A.T. seeper

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

ser = serial.Serial(
port='/dev/ttyUSB0',
baudrate= 9600,)
s = 0

client = OSC.OSCClient()
client.connect(('127.0.0.1', 4559))

GPIO.setmode(GPIO.BCM)
gaugePin = 19 #set pin for pressure gauge
ledPin = 26 
lampPin = 4


#GPIO.setup(lampPin,GPIO.OUT)
GPIO.setup(gaugePin,GPIO.OUT)
GPIO.setup(26,GPIO.OUT)

#GPIO.setup(25,GPIO.OUT)
#GPIO.output(25,GPIO.HIGH)

# 
# GPIO.setup(4,GPIO.OUT)
# GPIO.output(4,GPIO.LOW)

gauge = GPIO.PWM(gaugePin,100) 

# Import SPI library (for hardware SPI) and MCP3008 library.


CLK  = 12
MISO = 24
MOSI = 23
CS   = 18
mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

low_t = 50
high_t = 70
pot = 50
old_pot = 50
wheel_pack = 0
turn_speed = 0
pitch=840
old_pitch=840
f=0
old_f = 30
t_message = "200"
old_t_message = "202"

t=10 #starting pressure level
delay = 0.5 #set turn speed delay here
state = 6 #set initial state, should be 0 at showtime

SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 5001
RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 5000

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((RECV_UDP_IP, RECV_UDP_PORT))

emitted = ''


#def emit_once(body):
#    global emitted
#    if body != emitted:
#        emitted = body
#        send_packet(body) # just once

def send_packet(body):
    send_sock.sendto(body, (SEND_UDP_IP, SEND_UDP_PORT))
    

def receive_packet():
    print 'r_packet'
    data, addr = recv_sock.recvfrom(1024)
    print 'r_packet:',data
    return data

def reset_all():
    print 'reset all'
    global state
    global wheel_pack
    global t
    global t_message
    global old_t_message
    global old_f
    l = threading.Lock()
    l.acquire
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)
    gauge.start(0)
    GPIO.output(ledPin,GPIO.LOW)
    #GPIO.output(25,GPIO.HIGH)
    #GPIO.output(4,GPIO.LOW)
    state = 0
    wheel_pack = 0
    t = 10
    t_message = "200"
    old_t_message = "202"
    old_f = 440
    s = 100

    # ////////////////////////////////////////////////////
    
    l.release
    print 'all reset'
    
def start_game():
    global state
    print 'start game'
    l = threading.Lock()
    l.acquire
    state = 4

    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    ## actually this should probably go in reset_all(), start game shoudl never be called from the show controller without reset_all having already been called.  
    
    
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
    reset_all()
    ser.flushInput()
    voidval = ser.readline()
    time.sleep(1)
    t1 = threading.Thread(target=reset_loop)
    t1.daemon = False
    t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    

def lock(low_t, high_t): # the half second lock check routine
    global wheel_pack
    global state
    l = threading.Lock() # good job l.acquire without () does nothing, (holding locks over sleep is not good)
    time.sleep(0.5) # half second delay for to acquire number through ADC
    pot = mcp.read_adc(0)
    l.acquire # needs () to active, but 32 bit aligned memory access atomicity works. locks only required
    # when accessing 2 object items in the same object, and both have to be "changed at the same time"
    if pot >= low_t and pot <= high_t: # correct number
        wheel_pack += 1
        state = 1
        send_packet("101") # correct number send message ok
        l.release
    elif pot < 11: # moved to X position
        state = 1
        wheel_pack = 0
        send_packet('103') # dial reset
        # l.release # this is a function reference pointer. () is needed to use it
        # how would "t1 = threading.Thread(target=reset_loop)" set the thread to use? if reset_loop() was evaluated?
    else: # is this a flood of input when the machine first starts?
        wheel_pack = 0
        state = 4
        send_packet("100") # error noise (1st time ok, second time etc no does????)
        # maybe it was idling "bing! bing! bing!"
        l.release
        
        

def turn():
    global pot
    global turn_speed
    old_pot = pot
    time.sleep(delay)
    pot = mcp.read_adc(0)
    turn_speed = abs(pot - old_pot)


def waiting(): # checks to see if wheel moved before combination entry
    global state
    l = threading.Lock()
    turn()
    if turn_speed > 5:
        l.acquire
        state = 2
        l.release

def stop_wait(): # checks to see if wheel stopped before combination entry (1st digit?)
    global state
    l = threading.Lock()
    turn()
    
    if turn_speed < 5:
        l.acquire
        state = 3
        l.release

def Wheel_pack(): # check combination to see if digits entered (half second gaps in lock)
    global state
    l = threading.Lock()
    if wheel_pack == 0:
        lock(456, 563)
    elif wheel_pack == 1:
        lock(983,1023)
    elif wheel_pack == 2:
        lock(28,134)
    elif wheel_pack == 3:
        lock(348,453)
    else: # wheel pack at 4 starts theremin
        l.acquire
        #GPIO.output(ledPin,GPIO.HIGH)
        state = 5
        l.release    

def clear():
    global state
    l = threading.Lock()
    time.sleep(0.5)
    l.acquire
    pot = mcp.read_adc(0)
    if pot < 11:
        state = 1
        send_packet('103') # dial reset for start of combination entry
    else:
        # send_packet('100') # this is a wrong thing digit THERE MAYBE COMPLAINTS!!!
    l.release

def theremin():
    GPIO.output(ledPin,GPIO.HIGH)
    global t
    global s
    global pitch
    global old_pitch
    global state
    global t_message
    global old_t_message
    global old_f
    l = threading.Lock()
    msg = OSC.OSCMessage()
    msg.setAddress("/play_this")
    play = OSC.OSCMessage()
    play.setAddress("/play")
    
    old_f = s
    s = int(ser.readline())
    pitch = s
    print 'pitch:', pitch
    print 't:',t
    #gauge.ChangeDutyCycle(t)
    l.acquire       

    if s > 109 and s < 881:
        f = 0
        if pitch != old_pitch:
            msg.insert(0,pitch)
            client.send(msg)
     
    if s != 100 and old_f == 100 :
        play.insert(0,1)
        client.send(play)
    if s == 100 and old_f != 100 :
        t = 0
        play.insert(0,0)
        client.send(play)
    
    
    
    if pitch > 410 and pitch < 470:
        t = t + 1
    elif pitch == 100:
        pass
    else:
        t = t - 1
    
    if t > 60:
        t_message = "201"
    if t < 61:
        t_message = "200"
    
    if t > 90:
        t = 90
    elif t < 0:
        t = 0
    else:
        pass
    
    old_pitch = pitch
    
    if t >= 90:
        play.insert(0,0)
        client.send(play)
        state = 6
        t_message = "202"
        #GPIO.output(25,GPIO.HIGH)
        
    if t_message != old_t_message:
        send_packet(t_message)
        
    old_t_message = t_message
    
    l.release
    time.sleep(0.0048)


def idle():
    #GPIO.output(25,GPIO.HIGH)
    pot = mcp.read_adc(0)
    print 'pot:',pot
    time.sleep(0.5)    


def pressure(t):
    r = randint(1,10)
    p = t + (r-5)
    p = abs(p)
    gauge.ChangeDutyCycle(p)
    time.sleep(0.01)
    

def main():

    initialise()

    while True:
        global state
        global old_pot
        global wheel_pack
        print 'state:',state
        print 'wheel_pack:', wheel_pack
        time.sleep(0.0001)
        voidval = ser.readline()
        if state == 0:
            idle()
        if state == 1:
            pot = mcp.read_adc(0)
            old_pot = pot
            if wheel_pack == 4: # THIS IF STATEMENT REMOOVES THE THEREMIN
                state = 5 #this should be 5 when sensor is active
                #GPIO.output(25,GPIO.LOW)
                send_packet("102")
                #voidval = ser.readline()
                time.sleep(2)
                send_packet("202") 
                #voidval = ser.readline()
                #time.sleep(1)
            else:
                waiting()
        if state == 2:
            stop_wait()
        if state == 3:
            Wheel_pack()
        if state == 4:
            clear()
        if state == 5:
            pressure(t)
            theremin()
        if state == 6:
            pressure(t)
        


if __name__ == "__main__":
    main()
    
    
