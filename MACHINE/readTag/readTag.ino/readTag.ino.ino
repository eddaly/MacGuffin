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
//const int readerID = 1; //output pin will activate when reader ID matches tag ID.

//do not change these variables!
byte sector = 0;
byte blockAddr = 1;
byte trailerBlock = 3;

void setup() 
{ 
  //CLKPR = (1<<CLKPCE);
  //CLKPR = B00000001; //4 MHZ -> /64 SPI is 50 kHz approx !! -- ABOUT 8 SCANS PER SECOND WORKS
  //BUT STILL NEED NEW CABLES WITH GOOD DIAELECTRIC SPACING
  //pinMode(signalPin, OUTPUT);
  Serial.begin(9600);
  SPI.begin(); // Init SPI bus
  mfrc522.PCD_Init(); // Init MFRC522
  
  // sets key to 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF which is the factory deafult.
  for (byte i = 0; i < mfrc522.MF_KEY_SIZE; i++)
  {
    key.keyByte[i] = 0xFF;
  }
}

void loop()
{
  //identify any tags in range.
  if ( ! mfrc522.PICC_IsNewCardPresent() )
  {
    //digitalWrite(signalPin, LOW);
    //Serial.println(F("NONE"));
    return;
  }

  //verify data has been read from tag.
  if ( ! mfrc522.PICC_ReadCardSerial() )
  {return;}

  //authentication:
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    //digitalWrite(signalPin, LOW);
    //Serial.println(F("AFAIL"));
    //Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }


  //read data from entire block.
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    //digitalWrite(signalPin, LOW);
    //Serial.println(F("RFAIL"));
    //Serial.println(mfrc522.GetStatusCodeName(status));
    mfrc522.PCD_Init();
    return;
  }
  byte tagID = buffer[0];
  Serial.println(tagID, DEC);

  /* if(tagID == readerID)
  {
    digitalWrite(signalPin, HIGH);
  }
  else {digitalWrite(signalPin, LOW);} */

  mfrc522.PCD_Init();
}
