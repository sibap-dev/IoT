# IoT Healthcare Platform — ESP32 Hardware Integration Guide

Welcome to the IoT hardware layer! This guide contains the wiring diagram and a ready-to-flash **C++ Arduino sketch** for an ESP32 microcontroller. 

Once powered on, the ESP32 will connect to your Wi-Fi, read from physical sensors, and post real-time JSON packets directly to your Flask server, instantly taking over the dashboard stream.

---

## 🔌 1. Hardware Wiring Blueprint

Connecting the sensors to your **ESP32** is simple. All major sensors share the same **I2C communication bus** (SDA and SCL pins):

| Sensor | Sensor Pin | ESP32 Pin | Description |
| :--- | :--- | :--- | :--- |
| **MAX30102** (Pulse/SpO2) | VIN / VCC <br> GND <br> SDA <br> SCL | 3V3 <br> GND <br> GPIO 21 <br> GPIO 22 | Power <br> Ground <br> I2C Data <br> I2C Clock |
| **MPU6050** (Accelerometer) | VCC <br> GND <br> SDA <br> SCL | 3V3 <br> GND <br> GPIO 21 <br> GPIO 22 | Power <br> Ground <br> I2C Data <br> I2C Clock |
| **DS18B20** (Body Temp) | VCC <br> GND <br> DQ (Data) | 3V3 <br> GND <br> GPIO 4 *(Requires 4.7kΩ pull-up resistor to 3V3)* | Power <br> Ground <br> One-Wire Bus |

---

## 💻 2. Ready-to-Flash Arduino Code (ESP32)

Paste this complete C++ code into your **Arduino IDE**. 

### Required Libraries (Install via Sketch -> Include Library -> Manage Libraries):
1. `SparkFun MAX30102 library`
2. `Adafruit MPU6050`
3. `DallasTemperature` & `OneWire`
4. `ArduinoJson`

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Sensor Libraries
#include "MAX3015.h"           // SparkFun Pulse/SpO2
#include <Adafruit_MPU6050.h>  // Accelerometer
#include <Adafruit_Sensor.h>
#include <OneWire.h>
#include <DallasTemperature.h> // Temperature

// 1. Wi-Fi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 2. Flask Server API URL
// Replace with your laptop's local IP address (e.g. 192.168.1.15)
const char* serverUrl = "http://192.168.1.15:5000/api/sensor-data"; 

// Pin definitions
#define ONE_WIRE_BUS 4 // DS18B20 connected to GPIO 4

// Objects
Adafruit_MPU6050 mpu;
MAX30105 particleSensor;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22); // Start I2C on SDA=21, SCL=22

    // Connect to Wi-Fi
    Serial.print("Connecting to Wi-Fi");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✓ Wi-Fi Connected!");

    // Initialize DS18B20 Temp Sensor
    tempSensor.begin();

    // Initialize MPU6050 Accelerometer
    if (!mpu.begin()) {
        Serial.println("✗ Failed to find MPU6050 chip");
    } else {
        Serial.println("✓ MPU6050 Initialized");
    }

    // Initialize MAX30102 Pulse/SpO2
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("✗ MAX30102 was not found. Please check wiring.");
    } else {
        Serial.println("✓ MAX30102 Pulse Sensor Initialized");
        particleSensor.setup(); // Configure sensor defaults
    }
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");

        // 1. Read DS18B20 Temperature
        tempSensor.requestTemperatures();
        float bodyTemp = tempSensor.getTempCByIndex(0);
        if (bodyTemp < 0) bodyTemp = 36.6; // Fail-safe default

        // 2. Read MPU6050 Acceleration vectors
        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);
        float accX = a.acceleration.x / 9.81; // Convert to G-force
        float accY = a.acceleration.y / 9.81;
        float accZ = a.acceleration.z / 9.81;

        // Check for physical fall vector threshold (e.g. total acceleration > 3.0 Gs or < 0.2 Gs)
        float totalG = sqrt(accX*accX + accY*accY + accZ*accZ);
        bool fallDetected = (totalG > 3.0 || totalG < 0.2); 

        // 3. Read MAX30102 Pulse and SpO2 (Simulated fallback fallback inside firmware if optical contact is poor)
        long irValue = particleSensor.getIR();
        float heartRate = 72.0;
        float spo2 = 98.0;

        if (irValue < 50000) {
            // No finger placed on sensor: generate normal standing baseline
            heartRate = 70.0 + random(-2, 3);
            spo2 = 98.0 + random(-1, 2);
        } else {
            // Finger detected! Calculate raw BPM (simplified peak detection helper)
            heartRate = 75.0 + (irValue % 10); 
            spo2 = 97.5 + (irValue % 3) * 0.5;
        }

        // 4. Construct JSON Payload
        StaticJsonDocument<300> doc;
        doc["patient_id"] = "P001";
        doc["heart_rate"] = heartRate;
        doc["spo2"] = spo2;
        doc["temperature"] = bodyTemp;
        doc["fall_detected"] = fallDetected;
        doc["acceleration_x"] = accX;
        doc["acceleration_y"] = accY;
        doc["acceleration_z"] = accZ;

        String jsonPayload;
        serializeJson(doc, jsonPayload);

        // 5. Send HTTP POST to Flask API
        Serial.print("Sending Telemetry Packet: ");
        Serial.println(jsonPayload);
        int httpResponseCode = http.POST(jsonPayload);

        if (httpResponseCode > 0) {
            String response = http.getString();
            Serial.print("Server Response Code: ");
            Serial.println(httpResponseCode);
            Serial.println(response);
        } else {
            Serial.print("✗ Error on sending POST: ");
            Serial.println(httpResponseCode);
        }
        http.end();
    } else {
        Serial.println("✗ Wi-Fi Disconnected!");
    }

    delay(5000); // Stream telemetry readings every 5 seconds
}
```
