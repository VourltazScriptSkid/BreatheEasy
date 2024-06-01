#include <WiFiNINA.h>
#include <PubSubClient.h>

// WiFi Name and Key
const char* ssid = "Wifi";
const char* password = "Key for Wifi";

// Address for MQTT Broker
const char* mqtt_server = "10.0.0.89";

// MQ135 sensor pin
const int MQ135_PIN = A0;

// Creates WiFi and MQTT client instances
WiFiClient espClient;
PubSubClient client(espClient);

// Main Block
void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Connect to WiFi
  setup_wifi();

  // Set MQTT server
  client.setServer(mqtt_server, 1883);

  // Connect to MQTT broker
  reconnect();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Reads the sensor value
  int sensorValue = analogRead(MQ135_PIN);

  // Converts the sensor value to string
  char sensorValueStr[8];
  itoa(sensorValue, sensorValueStr, 10);

  // Publishes the sensor value to the MQTT topic
  client.publish("air_quality/mq135", sensorValueStr);

  // Waits before the next reading 
  delay(1000);
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ArduinoNano33IoT")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}
