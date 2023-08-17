from flask_socketio import SocketIO
import threading

class Config:
    socketio = None 
    mqtt_client = None
    latest_processed_frame = None
    latest_processed_frames = {}
    latest_processed_frame_lock = threading.Lock()
    streaming_to_user = False 
    latest_processed_frames_lock = threading.Lock()
    latest_processed_frames_locks = {}
    camera_statuses = {}
    mqtt_client_lock = threading.Lock()
def set_socketio(socketio):
    Config.socketio = socketio
