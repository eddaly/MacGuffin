
#define echoPin 11 // Echo Pin
#define trigPin 13 // Trigger Pin


char dataString[50] = {0};

int maximumRange = 500; // Maximum range needed
int minimumRange = 40; // Minimum range needed
long duration, distance, average; // Duration used to calculate distance
int freq = 0;
int old_freq = 0;
int good_freq = 0;
float alpha = 0.5;
long value;
int del = 0;
int f = 0;

int m_direction;
int old_m_direction;

int d_flag;
int old_d_flag;
int d_flag_change;
int timer;

int cntrl_pin = 2;
int cntrl_trigger = 0;

void setup() {
 Serial.begin (9600);
 pinMode(cntrl_pin, INPUT);
 pinMode(trigPin, OUTPUT);
 pinMode(echoPin, INPUT);

}

void loop() {
/* The following trigPin/echoPin cycle is used to determine the
 distance of the nearest object by bouncing soundwaves off of it. */ 
 //cntrl_trigger = digitalRead(cntrl_pin);
 //Serial.println(cntrl_trigger);
 //if (cntrl_trigger == LOW){
 digitalWrite(trigPin, LOW); 
 delayMicroseconds(2); 

 digitalWrite(trigPin, HIGH);
 delayMicroseconds(10); 
 
 digitalWrite(trigPin, LOW);
 
 duration = pulseIn(echoPin, HIGH, 10000);
 
 //Calculate the distance (in cm) based on the speed of sound.
 distance = duration/5.82;
 

old_freq = freq;  
freq = map(distance,40,500,110,880);


m_direction = freq - old_freq;
m_direction = abs(m_direction);


if (m_direction > 60){
  return;
}

 if (distance >= maximumRange || distance <= minimumRange){
f += 1;
freq = good_freq; 
}


else if (distance < maximumRange and distance > minimumRange){
f = 0;
}

if (f > 3){
  freq = 100;
}


sprintf(dataString, "%02X", freq);
Serial.println(freq);
good_freq = freq;
 
 delay(48);
}
