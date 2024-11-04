Following is the order of deployment for location retrieval app http e2e scenario.

`kubectl apply -f envs_configmap.yaml`

`kubectl apply -f loc_sim_deployment.yaml`

`kubectl apply -f loc_sim_service.yaml`

`kubectl apply -f loc_ret_deployment.yaml`

`kubectl apply -f loc_ret_service.yaml`