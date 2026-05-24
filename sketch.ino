#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const int PIN_UMIDADE = 1;
const int PIN_LED_OK = 2;
const int PIN_LED_ALERTA = 4;
const int PIN_BUZZER = 5;

const int LIMITE_URINA = 2200;
const int LIMITE_EXCESSO = 2800;
const int LIMITE_SECO = 1200;

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASS = "";

const char *MQTT_HOST = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;
const char *MQTT_TOPIC_EVENTOS = "solin/pet/coleira/uso";
const char *MQTT_TOPIC_ALERTAS = "solin/pet/coleira/alerta";
const char *DEVICE_ID = "meu-iot-coleira-s2";
const char *PRODUTO = "SOLIN";
const char *LOCAL_PADRAO = "coleira_tapete";

const unsigned long INTERVALO_LEITURA_MS = 500UL;
const unsigned long DEBOUNCE_EVENTO_MS = 8000UL;
const unsigned long TEMPO_SEM_EVENTO_MS = 90000UL;
const unsigned long COOLDOWN_ALERTA_MS = 45000UL;

WiFiClient net;
PubSubClient mqtt(net);

uint32_t contagemDia = 0;
unsigned long ultimoEventoMs = 0;
unsigned long ultimoDebounceMs = 0;
unsigned long ultimoAlertaMs = 0;
unsigned long ultimoCheckMs = 0;
bool alertaSemUsoEnviado = false;
bool estavaMolhado = false;

void wifiConnect() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("[SOLIN] WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println(" OK");
}

void mqttConnect() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  while (!mqtt.connected()) {
    if (mqtt.connect(DEVICE_ID)) {
      Serial.println("[SOLIN] MQTT OK");
      return;
    }
    delay(2000);
  }
}

void beepAlerta(int vezes) {
  for (int i = 0; i < vezes; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(80);
    digitalWrite(PIN_BUZZER, LOW);
    delay(80);
  }
}

bool publicar(const char *topico, const char *tipo, const char *msg,
              bool alerta, int umidade) {
  StaticJsonDocument<384> doc;
  doc["produto"] = PRODUTO;
  doc["device_id"] = DEVICE_ID;
  doc["tipo"] = tipo;
  doc["mensagem"] = msg;
  doc["alerta"] = alerta;
  doc["sensor"] = "umidade";
  doc["local"] = LOCAL_PADRAO;
  doc["contagem_dia"] = contagemDia;
  doc["umidade_raw"] = umidade;

  char buf[384];
  serializeJson(doc, buf);
  bool ok = mqtt.publish(topico, buf);
  Serial.println(buf);
  return ok;
}

void registrarUrina(int umidade, bool excesso) {
  unsigned long agora = millis();
  if (agora - ultimoDebounceMs < DEBOUNCE_EVENTO_MS) return;

  ultimoDebounceMs = agora;
  ultimoEventoMs = agora;
  contagemDia++;
  alertaSemUsoEnviado = false;

  if (excesso) {
    publicar(MQTT_TOPIC_ALERTAS, "uso_excessivo",
             "Umidade excessiva detectada — observar pet", true, umidade);
    publicar(MQTT_TOPIC_EVENTOS, "uso_excessivo",
             "Possivel urina em excesso ou tapete encharcado", true, umidade);
    digitalWrite(PIN_LED_ALERTA, HIGH);
    digitalWrite(PIN_LED_OK, LOW);
    beepAlerta(4);
  } else {
    publicar(MQTT_TOPIC_EVENTOS, "uso_normal",
             "Urina detectada pelo sensor de umidade (coleira/tapete)", false,
             umidade);
    digitalWrite(PIN_LED_OK, HIGH);
    digitalWrite(PIN_LED_ALERTA, LOW);
    beepAlerta(1);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("==========================================");
  Serial.println("  SOLIN - Coleira / tapete (umidade)");
  Serial.println("  Detecta urina -> LED + MQTT");
  Serial.println("==========================================");

  pinMode(PIN_LED_OK, OUTPUT);
  pinMode(PIN_LED_ALERTA, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED_OK, LOW);
  digitalWrite(PIN_LED_ALERTA, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  ultimoEventoMs = millis();

  wifiConnect();
  mqttConnect();
  publicar(MQTT_TOPIC_EVENTOS, "online",
           "Monitor de urina (umidade) online", false, 0);

  Serial.printf("[SOLIN] Limites: seco<%d urina>%d excesso>%d\n",
                LIMITE_SECO, LIMITE_URINA, LIMITE_EXCESSO);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) wifiConnect();
  if (!mqtt.connected()) mqttConnect();
  mqtt.loop();

  int umidade = analogRead(PIN_UMIDADE);
  unsigned long agora = millis();

  bool molhado = umidade > LIMITE_URINA;
  bool excesso = umidade > LIMITE_EXCESSO;
  bool seco = umidade < LIMITE_SECO;

  if (seco) {
    digitalWrite(PIN_LED_OK, HIGH);
    digitalWrite(PIN_LED_ALERTA, LOW);
  } else if (!molhado) {
    digitalWrite(PIN_LED_OK, LOW);
    digitalWrite(PIN_LED_ALERTA, LOW);
  }

  if (molhado && !estavaMolhado) {
    registrarUrina(umidade, excesso);
    Serial.printf("[SOLIN] Urina #%lu | ADC=%d\n", (unsigned long)contagemDia,
                  umidade);
  }
  estavaMolhado = molhado;

  if (agora - ultimoCheckMs >= 5000UL) {
    ultimoCheckMs = agora;
    if (ultimoEventoMs > 0 && agora - ultimoEventoMs >= TEMPO_SEM_EVENTO_MS) {
      if (!alertaSemUsoEnviado && agora - ultimoAlertaMs >= COOLDOWN_ALERTA_MS) {
        alertaSemUsoEnviado = true;
        ultimoAlertaMs = agora;
        publicar(MQTT_TOPIC_ALERTAS, "sem_uso",
                 "Nenhuma urina detectada no periodo — verificar rotina",
                 true, umidade);
        publicar(MQTT_TOPIC_EVENTOS, "sem_uso",
                 "Sem deteccao de urina — verificar rotina urinaria", true,
                 umidade);
        digitalWrite(PIN_LED_ALERTA, HIGH);
        beepAlerta(2);
        Serial.println("[SOLIN] ALERTA: sem uso no periodo");
      }
    }
  }

  static unsigned long ultimoLog = 0;
  if (agora - ultimoLog >= INTERVALO_LEITURA_MS) {
    ultimoLog = agora;
    Serial.printf("ADC=%d | %s\n", umidade,
                  molhado ? (excesso ? "EXCESSO" : "URINA") : "seco/normal");
  }

  delay(50);
}
