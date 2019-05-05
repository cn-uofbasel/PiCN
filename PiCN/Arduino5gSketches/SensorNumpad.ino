/**

    This is the MKR NB 1500 MQTT sketch, configured
    to work with the IoThon 2019 VMs.

    Required libraries:
      - MKRNB
      - PubSubClient
**/

/**************************************************
 * At minimum do change the following.
 *
 * If you don't change them, you will be sending your
 * data to the example server, at the example topic
 */
#define MQTT_TOPIC_TEMPERATURE "iothon/myteam/temperature"
#define MQTT_TOPIC_RSSI        "iothon/myteam/rssi"
#define MQTT_TOPIC_STATE       "iothon/myteam/status"
#define MY_SERVER  "10.200.1.1"
/****************************************************/

// #include <Adafruit_Sensor.h>
// #include <Adafruit_BME280.h>

#include <MKRNB.h>
#include <PubSubClient.h>
#include <SPI.h>        
#include <Ethernet.h>
#include <Wire.h>
#include "SparkFun_Qwiic_Keypad_Arduino_Library.h"
//#include <EthernetUdp.h>

// If you are not using the default PIN, consider using "arduino_secrets.h"
// See https://www.hackster.io/Arduino_Genuino/store-your-sensitive-data-safely-when-sharing-a-sketch-e7d0f0
const char PIN_NUMBER[] = "1234";
const char APN[] = ""; // "iot";

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

KEYPAD keypad1;
IPAddress ip(195, 148, 126, 102);
unsigned int localPort = 7777;  
NBUDP Udp;
String currentNumber;
String input;

//#define UDP_TX_PACKET_MAX_SIZE
char packetBuffer[UDP_TX_PACKET_MAX_SIZE];

NB           nbAccess(false); // NB access: use a 'true' parameter to enable debugging
GPRS         gprsAccess;     // GPRS access

void setup() {
  Serial.begin(115200);
  while (! Serial)
    ;

  String t;

  Serial.println("connecting keypad...");
  if (keypad1.begin() == false) {
    Serial.println("Keypad does not appear to be connected. Please check wiring. Freezing...");
    while (1);
  }

  Serial.println("Keypad connected");

  Serial.println("MKR NB 1500 MQTT client starting.");

  Serial.println("Connect: NB-IoT / LTE Cat M1 network (may take several minutes)...");
  while (nbAccess.begin(PIN_NUMBER, APN) != NB_READY) {
    Serial.println("Connect: NB-IoT: failed.  Retrying in 10 seconds.");
    delay(10000);
  }
  Serial.println("Connect: NB-IoT: connected.");

  Serial.println("Acquire: PDP context...");
  while (gprsAccess.attachGPRS() != GPRS_READY) {
    Serial.println("Acquire: PDP context: failed.  Retrying in 10 seconds.");
    delay(10000);
  }
  Serial.println("Acquire: PDP context: acquired.");
#if 1 /* Using newer version of the library */
  Serial.print("Acquire: PDP Context: ");
 // Serial.println(nbAccess.readPDPparameters());
#endif

  Serial.print("Enable all features: ... ");
  MODEM.send("AT+CFUN=1");
  MODEM.waitForResponse(10, &t);
  Serial.println(t);
  Serial.print("Modem to single send mode: ... ");
  MODEM.send("AT+CIPMUX=1");
  MODEM.waitForResponse(10, &t);
  Serial.println(t);


  IPAddress LocalIP = gprsAccess.getIPAddress();
  Serial.print("GPRS IP: ");
  Serial.print(LocalIP);
  Serial.print(" Port: ");
  Serial.println(localPort);
  
  Ethernet.begin(mac, LocalIP); // IP = LocalIP
  Udp.begin(localPort);


}

long lastMsgTime = 0;

void loop() {
  keypad1.updateFIFO();  
  char c = keypad1.getButton();
  if (c != 0){
    if (c == '#') {
      currentNumber = input; 
      Serial.println("Current Number:");
      Serial.println(currentNumber);  
      input = "";
    }
    else {
      input += c;
    }
  }
//  int counter = 0;
//  Serial.println("Sending Packet");
//  for(int i =0; i < 20; ++i){
//    Udp.beginPacket(ip, localPort);
//    Udp.write("I%58%2Ftest%2Fdata%58");
//    Udp.endPacket();
//    delay(50);
//  }

  char buffer[256];
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    Serial.print("Received packet of size ");
    Serial.println(packetSize);
    Serial.print("From ");
    IPAddress remote = Udp.remoteIP();
    for (int i =0; i < 4; i++)
    {
      Serial.print(remote[i], DEC);
      if (i < 3)
      {
        Serial.print(".");
      }
    }
    Serial.print(", port ");
    Serial.println(Udp.remotePort());
  
    // read the packet into packetBufffer
    memset (packetBuffer, 0, UDP_TX_PACKET_MAX_SIZE);
    Udp.read(packetBuffer,UDP_TX_PACKET_MAX_SIZE);
    Serial.println("Contents:");
    Serial.println(packetBuffer);
//    if (packetBuffer == "I:/data/numpad/latest:"){
      Serial.println("Sending packet");
      Serial.println("Content");
      Serial.println(currentNumber.c_str());
      Udp.beginPacket(ip, localPort);
      String data = "C:/data/numpad/latest::";
      data += currentNumber;
      Serial.println(data);
      Udp.write(data.c_str());
      Udp.endPacket();
//    }
  }
  delay(50);
}

int get_data_from_packet(char *content){
    //st
    return 0;
}
