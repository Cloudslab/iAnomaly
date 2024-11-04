During e2e non-http deployment (in MRC), 
* First deploy kafka
  * kubectl apply -f zookeeper_deployment.yaml
  * Replace IP address of KAFKA_ZOOKEEPER_CONNECT (in kafka-deployment.yaml) with the cluster-ip of zookeeper-service
  * kubectl apply -f kafka_deployment.yaml

* Apply configmap
  * kubectl apply -f envs_configmap.yaml

* Deploy anomaly detector (Corresponding docker image : dtfernando/ianomaly:anomaly_detect_gunicorn)
  * kubectl apply -f ad_gunicorn_deployment.yaml
  * kubectl apply -f ad_gunicorn_service.yaml

* Deploy missing data imputer (Corresponding docker image : dtfernando/ianomaly:mdi_gunicorn)
  * kubectl apply -f mdi_gunicorn_deployment.yaml
  * kubectl apply -f mdi_gunicorn_service.yaml

* Deploy producer (publisher) (Corresponding docker image : dtfernando/ianomaly:producer_sensor)
  * kubectl apply -f producer_deployment.yaml

* Deploy preprocessor (subscriber) (Corresponding docker image : dtfernando/ianomaly:subscriber_preprocessor)
  * kubectl apply -f subscriber_deployment.yaml