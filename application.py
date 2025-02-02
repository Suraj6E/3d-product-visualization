import os
import sys
import json
import numpy as np
from datetime import datetime
import traceback


from models.vision_processing import process_image, process_orthogonal_views
import plotly.utils

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
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
from routes.visualization import visualization

import boto3
from botocore.exceptions import ClientError

application = Flask(__name__)
app = application  # This provides compatibility with both 'app' and 'application' names
app.config.from_object(Config)


# Initialize Flask-Login with the correct login view
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Changed from 'auth.login' to just 'login'
login_manager.login_message = 'Please log in to access this feature.'

# Initialize our enhanced visualization system
visualizer = Enhanced3DVisualizer(log_dir=app.config['LOG_DIR'])
monitor = ModelMonitor(log_dir=app.config['LOG_DIR'])
benchmark_system = BenchmarkSystem(output_dir=app.config['BENCHMARK_DIR'])

# Initialize S3 client
s3_client = boto3.client('s3')
AWS_BUCKET_NAME = app.config['AWS_BUCKET_NAME']


app.register_blueprint(dashboard)

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

# Main application routes
@app.route('/')
def index():
    """Home page showing list of folders"""
    print("Upload folder: ", app.config['UPLOAD_FOLDER'])
    folders = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
            if os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    return render_template('index.html', folders=folders)


