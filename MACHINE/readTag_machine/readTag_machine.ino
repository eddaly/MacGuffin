#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN); // Instance of the class
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;
byte buffer[18];
byte size = sizeof(buffer);

const int signalPin = 2; //output pin on which signal is communicated.
const int readerID = 1; //output pin will activate when reader ID matches tag ID.
const int ledPin = 13;

//do not change these variables!
byte sector = 0;
byte blockAddr = 1;
byte trailerBlock = 3;

void setup() 
{ 
  pinMode(RST_PIN, OUTPUT);
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
    Serial.println(-1, DEC);
    pulse();
    reset(RST_PIN);
    return;
  }

  //Serial.println('G1');
  //verify data has been read from tag.
  if ( ! mfrc522.PICC_ReadCardSerial() )
  {
    Serial.println(-1, DEC);
    pulse();
    reset(RST_PIN);
    return;
  }

  //Serial.println('G2');
  //authentication:
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    Serial.println(-1, DEC);
    pulse();
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }


    //Serial.println('G3');
//read data from entire block.
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.println(-1, DEC);
    pulse();
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }

 // Serial.println('G4');
  int tagID = buffer[0];
//  if (tagID > 0)
//  {
    Serial.println(tagID, DEC);
//  }
//  else
//  {
//    Serial.println(-1, DEC);
//  }
  pulse();

  mfrc522.PCD_Init();
}

void pulse()
{
  digitalWrite(ledPin, HIGH);
  delay(1000);
  digitalWrite(ledPin, LOW);
}

