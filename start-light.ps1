# PowerShell script to start the Surya OCR Docker container in lightweight mode

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

# Run the container in lightweight mode
Write-Host "Starting container in lightweight mode with Turkish character support..." -ForegroundColor Green
docker run -d `
  --name surya-ocr `
  -p 5000:5000 `
  --memory=3g `
  --memory-swap=5g `
  --cpus=2 `
  -e SKIP_COMPILE=true `
  -e RECOGNITION_BATCH_SIZE=32 `
  -e DETECTOR_BATCH_SIZE=4 `
  -e ORDER_BATCH_SIZE=4 `
  -v "${PWD}/data/pdf:/app/pdf" `
  -v "${PWD}/data/uploads:/app/uploads" `
  surya-ocr-app

Write-Host "`nSurya OCR container started in lightweight mode. Access the web interface at http://localhost:5000" -ForegroundColor Cyan
Write-Host "This mode skips model compilation and uses the DejaVuSans font for Turkish character support." -ForegroundColor Yellow
Write-Host "PDF files will be saved to ./data/pdf" -ForegroundColor Cyan

# Check if container started successfully
docker ps | findstr surya-ocr
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nContainer started successfully. Waiting for application to initialize..." -ForegroundColor Green
    
    # Wait for 10 seconds then show initial logs
    Start-Sleep -Seconds 10
    Write-Host "`nInitial container logs:" -ForegroundColor Yellow
    docker logs --tail 20 surya-ocr
    
    Write-Host "`nUse 'docker logs -f surya-ocr' to follow logs." -ForegroundColor Cyan
} else {
    Write-Host "`nError: Container failed to start!" -ForegroundColor Red
    docker logs surya-ocr
} 