@app.route('/folder/<folder_name>')
def view_folder(folder_name):
    """Dedicated page for each folder"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    
    # Get images in folder
    images = []
    if os.path.exists(folder_path):
        images = [f for f in os.listdir(folder_path) 
                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    
    # Get feedback for this folder
    feedback_file = os.path.join(folder_path, 'feedback.json')
    feedback_data = {}
    if os.path.exists(feedback_file):
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
            
    # Check if plot data exists
    plot_file = os.path.join(folder_path, 'plot_data.json')
    has_plot = os.path.exists(plot_file)

    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=images,
                         feedback=feedback_data,
                         has_plot=has_plot)  # Pass this to template if needed


@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """Handle file uploads to S3 bucket with automatic view type naming"""
    try:
        if 'files[]' not in request.files:
            print("DEBUG: No files provided in request")
            return jsonify({'success': False, 'message': 'No files provided'})

        folder_name = request.form.get('folder_name', 'Untitled')
        s3_folder_path = f"{folder_name}/"  # S3 uses forward slashes
        print(f"DEBUG: Processing uploads for folder: {folder_name}")

        # Process files
        files = request.files.getlist('files[]')
        uploaded_files = []
        processed_views = []
        view_types = ['front', 'back', 'top']
        
        # Process each file and assign view type based on order
        for i, file in enumerate(files):
            if file and file.filename:
                if not allowed_file(file.filename):
                    return jsonify({
                        'success': False, 
                        'message': f'File {file.filename} has an invalid format. Allowed formats: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
                    })
                
                # Get file extension
                ext = os.path.splitext(file.filename)[1].lower()
                
                # Assign view type based on upload order
                if i < len(view_types):
                    new_filename = f"{view_types[i]}{ext}"
                    s3_file_path = f"{s3_folder_path}{new_filename}"
                    
                    try:
                        # Upload file to S3
                        s3_client.upload_fileobj(
                            file,
                            AWS_BUCKET_NAME,
                            s3_file_path,
                            ExtraArgs={'ContentType': file.content_type}
                        )
                        
                        uploaded_files.append(new_filename)
                        processed_views.append(view_types[i])
                        print(f"DEBUG: Saved file to S3 as {s3_file_path}")
                    
                    except ClientError as e:
                        print(f"DEBUG: S3 upload error: {str(e)}")
                        return jsonify({'success': False, 'message': f'Error uploading {new_filename} to S3'})
                else:
                    print(f"DEBUG: Skipping extra file {file.filename}, maximum 3 views supported")

        print(f"DEBUG: Successfully uploaded files: {uploaded_files}")

        # Process metrics
        try:
            metrics_data = json.loads(request.form.get('metrics', '{}'))
            print(f"Debug: metrics_data: {metrics_data}")

            feedback_data = {
                'interaction_type': 'upload',
                'metrics': metrics_data,
                'processed_views': processed_views,
                'visualization_type': '3D'
            }

            if current_user.is_authenticated:
                result = feedback_manager.create_feedback(
                    user_id=current_user.get_id(),
                    product_id=folder_name,
                    feedback_data=feedback_data
                )
                print(f"Debug: Feedback saved with result: {result}")
        
        except Exception as metrics_error:
            print(f"Debug: Error processing metrics: {str(metrics_error)}")
            traceback.print_exc()

        return jsonify({
            'success': True,
            'message': 'Files uploaded successfully',
            'uploadedFiles': uploaded_files,
            'redirect': url_for('view_folder', folder_name=folder_name)
        })
        
    except Exception as e:
        print(f"Debug: Upload error: {str(e)}")
        traceback.print_exc()
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
def process_folder(folder_name):
    print("Process folder: ", app.config['UPLOAD_FOLDER'])
    """Process images in a folder and generate 3D visualization"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    print(f"DEBUG: Processing folder: {folder_path}")
    
    # Look for specific view files
    view_files = {
        'front': os.path.join(folder_path, 'front.jpg'),
        'back': os.path.join(folder_path, 'back.jpg'),
        'top': os.path.join(folder_path, 'top.jpg')
    }
    
    # Check for other possible extensions
    for view in view_files.keys():
        if not os.path.exists(view_files[view]):
            for ext in ['.png', '.jpeg', '.gif']:
                alt_path = os.path.join(folder_path, f"{view}{ext}")
                if os.path.exists(alt_path):
                    view_files[view] = alt_path
                    break
    
    # Log found files
    print("DEBUG: Found view files:")
    for view, path in view_files.items():
        print(f"DEBUG: {view}: {'Found' if os.path.exists(path) else 'Not found'} - {path}")

    try:
        # Check if we have all three views
        if all(os.path.exists(path) for path in view_files.values()):
            print("DEBUG: Processing with all three views")
            figure = process_orthogonal_views(
                view_files['front'],
                view_files['back'],
                view_files['top']
            )
        else:
            # Fall back to single view if not all views are available
            print("DEBUG: Falling back to single view processing")
            front_path = view_files['front']
            if not os.path.exists(front_path):
                # If front view doesn't exist, use the first available view
                available_views = [path for path in view_files.values() if os.path.exists(path)]
                if not available_views:
                    print("DEBUG: No valid views found")
                    return jsonify({'success': False, 'message': 'No valid views found'})
                front_path = available_views[0]
            
            figure = process_image(front_path)
            
        if figure is None:
            print("DEBUG: Failed to generate plot data")
            return jsonify({'success': False, 'message': 'Failed to process images'})
        
        # Convert Plotly figure to JSON-serializable format and handle NumPy arrays
        try:
            # Custom conversion of any NumPy arrays in the figure data
            def convert_numpy(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {key: convert_numpy(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy(item) for item in list(obj)]
                return obj
            
            # First convert any NumPy arrays to Python lists
            plot_data = convert_numpy(figure)
            # Save plot data
            plot_file = os.path.join(folder_path, 'plot_data.json')
            with open(plot_file, 'w') as f:
                json.dump(plot_data, f, cls=plotly.utils.PlotlyJSONEncoder)
            print("DEBUG: Successfully saved plot data")
                
            # Return processing results with view status
            return jsonify({
                'success': True, 
                'plot': plot_data,
                'processedViews': {
                    'front': os.path.exists(view_files['front']),
                    'back': os.path.exists(view_files['back']),
                    'top': os.path.exists(view_files['top'])
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
        import traceback
        print("DEBUG: Full traceback:")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/get_feedback/<folder_name>')
def get_feedback(folder_name):
    """Get all feedback for a folder"""
    feedback_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'feedback.json')
    
    if os.path.exists(feedback_file):
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        return jsonify({'success': True, 'feedback': feedback_data})
    
    return jsonify({'success': True, 'feedback': []})

@app.route('/get-s3-data/<folder_name>')
@login_required
def get_s3_data(folder_name):
    try:
        s3_client = boto3.client('s3')
        
        # Generate a presigned URL that expires in 3600 seconds (1 hour)
        presigned_url = s3_client.generate_presigned_url('get_object',
            Params={
                'Bucket': AWS_BUCKET_NAME,
                'Key': f"{folder_name}/plot_data.json"
            },
            ExpiresIn=3600
        )
        
        return jsonify({
            'success': True,
            'url': presigned_url
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/feedback/<folder_name>', methods=['POST'])
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

if __name__ == '__main__':
    try:
        application.run(host='0.0.0.0', port=8000)
        # app.run(debug=True)
    except KeyboardInterrupt:
        print('Shutting down gracefully...')
        sys.exit(0)