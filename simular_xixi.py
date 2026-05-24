"""
SIMULADOR DA COLEIRA - para testar/demonstrar o dashboard
==========================================================

Este script "finge" ser a coleira (o ESP32) e manda eventos de xixi
para o broker MQTT, exatamente como o aparelho real faria.

Serve para demonstrar o dashboard funcionando, caso seja dificil
mexer no sensor dentro do Wokwi.

Como rodar (com o dashboard.py JA rodando em outra janela):
    python simular_xixi.py

Voce vai ver os numeros subindo no dashboard (http://localhost:5000).
"""

import json
import time

import paho.mqtt.client as mqtt

# Precisa ser IGUAL ao do dashboard e do ESP32
MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883
TOPICO_EVENTOS = "solin/pet/coleira/uso"
TOPICO_ALERTAS = "solin/pet/coleira/alerta"


def enviar(client, topico, tipo, mensagem, alerta, umidade, contagem):
    """Monta o JSON igualzinho ao do ESP32 e publica no broker."""
    evento = {
        "produto": "SOLIN",
        "device_id": "simulador-pc",
        "tipo": tipo,
        "mensagem": mensagem,
        "alerta": alerta,
        "sensor": "umidade",
        "local": "coleira_tapete",
        "contagem_dia": contagem,
        "umidade_raw": umidade,
    }
    client.publish(topico, json.dumps(evento))
    marca = "ALERTA" if alerta else "evento"
    print(f"  -> {marca} enviado: {tipo} (umidade={umidade})")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    print("Conectando ao broker MQTT...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    time.sleep(2)
    print("Conectado! Comecando a simular xixis...\n")

    contagem = 0

    # 1) Primeiro xixi normal
    contagem += 1
    print("Xixi 1 (normal):")
    enviar(client, TOPICO_EVENTOS, "uso_normal",
           "Urina detectada pelo sensor de umidade", False, 2400, contagem)
    time.sleep(4)

    # 2) Segundo xixi normal
    contagem += 1
    print("\nXixi 2 (normal):")
    enviar(client, TOPICO_EVENTOS, "uso_normal",
           "Urina detectada pelo sensor de umidade", False, 2300, contagem)
    time.sleep(4)

    # 3) Um alerta de excesso
    contagem += 1
    print("\nXixi 3 (EXCESSO - alerta):")
    enviar(client, TOPICO_ALERTAS, "uso_excessivo",
           "Umidade excessiva detectada — observar pet", True, 3100, contagem)
    enviar(client, TOPICO_EVENTOS, "uso_excessivo",
           "Possivel urina em excesso ou tapete encharcado", True, 3100, contagem)
    time.sleep(4)

    print("\nPronto! Olhe o dashboard - os numeros devem ter subido.")
    print("Para enviar mais xixis, rode este script de novo.")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
