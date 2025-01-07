from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import json
from models.vision_processing import process_image

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
    """Handle file uploads to a folder"""
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'})

    folder_name = request.form.get('folder_name', 'Untitled')
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)

    # Create folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    files = request.files.getlist('files[]')
    uploaded_files = []
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder_path, filename)
            file.save(file_path)
            uploaded_files.append(filename)

    return jsonify({'success': True, 
                   'message': 'Files uploaded successfully',
                   'redirect': url_for('view_folder', folder_name=folder_name)})

@app.route('/process/<folder_name>')
def process_folder(folder_name):
    """Process images in a folder and generate 3D visualization"""
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    
    # Get first image in folder
    images = [f for f in os.listdir(folder_path) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    
    if not images:
        return jsonify({'success': False, 'message': 'No images found'})

    # Process the first image
    image_path = os.path.join(folder_path, images[0])
    try:
        plot_data = process_image(image_path)
        
        if plot_data is None:
            return jsonify({'success': False, 'message': 'Failed to process image'})
            
        # Save plot data to folder
        plot_file = os.path.join(folder_path, 'plot_data.json')
        with open(plot_file, 'w') as f:
            json.dump(plot_data, f)
            
        return jsonify({
            'success': True, 
            'plot': plot_data  # Now this is JSON-serializable
        })
    except Exception as e:
        print(f"Processing error: {str(e)}")  # Add logging for debugging
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