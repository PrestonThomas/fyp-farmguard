from gevent import monkey
monkey.patch_socket()
from flask_socketio import SocketIO
from config import set_socketio
from config import Config
from web_server import app
from mqtt_server import start_broker
from video_processing import Camera
import threading
import datetime
import time
from web_server import serve_latest_frame
import asyncio

loop = asyncio.get_event_loop()

socketio = SocketIO(app, async_mode='gevent', websocket=True)

if __name__ == "__main__":
    # Start the Flask web server
    print("Starting Flask server...")
    set_socketio(SocketIO(app, async_mode='gevent', websocket=True, threaded=True))
    socketio_thread = threading.Thread(target=socketio.run, kwargs={'app': app, 'host': '0.0.0.0', 'port': 5000,})
    socketio_thread.start()

    # Start the MQTT broker
    stop_mqtt = threading.Event()
    mqtt_thread = threading.Thread(target=start_broker, args=(stop_mqtt,))
    mqtt_thread.start()

    # Start capturing and processing video frames using Camera instances
    cameras = [
        Camera(ip_address='192.168.1.239'),
        Camera(ip_address='192.168.1.232') 
    ]

    camera_streams = {}

    for camera in cameras:
        camera.start()
        camera_streams[camera.ip_address] = serve_latest_frame(camera.ip_address)

    try:
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Application shutting down...")
        
        print("Stopping Flask server...")
        socketio_thread.join(timeout=5.0)
        
        # Signal the MQTT broker thread to stop
        print("Stopping MQTT broker...")
        stop_mqtt.set()
        
        # Signal all camera threads to stop
        print("Stopping camera threads...")
        for camera in cameras:
            camera.stop_event.set()
        
        # Wait for the MQTT broker thread to finish
        mqtt_thread.join(timeout=5.0)
        
        # Wait for all camera threads to finish
        for camera in cameras:
            while camera.is_alive():
                time.sleep(0.1)
        
        print("Application shutdown complete.")


