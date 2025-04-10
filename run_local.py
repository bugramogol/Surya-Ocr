"""
Run the Surya OCR application directly on the local system without Docker.
This can be helpful for troubleshooting when Docker containers have resource issues.
"""
import os
import sys
import platform
import subprocess

# Set environment variables for optimization
os.environ["SKIP_COMPILE"] = "true"
os.environ["RECOGNITION_BATCH_SIZE"] = "64"
os.environ["DETECTOR_BATCH_SIZE"] = "8"
os.environ["ORDER_BATCH_SIZE"] = "8" 
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("pdf", exist_ok=True)
os.makedirs(os.path.join("static", "temp"), exist_ok=True)

# Install required packages if not already installed
try:
    import flask
    import reportlab
    import werkzeug
    import requests
    import uuid
except ImportError:
    print("Installing required packages...")
    packages = ["flask", "reportlab", "werkzeug", "requests", "uuid"]
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)

print("\nStarting Surya OCR application directly...")
print("This will run without Docker, using your system's resources directly.")
print("Access the web interface at http://localhost:5000\n")

# Run the application
from unified_app import app
app.run(host='0.0.0.0', port=5000, debug=False) 