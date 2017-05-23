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

void pulse() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
}

void setup() {
  pinMode(SIG_PIN, OUTPUT);
  digitalWrite(SIG_PIN, LOW);//default
  pinMode(SS_PIN, INPUT_PULLUP);
  pinMode(RST_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
}

void loop() {
  delay(5);
  if(digitalRead(SS_PIN) == ON && at == OFF) {
     at = ON;
     digitalWrite(SIG_PIN, HIGH);
     digitalWrite(LED_BUILTIN, HIGH);
     return;
  }
  if(digitalRead(RST_PIN) == ON && at == ON) {
     at = OFF;
     digitalWrite(SIG_PIN, LOW);
     digitalWrite(LED_BUILTIN, LOW);
     return;
  }
}

