from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename

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
        return jsonify({'success': False, 'message': 'No file part'})

    files = request.files.getlist('files[]')
    folder_title = request.form.get('folder_title', 'Untitled')
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_title)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    uploaded_files = []
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder_path, filename)
            file.save(file_path)
            uploaded_files.append(filename)

    return jsonify({'success': True, 'message': 'Files uploaded successfully', 'files': uploaded_files})

@app.route('/get_images/<folder>')
def get_images(folder):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    if os.path.exists(folder_path):
        images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        return jsonify({'success': True, 'images': images})
    else:
        return jsonify({'success': False, 'message': 'Folder not found'})

@app.route('/get_image/<folder>/<filename>')
def get_image(folder, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder), filename)

@app.route('/delete_image/<folder>/<filename>', methods=['DELETE'])
def delete_image(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': True, 'message': 'Image deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Image not found'})

@app.route('/delete_folder/<folder>', methods=['DELETE'])
def delete_folder(folder):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        return jsonify({'success': True, 'message': 'Folder deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Folder not found'})


if __name__ == '__main__':
    app.run(debug=True)