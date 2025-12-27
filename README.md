# Requirement
### 1. Docker
### 2. Kubernetes
### 3. Kubectl

# Cara deploy microservice
### 1. Masuk ke dalam folder microservice
### 2. Build image docker lalu push ke docker hub
    docker build -t [nama docker]/[nama service]-service:latest .
### 3. Masuk ke dalam folder deployment untuk microservice tersebut
### 4. Apply postgres-pvc.yaml untuk persistent volume claim lalu deploy postgreSQL Database dengan cara apply postgres-deployment.yaml
    kubectl apply -f postgres-pvc.yaml
    kubectl apply -f postgres-deployment.yaml
### 5. Ubah image yang digunakan pada [nama service]-service-deployment.yaml mengikuti image yang sudah dipush sebelumnya lalu deploy microservice menggunakan yaml tersebut
    kubectl apply -f [nama service]-service-deployment.yaml
### 6. Melakukan port-forward untuk service yang sudah dideploy
    kubectl port-forward --address 0.0.0.0 service/[nama service]-service 8000:8000 &
