import asyncio
from amqtt.broker import Broker
from config import Config
from topic_checker_plugin import TopicEventPlugin
from amqtt.client import MQTTClient
import time 
CONFIG = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': '0.0.0.0:1883',
        }
    },
    'topic-check': {
        'enabled': True,
        'plugins': [
            'topic_checker_plugin.TopicEventPlugin'
        ]
    },
}

def start_broker(stop_event):
    while not stop_event.is_set():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        global broker_event_loop
        global mqtt_client
        broker_event_loop = loop
        print("In broker loop, stop_event is_set: ", stop_event.is_set())
        time.sleep(1)
        Config.mqtt_client = MQTTClient(client_id="FarmGuard-Server")
        broker = Broker(config=CONFIG)

        try:
            loop.run_until_complete(broker.start())
            loop.run_until_complete(Config.mqtt_client.connect('mqtt://127.0.0.1:1883'))
            loop.run_forever()
        except KeyboardInterrupt:
            print("Gracefully shutting down... Please wait.")
            
            loop.run_until_complete(Config.mqtt_client.disconnect())
            
            shutdown_broker(loop, broker)
            
            if socketio.server:
                socketio.stop()
            
            print("Shutdown complete.")

if __name__ == "__main__":
    start_broker(stop_mqtt)
