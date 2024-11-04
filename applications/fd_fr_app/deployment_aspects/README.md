Following is the order of deployment
* RTSP stream setup
    * Start the RTSP server as a Docker container

    sudo docker run --rm -it \
-e MTX_PROTOCOLS=tcp \
-e MTX_WEBRTCADDITIONALHOSTS=0.0.0.0 \
-p 8554:8554 \
-p 1935:1935 \
-p 8888:8888 \
-p 8889:8889 \
-p 8890:8890/udp \
-p 8189:8189/udp \
bluenviron/mediamtx

    * Stream the video file over RTSP

ffmpeg -re -stream_loop -1 -i video2.mp4 -c copy -f rtsp rtsp://localhost:8554/live

* Start minikube or setup multi-node cluster in k3s
* Apply configmap (which contains env variables) - `kubectl apply -f envs_configmap.yaml`
* Deploy the DB server, execute the queries and expose the service - 

`kubectl apply -f mysql_db_deployment.yaml`

`kubectl exec -it mysql-deployment-777c6dfb68-rvfcv -- mysql -u root -p`

```
create database my_database;
use my_database;
CREATE TABLE detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    time DATETIME
);
```

`kubectl apply -f mysql_db_service.yaml`

* Apply the service and deployment yamls of FR, FD and preprocess microservices (in the given order)

`kubectl apply -f fr_deployment.yaml`

`kubectl apply -f fr_service.yaml`

`kubectl apply -f fd_deployment.yaml`

`kubectl apply -f fd_service.yaml`

`kubectl apply -f preprocessor_deployment.yaml`

* Deploy Pixie in the master node
