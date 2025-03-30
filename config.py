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

# -------------------
# JSearch API Configuration
# -------------------
# API keys and endpoints (placeholders, update with your actual keys)
JSEARCH_API = "16c7f72bd6mshf7c7c426eddf90bp173935jsn9286538f70b0"
API_HOST = "jsearch.p.rapidapi.com"
BASE_URL = "https://jsearch.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": JSEARCH_API,
    "x-rapidapi-host": API_HOST
}

# SendGrid API configuration
SENDGRID_API_KEY = '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'
EMAIL_SENDER = 'rylo5252@colorado.edu'    
EMAIL_RECIPIENT = 'jobscrape@yahoo.com'

# ClearBit API configuration
CLEARBIT_API_KEY = '16c7f72bd6mshf7c7c426eddf90bp173935jsn9286538f70b0'
CLEARBIT_FIND_COMPANY_URL = "https://clearbitmikilior1v1.p.rapidapi.com/findCompany"

# Retry Configuration
# -------------------
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds