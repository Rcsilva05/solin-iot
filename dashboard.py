"""
SOLIN - Dashboard do monitor de urina pet (coleira / tapete)
=============================================================

Este programa em Python faz a ponte entre o broker MQTT (onde o ESP32
publica os eventos da coleira) e um dashboard web que abre no navegador.

Arquitetura:

    ESP32 (C++)  --MQTT-->  broker.hivemq.com  --MQTT-->  ESTE SCRIPT (Python)
                                                                |
                                                                v
                                                    navegador (dashboard web)

Como funciona:
  1. Conecta no mesmo broker MQTT que o ESP32 usa (broker.hivemq.com).
  2. Assina os topicos onde a coleira publica os eventos.
  3. Cada mensagem recebida (JSON) e guardada em memoria.
  4. Um servidor web (Flask) entrega a pagina do dashboard e um endpoint
     /api/eventos que o navegador consulta a cada 2 segundos para atualizar
     os numeros e a lista de eventos em tempo real.

Para rodar:
    pip install flask paho-mqtt
    python dashboard.py
    Depois abra http://localhost:5000 no navegador.
"""

import json
import threading
from collections import deque
from datetime import datetime

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template

# ---------------------------------------------------------------------------
# Configuracao - precisa bater EXATAMENTE com o codigo do ESP32 (sketch.ino)
# ---------------------------------------------------------------------------
MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883
TOPICO_EVENTOS = "solin/pet/coleira/uso"
TOPICO_ALERTAS = "solin/pet/coleira/alerta"

# ---------------------------------------------------------------------------
# Estado compartilhado (preenchido pelo MQTT, lido pelo servidor web)
# Usamos um Lock porque o MQTT roda numa thread separada do Flask.
# ---------------------------------------------------------------------------
estado = {
    "online": False,
    "contagem_dia": 0,
    "ultima_umidade": 0,
    "ultimo_tipo": "-",
    "ultima_atualizacao": "-",
    "total_alertas": 0,
    "total_eventos": 0,
}
historico = deque(maxlen=50)  # guarda os ultimos 50 eventos
trava = threading.Lock()


# ---------------------------------------------------------------------------
# Callbacks do MQTT
# ---------------------------------------------------------------------------
def ao_conectar(client, userdata, flags, rc, properties=None):
    """Chamado quando a conexao com o broker e estabelecida."""
    if rc == 0:
        print("[DASHBOARD] Conectado ao broker MQTT.")
        client.subscribe(TOPICO_EVENTOS)
        client.subscribe(TOPICO_ALERTAS)
        print(f"[DASHBOARD] Assinando: {TOPICO_EVENTOS} e {TOPICO_ALERTAS}")
    else:
        print(f"[DASHBOARD] Falha ao conectar, codigo {rc}")


def ao_receber(client, userdata, msg):
    """Chamado toda vez que chega uma mensagem nos topicos assinados."""
    try:
        dados = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("[DASHBOARD] Mensagem ignorada (nao era JSON valido).")
        return

    agora = datetime.now().strftime("%H:%M:%S")
    eh_alerta = bool(dados.get("alerta", False))
    tipo = dados.get("tipo", "?")

    with trava:
        estado["online"] = True
        estado["ultima_umidade"] = dados.get("umidade_raw", estado["ultima_umidade"])
        estado["contagem_dia"] = dados.get("contagem_dia", estado["contagem_dia"])
        estado["ultimo_tipo"] = tipo
        estado["ultima_atualizacao"] = agora
        estado["total_eventos"] += 1
        if eh_alerta:
            estado["total_alertas"] += 1

        historico.appendleft({
            "hora": agora,
            "tipo": tipo,
            "mensagem": dados.get("mensagem", ""),
            "umidade": dados.get("umidade_raw", 0),
            "alerta": eh_alerta,
            "topico": msg.topic.split("/")[-1],  # "uso" ou "alerta"
        })

    marca = "ALERTA" if eh_alerta else "evento"
    print(f"[{agora}] {marca}: {tipo} (umidade={dados.get('umidade_raw', '?')})")


def iniciar_mqtt():
    """Sobe o cliente MQTT numa thread propria, em loop infinito."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = ao_conectar
    client.on_message = ao_receber
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
    except OSError as erro:
        print(f"[DASHBOARD] Nao consegui conectar ao broker: {erro}")
        return
    client.loop_forever()


# ---------------------------------------------------------------------------
# Servidor web (Flask)
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def pagina_inicial():
    return render_template("index.html")


@app.route("/api/eventos")
def api_eventos():
    """O navegador consulta este endpoint para atualizar o dashboard."""
    with trava:
        return jsonify({
            "estado": dict(estado),
            "historico": list(historico),
        })


if __name__ == "__main__":
    # Inicia o MQTT em segundo plano (daemon = morre junto com o programa).
    thread_mqtt = threading.Thread(target=iniciar_mqtt, daemon=True)
    thread_mqtt.start()

    print("=" * 55)
    print("  SOLIN - Dashboard pet")
    print("  Abra http://localhost:5000 no seu navegador")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=False)
