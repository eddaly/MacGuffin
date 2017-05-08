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

//do not change these variables!
byte sector = 0;
byte blockAddr = 1;
byte trailerBlock = 3;

void setup() 
{ 
  pinMode(signalPin, OUTPUT);
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
    digitalWrite(signalPin, LOW);
    return;
  }

  //verify data has been read from tag.
  if ( ! mfrc522.PICC_ReadCardSerial() )
  {return;}

  //authentication:
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    digitalWrite(signalPin, LOW);
    Serial.print(F("Authentication failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }


  //read data from entire block.
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    digitalWrite(signalPin, LOW);
    Serial.print(F("Read operation failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    reset(RST_PIN);
    mfrc522.PCD_Init();
    return;
  }
  int tagID = buffer[0];
  Serial.println(tagID);

  if(tagID == readerID)
  {
    digitalWrite(signalPin, HIGH);
  }
  else {digitalWrite(signalPin, LOW);}

  mfrc522.PCD_Init();
}
