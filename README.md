# SOLIN — Coleira/Tapete Inteligente para Pets (Projeto IoT)

## Integrantes do grupo

| Nome | RM |
|---|---|
| Rodrigo Silva | 565162 |
| Nickolas Davi | 564105 |
| Samara Vilela | 566133 |
| Natália Cristina | 564099 |
| Otávio Ferreira | 565960 |

---

Sistema IoT que detecta quando o pet faz xixi (no tapete ou coleira) usando um
sensor de umidade, aciona avisos locais (LED + buzzer) e envia os eventos pela
internet via MQTT para um **dashboard web em tempo real**.

## Arquitetura

```
  ESP32 + sensor de umidade        Broker MQTT              Dashboard (Python)
  (firmware em C++/Arduino)   -->  broker.hivemq.com  -->   Flask + página web
       detecta o xixi              (intermediário)          mostra os dados
       acende LED / buzzer                                  em tempo real
       publica via MQTT
```

- **Sensor → ESP32 (C++):** detecta a umidade. Acima de um limite = xixi detectado.
- **MQTT:** protocolo leve de mensagens. O ESP32 *publica* eventos; o dashboard *assina* e recebe.
- **Dashboard (Python):** recebe os eventos e exibe contadores, alertas e histórico.

## Frameworks e ferramentas usados

| Ferramenta | Onde | Para quê |
|---|---|---|
| **Arduino / ESP32** | Firmware (C++) | Roda no microcontrolador, lê o sensor |
| **PubSubClient** | Firmware | Cliente MQTT no ESP32 |
| **ArduinoJson** | Firmware | Monta as mensagens em formato JSON |
| **MQTT (HiveMQ)** | Comunicação | Transporte dos eventos pela rede |
| **paho-mqtt** | Dashboard (Python) | Recebe as mensagens MQTT |
| **Flask** | Dashboard (Python) | Servidor web que entrega a página |
| **Wokwi** | Simulação | Simula o circuito sem hardware físico |

## Tópicos MQTT

| Tópico | Conteúdo |
|---|---|
| `solin/pet/coleira/uso` | Eventos de uso (xixi detectado, online, etc.) |
| `solin/pet/coleira/alerta` | Alertas (excesso de umidade, muito tempo sem uso) |

Cada mensagem é um JSON, por exemplo:

```json
{
  "produto": "SOLIN",
  "tipo": "uso_normal",
  "mensagem": "Urina detectada pelo sensor",
  "alerta": false,
  "umidade_raw": 2400,
  "contagem_dia": 1
}
```

## Como rodar o dashboard

Pré-requisito: ter o **Python** instalado (https://python.org — na instalação,
marque a caixa "Add Python to PATH").

1. Abra o terminal (Prompt de Comando no Windows) dentro da pasta do projeto.
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Rode o dashboard:
   ```
   python dashboard.py
   ```
4. Abra no navegador: **http://localhost:5000**

Enquanto isso, inicie a simulação no Wokwi. Ao mexer no sensor de umidade,
os eventos vão aparecendo no dashboard automaticamente.

link repositório: https://github.com/Rcsilva05/solin-iot

## Estrutura do projeto

```
solin-dashboard/
├── dashboard.py          # servidor Python (MQTT + web)
├── requirements.txt      # dependências
├── templates/
│   └── index.html        # página do dashboard
├── sketch.ino            # firmware do ESP32 (C++) — feito no Wokwi
└── README.md             # este arquivo
```

## Justificativa técnica: por que sensor de umidade?

A detecção é feita por **umidade**, não por temperatura. A urina esfria muito
rápido ao contato com o tapete e a diferença de temperatura desaparece em
segundos, o que tornaria a detecção por temperatura pouco confiável. A umidade
permanece detectável por mais tempo, sendo a escolha de engenharia mais robusta
para este caso.
