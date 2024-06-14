import os
import logging
from flask import Flask, request, render_template, send_from_directory
from werkzeug.utils import secure_filename
from add1 import generate_subtitles  # Import your subtitle generation module
from os.path import basename  # Import basename function

import uuid

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'subtitles'

# Configure upload and output directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define custom filter to get basename
@app.template_filter('basename')
def get_basename(path):
    return basename(path)

# Home page with upload form
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    subtitle_path = None
    video_path = None
    subtitles = None  # Define subtitles variable

    if request.method == 'POST':
        logging.debug("File upload request received")
        if 'file' not in request.files:
            return render_template('index.html', message='No file part')
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', message='No selected file')
        if file:
            video_language = request.form['video_language']

            # Generate a unique filename
            filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(file_path)
            logging.debug(f"Saved file: {filename}")

            # Generate subtitles
            subtitle_filename = generate_subtitles(file_path, video_language)  # Pass the full path and language
            subtitle_path = os.path.join(app.config['OUTPUT_FOLDER'], subtitle_filename)
            logging.debug(f"Generated subtitle file: {subtitle_filename}")

            # Read generated subtitles
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                subtitles = f.read()

            video_path = file_path

    return render_template('index.html', subtitle_path=subtitle_path, video_path=video_path, subtitles=subtitles)

# Route for downloading modified subtitles
@app.route('/download_modified_subtitles/<filename>', methods=['POST'])
def download_modified_subtitles(filename):
    modified_subtitles = request.form['modified_subtitles']
    modified_subtitle_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    # Write modified subtitles to file
    with open(modified_subtitle_path, 'w', encoding='utf-8') as f:
        f.write(modified_subtitles)

    # Return the modified subtitle file for download
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# Serve uploaded videos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve generated subtitles
@app.route('/subtitles/<filename>')
def download_subtitles(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
