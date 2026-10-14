/*
  ESP32 node RAS (contoh) - 1 tangki
  Library: PubSubClient, OneWire, DallasTemperature
  Publish tiap 10 detik:  farm1/tank3/temp  {"v":27.8}
                          farm1/tank3/do    {"v":6.1}
  FAIL-SAFE LOKAL: jika DO < DO_CRITICAL, relay aerator cadangan ON walau WiFi/Odoo mati.
*/
#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

const char* WIFI_SSID = "SSID";
const char* WIFI_PASS = "PASSWORD";
const char* MQTT_HOST = "192.168.10.5";
const char* MQTT_USER = "esp_tank3";
const char* MQTT_PASS = "GANTI";
const char* TOPIC_BASE = "farm1/tank3";

const int PIN_DS18B20 = 4;
const int PIN_DO_ADC = 34;
const int PIN_RELAY_BACKUP = 26;   // aerator cadangan
const float DO_CRITICAL = 3.5;     // mg/L
const float DO_RECOVER  = 4.5;     // histeresis

OneWire oneWire(PIN_DS18B20);
DallasTemperature ds(&oneWire);
WiFiClient wifi;
PubSubClient mqtt(wifi);
bool backupOn = false;

// Kalibrasi 2 titik DO: ganti dengan hasil kalibrasi probe Anda
float readDO() {
  int raw = analogRead(PIN_DO_ADC);
  float volt = raw * 3.3f / 4095.0f;
  const float V_ZERO = 0.10f, V_SAT = 1.60f, DO_SAT = 8.0f;   // CONTOH
  float v = (volt - V_ZERO) / (V_SAT - V_ZERO) * DO_SAT;
  return v < 0 ? 0 : v;
}

void connectNet() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < 8000) delay(200);
  }
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) {
    mqtt.connect("esp_tank3", MQTT_USER, MQTT_PASS);
  }
}

void publishValue(const char* name, float v) {
  char topic[64], payload[32];
  snprintf(topic, sizeof(topic), "%s/%s", TOPIC_BASE, name);
  snprintf(payload, sizeof(payload), "{\"v\":%.2f}", v);
  mqtt.publish(topic, payload);
}

void setup() {
  pinMode(PIN_RELAY_BACKUP, OUTPUT);
  digitalWrite(PIN_RELAY_BACKUP, LOW);
  ds.begin();
  mqtt.setServer(MQTT_HOST, 1883);
}

void loop() {
  static unsigned long last = 0;
  float doVal = readDO();

  // ---- kontrol lokal (tidak bergantung jaringan) ----
  if (!backupOn && doVal < DO_CRITICAL) { backupOn = true;  digitalWrite(PIN_RELAY_BACKUP, HIGH); }
  if (backupOn  && doVal > DO_RECOVER)  { backupOn = false; digitalWrite(PIN_RELAY_BACKUP, LOW);  }

  if (millis() - last > 10000) {
    last = millis();
    connectNet();
    ds.requestTemperatures();
    float t = ds.getTempCByIndex(0);
    if (mqtt.connected()) {
      if (t > -50) publishValue("temp", t);
      publishValue("do", doVal);
      publishValue("aerator_backup", backupOn ? 1 : 0);
    }
  }
  mqtt.loop();
  delay(100);
}
