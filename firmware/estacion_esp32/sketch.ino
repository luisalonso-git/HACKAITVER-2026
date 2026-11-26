/*
  Kardex Vivo · Firmware de la estación de recepción (ESP32 + MPU6050 + HX711)

  Es el mismo detector de Hackaton/iot_hackaitver/iot/detector.py portado a C++, con los mismos umbrales.
  Lee el acelerómetro a 100 Hz, detecta presencia, golpe e inclinación, lee la báscula y publica cada
  evento con el JSON del contrato (Hackaton/CONTRATO.md, sección 1).

  Envío:
    USAR_MQTT 1 -> publica en un broker MQTT; firmware/puente_mqtt.py lo reenvía al backend (Wokwi gratis).
    USAR_MQTT 0 -> POST directo a BACKEND_URL (ESP32 real en la misma red que el backend).

  En Wokwi: clic en el MPU6050 para mover la aceleración (en g) y clic en el HX711 para poner el peso (kg).
*/
#include <limits.h>
#include <WiFi.h>
#include <Wire.h>
#include <PubSubClient.h>
#include <HTTPClient.h>

// ---------------- Configuración ----------------
#define USAR_MQTT 1
const char* WIFI_SSID = "Wokwi-GUEST";          // en el ESP32 real: la red del hotspot
const char* WIFI_PASS = "";
const char* ESTACION = "E1";
const char* ORIGEN = "simulado";                // "fisico" cuando corra en el ESP32 real
const char* DISPOSITIVO = "ESP32 Wokwi";        // se muestra en el frontend
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PUERTO = 1883;
const char* MQTT_TOPICO = "kardexvivo/hackaitver2026/eventos";   // igual que en puente_mqtt.py
const char* BACKEND_URL = "http://192.168.1.50:8000/api/evento"; // solo si USAR_MQTT es 0

// Pines
const int PIN_HX711_DT = 4;
const int PIN_HX711_SCK = 5;
const int PIN_LED = 2;
const uint8_t MPU_DIR = 0x68;

// ---------------- Parámetros del detector (iguales a detector.py) ----------------
const float UMBRAL_PRESENCIA_G = 0.4;
const float UMBRAL_GOLPE_G = 2.5;
const float PAUSA_MIN_S = 0.15;
const float VENTANA_PICO_S = 0.10;
const float UMBRAL_INCLINACION_DEG = 30.0;
const float HISTERESIS_DEG = 5.0;
const float TIEMPO_INCLINACION_S = 0.5;
const int   VENTANA_PROMEDIO = 10;
const int   FS = 100;                            // muestras por segundo

// Báscula: unidades crudas por kg (Wokwi, celda de 50 kg). Ajustar al calibrar la celda real.
const float FACTOR_CALIBRACION = 420.0;
const float PESO_MINIMO_KG = 0.2;                // por debajo, la báscula está vacía
const float TOLERANCIA_ESTABLE_KG = 0.05;
const int   LECTURAS_ESTABLES = 8;               // ~0.8 s sin cambios para reportar el peso

WiFiClient red;
PubSubClient mqtt(red);

// ---------------- Envío de eventos ----------------
void enviarEvento(const char* tipo, float magnitud) {
  char json[220];
  snprintf(json, sizeof(json),
           "{\"estacion\":\"%s\",\"tipo\":\"%s\",\"magnitud\":%.2f,\"ts\":\"\",\"origen\":\"%s\",\"dispositivo\":\"%s\"}",
           ESTACION, tipo, magnitud, ORIGEN, DISPOSITIVO);
  bool ok = false;
#if USAR_MQTT
  ok = mqtt.connected() && mqtt.publish(MQTT_TOPICO, json);
#else
  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");
  ok = http.POST(json) == 201;
  http.end();
#endif
  Serial.printf("[%s] %-11s %6.2f  %s\n", ok ? "ENVIADO" : "FALLO  ", tipo, magnitud, json);
  digitalWrite(PIN_LED, HIGH);
  delay(30);
  digitalWrite(PIN_LED, LOW);
}

