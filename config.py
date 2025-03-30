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
JSEARCH_API = "16c7f72bd6mshf7c7c426eddf90bp173935jsn9286538f70b0"

SENDGRID_API_KEY = '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'
EMAIL_SENDER = 'rylo5252@colorado.edu'    
EMAIL_RECIPIENT = 'jobscrape@yahoo.com'


