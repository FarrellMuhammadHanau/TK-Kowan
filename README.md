# Deployment Guide

## **Requirements**
- Docker
- Kubernetes
- kubectl

---

## **Step 1: Build & Push Docker Image (OPTIONAL)**

**PENTING:** Image untuk semua services sudah tersedia secara **public** di Docker Hub dan sudah dikonfigurasi di deployment YAML:

- `farrellmuhammadhanau/auth-service:latest`
- `farrellmuhammadhanau/attendee-service:latest`
- `farrellmuhammadhanau/room-service:latest`
- `yodh4/class-service:latest`
- `yodh4/schedule-service:latest`
- `yodh4/attendance-service:latest`

**Anda dapat langsung ke Step 2** jika ingin menggunakan image yang sudah ada.

---

### **Jika Ingin Build Image Sendiri:**

Masuk ke folder microservice yang ingin di-deploy:

```bash
cd [nama-service]-service/

# Build image
docker build -t [docker-username]/[nama-service]-service:latest .

# Push ke Docker Hub
docker push [docker-username]/[nama-service]-service:latest
```

**Contoh:**
```bash
cd auth-service/
docker build -t yourusername/auth-service:latest .
docker push yourusername/auth-service:latest
```

**Kemudian update image name di deployment YAML:**

Edit file `deployment/[nama-service]-service/[nama-service]-service-deployment.yaml`:

```yaml
spec:
  containers:
  - name: [nama-service]
    image: yourusername/[nama-service]-service:latest  # Ganti dengan image Anda
    imagePullPolicy: Always
```

**Atau gunakan command kubectl:**

```bash
kubectl set image deployment/[nama-service] \
  [nama-service]=yourusername/[nama-service]-service:latest
```

---

## **Step 2: Deploy Database**

Masuk ke folder deployment untuk service tersebut:

```bash
cd deployment/[nama-service]-service/

# Deploy PersistentVolumeClaim
kubectl apply -f postgres-pvc.yaml

# Deploy PostgreSQL
kubectl apply -f postgres-deployment.yaml

# Verify
kubectl get pods | grep postgres
```

---

## **Step 3: Deploy Microservice**

Pastikan image name di `[nama-service]-service-deployment.yaml` sudah sesuai dengan yang Anda push.

```bash
# Deploy microservice
kubectl apply -f [nama-service]-service-deployment.yaml

# Verify
kubectl get pods
kubectl get services
```

---

## **Step 4: Mendapatkan External IP**

Services menggunakan LoadBalancer dan akan mendapat IP public otomatis:

```bash
# Watch sampai External IP assigned
kubectl get service [nama-service]-service --watch

# Atau cek semua services
kubectl get services
```

**Output example:**
```
NAME              TYPE           EXTERNAL-IP        PORT(S)          AGE
auth-service      LoadBalancer   xxx.xxx.xxx.x    8000:31234/TCP   5m
```
IP yang tertulis di `EXTERNAL-IP` akan berupa IP Private jika menggunakan Self-Managed Kubernetes 
---

## **Recommended Deployment Order**

1. Auth Service
2. Attendee Service  
3. Room Service
4. Class Service (update `ATTENDEE_SERVICE_URL` dengan IP dari step 4)
5. Schedule Service (update `ROOM_SERVICE_URL` dan `CLASS_SERVICE_URL`)
6. Attendance Service (update semua service URLs)

**Note:** Beberapa services memerlukan environment variable berisi IP dari services lain. Update deployment YAML jika diperlukan, lalu apply ulang.

---

## **Verification**

```bash
# Check status
kubectl get pods
kubectl get services

# Check logs jika ada error
kubectl logs <pod-name>

# Test endpoint
curl http://<EXTERNAL-IP>:8000/docs
```

---

## **Setup Environment Variables untuk Inter-Service Communication**

Setelah semua services di-deploy, beberapa services memerlukan IP dari services lain untuk berkomunikasi.

### **1. Catat Semua External IP**

Jalankan di setiap VM atau cluster:

```bash
kubectl get services
```

Catat IP untuk setiap service (gunakan **Public IP VM** jika EXTERNAL-IP menunjukkan private IP):

```
Auth Service:       http://<IP>:8000
Attendee Service:   http://<IP>:8000
Room Service:       http://<IP>:8000
Class Service:      http://<IP>:8000
Schedule Service:   http://<IP>:8000
```

### **2. Update Deployment YAML**

#### **Class Service** - memerlukan Attendee Service URL

Edit `deployment/class-service/class-service-deployment.yaml`:

```yaml
env:
- name: ATTENDEE_SERVICE_URL
  value: http://<ATTENDEE-SERVICE-IP>:8000
```

#### **Schedule Service** - memerlukan Room & Class Service URL

Edit `deployment/schedule-service/schedule-service-deployment.yaml`:

```yaml
env:
- name: ROOM_SERVICE_URL
  value: http://<ROOM-SERVICE-IP>:8000
- name: CLASS_SERVICE_URL
  value: http://<CLASS-SERVICE-IP>:8000
```

#### **Attendance Service** - memerlukan semua Service URLs

Edit `deployment/attendance-service/attendance-service-deployment.yaml`:

```yaml
env:
- name: ATTENDEE_SERVICE_URL
  value: http://<ATTENDEE-SERVICE-IP>:8000
- name: CLASS_SERVICE_URL
  value: http://<CLASS-SERVICE-IP>:8000
- name: SCHEDULE_SERVICE_URL
  value: http://<SCHEDULE-SERVICE-IP>:8000
- name: ROOM_SERVICE_URL
  value: http://<ROOM-SERVICE-IP>:8000
```

### **3. Apply Update**

Setelah edit YAML, apply ulang deployment:

```bash
# Class Service
kubectl apply -f deployment/class-service/class-service-deployment.yaml
kubectl rollout restart deployment class-service

# Schedule Service
kubectl apply -f deployment/schedule-service/schedule-service-deployment.yaml
kubectl rollout restart deployment schedule-service

# Attendance Service
kubectl apply -f deployment/attendance-service/attendance-service-deployment.yaml
kubectl rollout restart deployment attendance-service
```

### **4. Verifikasi**

Check logs untuk memastikan tidak ada connection error:

```bash
kubectl logs -f deployment/class-service
kubectl logs -f deployment/schedule-service
kubectl logs -f deployment/attendance-service
```

**Note:** IP akan berbeda setiap kali deploy di environment baru, jadi langkah ini **wajib dilakukan** saat setup pertama kali.