// ---------------- MPU6050 (lectura directa por I2C, rango ±16 g) ----------------
void iniciarMPU() {
  Wire.begin(21, 22);
  Wire.beginTransmission(MPU_DIR); Wire.write(0x6B); Wire.write(0x00); Wire.endTransmission();  // despertar
  Wire.beginTransmission(MPU_DIR); Wire.write(0x1C); Wire.write(0x18); Wire.endTransmission();  // ±16 g
}

bool leerAceleracion(float& ax, float& ay, float& az) {
  Wire.beginTransmission(MPU_DIR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_DIR, 6) != 6) return false;
  int16_t x = (Wire.read() << 8) | Wire.read();
  int16_t y = (Wire.read() << 8) | Wire.read();
  int16_t z = (Wire.read() << 8) | Wire.read();
  const float LSB_POR_G = 2048.0;  // ±16 g
  ax = x / LSB_POR_G; ay = y / LSB_POR_G; az = z / LSB_POR_G;
  return true;
}

// ---------------- HX711 (lectura directa, ganancia 128) ----------------
long leerHX711() {
  unsigned long inicio = millis();
  while (digitalRead(PIN_HX711_DT) == HIGH) {
    if (millis() - inicio > 100) return LONG_MIN;
  }
  long valor = 0;
  for (int i = 0; i < 24; i++) {
    digitalWrite(PIN_HX711_SCK, HIGH); delayMicroseconds(1);
    valor = (valor << 1) | digitalRead(PIN_HX711_DT);
    digitalWrite(PIN_HX711_SCK, LOW); delayMicroseconds(1);
  }
  digitalWrite(PIN_HX711_SCK, HIGH); delayMicroseconds(1);
  digitalWrite(PIN_HX711_SCK, LOW); delayMicroseconds(1);
  if (valor & 0x800000) valor |= 0xFF000000;  // signo de 24 bits
  return valor;
}

long tara = 0;

// ---------------- Detector (máquina de estados de detector.py) ----------------
struct Detector {
  bool enPico = false, armado = true, inclActiva = false;
  float pico = 0, tPico = 0, libreDesde = 0;
  int nIncl = 0, nBuf = 0, iBuf = 0;
  float bx[VENTANA_PROMEDIO], by[VENTANA_PROMEDIO], bz[VENTANA_PROMEDIO];

  void procesar(float t, float ax, float ay, float az) {
    float mag = sqrt(ax * ax + ay * ay + az * az);
    float dyn = fabs(mag - 1.0);

    // Picos: presencia y golpe. "armado" exige volver al reposo antes del siguiente pico
    // (en Wokwi el valor se queda fijo mientras no lo muevas; en el sensor real el pico dura milisegundos).
    if (dyn < UMBRAL_PRESENCIA_G * 0.5) armado = true;
    if (enPico) {
      pico = max(pico, dyn);
      if (dyn < UMBRAL_PRESENCIA_G * 0.5 || (t - tPico) >= VENTANA_PICO_S) {
        enviarEvento("presencia", pico);
        if (pico >= UMBRAL_GOLPE_G) enviarEvento("golpe", pico);
        enPico = false; armado = false;
        libreDesde = t + PAUSA_MIN_S;
      }
    } else if (armado && dyn >= UMBRAL_PRESENCIA_G && t >= libreDesde) {
      enPico = true; pico = dyn; tPico = t;
    }

    // Inclinación: ángulo promedio respecto a la vertical
    bx[iBuf] = ax; by[iBuf] = ay; bz[iBuf] = az;
    iBuf = (iBuf + 1) % VENTANA_PROMEDIO;
    if (nBuf < VENTANA_PROMEDIO) nBuf++;
    float mx = 0, my = 0, mz = 0;
    for (int i = 0; i < nBuf; i++) { mx += bx[i]; my += by[i]; mz += bz[i]; }
    mx /= nBuf; my /= nBuf; mz /= nBuf;
    float ang = degrees(atan2(sqrt(mx * mx + my * my), mz));
    if (ang >= UMBRAL_INCLINACION_DEG) {
      nIncl++;
      if (!inclActiva && nIncl >= (int)(TIEMPO_INCLINACION_S * FS)) {
        enviarEvento("inclinacion", ang);
        inclActiva = true;
      }
    } else {
      nIncl = 0;
      if (ang < UMBRAL_INCLINACION_DEG - HISTERESIS_DEG) inclActiva = false;
    }
  }
} detector;

