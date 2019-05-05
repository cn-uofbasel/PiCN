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
#define UDP_SIZE 256
/****************************************************/

// #include <Adafruit_Sensor.h>
// #include <Adafruit_BME280.h>


#include <Wire.h>
#include "Qwiic_LED_Stick.h" // Click here to get the library: http://librarymanager/All#SparkFun_Qwiic_LED_Stick
#include <MKRNB.h>
#include <PubSubClient.h>
#include <SPI.h>        
#include <Ethernet.h>
//#include <EthernetUdp.h>

// If you are not using the default PIN, consider using "arduino_secrets.h"
// See https://www.hackster.io/Arduino_Genuino/store-your-sensitive-data-safely-when-sharing-a-sketch-e7d0f0
const char PIN_NUMBER[] = "1234";
const char APN[] = ""; // "iot";

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

LED LEDStick; //Create an object of the LED class


IPAddress ip(195, 148, 126, 102);
unsigned int localPort = 8888;  
NBUDP Udp;

//#define UDP_TX_PACKET_MAX_SIZE
char packetBuffer[UDP_SIZE];

NB           nbAccess(false); // NB access: use a 'true' parameter to enable debugging
GPRS         gprsAccess;     // GPRS access

void setup() {
  Serial.begin(115200);
  while (! Serial)
    ;

  String t;

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

  LEDStick.begin();
  clearLED();
}

long lastMsgTime = 0;

int get_int_data_from_packet(char *content){
    String str(content);
    str = str.substring(2);
    int pos = str.indexOf(":");
    str = str.substring(pos+2);
    return str.toInt();
}

String get_name_from_content(char *content){ 
    String str(content);
    str = str.substring(2);
    int pos = str.indexOf(":");
    str = str.substring(0, pos);
    return str;
}

void clearLED(){
  for(byte i=0;i<10;i++){
    LEDStick.setLEDColor(10 - i, 0, 0, 0);
  }
}

void LEDDisplayNumb(int numb){
  for(byte i=0;i<numb;i++){
    LEDStick.setLEDColor(10 - i, 50, 50, 50);
  } 
}

void loop() {
   int counter = 0;
    Serial.println("Sending Packet");
    char buffer[256];
    Serial.println("Waiting for Packet");
    //int packetSize = Udp.parsePacket();
    int packetSize = Udp.parsePacket();
    while (!packetSize)
    {
      packetSize = Udp.parsePacket();
      delay(500);
      Serial.print(".");
      counter = counter + 1;
      if (counter % 8 == 0){
         Serial.println();
         //Serial.println("Retransmit Packet");
         Udp.beginPacket(ip, localPort);
         Udp.write("I:/edge/modTen/_(%2Fdata%2Fnumpad%2Flatest)/NFN:");
         Udp.endPacket();
      }
    }
    packetSize = Udp.parsePacket();
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
    memset (packetBuffer, 0, UDP_SIZE);
    Udp.read(packetBuffer,UDP_SIZE);
    Serial.println("Contents:");
    Serial.println(packetBuffer);
        
    String name = get_name_from_content(packetBuffer);
    int value = get_int_data_from_packet(packetBuffer);
    Serial.println(value);
    clearLED();
    LEDDisplayNumb(value);
    
    delay(1000);
}
