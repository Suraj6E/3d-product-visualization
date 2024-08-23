from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from models.template_model import process_images  # Import your model processing function

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'


# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def upload_images():
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        
        image_paths = []
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_paths.append(filepath)
        
        # Process images with your model
        results = process_images(image_paths)  # Assume this returns a list of results

        # Zip the images and results together
        zipped_data = zip(image_paths, results)

        return render_template('index.html', zipped_data=zipped_data)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
