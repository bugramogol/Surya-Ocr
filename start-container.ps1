# PowerShell script to start the Surya OCR Docker container

# Build the Docker image
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t surya-ocr-app .

# Create local directories for volume mapping
Write-Host "Creating data directories..." -ForegroundColor Green
New-Item -ItemType Directory -Path ".\data\pdf" -Force | Out-Null
New-Item -ItemType Directory -Path ".\data\uploads" -Force | Out-Null

# Stop any existing container
Write-Host "Stopping any existing container..." -ForegroundColor Green
docker stop surya-ocr 2>$null
docker rm surya-ocr 2>$null

# Run the container with more resources
Write-Host "Starting new container with increased resources..." -ForegroundColor Green
docker run -d `
  --name surya-ocr `
  -p 5000:5000 `
  --memory=4g `
  --memory-swap=8g `
  --cpus=2 `
  -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 `
  -e RECOGNITION_BATCH_SIZE=128 `
  -e DETECTOR_BATCH_SIZE=16 `
  -e ORDER_BATCH_SIZE=16 `
  -v "${PWD}/data/pdf:/app/pdf" `
  -v "${PWD}/data/uploads:/app/uploads" `
  surya-ocr-app

Write-Host "`nSurya OCR container started. Access the web interface at http://localhost:5000" -ForegroundColor Cyan
Write-Host "PDF files will be saved to ./data/pdf" -ForegroundColor Cyan
Write-Host "`nContainer logs (will follow logs until Ctrl+C):" -ForegroundColor Yellow
docker logs -f surya-ocr 