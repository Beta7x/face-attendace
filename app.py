import os
import cv2
import time
from flask_socketio import SocketIO
from flask import Flask, render_template, Response, request, flash
from core_service.facerecognition import Recognizer
from core_service.dl_core_main import TransferLearning

app = Flask(__name__)
app.config['SECRET_KEY'] = 'qwerty123'
socketio = SocketIO(app)

PATH = '/'.join(os.path.abspath(__file__).split('/')[0:-1])
DATASET_PATH = os.path.join(PATH, 'dataset')

recognizer = Recognizer(
    socketio=socketio,
    facerecognition_model = os.path.join(PATH, "core_service/bin/frozen_graph.pb"),
    labels_filename = os.path.join(PATH, "core_service/labels.csv"),
    facedetection_model = os.path.join(PATH, "core_service/bin/haarcascade_frontalface_default.xml"),
    use_mtcnn=False,
    camera_src=0
)

@app.route("/transfer_learning")
def transfer_learning():
    return render_template("transfer_learning.html")

@socketio.on('run')
def handle_message(message):
    if not tl.is_running :
        socketio.start_background_task(target=tl.run)
    else :
        socketio.emit("feedback", "Transfer Learning already running.")

@socketio.on('check')    
def handle_message(message):
    print("status", tl.is_running)
    socketio.emit("status", tl.is_running)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    class_name = request.args.get('class_name')
    # path_new_class = os.path.join(DATASET_PATH, class_name)
    path_new_class = os.path.join(os.path.join(PATH, "dataset"), class_name)
    
    # Create directory label if not exist
    if not os.path.exists(path_new_class):
        os.mkdir(path_new_class)
        
    # Save uploaded image
    filename = class_name + '%04d.jpg' % (len(os.listdir(path_new_class)) + 1)
    file = request.files['webcam']
    file.save(os.path.join(path_new_class, filename))
    
    # Resize image
    img = cv2.imread(os.path.join(path_new_class, filename))
    img = cv2.resize(img, (250, 250))
    cv2.imwrite(os.path.join(path_new_class, filename), img)
    
    tl.dim=len(os.listdir(os.path.join(PATH, "dataset")))

    return '', 200

@app.route('/video_feed')
def video_feed():
    return Response(recognizer.gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    camera = request.args.get("camera")
    
    if camera is not None and camera == 'off':
        recognizer.close()
        flash("Camera turn off!", "info")
    elif camera is not None and camera == 'on':
        recognizer.open()
        flash("Camera turn on!", "success")
    print("Camera status", recognizer.status())
    return render_template("index.html", is_camera = recognizer.status())

@app.route('/history')
def history():
    return render_template("history.html")

@app.route('/face_registration')
def face_registration():
    return render_template("face_registration.html")

# @socketio.on('server_event')
# def handle_message(message):
#     print('receive message: ', message)
#     time.sleep(1)
#     socketio.emit('client_event', "Hello from server :)")

if __name__ == '__main__':
    
    global tl 
    tl = TransferLearning(socketio,
                        event="feedback",
                        model_name=os.path.join(PATH, "core_service/bin/model-cnn-facerecognition.h5"), 
                        dim=len(os.listdir(os.path.join(PATH, "dataset"))), 
                        dataset=os.path.join(PATH, "dataset"), 
                        use_augmentation=False,
                        epoch=10)
    
    tl.init_model()

    socketio.run(app)
    
    # app.run(debug=True)
