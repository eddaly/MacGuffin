#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN); // Instance of the class
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;
byte buffer[18];
byte size = sizeof(buffer);

const int signalPinTarot = 2; //output pin on which any tarot is communicated.
const int signalPinCorrect = 3; //output pin on which correct tarot is communicated.

const int readerID = 101; //output pin will activate when reader ID matches tag ID.
const int keys[6] = { 101, 102, 103, 104, 105, 106 };

const int ledPin = 13;

//do not change these variables!
byte sector = 0;
byte blockAddr = 1;
byte trailerBlock = 3;

void setup() 
{ 
  pinMode(RST_PIN, OUTPUT);
  pinMode(signalPinTarot, OUTPUT);
  digitalWrite(signalPinTarot, LOW);
  pinMode(signalPinCorrect, OUTPUT);
  digitalWrite(signalPinCorrect, LOW);
  digitalWrite(RST_PIN, LOW);
  Serial.begin(9600);
  SPI.begin(); // Init SPI bus
  mfrc522.PCD_Init(); // Init MFRC522
  
  // sets key to 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF which is the factory deafult.
  for (byte i = 0; i < mfrc522.MF_KEY_SIZE; i++)
  {
    key.keyByte[i] = 0xFF;
  }
}

void reset (int reset_pin)
{
  mfrc522.PCD_Init();
  digitalWrite(reset_pin, HIGH);
  delay(500);
  digitalWrite(reset_pin, LOW);
  asm volatile ("jmp 0"); 
}

void loop()
{
  //identify any tags in range.
  if ( ! mfrc522.PICC_IsNewCardPresent() )
  {
    //Serial.println(-1, DEC);
    pulse();
    removeCard();
    reset(RST_PIN);
    return;
  }

  //Serial.println('G1');
  //verify data has been read from tag.
  if ( ! mfrc522.PICC_ReadCardSerial() )
  {
    //Serial.println(-1, DEC);
    pulse();
    removeCard();
    reset(RST_PIN);
    return;
  }

  //Serial.println('G2');
  //authentication:
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    //Serial.println(-1, DEC);
    pulse();
    removeCard();
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }


    //Serial.println('G3');
//read data from entire block.
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    //Serial.println(-1, DEC);
    pulse();
    removeCard();
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }

 // Serial.println('G4');
  int tagID = buffer[0];
  Serial.println(tagID, DEC);
  if (tagID == readerID)
  {
    //CORRECT
    //CORRECT_ACK goes high, and then TAROT_ACK goes high.
      digitalWrite(signalPinCorrect, HIGH);
      delay(1);
      digitalWrite(signalPinTarot, HIGH);
  } else {
    //NOT CORRECT
    int j = 0;
    for(int i = 0; i < 6; i++) {
      if(keys[i] == tagID) {
        j++;
        //WRONG POSITION
        //TAROT_ACK goes high, while CORRECT_ACK remains low.
        digitalWrite(signalPinCorrect, LOW);
        digitalWrite(signalPinTarot, HIGH);
      }
    }
    if(j == 0) {
      //WRONG CARD
      //if CORRECT_ACK goes high, and TAROT_ACK remains low this implies the error of a wrong card.
      digitalWrite(signalPinTarot, LOW);
      digitalWrite(signalPinCorrect, HIGH);
    }
  }
  pulse();
  reset(RST_PIN);//NEEDS TO BE HERE TO LIMIT RATE OF SEND TO AVOID RACE (PI WAITS 100)

  mfrc522.PCD_Init();
}

void removeCard() {
  //REMOVE
  //TAROT_ACK goes low, then CORRECT_ACK goes low.
  digitalWrite(signalPinTarot, LOW);
  delay(1);
  digitalWrite(signalPinCorrect, LOW);
}

void pulse()
{
  digitalWrite(ledPin, HIGH);
  delay(100);
  digitalWrite(ledPin, LOW);
}

