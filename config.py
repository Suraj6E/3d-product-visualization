# config.py
import os
from datetime import timedelta
from pathlib import Path


class Config:
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # MongoDB configuration
    MONGO_URI = 'mongodb+srv://3dvis:.7yt_QtvB6fU68J@3dvisualization.eevq2.mongodb.net/'
    MONGO_DB_NAME = '3dvisualization'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    
    # Security configurations
    CSRF_ENABLED = True
    
    # Logging configuration
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'

     # Directory configurations
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    LOG_DIR = BASE_DIR / 'logs'
    BENCHMARK_DIR = BASE_DIR / 'benchmarks'
    
    # Create necessary directories
    for directory in [UPLOAD_FOLDER, LOG_DIR, BENCHMARK_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # File configurations
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
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
    # In production, you should set a proper secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'generate-a-proper-key-here'
    
    # Production logging
    LOG_LEVEL = 'ERROR'
    
    # Production security settings
    SESSION_COOKIE_SECURE = True

# Choose configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Returns the appropriate configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])