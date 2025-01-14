# run.py
import os
from app import create_app
from config import get_config

# Create the application instance
app = create_app(get_config())

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=(os.environ.get('FLASK_ENV') == 'development')
    )