// ---------------- Báscula: reporta el peso una vez que se estabiliza ----------------
struct Bascula {
  float ultimo = 0, anterior = -1, reportado = 0;
  int estables = 0;

  void procesar(float kg) {
    if (fabs(kg - anterior) <= TOLERANCIA_ESTABLE_KG) estables++; else estables = 0;
    anterior = kg;
    if (kg < PESO_MINIMO_KG) { reportado = 0; return; }          // báscula vacía: se rearma
    if (estables >= LECTURAS_ESTABLES && fabs(kg - reportado) > TOLERANCIA_ESTABLE_KG * 4) {
      enviarEvento("peso", kg);
      reportado = kg;
    }
  }
} bascula;

// ---------------- Conexiones ----------------
void conectarWiFi() {
  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS, 6);
  while (WiFi.status() != WL_CONNECTED) { delay(250); Serial.print("."); }
  Serial.printf(" listo (%s)\n", WiFi.localIP().toString().c_str());
}

void conectarMQTT() {
#if USAR_MQTT
  while (!mqtt.connected()) {
    String id = "kardexvivo-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("Conectando a MQTT... ");
    if (mqtt.connect(id.c_str())) Serial.println("listo");
    else { Serial.printf("error %d, reintento\n", mqtt.state()); delay(1500); }
  }
#endif
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_HX711_SCK, OUTPUT);
  pinMode(PIN_HX711_DT, INPUT);
  iniciarMPU();
  delay(200);
  long suma = 0; int n = 0;                  // tara con la báscula vacía
  for (int i = 0; i < 10; i++) { long v = leerHX711(); if (v != LONG_MIN) { suma += v; n++; } delay(20); }
  tara = n ? suma / n : 0;
  conectarWiFi();
#if USAR_MQTT
  mqtt.setServer(MQTT_BROKER, MQTT_PUERTO);
#endif
  conectarMQTT();
  Serial.printf("Estación %s lista. Tópico: %s\n", ESTACION, MQTT_TOPICO);
}

unsigned long proximaMuestra = 0, proximoPeso = 0, proximoReporte = 0;
float ultimoKg = 0;

void loop() {
#if USAR_MQTT
  if (!mqtt.connected()) conectarMQTT();
  mqtt.loop();
#endif
  unsigned long ahora = millis();
  if (ahora >= proximaMuestra) {           // acelerómetro a 100 Hz
    proximaMuestra = ahora + 1000 / FS;
    float ax, ay, az;
    if (leerAceleracion(ax, ay, az)) detector.procesar(ahora / 1000.0, ax, ay, az);
  }
  if (ahora >= proximoPeso) {              // báscula a 10 Hz
    proximoPeso = ahora + 100;
    long crudo = leerHX711();
    if (crudo != LONG_MIN) {
      ultimoKg = (crudo - tara) / FACTOR_CALIBRACION;
      bascula.procesar(ultimoKg);
    }
  }
  if (ahora >= proximoReporte) {           // ayuda para calibrar: lo que mide la báscula
    proximoReporte = ahora + 3000;
    Serial.printf("Báscula: %.2f kg\n", ultimoKg);
  }
}
