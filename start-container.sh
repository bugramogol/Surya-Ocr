#!/bin/bash

# Build the Docker image
docker build -t surya-ocr-app .

# Create local directories for volume mapping
mkdir -p ./data/pdf ./data/uploads

# Run the container with volume mappings
docker run -d \
  --name surya-ocr \
  -p 5000:5000 \
  -v "$(pwd)/data/pdf:/app/pdf" \
  -v "$(pwd)/data/uploads:/app/uploads" \
  surya-ocr-app

echo "Surya OCR container started. Access the web interface at http://localhost:5000"
echo "PDF files will be saved to ./data/pdf" 