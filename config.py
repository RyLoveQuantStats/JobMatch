# config.py

import os

# Database configuration
DATABASE_FILE = 'data.db'
# Get the base directory where config.py is located.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE = os.path.join(BASE_DIR, 'database', 'schema.sql')

# Logging configuration
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = 'app.log'
LOG_LEVEL = 'INFO'

# API keys and endpoints (placeholders, update with your actual keys)
JSEARCH_API = "22d7e554a0msh4b5224dbea1a4dbp1baac7jsn2197588dd568"
YFINANCE_API_KEY = 'YOUR_YFINANCE_API_KEY'




