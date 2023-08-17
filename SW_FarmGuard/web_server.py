from flask import Flask, render_template, request, redirect, url_for, Response
from threading import Thread
from config import Config
from flask_socketio import SocketIO, emit
from config import set_socketio
import datetime
import time
from flask_cors import CORS
import os
import psutil
import subprocess


app = Flask(__name__)
CORS(app)
app.config['MIME_TYPES'] = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
}

camera_streams = {}  
def get_system_stats():
    cpu_usage = psutil.cpu_percent()
    
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    try:
        temp = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True)
        cpu_temp = temp.stdout.decode('utf-8').split('=')[1].split('\'')[0]
    except:
        cpu_temp = 'N/A'
    
    return {
        'cpu_usage': cpu_usage,
        'ram_usage': ram_usage,
        'cpu_temp': cpu_temp
    }
    
def serve_latest_frame(camera_name):
    while True:
        with Config.latest_processed_frames_lock:
            if camera_name in Config.latest_processed_frames:
                frame = Config.latest_processed_frames[camera_name]
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            time.sleep(0.1)
            
@app.context_processor
def inject_system_stats():
    stats = get_system_stats()
    return stats

@app.route('/api/system_stats', methods=['GET'])
def api_system_stats():
    stats = get_system_stats()
    return render_template('system_stats.html', **stats)

@app.route('/video_feed/<camera_name>')
def video_feed(camera_name):
    if camera_name in Config.latest_processed_frames:
        print(f"Serving video feed for camera {camera_name} at {datetime.datetime.now()}")
        return Response(serve_latest_frame(camera_name),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        print(f"Camera stream not available for {camera_name} at {datetime.datetime.now()}. Available cameras: {list(Config.latest_processed_frames.keys())}")
        return "Camera stream not available."
    
@app.route('/video_viewer/<camera_name>')
def video_viewer(camera_name):
    return render_template('video_viewer.html', camera_name=camera_name)
    
@app.route('/available_cameras')
def available_cameras():
    cameras = list(Config.latest_processed_frames.keys())
    return {"available_cameras": cameras}

@app.route('/camera_statuses')
def camera_statuses():
    return render_template('camera_statuses.html', camera_statuses=Config.camera_statuses)


@app.route('/temperature')
def temperature():
    return render_template('temperature.html', dt=datetime.datetime.now())

@app.route('/view_image/<date>/<camera_ip>/<entity_detected>/<time>')
def view_image(date, camera_ip, entity_detected, time):
    filename = f"{camera_ip}_{entity_detected}_{date} {time}.jpg"
    
    base_path = os.path.join(os.getcwd(), 'static', 'detection_images', date)
    image_path = os.path.join(base_path, filename)
    
    if os.path.exists(image_path):
        relative_path = os.path.join('detection_images', date, filename)
        return render_template('image_modal.html', image_path=url_for('static', filename=relative_path))
    else:
        return "Image not found."


@app.route('/gallery', methods=['GET'])
def gallery():
    base_path = os.path.join(os.getcwd(), 'static', 'detection_images')
    all_images = []
    camera_names = set()
    object_types = set()

    for date_dir in os.listdir(base_path):
        for image_file in os.listdir(os.path.join(base_path, date_dir)):
            if image_file.endswith(".jpg"):
                img_path = os.path.join('detection_images', date_dir, image_file)
                all_images.append(img_path)
                
                camera_name = image_file.split('_')[0]
                camera_names.add(camera_name)
                
                object_detected = image_file.split('_')[1]
                object_types.add(object_detected)
    
    sort_order = request.args.get('sort_order', 'desc')

    def get_datetime_from_filename(filename):
        date_str = filename.split('_')[-1].replace('.jpg', '')
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    all_images = sorted(all_images, key=get_datetime_from_filename, reverse=(sort_order == 'desc'))
    
    selected_object_type = request.args.get('object_type')
    if selected_object_type:
        all_images = [img for img in all_images if selected_object_type in img]

    selected_date = request.args.get('date', datetime.datetime.today().strftime('%Y-%m-%d'))
    all_images = [img for img in all_images if selected_date in img]

    selected_camera = request.args.get('camera')
    if selected_camera:
        all_images = [img for img in all_images if selected_camera in img]

    return render_template('gallery.html', images=all_images, cameras=sorted(list(camera_names)), object_types=sorted(list(object_types)), selected_camera=selected_camera, selected_date=selected_date, selected_object_type=selected_object_type, sort_order=sort_order)



@app.route('/delete_images', methods=['POST'])
def delete_images():
    images_to_delete = request.form.getlist('images_to_delete')
    for image_path in images_to_delete:
        full_path = os.path.join(os.getcwd(), 'static', image_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    return redirect(url_for('gallery'))

@app.route('/delete_all_images', methods=['POST'])
def delete_all_images():
    base_path = os.path.join(os.getcwd(), 'static', 'detection_images')
    for date_dir in os.listdir(base_path):
        for image_file in os.listdir(os.path.join(base_path, date_dir)):
            if image_file.endswith(".jpg"):
                full_path = os.path.join(base_path, date_dir, image_file)
                os.remove(full_path)
    return redirect(url_for('gallery'))

@app.route('/')
def home():
    return render_template('index.html', dt=datetime.datetime.now(), camera_statuses=Config.camera_statuses)

