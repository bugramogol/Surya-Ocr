# PowerShell script to start the Surya OCR Docker container with GPU support
Write-Host "Surya OCR - GPU Destekli Sürüm" -ForegroundColor Cyan

# Check if NVIDIA Docker is available
Write-Host "NVIDIA Docker kontrolü yapılıyor..." -ForegroundColor Yellow
$nvidiaDocker = docker info | Select-String "Runtimes:.*nvidia"
$gpuAvailable = $null -ne $nvidiaDocker

if (-not $gpuAvailable) {
    Write-Host "UYARI: NVIDIA Docker runtime bulunamadı. GPU desteği olmadan devam edilecek." -ForegroundColor Red
    Write-Host "GPU desteği için NVIDIA Container Toolkit kurulu olmalıdır: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html" -ForegroundColor Red
    Write-Host "Devam etmek istiyor musunuz? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "İşlem iptal edildi." -ForegroundColor Red
        exit
    }
}

# Set environment variables for GPU optimization
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:512"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:SURYA_USE_CUDA = "1"

# Create local directories for volume mapping
Write-Host "Veri dizinleri oluşturuluyor..." -ForegroundColor Green
New-Item -ItemType Directory -Path ".\data\pdf" -Force | Out-Null
New-Item -ItemType Directory -Path ".\data\uploads" -Force | Out-Null

# Stop any existing container
Write-Host "Varolan container durduruluyor..." -ForegroundColor Green
docker stop surya-ocr 2>$null
docker rm surya-ocr 2>$null

# Modify the Dockerfile to include CUDA support
Write-Host "Dockerfile.gpu kullanılarak Docker image oluşturuluyor..." -ForegroundColor Green

# Check if Dockerfile.gpu exists, otherwise create it
if (-not (Test-Path "Dockerfile.gpu")) {
    Write-Host "Dockerfile.gpu oluşturuluyor..." -ForegroundColor Yellow
    @"
FROM registry.hf.space/artificialguybr-surya-ocr:latest

# Root yetkisi ile çalış
USER root

# Install Flask and other dependencies
RUN pip install flask reportlab werkzeug requests uuid

# Install font packages for Turkish character support
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-freefont-ttf \
    fonts-liberation \
    fonts-noto \
    fonts-ubuntu \
    fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy DejaVu font to app directory for direct access
RUN mkdir -p /app/fonts && \
    cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /app/fonts/ || true && \
    cp /usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf /app/fonts/ || true && \
    cp /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf /app/fonts/ || true && \
    cp /usr/share/fonts/truetype/freefont/FreeSans.ttf /app/fonts/ || true && \
    chmod -R 755 /app/fonts

# Register fonts with the system
RUN fc-cache -f -v

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/pdf /app/static/temp
RUN chmod -R 777 /app/uploads /app/pdf /app/static/temp

# Copy files
COPY unified_app.py /app/unified_app.py
COPY static/ /app/static/
COPY templates/ /app/templates/

# Set working directory
WORKDIR /app

# Define volumes for persistent storage
VOLUME ["/app/pdf", "/app/uploads"]

# Expose port for the API
EXPOSE 5000

# Set environment variables for GPU
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV CUDA_VISIBLE_DEVICES=0
ENV SURYA_USE_CUDA=1
ENV TORCH_DEVICE=cuda

# Run the unified application
CMD ["python", "/app/unified_app.py"]
"@ | Out-File -FilePath "Dockerfile.gpu" -Encoding utf8
}

# Build the GPU-enabled image
docker build -t surya-ocr-gpu -f Dockerfile.gpu .

# Run the container with GPU support if available
if ($gpuAvailable) {
    Write-Host "GPU destekli container başlatılıyor..." -ForegroundColor Green
    docker run -d `
      --name surya-ocr `
      --gpus all `
      -p 5000:5000 `
      -e TORCH_DEVICE=cuda `
      -e SURYA_USE_CUDA=1 `
      -e CUDA_VISIBLE_DEVICES=0 `
      -v "${PWD}/data/pdf:/app/pdf" `
      -v "${PWD}/data/uploads:/app/uploads" `
      surya-ocr-gpu
} else {
    Write-Host "Container CPU modunda başlatılıyor..." -ForegroundColor Yellow
    docker run -d `
      --name surya-ocr `
      -p 5000:5000 `
      -e TORCH_DEVICE=cpu `
      -e SURYA_USE_CUDA=0 `
      -v "${PWD}/data/pdf:/app/pdf" `
      -v "${PWD}/data/uploads:/app/uploads" `
      surya-ocr-gpu
}

# Check if container started successfully
docker ps | findstr surya-ocr
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nContainer başarıyla başlatıldı. Uygulama başlatılıyor..." -ForegroundColor Green
    Write-Host "Web arayüzüne erişim: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "PDF dosyaları burada saklanacak: ./data/pdf" -ForegroundColor Cyan
    
    # Optional: Follow logs
    Write-Host "`nContainerin başlangıç logları:" -ForegroundColor Yellow
    docker logs --tail 20 surya-ocr
    
    Write-Host "`nTüm logları görmek için şu komutu kullanın: 'docker logs -f surya-ocr'" -ForegroundColor Cyan
} else {
    Write-Host "`nHATA: Container başlatılamadı!" -ForegroundColor Red
    docker logs surya-ocr
} 