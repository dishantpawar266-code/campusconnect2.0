import sys
import os

# Add root directory to sys.path so modules can be imported smoothly on Vercel
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel Serverless Function entry point
app = app
