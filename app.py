import os
import json
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from models.vision_processing import process_image, process_orthogonal_views
import plotly.utils

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    """Home page showing list of folders"""
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

    return render_template('folder.html', 
                         folder_name=folder_name,
                         images=images,
                         feedback=feedback_data)


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads to a folder with automatic view type naming"""
    if 'files[]' not in request.files:
        print("DEBUG: No files provided in request")
        return jsonify({'success': False, 'message': 'No files provided'})

    folder_name = request.form.get('folder_name', 'Untitled')
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    print(f"DEBUG: Processing uploads for folder: {folder_name}")

    # Create folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"DEBUG: Created new folder: {folder_path}")

    files = request.files.getlist('files[]')
    uploaded_files = []
    
    # Define view types in order of upload
    view_types = ['front', 'back', 'top']
    
    # Process each file and assign view type based on order
    for i, file in enumerate(files):
        if file and file.filename:
            # Get file extension
            ext = os.path.splitext(file.filename)[1].lower()
            
            # Assign view type based on upload order
            if i < len(view_types):
                new_filename = f"{view_types[i]}{ext}"
                file_path = os.path.join(folder_path, new_filename)
                file.save(file_path)
                uploaded_files.append(new_filename)
                print(f"DEBUG: Saved file as {new_filename}")
            else:
                print(f"DEBUG: Skipping extra file {file.filename}, maximum 3 views supported")

    print(f"DEBUG: Successfully uploaded files: {uploaded_files}")
    return jsonify({
        'success': True, 
        'message': 'Files uploaded successfully',
        'uploadedFiles': uploaded_files,
        'redirect': url_for('view_folder', folder_name=folder_name)
    })

@app.route('/process/<folder_name>')
def process_folder(folder_name):
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

# @app.route('/upload', methods=['POST'])
# def upload_files():
#     """Handle file uploads to a folder"""
#     if 'files[]' not in request.files:
#         return jsonify({'success': False, 'message': 'No files provided'})

#     folder_name = request.form.get('folder_name', 'Untitled')
#     folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)

#     # Create folder if it doesn't exist
#     if not os.path.exists(folder_path):
#         os.makedirs(folder_path)

#     files = request.files.getlist('files[]')
#     uploaded_files = []
    
#     for file in files:
#         if file and file.filename:
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(folder_path, filename)
#             file.save(file_path)
#             uploaded_files.append(filename)

#     return jsonify({'success': True, 
#                    'message': 'Files uploaded successfully',
#                    'redirect': url_for('view_folder', folder_name=folder_name)})

# @app.route('/process/<folder_name>')
# def process_folder(folder_name):
#     """Process images in a folder and generate 3D visualization"""
#     folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    
#     # Get first image in folder
#     images = [f for f in os.listdir(folder_path) 
#              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    
#     if not images:
#         return jsonify({'success': False, 'message': 'No images found'})

#     # Process the first image
#     image_path = os.path.join(folder_path, images[0])
#     try:
#         plot_data = process_image(image_path)
        
#         if plot_data is None:
#             return jsonify({'success': False, 'message': 'Failed to process image'})
            
#         # Save plot data to folder
#         plot_file = os.path.join(folder_path, 'plot_data.json')
#         with open(plot_file, 'w') as f:
#             json.dump(plot_data, f)
            
#         return jsonify({
#             'success': True, 
#             'plot': plot_data  # Now this is JSON-serializable
#         })
#     except Exception as e:
#         print(f"Processing error: {str(e)}")  # Add logging for debugging
#         return jsonify({'success': False, 'message': str(e)})

@app.route('/get_feedback/<folder_name>')
def get_feedback(folder_name):
    """Get all feedback for a folder"""
    feedback_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'feedback.json')
    
    if os.path.exists(feedback_file):
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        return jsonify({'success': True, 'feedback': feedback_data})
    
    return jsonify({'success': True, 'feedback': []})

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

if __name__ == '__main__':
    app.run(debug=True)