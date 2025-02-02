# config.py
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-here'
    
    # MongoDB configuration
    MONGO_URI = 'mongodb+srv://3dvis:.7yt_QtvB6fU68J@3dvisualization.eevq2.mongodb.net/'
    MONGO_DB_NAME = '3dvisualization'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    
    # Environment configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Security configurations
    CSRF_ENABLED = True
    
    # Base directory configurations
    BASE_DIR = Path(__file__).parent
    LOG_DIR = BASE_DIR / 'logs'
    BENCHMARK_DIR = BASE_DIR / 'benchmarks'

    # Storage configuration
    if FLASK_ENV == 'production':
        # AWS S3 configuration
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
        AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME', '3d-product-uploads')
        UPLOAD_FOLDER = None  # Not used in production
    else:
        # Local storage configuration
        UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
        # Create upload directory if it doesn't exist
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # File configurations
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Create necessary directories
    for directory in [LOG_DIR, BENCHMARK_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Model configurations
    MODEL_SETTINGS = {
        'depth_threshold': 0.25,
        'sampling_rate': 1.0,
        'quality_threshold': 0.7
    }
    
    # Monitoring configurations
    MONITORING_ENABLED = True
    MONITORING_INTERVAL = 30  # seconds

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP for development
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY') or 'generate-a-proper-key-here'
    LOG_LEVEL = 'ERROR'
    SESSION_COOKIE_SECURE = True

# Choose configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Returns the appropriate configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])