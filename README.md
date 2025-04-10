---
title: Surya OCR
emoji: 👀
colorFrom: purple
colorTo: green
sdk: gradio
sdk_version: 4.41.0
app_file: app.py
pinned: false
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

# Surya OCR API

This is a REST API that uses Surya OCR to extract text from images.

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the API server:
   ```
   python api.py
   ```

   The server will start on port 5000.

## API Usage

### OCR Endpoint

**URL:** `/ocr`

**Method:** `POST`

**Form Parameters:**
- `image`: The image file to process
- `langs` (optional): Comma-separated list of language codes (default: "en")

**Example using curl:**
```bash
curl -X POST -F "image=@path/to/your/image.jpg" -F "langs=en,tr" http://localhost:5000/ocr
```

**Example using Python requests:**
```python
import requests

url = "http://localhost:5000/ocr"
files = {"image": open("path/to/your/image.jpg", "rb")}
data = {"langs": "en,tr"}  # Optional, default is "en"

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Response Format:**
```json
{
  "text": "The full extracted text as a single string...",
  "details": [
    {
      "text": "First line of text",
      "bbox": [x1, y1, x2, y2]
    },
    {
      "text": "Second line of text",
      "bbox": [x1, y1, x2, y2]
    }
  ]
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- 400: Bad request (missing image file)
- 500: Server error (processing error)

Error responses will include a JSON object with an "error" field explaining the issue.

# Surya OCR Kubernetes Deployment

Bu repo, Surya OCR uygulamasının Kubernetes ortamında çalıştırılması için gerekli YAML dosyalarını ve Helm Chart'ını içerir.

## İçerik

- `surya-ocr-deployment.yaml`: CPU modu için temel Kubernetes deployment ve service dosyası
- `surya-ocr-gpu-deployment.yaml`: GPU destekli Kubernetes deployment ve service dosyası
- `surya-ocr-ingress.yaml`: İnternetten erişim için Ingress kaynağı
- `surya-ocr-helm/`: Helm Chart dosyaları (CPU/GPU)

## Ön Koşullar

- Kubernetes Cluster (1.19+)
- kubectl CLI
- (Opsiyonel) NVIDIA GPU ve NVIDIA Device Plugin kurulu Kubernetes cluster
- (Opsiyonel) Helm (3.0+)

## Direkt YAML Dosyalarıyla Kurulum

### CPU Modu

```bash
kubectl apply -f surya-ocr-deployment.yaml
```

### GPU Modu

NVIDIA Device Plugin kurulu bir Kubernetes cluster'ında:

```bash
kubectl apply -f surya-ocr-gpu-deployment.yaml
```

### Ingress Kaynağı Oluşturma

```bash
kubectl apply -f surya-ocr-ingress.yaml
```

> **Not**: Ingress'i etkinleştirmeden önce, `surya-ocr-ingress.yaml` dosyasındaki `host` alanını kendi domain adınızla değiştirmelisiniz.

## Helm ile Kurulum

Helm Chart, CPU ve GPU modu arasında kolayca geçiş yapmanızı sağlar. 

### CPU Modu Kurulum

```bash
helm install surya-ocr ./surya-ocr-helm
```

### GPU Modu Kurulum

```bash
helm install surya-ocr ./surya-ocr-helm --set gpuEnabled=true
```

### Özel Değerlerle Kurulum

```bash
helm install surya-ocr ./surya-ocr-helm -f custom-values.yaml
```

## Parametre Açıklamaları

### Kullanılabilir GPU Parametreleri

```yaml
gpuEnabled: true
config:
  gpu:
    recognitionBatchSize: "1024"  # Tanıma batch boyutu
    detectorBatchSize: "64"       # Tespit batch boyutu
    orderBatchSize: "64"          # Sıralama batch boyutu
    torchDevice: "cuda"           # PyTorch cihazı
    suryaUseCuda: "1"             # Surya CUDA kullanımı
    cudaVisibleDevices: "0"       # Kullanılacak CUDA cihazı
    pytorchCudaAllocConf: "max_split_size_mb:512"  # CUDA bellek ayarları
```

## Kubernetes'te Ölçeklendirme

Surya OCR uygulamasını yatay olarak ölçeklendirmek için:

```bash
kubectl scale deployment surya-ocr --replicas=3
```

## Kalıcı Depolama

Uygulama, OCR işlemi sonucunda oluşturulan PDF dosyalarını ve yüklenen dosyaları saklamak için kalıcı depolama kullanır. Bu alanlar:

- `/app/pdf`: OCR işlemi sonrası oluşturulan PDF dosyaları
- `/app/uploads`: Yüklenen dosyaların geçici olarak saklandığı alan

## Docker Hub

Docker imajına şu komutla erişebilirsiniz:

```bash
docker pull abmogol/surya-ocr:latest
```

## Kaynaklar

- [Surya OCR Projesi](https://github.com/yourname/surya-ocr)
- [Kubernetes Belgeleri](https://kubernetes.io/docs/home/)
- [Helm Belgeleri](https://helm.sh/docs/)