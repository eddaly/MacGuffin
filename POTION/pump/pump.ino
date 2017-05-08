//device reset (the closed, return position)
#define RST_PIN 9
//slave select (the pressed position)
#define SS_PIN  10
//pi signal pin
#define SIG_PIN 2

//needs a hang check
#define ON LOW
#define OFF HIGH

int at = OFF;

void setup() {
  pinMode(SIG_PIN, OUTPUT);
  digitalWrite(SIG_PIN, LOW);//default
  pinMode(SS_PIN, INPUT_PULLUP);
  pinMode(RST_PIN, INPUT_PULLUP);
}

void loop() {
  delay(0.05);
  if(digitalRead(SS_PIN) == ON && at == OFF) {
     at = ON;
     digitalWrite(SIG_PIN, HIGH);
     return;
  }
  if(digitalRead(RST_PIN) == ON && at == ON) {
     at = OFF;
     digitalWrite(SIG_PIN, LOW);
     return;
  }
}

