#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Wire.h> 
#include <LiquidCrystal_I2C.h>
#include "wifi_keys.h"
LiquidCrystal_I2C lcd(0x27,20,4); 

// MQTT Broker
const char *mqtt_server = "192.168.1.234";
const char* topics[] = {
  "temperature_alarm",
  "intrusion_human",
  "intrusion_animal"
};
const int numTopics = sizeof(topics) / sizeof(topics[0]);
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char *topic, byte *payload, unsigned int length) {
    if (strcmp(topic, "temperature_alarm") == 0) {
        Serial.print("Alert! Temperature alarm received in topic: ");
        Serial.println(topic);
        Serial.print("Message:");
        for (int i = 0; i < length; i++) {
            Serial.print((char) payload[i]);
        }
        Serial.println();
        Serial.println("-----------------------");

        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("High Temperature");
        lcd.setCursor(0,1);
        lcd.print("Detected!");

        tone(12, 1000, 2000);
        delay(1000);          
        tone(12, 500, 2000);  
        delay(1000);                       
    } 
    // Handle intrusion_alarm topic
    else if (strcmp(topic, "intrusion_human") == 0) {
        Serial.print("Alert! Human intrusion detected in topic: ");
        Serial.println(topic);
        Serial.print("Message:");
        for (int i = 0; i < length; i++) {
            Serial.print((char) payload[i]);
        }
        Serial.println();
        Serial.println("-----------------------");

        // Display alert message on LCD for intrusion_human
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Human Intrusion");
        lcd.setCursor(0,1);
        lcd.print("Detected!");

        // Play a different tone for human intrusion (customize as needed)
        tone(12, 800, 2000);
        delay(1000);          
        tone(12, 400, 2000);  
        delay(1000);  
    }

    // Handle intrusion_animal topic
    else if (strcmp(topic, "intrusion_animal") == 0) {
        Serial.print("Alert! Animal intrusion detected in topic: ");
        Serial.println(topic);
        Serial.print("Message:");
        for (int i = 0; i < length; i++) {
            Serial.print((char) payload[i]);
        }
        Serial.println();
        Serial.println("-----------------------");

        // Display alert message on LCD for intrusion_animal
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Animal Intrusion");
        lcd.setCursor(0,1);
        lcd.print("Detected!");

        // Play a different tone for animal intrusion (customize as needed)
        tone(12, 600, 2000);
        delay(1000);          
        tone(12, 300, 2000);  
        delay(1000);  
    }
}

void playReadyTone() {
  int melody[] = {262, 330, 392, 523};
  int noteDurations[] = {4, 4, 4, 4};

  for (int thisNote = 0; thisNote < 4; thisNote++) {
    int noteDuration = 1000 / noteDurations[thisNote];
    tone(12, melody[thisNote], noteDuration);

    int pauseBetweenNotes = noteDuration * 1.30;
    delay(pauseBetweenNotes);

    }
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT reconnection...");
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
      // Resubscribe to MQTT topics after reconnecting
      for (int i = 0; i < numTopics; i++) {
        client.subscribe(topics[i]);
      }
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}


void setup()
{
  // Initialize serial and LCD
  Serial.begin(9600);
  Wire.begin(4, 5);
  lcd.init();
  lcd.backlight();

  // Welcome message on LCD
  lcd.setCursor(0,0);   
  lcd.print("Initializing...");
  delay(1000);
  lcd.clear();

  // Connect to Wi-Fi
  lcd.setCursor(0,0);
  lcd.print("Connecting Wifi");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    lcd.setCursor(0,1);
    lcd.print("Please wait...");
    delay(1000);
    lcd.setCursor(0,1);
    lcd.print("              ");  // Clear the previous message
  }

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("WiFi connected!");
  Serial.println("WiFi connected");
  delay(1000);
  lcd.clear();

  // Connect to MQTT broker
  lcd.setCursor(0,0);
  lcd.print("Connecting MQTT");


  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(15360);
  client.setCallback(callback);

  while (!client.connected()) {
    lcd.setCursor(0,1);
    lcd.print("Please wait...");
    delay(1000);
    lcd.setCursor(0,1);
    lcd.print("              ");  // Clear the previous message

    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP8266Client")) {
      lcd.setCursor(0,1);
      lcd.print("MQTT connected!");
      Serial.println("MQTT connected");
      delay(1000);
    } else {
      lcd.setCursor(0,1);
      lcd.print("Retry in 5 secs");
      Serial.print("Connection failed, rc=");
      Serial.print(client.state());
      Serial.println(". Retrying in 5 seconds...");
      delay(5000);
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Connecting to MQTT");
    }
  }

  // Subscribe to topics
  for (int i = 0; i < numTopics; i++) {
    client.subscribe(topics[i]);
  }
  delay(1000);
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("System ready!");
  delay(1000);
  playReadyTone();
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();
}


