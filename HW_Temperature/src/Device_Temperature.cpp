#include <Adafruit_MLX90640.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "wifi_keys.h"

const char* mqtt_server = "192.168.1.234";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

Adafruit_MLX90640 mlx;
float frame[32*24]; // buffer for full frame of temperatures
StaticJsonDocument<15360> doc;
char jsonString[15360];

void setup() {
  Serial.begin(115200);
  delay(100);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  // Connect to MQTT broker
  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(15360);
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }

  // Initialize the MLX90640 sensor
  if (!mlx.begin(MLX90640_I2CADDR_DEFAULT, &Wire)) {
    Serial.println("MLX90640 not found!");
    while (1) delay(10);
  }

  // Set sensor mode, resolution, and refresh rate 
  mlx.setMode(MLX90640_CHESS);
  mlx.setResolution(MLX90640_ADC_18BIT);
  mlx.setRefreshRate(MLX90640_2_HZ);
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT reconnection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  // Read temperature data from the MLX90640 sensor
  if (mlx.getFrame(frame) != 0) {
    Serial.println("Failed to read MLX90640 frame");
    return;
  }

  // Create JSON payload
  doc.clear();
  JsonArray temperatures = doc.createNestedArray("temperatures");
  for (uint8_t h = 0; h < 24; h++) {
    JsonArray row = temperatures.createNestedArray();
    for (uint8_t w = 0; w < 32; w++) {
      float t = frame[h * 32 + w];  // removed the rounding
      row.add(t);
    }
  }
  
  JsonArray columnData = doc.createNestedArray("columns");
  for (uint8_t w = 0; w < 32; w++) {
    JsonArray column = columnData.createNestedArray();
    for (uint8_t h = 0; h < 24; h++) {
      float t = frame[h * 32 + w];  // removed the rounding
      column.add(t);
    }
  }

  serializeJson(doc, jsonString, sizeof(jsonString));

  while (!client.publish("temperatures", jsonString, 0)) {
    Serial.println("Failed to publish, retrying...");
    delay(5000); // Wait for 5 seconds before retrying
    if (!client.connected()) {
      // Attempt to reconnect to the MQTT server
      reconnectMQTT();
    }
  }
  
  Serial.println("Published successfully");
  delay(500);

}
