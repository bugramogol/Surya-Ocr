# PowerShell script to start the Surya OCR Docker container with minimal memory requirements

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

# Run the container with minimal resource requirements
Write-Host "Starting container with minimal resources configuration..." -ForegroundColor Green
docker run -d `
  --name surya-ocr `
  -p 5000:5000 `
  --memory=2g `
  --memory-swap=4g `
  --cpus=1 `
  -e SKIP_COMPILE=true `
  -e RECOGNITION_BATCH_SIZE=64 `
  -e DETECTOR_BATCH_SIZE=8 `
  -e ORDER_BATCH_SIZE=8 `
  -v "${PWD}/data/pdf:/app/pdf" `
  -v "${PWD}/data/uploads:/app/uploads" `
  surya-ocr-app

Write-Host "`nSurya OCR container started in minimal mode. Access the web interface at http://localhost:5000" -ForegroundColor Cyan
Write-Host "This mode skips model compilation to reduce memory usage but may be slower." -ForegroundColor Yellow
Write-Host "PDF files will be saved to ./data/pdf" -ForegroundColor Cyan
Write-Host "`nContainer logs (will follow logs until Ctrl+C):" -ForegroundColor Yellow
docker logs -f surya-ocr 