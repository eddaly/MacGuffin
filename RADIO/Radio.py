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

ser = serial.Serial(
port='/dev/ttyUSB0',
baudrate= 9600,)
s = 0

client = OSC.OSCClient()
client.connect(('127.0.0.1', 4559))

GPIO.setmode(GPIO.BCM)
gaugePin = 19 #set pin for pressure gauge
ledPin = 26 

GPIO.setup(gaugePin,GPIO.OUT)
GPIO.setup(26,GPIO.OUT)



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
delay = 1 #set turn speed delay here

wheel_pack = 0

state = 4 #set initial state, should be 0 at showtime
print 'state:', state


turn_speed = 0

pitch=840
old_pitch=840
f=0
t=10

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
    l = threading.Lock()
    l.acquire
    print 'reset all - got the lock... continue processing'
    gauge.start(0)
    GPIO.output(ledPin,GPIO.LOW)
    state = 0
    wheel_pack = 0
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)
    
    l.release
    print 'all reset - releasing the lock'
    
def start_game():
    global state
    l = threading.Lock()
    l.acquire
    state = 1
    wheel_pack = 0
    # TODO: If there is anything else you want to reset when you receive the start game packet, put it here :)
    l.release

def reset_loop():
    while True:
        result = receive_packet()
        print 'waiting for interupt'
        
        if result == "101":
            reset_all()
        if result == "102":
            start_game()
        
        time.sleep(0.01)
    

def heartbeat_loop():
    while True:
        l = threading.Lock()
        l.acquire
        send_packet("I am alive!")
        print 'isAlive'
        l.release
        time.sleep(10)
    

def initialise():
    reset_all()
    t1 = threading.Thread(target=reset_loop)
    t1.daemon = False
    t1.start()
    t2 = threading.Thread(target=heartbeat_loop)
    t2.daemon = False
    t2.start()
    

def lock(low_t, high_t):
    global wheel_pack
    global state
    l = threading.Lock()
    time.sleep(0.5)
    pot = mcp.read_adc(0)
    l.acquire
    if pot >= low_t and pot <= high_t:
        wheel_pack += 1
        state = 1
        l.release
    else:
        wheel_pack = 0
        state = 4
        l.release
        
        

def turn():
    global pot
    global turn_speed
    old_pot = pot
    time.sleep(delay)
    pot = mcp.read_adc(0)
    turn_speed = abs(pot - old_pot)


def waiting():
    global state
    l = threading.Lock()
    turn()
    if turn_speed > 5:
        l.acquire
        state = 2
        l.release

def stop_wait():
    global state
    l = threading.Lock()
    turn()
    
    if turn_speed < 5:
        l.acquire
        state = 3
        l.release

def Wheel_pack():
    global state
    l = threading.Lock()
    if wheel_pack == 0:
        lock(1000, 1023)
    elif wheel_pack == 1:
        lock(240,300)
    elif wheel_pack == 2:
        lock(705, 770)
    elif wheel_pack == 3:
        lock(113, 163)
    else:
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
      
    l.release

def theremin():
    GPIO.output(ledPin,GPIO.HIGH)
    global t
    global f
    global pitch
    global old_pitch
    global state
    l = threading.Lock()
    ser.flushInput()
    msg = OSC.OSCMessage()
    msg.setAddress("/play_this")
    play = OSC.OSCMessage()
    play.setAddress("/play")
    
    s = int(ser.readline())
    pitch = s
    print 't:',t
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
        
    if pitch > 420 and pitch < 460:
        t = t + 1
    elif pitch == 100:
        pass
    else:
        t = t - 1
    
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
    
    l.release
    time.sleep(0.01)


def idle():
    
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
        time.sleep(0.001)
        if state == 0:
            idle()
        if state == 1:
            pot = mcp.read_adc(0)
            old_pot = pot
            if wheel_pack == 4:
                state = 5
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
    
    
