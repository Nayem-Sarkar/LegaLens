import sys
import os

# Add the root directory to path so we can import server.py and main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app instance
from server import app 
