import os

# Production Configuration

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'generate-a-secure-key-here')
DEBUG = False
TESTING = False

# Server
HOST = '0.0.0.0'
PORT = 8000

# File Upload
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = '/opt/ytnew/downloads'

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'youtube_downloader.log'

# Security Headers
SECURE_HEADERS = {
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'X-Content-Type-Options': 'nosniff',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'"
} 