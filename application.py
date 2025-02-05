import os
import sys
import json
import numpy as np
from datetime import datetime
import traceback


from models.vision_processing import process_image, process_orthogonal_views
import plotly.utils

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from urllib.parse import urlparse

# Import our MongoDB managers and models
from db.manager import user_manager, survey_manager, feedback_manager
from db.models import User
from models.vision_processing import process_image, process_orthogonal_views


from config import Config
from models.enhanced_visualization import Enhanced3DVisualizer
from models.model_monitoring import ModelMonitor
from utils.benchmark_system import BenchmarkSystem

from routes.dashboard import dashboard

from botocore.exceptions import ClientError

from storage import create_storage_manager, S3StorageManager

from datetime import timedelta
import secrets



application = Flask(__name__)
app = application  # This provides compatibility with both 'app' and 'application' names
app.config.from_object(Config)

# Add these configurations after creating the Flask app
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Generate a secure secret key
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Set remember me duration
app.config['SESSION_PROTECTION'] = 'strong'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Session lifetime

# Initialize Flask-Login with the correct login view
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Changed from 'auth.login' to just 'login'
login_manager.session_protection = 'strong'
login_manager.login_message = 'Please log in to access this feature.'
login_manager.login_message_category = 'info'


# Initialize our enhanced visualization system
visualizer = Enhanced3DVisualizer(log_dir=app.config['LOG_DIR'])
monitor = ModelMonitor(log_dir=app.config['LOG_DIR'])
benchmark_system = BenchmarkSystem(output_dir=app.config['BENCHMARK_DIR'])

# Initialize storage manager
storage = create_storage_manager(app)
        
app.register_blueprint(dashboard)

# Add a before_request handler to check session
@app.before_request
def before_request():
    if current_user.is_authenticated:
        # Refresh the user's session to prevent timeout
        session.modified = True

