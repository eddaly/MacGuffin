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

int id = -1;
int delayed_id = -1;
int compare_id = -1; // A delay slot
int compare2_id = -1; // A second delay slot

void indicate() {
  if(id == delayed_id) {// id 
    compare_id = id; // A WOBBLE FIX
    compare2_id = id;
  }
  if(id != delayed_id) return; // fresh wobble
  Serial.println(delayed_id, DEC);// NO CARD
}

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
  // delayed comparison for wiggle debounce
  delayed_id = compare2_id;
  compare2_id = compare_id;
  compare_id = id;

  delay(120); //delay 120 ms so as to have lower output rate than python reading
  //identify any tags in range.
  if ( ! mfrc522.PICC_IsNewCardPresent() )
  {
    //digitalWrite(signalPin, LOW);
    id = -1;
    indicate();// NO CARD
    return;
  }

  //verify data has been read from tag.
  if ( ! mfrc522.PICC_ReadCardSerial() )
  {return;} // A POTENTIAL READ ERROR IGNORED

  //authentication:
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    //digitalWrite(signalPin, LOW);
    //Serial.println(-1, DEC); // A POTENTIAL AUTHENTICATION ERROR IGNORED
    //Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }


  //read data from entire block.
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    //digitalWrite(signalPin, LOW);
    //Serial.println(-1, DEC); // READ FAIL IGNORE
    //Serial.println(mfrc522.GetStatusCodeName(status));
    mfrc522.PCD_Init();
    return;
  }
  byte tagID = buffer[0];
  id = tagID;
  indicate();// PRINT CARD ID

  /* if(tagID == readerID)
  {
    digitalWrite(signalPin, HIGH);
  }
  else {digitalWrite(signalPin, LOW);} */

  mfrc522.PCD_Init();
}
