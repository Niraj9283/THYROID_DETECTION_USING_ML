import sys
import os

# Add root project directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app

# Vercel serverless WSGI entry point
app = app
