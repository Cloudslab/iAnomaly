* preprocessor, face_detector and face_recognizer subfolders - contain code corresponding to 3 microservices of the FD/FR application.
* deployment_aspects - contain code for e2e non-http deployment
* Docker images corresponding to 
  * preprocessor/rtsp_preprocessor.py - dtfernando/preprocess:v1.0amd
  * face_detector/face_detection_app.py - dtfernando/face_detect:v1.0amd
  * face_recognizer/face_recognition_app.py - dtfernando/face_recog:v1.0amd