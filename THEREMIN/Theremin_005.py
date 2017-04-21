# Mc Guffin Theremin 
# 
# Author: A.T. seeper

# Import SPI library (for hardware SPI) and MCP3008 library.
import OSC
from random import randint
import time
from math import*
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

GPIO.setup(gaugePin,GPIO.OUT)
#GPIO.setup(19,GPIO.OUT)

gauge = GPIO.PWM(gaugePin,100) 

GPIO.setwarnings(False)


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
r=0
t=10

SEND_UDP_IP = "10.100.1.100"
SEND_UDP_PORT = 501
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

RECV_UDP_IP = "0.0.0.0"
RECV_UDP_PORT = 5000

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
    
    state = 6
    wheel_pack = 0
    # TODO: If there is anything else you want to reset when you receive the reset packet, put it here :)
    
    l.release
    print 'all reset - releasing the lock'
    

def reset_loop():
    while True:
        result = receive_packet()
        print 'waiting for interupt'
        
        if result == "101":
            reset_all()
        
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
    print 'lock', wheel_pack
    time.sleep(0.5)
    pot = mcp.read_adc(0)
    if pot >= low_t and pot <= high_t:
        wheel_pack += 1
        state = 1
    else:
        wheel_pack = 0
        state = 5
        
        

def turn():
    global pot
    global turn_speed
    old_pot = pot
    time.sleep(delay)
    pot = mcp.read_adc(0)
    print 'turn', 'pot:',pot
    turn_speed = abs(pot - old_pot)
                  

def waiting():
    global state
    turn()
    print 'waiting', turn_speed
    if turn_speed > 5:
        state = 2
    

##def state_1(state):
##    l = threading.Lock()
##    l.acquire
##    global wheel_pack
##    print 'state 1', wheel_pack
##    print(state)
##    pot = mcp.read_adc(0)
##    waiting()
##    l.release

def pressure(state, t):
    if state == 4:
        r = random.randint(0,10)
        p = t + (r-5) 
        gauge.ChangeDutyCycle(p)
        time.sleep(0.01)
    

def main():

    initialise()

    while True:
        global state
        if state == 1:
            state_1(state)
        
        while state == 1:
            print 'state 1', wheel_pack
            print(state)
            pot = mcp.read_adc(0)
            waiting()

        while state == 2:
            print('state 2')
            turn()
            if turn_speed < 5:
                state = 3
            
        while state == 3:# set lock values here. 
            print('state 3',wheel_pack)
            if wheel_pack == 0:
                lock(500, 550)
            elif wheel_pack == 1:
                lock(50,100)
            elif wheel_pack == 2:
                lock(950, 1000)
            elif wheel_pack == 3:
                lock(230, 380)
            else:
                state = 4

            
        while state == 5:
            print 'state5'
            pot = mcp.read_adc(0)
            time.sleep(0.5)
            if pot == 0:
                state = 1
        
        while state == 4:
            print("state5")
            #light output low, noisey
            #sensor controls pitch
            #pressure and brigtness rise as you get close to correct pitch

            #while state == 6:
            #time on correctpitch = win
            #send trigger
            ser.flushInput()
            msg = OSC.OSCMessage()
            msg.setAddress("/play_this")
            play = OSC.OSCMessage()
            play.setAddress("/play")
            
            s = int(ser.readline())
            
            #gauge.ChangeDutyCycle(t)
                    
            if s == 100:
                r = r + 1
                print("OOR")
            
            elif s > 109 and s < 881:
                r = 0
                pitch = s
                if pitch != old_pitch:
                    msg.insert(0,pitch)
                    client.send(msg)
             
            if r == 0 :
                play.insert(0,1)
                client.send(play)
            if r > 30 :
                play.insert(0,0)
                client.send(play)
                
            if pitch > 420 and pitch < 460:
                t = t + 3
            
            old_pitch = pitch
            
            if t > 90:
                play.insert(0,0)
                client.send(play)
                state = 6
        
            time.sleep(0.01)

        while state == 6:
            print("winner")
            time.sleep(10)
            state = 1
        l.release()
        sleep(0.001)

if __name__ == "__main__":
    
    print state
    
    main()
