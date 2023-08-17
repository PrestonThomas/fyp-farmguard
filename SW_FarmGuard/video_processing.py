import threading
import cv2
import queue
import numpy as np
import asyncio

from edgetpumodel import EdgeTPUModel
from utils import resize_and_pad, get_image_tensor, save_one_json, coco80_to_coco91_class
from config import Config
import datetime
import time
from ping3 import ping


frame_queue = queue.Queue(maxsize=10)
interpreter_lock = threading.Lock()

model_file = "yolov5s-int8-224_edgetpu.tflite"
names = "coco.yaml"

conf_thresh = 0.25
iou_thresh = 0.45
classes = None
agnostic_nms = False
max_det = 1000

model = EdgeTPUModel(model_file, names, conf_thresh)
input_size = model.get_image_size()

x = (255*np.random.random((3,*input_size))).astype(np.uint8)
model.forward(x)

first_frame = None
motion_detected = False
latest_processed_frame = None
latest_processed_frame_lock = threading.Lock()
streaming_to_user = False

def check_camera_status(ip_address):
    response_time = ping(ip_address)
    if response_time is not None:
        return f"Camera at {ip_address} is online (Response Time: {response_time} ms)"
    else:
        return f"Camera at {ip_address} is offline"

class Camera:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.frame_queue = queue.Queue(maxsize=10)
        self.capture_thread = threading.Thread(target=self.capture_rtsp_stream, daemon=True)
        self.process_thread = threading.Thread(target=self.process_frames, daemon=True)
        self.motion_detected = False
        self.latest_processed_frame = None
        self.latest_processed_frame_lock = threading.Lock()
        self.first_frame = None
        self.last_status_check = 0
        self.status_check_interval = 300  # Check camera status every 300 seconds
        self.mqttClient = Config.mqtt_client
        self.stop_event = threading.Event()
        
        if ip_address not in Config.latest_processed_frames_locks:
            Config.latest_processed_frames_locks[ip_address] = threading.Lock()
        self.latest_processed_frame_lock = Config.latest_processed_frames_locks[ip_address]


    def start(self):
        self.capture_thread.start()
        self.process_thread.start()
        
    def stop(self):
        self.stop_event.set()
        
    def is_alive(self):
        return self.capture_thread.is_alive() or self.process_thread.is_alive()

    def capture_rtsp_stream(self):
        # global first_frame, motion_detected

        while True:
            while not self.stop_event.is_set():
                cam = None  # Define the cam object outside the try block
                try:
                    print(f"Connecting to camera at {self.ip_address}...")
                    Config.socketio.emit('device_status', 'Connecting to camera at {self.ip_address}...')
                    cam = cv2.VideoCapture(f'rtsp://{self.ip_address}:8554/mjpeg/1')
                    if not cam.isOpened():
                        raise Exception("Failed to open camera")
                    print(f"Camera ({self.ip_address}) Connected!")
                    Config.socketio.emit('device_status', f"Camera ({self.ip_address}) Connected!")
                    while True:
                        res, image = cam.read()
                        current_time = time.time()
                        if current_time - self.last_status_check > self.status_check_interval:
                            self.last_status_check = current_time
                            camera_status = check_camera_status(self.ip_address)
                            # print(camera_status)
                            Config.camera_statuses[self.ip_address] = camera_status
                        if not res:
                            logger.error("Failed to read frame")
                            continue
                        with self.latest_processed_frame_lock:
                            ret, jpeg = cv2.imencode('.jpg', image)
                            if ret:
                                self.latest_processed_frame = jpeg.tobytes()
                                Config.latest_processed_frames[self.ip_address] = self.latest_processed_frame

                        # Motion detection
                        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        gray = cv2.GaussianBlur(gray, (21, 21), 0)

                        if self.first_frame is None:
                            self.first_frame = gray
                            continue

                        frame_delta = cv2.absdiff(self.first_frame, gray)
                        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                        thresh = cv2.dilate(thresh, None, iterations=2)
                        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        motion_detected = False
                        for contour in cnts:
                            if cv2.contourArea(contour) > 500:  
                                motion_detected = True
                                break  

                        if motion_detected or Config.streaming_to_user:
                            if not self.frame_queue.full():
                                self.frame_queue.put(image)
                
                except Exception as e:
                    print(f"Failed to connect to camera at {self.ip_address}. Retrying in 30 seconds...")
                    time.sleep(30)
                    
                finally:
                    if cam is not None:
                        cam.release()  # Release the camera capture
                    print(f"Connection to camera at {self.ip_address} lost. Retrying in 30 seconds...")
                    time.sleep(30)



    def process_frames(self):
    # global latest_processed_frame
        while True:
            if not self.frame_queue.empty():
                image = self.frame_queue.get()
                full_image, net_image, pad = get_image_tensor(image, input_size[0])
                with interpreter_lock:
                    pred = model.forward(net_image)
                
                det, detected_info, file_name = model.process_predictions(pred[0], full_image, pad, camera_name=self.ip_address)
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if detected_info:
                    print(f"At {current_time}, Camera {self.ip_address} detected: {detected_info}")
                    
                    detected_entity = detected_info.split(' ')[-1]
                    print(detected_entity)
                    
                    if detected_entity == 'person':
                        topic = 'intrusion_human'
                    elif detected_entity in ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']:
                        topic = 'intrusion_animal'
                    else:
                        continue
                    
                    image_date = current_time.split(' ')[0]  
                    image_path = f'static/detection_images/{image_date}/{file_name}'

                    onclick_attribute = f"showModal('{image_path}')"

                    web_message = f'Camera {self.ip_address} detected: {detected_info} <a href="javascript:void(0);" onclick="{onclick_attribute}">View snapshot</a>'

                    detection_message = f"At {current_time}, Camera {self.ip_address} detected: {detected_info}"
                    message = detection_message.encode('utf-8')

                    Config.socketio.emit(topic, web_message)
                    asyncio.run(Config.mqtt_client.publish(topic, message))
                    
                    # with Config.mqtt_client_lock:
                    #     # Config.mqtt_client.publish(topic, message)
                    #     # self.event_loop.create_task(publish_mqtt_async(topic, message))
                    #     self.mqttClient.publish(topic, message)

                
                ret, jpeg = cv2.imencode('.jpg', full_image)
                if not ret:
                    logger.error("Failed to encode image")
                    continue

                Config.latest_processed_frame = jpeg.tobytes()
                
                with self.latest_processed_frame_lock:
                    Config.latest_processed_frames[self.ip_address] = jpeg.tobytes()

    def serve_latest_frame(self):
        while True:
            with self.latest_processed_frame_lock:
                if self.latest_processed_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.latest_processed_frame + b'\r\n\r\n')
            time.sleep(0.1)

