from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
from models.template_model import process_images

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['SECRET_KEY'] = 'your_secret_key_here'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_folders_and_images():
    folders = {}
    for folder in os.listdir(app.config['UPLOAD_FOLDER']):
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if os.path.isdir(folder_path):
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            folders[folder] = images
    return folders

@app.route('/')
def index():
    folders = get_folders_and_images()
    return render_template('index.html', folders=folders)

@app.route('/upload', methods=['POST'])
def upload_images():
    if 'files[]' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))

    files = request.files.getlist('files[]')
    folder_title = request.form.get('folder_title', 'Untitled')
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_title)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder_path, filename)
            file.save(file_path)

    flash('Files uploaded successfully', 'success')
    return redirect(url_for('index'))

@app.route('/delete/<folder>/<filename>', methods=['POST'])
def delete_image(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('Image deleted successfully', 'success')
    else:
        flash('Image not found', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)