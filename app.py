import asyncio
import websockets
import json
import paho.mqtt.client as mqtt
from database.conn import connectToDatabase
from controllers.statisticsController import insertBpm, insertTemp, getBPMRecords, getTempRecords
from loguru import logger

# Lista de clientes WebSocket conectados
connected_clients = set()

# Función para manejar nuevos clientes WebSocket
async def ws_handler(websocket, path):
    # Añadir el nuevo cliente a la lista
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            logger.info(f"recieved message from a client: {message}")
            parsedData = json.loads(message)
            logger.info(f"parsed message: {parsedData}")
            if parsedData.get("event") == "getBPMRecords":
                records = await getBPMRecords(parsedData.get("tiempo"), parsedData)
                await websocket.send(json.dumps(records))
                continue
            if parsedData.get("event") == "getTempRecords":
                records  = await getTempRecords(parsedData.get("tiempo"), parsedData)
                await websocket.send(json.dumps(records))
                continue
            if parsedData.get("event") == "insertBPMRecords":
                response = await insertBpm(parsedData)
                await websocket.send(json.dumps(response))
                continue
            if parsedData.get("event") == "insertTempRecords":
                response = await insertTemp(parsedData)
                await websocket.send(json.dumps(response))
                continue
            pass
    finally:
        # Eliminar el cliente cuando se desconecta
        connected_clients.remove(websocket)

# Función para enviar mensaje a todos los clientes WebSocket conectados
async def broadcast_message(message):
    if connected_clients:  # Solo si hay clientes conectados
        await asyncio.wait([client.send(message) for client in connected_clients])

# Función para manejar mensajes recibidos por MQTT
def on_mqtt_message(client, userdata, msg):
    message_data = {
        "topic": msg.topic,
        "payload": msg.payload.decode()
    }
    message_json = json.dumps(message_data)
    # Usar asyncio.run para enviar mensajes en el loop principal
    asyncio.run(broadcast_message(message_json))

# Configurar el cliente MQTT
mqtt_client = mqtt.Client()
#mqtt_client.username_pw_set("polter", "123")
mqtt_client.on_message = on_mqtt_message

async def main():
    # Conectarse a la base de datos
    await connectToDatabase()
    print("Conectado a la base de datos.")

    # Conectar el cliente MQTT
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.subscribe("message/event")
    # Iniciar el cliente MQTT en un thread separado
    mqtt_client.loop_start()
    print("Cliente MQTT conectado.")

    # Iniciar el servidor WebSocket
    start_server = websockets.serve(ws_handler, "localhost", 8765)
    print("Servidor WebSocket iniciado en ws://localhost:8765.")

    # Ejecutar el servidor WebSocket
    await start_server
    # Mantener el programa corriendo
    await asyncio.Future()  # Espera indefinidamente

# Ejecutar el bucle principal
if __name__ == "__main__":
    asyncio.run(main())
