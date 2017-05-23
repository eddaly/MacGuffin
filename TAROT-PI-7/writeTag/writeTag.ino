//Use this program to change the tag ID of RFID tokens.

#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN  10

MFRC522 mfrc522(SS_PIN, RST_PIN);

MFRC522::MIFARE_Key key;

int tagID = 401;

//do not change these vaiables!
const byte sector = 0;
const byte blockAddr = 1;
const byte trailerBlock = 3;

//variables associated with program flow control.
bool secondAttempt = false;
char proceed = 'n';
long timeout = 0;
const long timeoutMax = 5000;

//tag ID will be written into index 0 of the data block.
byte dataBlock[] =
  {
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00
  };

void setup()
{
  Serial.begin(9600); // Initialize serial communications with the PC
  SPI.begin();        // Init SPI bus
  mfrc522.PCD_Init(); // Init MFRC522 card

  // sets key to 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF which is the factory deafult.
  for (byte i = 0; i < mfrc522.MF_KEY_SIZE; i++)
  {
    key.keyByte[i] = 0xFF;
  }
  
  Serial.println(F("CAUTION: this application will overwrite tag data!"));
}

void loop()
{
  //only prints text when main loop initalises.
  if (secondAttempt == true)
  {}
  else
  {
    Serial.println("Please enter tag ID (from 1 to 255) via serial monitor.");
    Serial.println();
  }

  //waits for serial monitor input.
  while (! Serial.available())
  {
    delay(10);
  }
  
  while (Serial.available() > 0)
  {    
    tagID = Serial.parseInt();
    if ( (tagID <= 0) || (tagID > 255) ) //if serial input is outside valid range request another serial input.
    {
      Serial.println("Not a valid ID, please enter another ID.");
      Serial.println();
      secondAttempt = true;
      return;
    }
  }
  
  dataBlock[0] = tagID;
  Serial.print("New tag ID will be: ");
  Serial.println(tagID);
  Serial.println();
  Serial.print("Is this correct (y/n)?");
  Serial.println();
  while (! Serial.available() )
  {
    delay(10);
  }
  while (Serial.available() > 0)
  {    
    proceed = Serial.read();
    if ( (proceed == 'y') )
    {}
    else
    {
      secondAttempt = false;
      Serial.println();
      return;
    }
  }
  
  Serial.println("Present tag to RFID reader");
  Serial.println();
  
  //continuously searches for a tag. If no tag is detected, program is reset.
  timeout = 0;
  while ( ! mfrc522.PICC_IsNewCardPresent())
  {
    delay(10);
    timeout = timeout + 10;
    if (timeout >= timeoutMax)
    {
      Serial.println("No tag detected. Program timed out");
      Serial.println();
      secondAttempt = false;
      return;  
    }
  }

  //ensures data has been read. If tag cannot be read, program is reset.
  timeout = 0;
  while ( ! mfrc522.PICC_ReadCardSerial())
  {
    delay(10);
    timeout = timeout + 10;
    if (timeout >= timeoutMax)
    {
      Serial.println("Tag could not be read. Program timed out");
      Serial.println();
      secondAttempt = false;
      return;  
    }  
  }

  Serial.println("Card detected and data received.");
  Serial.println();
  Serial.println("Do not remove card until overwrite is complete.");
  Serial.println();
  delay(1000);

  Serial.print(F("PICC type: "));
  MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
  Serial.println(mfrc522.PICC_GetTypeName(piccType));
  if ( piccType != MFRC522::PICC_TYPE_MIFARE_MINI && piccType != MFRC522::PICC_TYPE_MIFARE_1K && piccType != MFRC522::PICC_TYPE_MIFARE_4K )
  {
    Serial.println(F("This sample only works with MIFARE Classic cards."));
    delay(2000);
    return;
  }
  Serial.println();

  MFRC522::StatusCode status;
  byte buffer[18];
  byte size = sizeof(buffer);

  //authentication:
  Serial.println(F("Authenticating..."));
  status = (MFRC522::StatusCode) mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print(F("Authentication failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    delay(2000);
    return;
  }
  else
  {
    Serial.println("Authentication complete");
  }
  Serial.println();

  //read data from entire block.
  Serial.println(F("Reading current tag ID..."));
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print(F("Read operation failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    delay(2000);
    return;
  }
  Serial.print("Current tag ID: ");
  Serial.println(buffer[0]);
  Serial.println();

  //write data to entire block
  Serial.print(F("Overwriting current tag ID..."));
  Serial.println();
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Write(blockAddr, dataBlock, sizeof(dataBlock));
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print(F("Write opteration failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    delay(2000);
    return;
  }
  else
  {
    Serial.println("Overwrite complete.");
  }
  Serial.println();

  //check data has been written to entire block correctly.
  Serial.print(F("Checking tag ID was overwritten correctly..."));
  Serial.println();
  status = (MFRC522::StatusCode) mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print(F("Read operation failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    delay(2000);
    return;
  }
        
  byte count = 0;
  //compare buffer (i.e. what has been read) with dataBlock (i.e. what was written).
  for (byte i = 0; i < 16; i++)
  {
    if (buffer[i] == dataBlock[i])
      {count++;}
  }
  if (count == 16)
  {
    Serial.println(F("Tag ID overwritten successfully."));
    Serial.println();
    Serial.print(F("New tag ID: "));
    Serial.println(buffer[0]);
  }
  else
  {
    Serial.println(F("Tag ID failed to overwrite correctly. Please try again."));
    delay(2000);
    return;
  }
  Serial.println();

  // Halt PICC
  mfrc522.PICC_HaltA();
  // Stop encryption on PCD
  mfrc522.PCD_StopCrypto1();

  secondAttempt = false;
}

/**
 * Helper routine to dump a byte array as hex values to Serial.
 */
void dump_byte_array(byte *buffer, byte bufferSize)
{
  for (byte i = 0; i < bufferSize; i++)
  {
    Serial.print(buffer[i] < 0x10 ? " 0" : " ");
    Serial.print(buffer[i], HEX);
  }
}
