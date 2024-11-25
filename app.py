import asyncio
import websockets
import json
import paho.mqtt.client as mqtt
from database.conn import connectToDatabase
from controllers.statisticsController import (
    insertBpm,
    insertTemp,
    getBPMRecords,
    getTempRecords
)
from loguru import logger
from dotenv import load_dotenv
import os
from typing import Set
from queue import Queue
from threading import Lock

load_dotenv()

class WebSocketMQTTBridge:
    def __init__(self):
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.mqtt_client = self._setup_mqtt_client()
        self.message_queue = Queue()
        self.event_loop = None
        self.lock = Lock()
        
    def _setup_mqtt_client(self) -> mqtt.Client:
        """Configura y retorna un cliente MQTT."""
        client = mqtt.Client()
        client.on_message = self._on_mqtt_message
        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect
        
        mqtt_username = os.getenv("MQTT_USERNAME", "polter")
        mqtt_password = os.getenv("MQTT_PASSWORD", "123")
        client.username_pw_set(mqtt_username, mqtt_password)
        
        return client
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback cuando el cliente MQTT se conecta."""
        if rc == 0:
            logger.info("Conectado al broker MQTT")
            client.subscribe("message/event")
            client.subscribe("sensor/distancia")
            client.subscribe("sensor/bpm")
            client.subscribe("sensor/temperatura")
            client.subscribe("sensor/toque")
        else:
            logger.error(f"Error de conexión MQTT con código: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback cuando el cliente MQTT se desconecta."""
        logger.warning("Desconectado del broker MQTT")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Callback para manejar mensajes MQTT recibidos."""
        try:
            message_data = {
                "topic": msg.topic,
                "parsedData": json.loads(msg.payload.decode())
            }
            message_json = json.dumps(message_data)
            
            # Agregar el mensaje a la cola
            self.message_queue.put(message_json)
            
            # Notificar al event loop que hay un nuevo mensaje
            with self.lock:
                if self.event_loop is not None:
                    self.event_loop.call_soon_threadsafe(self._process_message_queue)
                    
        except Exception as e:
            logger.error(f"Error en callback MQTT: {e}")

    def _process_message_queue(self):
        """Procesa los mensajes en la cola."""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                asyncio.create_task(self._broadcast_message(message))
        except Exception as e:
            logger.error(f"Error procesando cola de mensajes: {e}")

    async def _broadcast_message(self, message: str):
        """Envía un mensaje a todos los clientes WebSocket conectados."""
        if not self.connected_clients:
            return
            
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error enviando mensaje a cliente: {e}")
                disconnected_clients.add(client)
                
        # Eliminar clientes desconectados
        self.connected_clients -= disconnected_clients

    async def handle_websocket(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Maneja las conexiones WebSocket entrantes."""
        self.connected_clients.add(websocket)
        logger.info("Nuevo cliente WebSocket conectado")
        
        try:
            async for message in websocket:
                await self._process_websocket_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Cliente WebSocket desconectado")
        except Exception as e:
            logger.error(f"Error en manejo de WebSocket: {e}")
        finally:
            self.connected_clients.remove(websocket)

    async def _process_websocket_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """Procesa los mensajes recibidos por WebSocket."""
        try:
            parsed_data = json.loads(message)
            logger.info(f"Mensaje recibido: {parsed_data}")
            
            event_handlers = {
                "getBPMRecords": lambda: getBPMRecords(parsed_data.get("tiempo"), parsed_data),
                "getTempRecords": lambda: getTempRecords(parsed_data.get("tiempo"), parsed_data),
                "insertBPMRecords": lambda: insertBpm(parsed_data),
                "insertTempRecords": lambda: insertTemp(parsed_data)
            }
            
            event = parsed_data.get("event")
            if event in event_handlers:
                response = await event_handlers[event]()
                logger.info("mensaje enviado.\n" + str(response))
                await websocket.send(json.dumps(response))
            else:
                logger.warning(f"Evento desconocido: {event}")
                
        except json.JSONDecodeError:
            logger.error("Error decodificando JSON")
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")

    async def start(self):
        """Inicia el servicio WebSocket-MQTT."""
        try:
            # Guardar referencia al event loop
            self.event_loop = asyncio.get_running_loop()
            
            # Conectar a la base de datos
            await connectToDatabase()
            logger.info("Conectado a la base de datos")
            
            # Conectar cliente MQTT
            self.mqtt_client.connect(
                host=os.getenv("MQTT_BROKER", "localhost"),
                port=int(os.getenv("MQTT_PORT", 1883)),
                keepalive=60
            )
            self.mqtt_client.loop_start()
            
            # Iniciar servidor WebSocket
            ws_host = os.getenv("WEBSOCKET_HOST", "localhost")
            ws_port = int(os.getenv("WEBSOCKET_PORT", 8765))
            
            async with websockets.serve(self.handle_websocket, ws_host, ws_port):
                logger.info(f"Servidor WebSocket iniciado en ws://{ws_host}:{ws_port}")
                await asyncio.Future()  # Mantener el servicio ejecutándose
                
        except Exception as e:
            logger.error(f"Error iniciando el servicio: {e}")
            raise
        
    async def stop(self):
        """Detiene el servicio."""
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
            # Cerrar todas las conexiones WebSocket
            for client in self.connected_clients:
                await client.close()
            self.connected_clients.clear()
            
        except Exception as e:
            logger.error(f"Error deteniendo el servicio: {e}")

async def main():
    """Función principal para iniciar el servicio."""
    bridge = WebSocketMQTTBridge()
    try:
        await bridge.start()
    except KeyboardInterrupt:
        await bridge.stop()
    except Exception as e:
        logger.error(f"Error en main: {e}")
        await bridge.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servicio detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")