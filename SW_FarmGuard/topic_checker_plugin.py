import json
from flask_socketio import emit
from config import Config
import datetime
import time  

class TopicEventPlugin:
    def __init__(self, context):
        self.context = context
        self.socketio = Config.socketio
        self.mqttClient = Config.mqtt_client
        self.sent_messages = {}  
        print("TopicEventPlugin initialized!")
        
    async def on_broker_client_connected(self, *args, **kwargs):
        client_id = kwargs.get('client_id')
        print(client_id + " connected to broker!")
        self.socketio.emit('device_status', client_id + " connected to broker!")
        
    async def on_broker_client_disconnected(self, *args, **kwargs):
        client_id = kwargs.get('client_id')
        print(client_id + " disconnected from broker!")

    async def on_broker_message_received(self, *args, **kwargs):
        # print("on_broker_message_received triggered!")
        client_id = kwargs.get('client_id')
        message = kwargs.get('message')
        # print(dir(message))
        
        if not message:
            print("No message received!")
            return

        topic = message.topic
        payload = message.data.decode()
        
        if topic == 'health_check':
            print(f"Health check from client {client_id}")
            
        if topic == 'temperatures':
            try:
                jsonData = json.loads(payload)
                if 'temperatures' in jsonData and isinstance(jsonData['temperatures'], list):
                    temperatures = jsonData['temperatures']
                    for row_idx, row in enumerate(temperatures):
                        for col_idx, temp in enumerate(row):
                            if temp is None:
                                # Calculate the average of adjacent non-null values
                                adjacent_values = []
                                if col_idx > 0 and temperatures[row_idx][col_idx - 1] is not None:
                                    adjacent_values.append(temperatures[row_idx][col_idx - 1])
                                if col_idx < len(row) - 1 and temperatures[row_idx][col_idx + 1] is not None:
                                    adjacent_values.append(temperatures[row_idx][col_idx + 1])
                                
                                if adjacent_values:
                                    average_temp = sum(adjacent_values) / len(adjacent_values)
                                    temperatures[row_idx][col_idx] = average_temp
                    message_with_timestamp = json.dumps({
                        'temperatures': temperatures,
                        'timestamp': time.time() 
                    })
                    # Check if the message was sent recently
                    if message_with_timestamp not in self.sent_messages or time.time() - self.sent_messages[message_with_timestamp] > 5:
                        # Store the timestamp of the sent message
                        self.sent_messages[message_with_timestamp] = time.time()
                        # print('___________________________')
                        # print(temperatures)
                        # print('___________________________')
                        # print('Received')
                        self.socketio.emit('temperature', temperatures)
                        # Check for high temperature
                        if any(temp > 50 for sublist in temperatures for temp in sublist if temp is not None):
                            print("High temperature detected!")
                            await self.publish_alarm()
                    else:
                        print("Message already sent recently, skipping.")
                else:
                    print('Invalid JSON format.')
            except json.JSONDecodeError:
                print('Error parsing JSON.')
                
        if topic == 'alarm':
            print('Received alarm')
            print("Topic:" + topic + "\nPayload:" + payload)

    async def publish_alarm(self):
        if self.mqttClient is None:
            raise Exception("MQTT client not initialized!")

        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"High Temperature Detected at {current_time}!"
        
        # print(f"Publishing: {message}")
        web_message = "High Temperature Detected!"
        self.socketio.emit('temperature_alarm', web_message)
        await self.mqttClient.publish('temperature_alarm', message.encode())
