FROM registry.hf.space/artificialguybr-surya-ocr:latest

# Root yetkisi ile çalış
USER root

# Install Flask and other dependencies
RUN pip install flask reportlab werkzeug requests uuid

# Install more fonts for better Turkish character support
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-freefont-ttf \
    fonts-liberation \
    fonts-noto \
    fonts-ubuntu \
    fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy multiple fonts to app directory for direct access
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

# Run the unified application
CMD ["python", "/app/unified_app.py"] 