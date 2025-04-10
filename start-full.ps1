# PowerShell script to start the Surya OCR Docker container with full performance

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

# Run the container with full resources
Write-Host "Starting container with full performance settings..." -ForegroundColor Green
docker run -d `
  --name surya-ocr `
  -p 5000:5000 `
  --memory=8g `
  --memory-swap=12g `
  --cpus=4 `
  -v "${PWD}/data/pdf:/app/pdf" `
  -v "${PWD}/data/uploads:/app/uploads" `
  surya-ocr-app

Write-Host "`nSurya OCR container started. Access the web interface at http://localhost:5000" -ForegroundColor Cyan
Write-Host "This mode runs with full model compilation and Türkçe character support." -ForegroundColor Yellow
Write-Host "PDF files will be saved to ./data/pdf" -ForegroundColor Cyan
Write-Host "`nNOTE: The container may take some time to fully initialize as models are loading." -ForegroundColor Magenta
Write-Host "The interface will be available after all models are loaded." -ForegroundColor Magenta

# Check if container started successfully
docker ps | findstr surya-ocr
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nContainer started successfully. Following container logs..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop following logs when you're done." -ForegroundColor Yellow
    
    # Follow logs to monitor startup progress
    docker logs -f surya-ocr
} else {
    Write-Host "`nError: Container failed to start!" -ForegroundColor Red
    docker logs surya-ocr
} 