def is_safe_url(target):
    """
    Validates if a URL is safe to redirect to by checking if it's relative
    and doesn't contain a scheme or network location.
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return (not test_url.scheme and not test_url.netloc) or \
           (test_url.scheme == ref_url.scheme and test_url.netloc == ref_url.netloc)


@app.context_processor
def utility_processor():
    """Make monitoring data available to all templates"""
    def get_model_metrics():
        return monitor.get_summary_metrics()
    return dict(get_model_metrics=get_model_metrics)

@login_manager.user_loader
def load_user(user_id):
    """Loads user from MongoDB for Flask-Login"""
    user_doc = user_manager.get_user_by_id(user_id)
    if user_doc:
        return User(user_doc)
    return None

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with secure redirect handling"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user_doc = user_manager.get_user_by_email(email)
        
        if user_doc and user_manager.verify_password(user_doc, password):
            user = User(user_doc)
            login_user(user, remember=remember)
            
            # Safely handle the next parameter
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            
            print(f"User {email} logged in successfully")
            return redirect(url_for('index'))
        
        flash('Invalid email or password')
        print(f"Failed login attempt for email: {email}")

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if user already exists
        if user_manager.get_user_by_email(email):
            flash('Email already registered')
            return redirect(url_for('register'))  # Changed from 'auth.register'

        # Create new user
        user_doc = user_manager.create_user(
            username=username,
            email=email,
            password=password
        )

        if user_doc:
            user = User(user_doc)
            login_user(user)
            print(f"New user registered: {email}")
            return redirect(url_for('index'))
        else:
            flash('Registration failed. Please try again.')
            print(f"Registration failed for email: {email}")

    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    if current_user.is_authenticated:
        email = current_user.email
        logout_user()
        print(f"User {email} logged out")
    return redirect(url_for('index'))

# Update the routes to use the storage manager
@app.route('/')
@login_required
def index():
    """Home page showing list of folders"""
    try:
        # List all unique folder names from existing files
        folders = storage.list_folders()
        return render_template('index.html', folders=sorted(list(folders)))
    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', folders=[], error="Error loading folders")


@app.route('/folder/<folder_name>')
@login_required
def view_folder(folder_name):
    print("""Dedicated page for each folder""")
    try:
        # Get list of images in the folder
        images = storage.list_files(folder_name)
        
        # Filter for image files
        images = [f for f in images if f.lower().endswith(tuple(app.config['ALLOWED_EXTENSIONS']))]
        
        # Debug print
        print("\nDebug - Folder View:")
        print(f"Folder: {folder_name}")
        print(f"Found images: {images}")
        
        # For each image, get its URL
        image_urls = {}
        for img in images:
            url = storage.get_file_url(folder_name, img)
            image_urls[img] = url
            print(f"Image URL for {img}: {url}")
        
        return render_template('folder.html',
                             folder_name=folder_name,
                             images=images,
                             image_urls=image_urls)
    except Exception as e:
        print(f"Error in view_folder route: {str(e)}")
        traceback.print_exc()  # Add this for more detailed error information
        return render_template('folder.html', 
                             folder_name=folder_name,
                             images=[],
                             image_urls={},
                             error="Error loading folder")


@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """Handle file uploads to storage"""
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'})

    folder_name = request.form.get('folder_name', 'Untitled')
    files = request.files.getlist('files[]')
    uploaded_files = []
    processed_views = []
    view_types = ['front', 'back', 'top']

    try:
        for i, file in enumerate(files):
            if file and file.filename:
                if not allowed_file(file.filename):
                    return jsonify({
                        'success': False, 
                        'message': f'Invalid file format. Allowed: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
                    })
                
                # Get file extension and create new filename
                ext = os.path.splitext(file.filename)[1].lower()
                if i < len(view_types):
                    new_filename = f"{view_types[i]}{ext}"
                    
                    # Save file using storage manager
                    storage.save_file(file, folder_name, new_filename)
                    uploaded_files.append(new_filename)
                    processed_views.append(view_types[i])

        # Process metrics
        metrics_data = json.loads(request.form.get('metrics', '{}'))
        feedback_data = {
            'interaction_type': 'upload',
            'metrics': metrics_data,
            'processed_views': processed_views,
            'visualization_type': '3D'
        }

        if current_user.is_authenticated:
            feedback_manager.create_feedback(
                user_id=current_user.get_id(),
                product_id=folder_name,
                feedback_data=feedback_data
            )

        return jsonify({
            'success': True,
            'message': 'Files uploaded successfully',
            'uploadedFiles': uploaded_files,
            'redirect': url_for('view_folder', folder_name=folder_name)
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/track-interaction/<folder_name>', methods=['POST'])
@login_required
def track_interaction(folder_name):
    try:
        interaction_data = request.json
        feedback_manager.create_feedback(
            user_id=current_user.get_id(),
            product_id=folder_name,
            feedback_data={
                'interaction_type': 'page_interaction',
                **interaction_data
            }
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error tracking interaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    
    
@app.route('/process/<folder_name>')
@login_required
def process_folder(folder_name):
    """Process images in a folder and generate 3D visualization"""
    print(f"DEBUG: Processing folder: {folder_name}")
    
    try:
        # Get list of files in the folder
        files = storage.list_files(folder_name)
        
        # Initialize view files dictionary
        view_files = {'front': None, 'back': None, 'top': None}
        
        # Look for view files with different extensions
        for file in files:
            file_lower = file.lower()
            for view in view_files.keys():
                if file_lower.startswith(view) and file_lower.endswith(('.jpg', '.png', '.jpeg', '.gif')):
                    # Get the actual file content for processing
                    if isinstance(storage, S3StorageManager):
                        # For S3, we need to download the file temporarily
                        temp_path = os.path.join('/tmp', file)
                        s3_client = storage.s3_client
                        s3_client.download_file(
                            storage.bucket_name,
                            f"{folder_name}/{file}",
                            temp_path
                        )
                        view_files[view] = temp_path
                    else:
                        # For local storage, use the direct path
                        view_files[view] = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, file)
        
        # Log found files
        print("DEBUG: Found view files:")
        for view, path in view_files.items():
            print(f"DEBUG: {view}: {'Found' if path else 'Not found'} - {path}")

        try:
            # Check if we have all three views
            if all(view_files.values()):
                print("DEBUG: Processing with all three views")
                figure = process_orthogonal_views(
                    view_files['front'],
                    view_files['back'],
                    view_files['top']
                )
            else:
                # Fall back to single view if not all views are available
                print("DEBUG: Falling back to single view processing")
                available_views = [path for path in view_files.values() if path]
                if not available_views:
                    print("DEBUG: No valid views found")
                    return jsonify({'success': False, 'message': 'No valid views found'})
                figure = process_image(available_views[0])
            
            if figure is None:
                print("DEBUG: Failed to generate plot data")
                return jsonify({'success': False, 'message': 'Failed to process images'})
            
            # Convert Plotly figure to JSON-serializable format
            def convert_numpy(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {key: convert_numpy(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy(item) for item in list(obj)]
                return obj
            
            # Convert and save plot data
            plot_data = convert_numpy(figure)
            
            if isinstance(storage, S3StorageManager):
                # Save to S3
                plot_data_json = json.dumps(plot_data, cls=plotly.utils.PlotlyJSONEncoder)
                s3_client.put_object(
                    Bucket=storage.bucket_name,
                    Key=f"{folder_name}/plot_data.json",
                    Body=plot_data_json,
                    ContentType='application/json'
                )
            else:
                # Save locally
                plot_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'plot_data.json')
                with open(plot_file, 'w') as f:
                    json.dump(plot_data, f, cls=plotly.utils.PlotlyJSONEncoder)
            
            print("DEBUG: Successfully saved plot data")
            
            # Clean up temporary files if using S3
            if isinstance(storage, S3StorageManager):
                for path in view_files.values():
                    if path and os.path.exists(path):
                        os.remove(path)
            
            return jsonify({
                'success': True, 
                'plot': plot_data,
                'processedViews': {
                    'front': bool(view_files['front']),
                    'back': bool(view_files['back']),
                    'top': bool(view_files['top'])
                }
            })
            
        except TypeError as json_error:
            print(f"DEBUG: JSON serialization error: {str(json_error)}")
            return jsonify({
                'success': False,
                'message': 'Failed to serialize visualization data'
            })
            
    except Exception as e:
        print(f"DEBUG: Processing error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        # Ensure temporary files are cleaned up in case of errors
        if isinstance(storage, S3StorageManager):
            for path in view_files.values():
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

@app.route('/get_feedback/<folder_name>')
@login_required
def get_feedback(folder_name):
    """Get all feedback for a folder"""
    feedback_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'feedback.json')
    
    if os.path.exists(feedback_file):
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        return jsonify({'success': True, 'feedback': feedback_data})
    
    return jsonify({'success': True, 'feedback': []})


@app.after_request
def after_request(response):
    """Log important headers and session info after each request"""
    if app.debug:
        print("\nRequest Debug Info:")
        print(f"Endpoint: {request.endpoint}")
        print(f"Method: {request.method}")
        print(f"User Authenticated: {current_user.is_authenticated}")
        if current_user.is_authenticated:
            print(f"User ID: {current_user.get_id()}")
        print(f"Session: {dict(session)}")
        print(f"Response Status: {response.status_code}")
    return response

# @app.route('/get-s3-data/<folder_name>')
# @login_required
# def get_s3_data(folder_name):
#     try:
#         s3_client = boto3.client('s3')
        
#         # Generate a presigned URL that expires in 3600 seconds (1 hour)
#         presigned_url = s3_client.generate_presigned_url('get_object',
#             Params={
#                 'Bucket': AWS_BUCKET_NAME,
#                 'Key': f"{folder_name}/plot_data.json"
#             },
#             ExpiresIn=3600
#         )
        
#         return jsonify({
#             'success': True,
#             'url': presigned_url
#         })
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         })

@app.route('/feedback/<folder_name>', methods=['POST'])
@login_required
def save_feedback(folder_name):
    """Save feedback for a folder"""
    feedback_data = request.json
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    feedback_file = os.path.join(folder_path, 'feedback.json')
    
    try:
        # Ensure the folder exists
        if not os.path.exists(folder_path):
            return jsonify({'success': False, 'error': 'Folder not found'})
            
        # Load existing feedback or create new list
        existing_feedback = []
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                existing_feedback = json.load(f)
        
        # Add new feedback
        existing_feedback.append(feedback_data)
        
        # Save updated feedback
        with open(feedback_file, 'w') as f:
            json.dump(existing_feedback, f, indent=2)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
# Add at the top of app.py
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/debug/session')
def debug_session():
    """Debug endpoint to check session data"""
    if not current_user.is_authenticated:
        return jsonify({
            'authenticated': False,
            'session': dict(session),
            'user': None
        })
    
    return jsonify({
        'authenticated': True,
        'session': dict(session),
        'user': {
            'id': current_user.get_id(),
            'email': current_user.email,
            'username': current_user.username
        }
    })

if __name__ == '__main__':
    try:
        application.run(host='0.0.0.0', port=8000)
        # app.run(debug=True)
    except KeyboardInterrupt:
        print('Shutting down gracefully...')
        sys.exit(0)